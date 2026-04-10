import json
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI
from app.core.config import settings
from app.schemas.decision_engine import (
    FailureContext, 
    LLMDecision, 
    DecisionRequest, 
    DecisionResponse,
    FailureType,
    RecoveryAction
)
from app.schemas.rag_memory import MemoryQuery, MemoryResult
from app.services.rag_memory import rag_memory_service


class DecisionEngine:
    """
    LLM-based decision engine for automated failure recovery in AI video pipeline
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """
        System prompt for the LLM decision engine
        """
        return """You are an AI Orchestration Decision Engine for a multi-stage video generation pipeline.

Your job is to:
1. Analyze pipeline state and failure context
2. Classify failure type
3. Decide optimal recovery strategy
4. Optimize for:
   - Output quality
   - Cost efficiency
   - Execution time

---

AVAILABLE ACTIONS:
1. RETRY (same config)
2. MODIFY_PROMPT
3. SWITCH_MODEL
4. ADJUST_PARAMETERS
5. SKIP_TASK
6. ESCALATE_RESOURCES

---

FAILURE TYPES:
- TIMEOUT
- API_ERROR
- LOW_QUALITY
- RESOURCE_EXHAUSTION

---

INSTRUCTIONS:
1. First classify failure type
2. Explain WHY failure occurred
3. Choose best recovery action
4. If MODIFY_PROMPT -> generate improved prompt
5. If SWITCH_MODEL -> suggest best alternative
6. If ADJUST_PARAMETERS -> specify changes
7. Return structured JSON

---

OUTPUT FORMAT:
{
  "failure_type": "...",
  "reason": "...",
  "action": "...",
  "new_prompt": "...",
  "new_model": "...",
  "parameter_changes": {...},
  "confidence": 0-1
}

IMPORTANT: Always return valid JSON. Be concise but thorough in your reasoning."""
    
    async def analyze_failure(self, context: FailureContext) -> LLMDecision:
        """
        Analyze failure and return recovery decision with RAG memory
        """
        if not self.client:
            # Fallback to rule-based decision if no LLM available
            return self._rule_based_decision(context)
        
        start_time = time.time()
        
        try:
            # Retrieve similar past failures using RAG memory
            similar_failures = await self._retrieve_similar_failures(context)
            
            # Construct the user prompt with context and historical data
            user_prompt = self._construct_user_prompt(context, similar_failures)
            
            # Call LLM with enhanced context
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500  # Increased limit for RAG context
            )
            
            # Parse response
            decision_json = response.choices[0].message.content.strip()
            
            # Ensure we have valid JSON
            if decision_json.startswith("```"):
                decision_json = decision_json.split("```")[1]
                if decision_json.startswith("json"):
                    decision_json = decision_json[4:].strip()
            
            decision_data = json.loads(decision_json)
            
            # Validate and create decision object
            decision = LLMDecision(**decision_data)
            
            # Store this decision in memory for future learning
            await self._store_decision_memory(context, decision, similar_failures)
            
            return decision
            
        except Exception as e:
            # Fallback to rule-based decision on LLM failure
            print(f"LLM decision failed: {e}, falling back to rule-based")
            return self._rule_based_decision(context)
    
    async def _retrieve_similar_failures(self, context: FailureContext) -> List[MemoryResult]:
        """
        Retrieve similar past failures using RAG memory
        """
        if not rag_memory_service.is_available():
            return []
        
        try:
            # Create memory query
            query = MemoryQuery(
                failure_type=context.failure_type if hasattr(context, 'failure_type') else FailureType.UNKNOWN,
                stage=context.stage,
                error_logs=context.error_logs,
                prompt_used=context.prompt_used,
                model_used=context.model_used,
                top_k=5,
                min_similarity=0.6,
                require_success=True
            )
            
            # Search for similar failures
            search_response = await rag_memory_service.search_similar_failures(query)
            
            return search_response.results
            
        except Exception as e:
            print(f"Failed to retrieve similar failures: {e}")
            return []
    
    def _construct_user_prompt(self, context: FailureContext, similar_failures: List[MemoryResult] = None) -> str:
        """
        Construct user prompt with failure context and historical data
        """
        prompt = f"""INPUT:
- Task: {context.task_name}
- Stage: {context.stage.value}
- Error Logs: {context.error_logs}
- Previous Attempts: {context.retry_count}
- Output Quality Score: {context.output_quality_score or 'N/A'}
- Cost So Far: ${context.cost_so_far:.4f}
- Model Used: {context.model_used}
- Prompt Used: {context.prompt_used}"""
        
        if context.additional_context:
            prompt += f"\n- Additional Context: {json.dumps(context.additional_context, indent=2)}"
        
        # Add RAG memory context
        if similar_failures:
            prompt += "\n\n--- SIMILAR PAST FAILURES AND RECOVERIES ---"
            for i, failure in enumerate(similar_failures, 1):
                prompt += f"\n\n{i}. Similar Failure (similarity: {failure.similarity_score:.2f}):\n"
                prompt += f"   - Error: {failure.memory.error_logs[:200]}...\n"
                prompt += f"   - Original Prompt: {failure.memory.prompt_used[:100]}...\n"
                prompt += f"   - Action Taken: {failure.memory.action_taken.value}\n"
                prompt += f"   - Success: {failure.memory.success}\n"
                prompt += f"   - Quality Score: {failure.memory.final_quality_score or 'N/A'}\n"
                prompt += f"   - Retry Count: {failure.memory.retry_count}\n"
                
                if failure.memory.new_prompt:
                    prompt += f"   - New Prompt: {failure.memory.new_prompt[:100]}...\n"
                if failure.memory.new_model:
                    prompt += f"   - New Model: {failure.memory.new_model}\n"
                if failure.memory.parameter_changes:
                    prompt += f"   - Parameter Changes: {json.dumps(failure.memory.parameter_changes)}\n"
                
                prompt += f"   - Relevance: {failure.relevance_explanation}"
        
        prompt += "\n\n--- DECISION GUIDANCE ---\n"
        prompt += "If similar successful recoveries exist, strongly bias toward those strategies. "
        prompt += "If similar failures show consistent patterns, learn from them. "
        prompt += "Consider the success rates and quality scores of past actions."
        
        return prompt
    
    async def _store_decision_memory(self, context: FailureContext, decision: LLMDecision, similar_failures: List[MemoryResult]):
        """
        Store the decision and its outcome in memory for future learning
        """
        # This will be called after the decision is executed and we know the outcome
        # For now, we'll store the decision and update it later with results
        pass
    
    def update_decision_outcome(self, context: FailureContext, decision: LLMDecision, success: bool, quality_score: float = None):
        """
        Update decision memory with actual outcome
        """
        # This will be called after the recovery action is executed
        # Implementation depends on how we track the execution results
        pass
    
    def _rule_based_decision(self, context: FailureContext) -> LLMDecision:
        """
        Rule-based fallback decision making
        """
        error_logs_lower = context.error_logs.lower()
        
        # Classify failure type
        if "timeout" in error_logs_lower or "time limit" in error_logs_lower:
            failure_type = FailureType.TIMEOUT
            if context.retry_count >= 2:
                action = RecoveryAction.ESCALATE_RESOURCES
                reason = "Multiple timeouts detected, escalating resources"
            else:
                action = RecoveryAction.RETRY
                reason = "Timeout detected, retrying"
        
        elif "api" in error_logs_lower or "http" in error_logs_lower or "connection" in error_logs_lower:
            failure_type = FailureType.API_ERROR
            if context.retry_count >= 3:
                action = RecoveryAction.SWITCH_MODEL
                reason = "Multiple API errors, switching model"
            else:
                action = RecoveryAction.RETRY
                reason = "API error detected, retrying"
        
        elif "quality" in error_logs_lower or "low score" in error_logs_lower:
            failure_type = FailureType.LOW_QUALITY
            action = RecoveryAction.MODIFY_PROMPT
            reason = "Low quality detected, modifying prompt"
        
        elif "memory" in error_logs_lower or "resource" in error_logs_lower or "gpu" in error_logs_lower:
            failure_type = FailureType.RESOURCE_EXHAUSTION
            action = RecoveryAction.ESCALATE_RESOURCES
            reason = "Resource exhaustion detected, escalating resources"
        
        else:
            failure_type = FailureType.UNKNOWN
            action = RecoveryAction.RETRY
            reason = "Unknown error, retrying"
        
        # Generate specific changes based on action
        new_prompt = None
        new_model = None
        parameter_changes = None
        
        if action == RecoveryAction.MODIFY_PROMPT:
            new_prompt = self._improve_prompt(context.prompt_used)
        elif action == RecoveryAction.SWITCH_MODEL:
            new_model = self._suggest_alternative_model(context.model_used)
        elif action == RecoveryAction.ESCALATE_RESOURCES:
            parameter_changes = {"timeout": 300, "memory": "8GB"}
        
        return LLMDecision(
            failure_type=failure_type,
            reason=reason,
            action=action,
            new_prompt=new_prompt,
            new_model=new_model,
            parameter_changes=parameter_changes,
            confidence=0.7  # Lower confidence for rule-based
        )
    
    def _improve_prompt(self, original_prompt: str) -> str:
        """
        Improve prompt for better quality
        """
        improvements = [
            "high quality",
            "detailed",
            "professional",
            "4K resolution"
        ]
        
        if not any(imp in original_prompt.lower() for imp in improvements):
            return f"{original_prompt}, high quality, detailed, professional"
        return original_prompt
    
    def _suggest_alternative_model(self, current_model: str) -> str:
        """
        Suggest alternative model
        """
        model_alternatives = {
            "gpt-4": "gpt-3.5-turbo",
            "dall-e-3": "dall-e-2",
            "stable-diffusion-xl": "stable-diffusion-v1-5"
        }
        return model_alternatives.get(current_model, "fallback-model")
    
    def is_available(self) -> bool:
        """
        Check if LLM decision engine is available
        """
        return self.client is not None and settings.openai_api_key is not None


# Singleton instance
decision_engine = DecisionEngine()
