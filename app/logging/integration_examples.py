"""
Integration examples for structured logging and metrics tracking
"""

# Example 1: Integrating with existing agents
from app.logging.agent_metrics import track_agent_metrics, track_image_generation_metrics
from app.logging.metrics_tracker import metrics_tracker

class ImageGenerationAgent:
    def __init__(self):
        self.name = "image_generation_agent"
    
    @track_agent_metrics("image_generation")
    async def generate_image(self, scene):
        # This will automatically track:
        # - Task start/end
        # - Execution time
        # - Success/failure
        # - Cost
        # - Quality before/after
        
        task_id = metrics_tracker.start_task(
            task_name="image_generation",
            video_id=scene.video_id,
            scene_id=scene.id,
            model_used=scene.model_used
        )
        
        try:
            # Your existing image generation logic
            result = await self._generate_image_logic(scene)
            
            # Track quality improvement
            if hasattr(scene, 'quality_before') and hasattr(result, 'quality_score'):
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=True,
                    cost=result.cost,
                    quality_before=scene.quality_before,
                    quality_after=result.quality_score,
                    action_taken="image_generated"
                )
            
            return result
            
        except Exception as e:
            # Track failure
            metrics_tracker.log_failure(
                task_id=task_id,
                failure_type="generation_error",
                error_message=str(e)
            )
            metrics_tracker.complete_task(
                task_id=task_id,
                success=False,
                error_message=str(e)
            )
            raise


# Example 2: Manual metrics tracking with context manager
from app.logging.agent_metrics import MetricsContext

async def manual_tracking_example():
    """Example of manual metrics tracking"""
    
    with MetricsContext("custom_task", 
                       video_id=123, 
                       custom_param="value") as ctx:
        
        # Your custom logic here
        result = await some_async_operation()
        
        # Log quality improvement
        ctx.log_quality_before_after(quality_before=0.3, quality_after=0.8)
        
        # Log cost
        ctx.log_cost(cost=0.05)
        
        return result


# Example 3: Decision agent integration
from app.logging.agent_metrics import track_decision_metrics

class DecisionAgent:
    @track_decision_metrics()
    async def make_decision(self, failure_context):
        # This will automatically track:
        # - Decision type
        # - Action taken
        # - Confidence
        # - RAG usage
        # - Similar failures found
        
        # Your existing decision logic
        decision = await self._analyze_failure(failure_context)
        
        # Log the decision
        metrics_tracker.log_decision(
            task_id=failure_context.get('task_id'),
            decision_type="failure_recovery",
            action=decision.action.value,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            rag_context_used=len(failure_context.get('similar_failures', [])) > 0,
            similar_failures_found=len(failure_context.get('similar_failures', [])),
            cost_impact=decision.estimated_cost_impact
        )
        
        return decision


# Example 4: Quality evaluation integration
from app.logging.agent_metrics import track_quality_metrics

class QualityEvaluationAgent:
    @track_quality_metrics()
    async def evaluate_quality(self, image_path, prompt):
        # This will automatically track:
        # - CLIP score
        # - LLM score
        # - Combined score
        # - Evaluation time
        # - Threshold pass/fail
        
        # Your existing quality evaluation logic
        result = await self._evaluate_image_quality(image_path, prompt)
        
        # Log quality evaluation
        metrics_tracker.log_quality_evaluation(
            task_id=self.current_task_id,
            clip_score=result.clip_score,
            llm_score=result.llm_score,
            combined_score=result.quality_score,
            passes_threshold=result.passes_threshold,
            evaluation_time_ms=result.evaluation_time_ms,
            model_used="gpt-4-vision"
        )
        
        return result


# Example 5: Retry tracking
from app.logging.agent_metrics import track_retry_metrics

class RetryHandler:
    @track_retry_metrics()
    async def handle_retry(self, task, retry_count):
        # This will automatically track:
        # - Retry attempts
        # - Original error
        # - Retry success/failure
        
        # Your existing retry logic
        try:
            result = await self._execute_retry(task)
            
            # Log successful retry
            metrics_tracker.log_retry(
                task_id=task.id,
                retry_count=retry_count,
                original_error=task.last_error
            )
            
            return result
            
        except Exception as e:
            # Log failed retry
            metrics_tracker.log_failure(
                task_id=task.id,
                failure_type="retry_failed",
                error_message=str(e)
            )
            raise


# Example 6: Cost optimization tracking
from app.logging.agent_metrics import track_cost_optimization_metrics

class CostOptimizationAgent:
    @track_cost_optimization_metrics()
    async def optimize_costs(self, state):
        # This will automatically track:
        # - Total cost
        # - Budget limit
        # - Potential savings
        # - Optimization recommendations
        
        # Your existing cost optimization logic
        result = await self._analyze_costs(state)
        
        # Log cost optimization
        metrics_tracker.complete_task(
            task_id=self.current_task_id,
            success=True,
            cost=result.potential_savings,
            action_taken=f"optimization_applied_{len(result.optimization_suggestions)}"
        )
        
        return result


# Example 7: JSON log output format
"""
Example JSON log outputs:

1. Task Start:
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "event_type": "task_start",
  "request_id": "uuid-1234",
  "task_name": "image_generation",
  "task_id": "uuid-5678",
  "video_id": 123,
  "scene_id": 1,
  "agent_name": "image_generation_agent"
}

2. Task Success:
{
  "timestamp": "2024-01-15T10:30:05.000Z",
  "event_type": "task_success",
  "request_id": "uuid-1234",
  "task_name": "image_generation",
  "execution_time_ms": 5000,
  "cost": 0.02,
  "quality_before": 0.3,
  "quality_after": 0.8,
  "action_taken": "image_generated",
  "task_id": "uuid-5678"
}

3. Decision Log:
{
  "timestamp": "2024-01-15T10:30:10.000Z",
  "event_type": "decision",
  "request_id": "uuid-1234",
  "decision_type": "failure_recovery",
  "action": "modify_prompt",
  "confidence": 0.85,
  "reasoning": "Low quality detected, improving prompt",
  "rag_context_used": true,
  "similar_failures_found": 3,
  "cost_impact": 0.0,
  "task_id": "uuid-5678"
}

4. Quality Metrics:
{
  "timestamp": "2024-01-15T10:30:15.000Z",
  "event_type": "quality_metrics",
  "request_id": "uuid-1234",
  "quality_before": 0.3,
  "quality_after": 0.8,
  "improvement": 0.5,
  "task_id": "uuid-5678"
}

5. Cost Metrics:
{
  "timestamp": "2024-01-15T10:30:20.000Z",
  "event_type": "cost_metrics",
  "request_id": "uuid-1234",
  "cost": 0.02,
  "task_name": "image_generation",
  "task_id": "uuid-5678"
}

6. Retry Log:
{
  "timestamp": "2024-01-15T10:30:25.000Z",
  "event_type": "retry",
  "request_id": "uuid-1234",
  "task_name": "image_generation",
  "retry_count": 2,
  "original_error": "API timeout",
  "task_id": "uuid-5678"
}
"""


# Example 8: Log analysis script
"""
#!/usr/bin/env python3
# Example script to analyze logs and prove system improvements

from app.logging.log_analyzer import LogAnalyzer
import json

def analyze_system_improvements():
    # Load logs from file
    analyzer = LogAnalyzer()
    analyzer.load_logs_from_file("pipeline_logs.json")
    
    # Generate comprehensive report
    report = analyzer.generate_report()
    
    # Extract key improvement metrics
    improvement_metrics = report["improvement_metrics"]["improvement_scores"]
    
    print("=== SYSTEM IMPROVEMENT REPORT ===")
    print(f"Overall Improvement Score: {improvement_metrics['overall_improvement_score']:.1f}/100")
    print(f"Quality Improvement Score: {improvement_metrics['quality_improvement_score']:.1f}/100")
    print(f"Failure Reduction Score: {improvement_metrics['failure_reduction_score']:.1f}/100")
    print(f"Cost Efficiency Score: {improvement_metrics['cost_efficiency_score']:.1f}/100")
    print(f"Time Efficiency Score: {improvement_metrics['time_efficiency_score']:.1f}/100")
    
    # Detailed analysis
    detailed = report["improvement_metrics"]["detailed_analysis"]
    
    print("\n=== QUALITY IMPROVEMENTS ===")
    quality = detailed["quality"]
    print(f"Average Quality Before: {quality['average_quality_before']:.3f}")
    print(f"Average Quality After: {quality['average_quality_after']:.3f}")
    print(f"Average Improvement: {quality['average_improvement']:.3f}")
    print(f"Improvement Rate: {quality['improvement_rate']:.1%}")
    
    print("\n=== FAILURE ANALYSIS ===")
    failures = detailed["failures"]
    print(f"Total Failures: {failures['total_failures']}")
    print(f"Failure Types: {failures['failure_types']}")
    
    print("\n=== DECISION EFFECTIVENESS ===")
    decisions = detailed["actions"]
    print(f"Total Decisions: {decisions['total_decisions']}")
    print(f"Action Effectiveness: {decisions['action_effectiveness']}")
    
    print("\n=== RECOMMENDATIONS ===")
    for rec in report["recommendations"]:
        print(f"- {rec}")
    
    # Export for further analysis
    with open("improvement_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nDetailed report saved to: improvement_report.json")

if __name__ == "__main__":
    analyze_system_improvements()
"""


# Example 9: API integration for real-time monitoring
"""
# Example API calls to get metrics:

# Get overall metrics
curl -X GET "http://localhost:8000/api/v1/metrics/overview"

# Get quality metrics
curl -X GET "http://localhost:8000/api/v1/metrics/quality"

# Get failure analysis
curl -X GET "http://localhost:8000/api/v1/metrics/failures"

# Get decision metrics
curl -X GET "http://localhost:8000/api/v1/metrics/decisions"

# Get cost analysis
curl -X GET "http://localhost:8000/api/v1/metrics/costs"

# Get performance metrics
curl -X GET "http://localhost:8000/api/v1/metrics/performance"

# Get improvement metrics
curl -X GET "http://localhost:8000/api/v1/metrics/improvement"

# Get dashboard data
curl -X GET "http://localhost:8000/api/v1/metrics/dashboard"

# Export all metrics
curl -X GET "http://localhost:8000/api/v1/metrics/export"

# Analyze log files
curl -X POST "http://localhost:8000/api/v1/metrics/analyze-logs" \
  -F "file=@pipeline_logs.json"
"""


# Example 10: Production deployment configuration
"""
# Docker configuration for structured logging
version: '3.8'
services:
  app:
    build: .
    environment:
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - METRICS_ENABLED=true
    volumes:
      - ./logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"

  # Optional: Log aggregation with ELK stack
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch
"""
