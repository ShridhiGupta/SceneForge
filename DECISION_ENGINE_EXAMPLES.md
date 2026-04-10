# LLM Decision Engine Integration Guide

## Overview

This document explains how to use the LLM-based decision engine for automated failure recovery in your AI video pipeline.

## Architecture

```
Task Failure -> Decision Engine -> LLM Analysis -> Recovery Action -> Execution
```

### Components

1. **Decision Engine** (`app/services/decision_engine.py`)
   - Analyzes failures using LLM
   - Returns structured recovery decisions
   - Falls back to rule-based logic if LLM unavailable

2. **Decision Executor** (`app/services/decision_executor.py`)
   - Executes LLM decisions
   - Applies changes to database and services
   - Handles all recovery actions

3. **Task Decorator** (`app/utils/task_utils.py`)
   - Automatic failure handling for Celery tasks
   - Context extraction and decision triggering
   - Retry logic integration

## Usage Examples

### 1. Basic Integration

```python
from app.utils.task_utils import with_failure_handling
from app.schemas.decision_engine import PipelineStage

@celery_app.task(bind=True, max_retries=5)
@with_failure_handling(PipelineStage.IMAGE)
def generate_image(self, scene_id: int):
    # Your task logic here
    pass
```

### 2. Manual Decision Engine Usage

```python
from app.services.decision_engine import decision_engine
from app.schemas.decision_engine import FailureContext, PipelineStage

# Create failure context
context = FailureContext(
    task_name="generate_image",
    stage=PipelineStage.IMAGE,
    error_logs="API timeout after 30 seconds",
    retry_count=2,
    output_quality_score=0.3,
    cost_so_far=0.15,
    model_used="stable-diffusion-xl",
    prompt_used="A beautiful sunset over mountains",
    additional_context={"scene_id": 123}
)

# Get decision
decision = await decision_engine.analyze_failure(context)
print(f"Action: {decision.action}")
print(f"Reason: {decision.reason}")
```

### 3. Custom Decision Execution

```python
from app.services.decision_executor import decision_executor

result = await decision_executor.handle_failure(context)
if result["success"]:
    print(f"Executed: {result['execution_result']['action']}")
```

## Decision Types

### Recovery Actions

1. **RETRY** - Simple retry with same configuration
2. **MODIFY_PROMPT** - Improve prompt for better quality
3. **SWITCH_MODEL** - Use alternative AI model
4. **ADJUST_PARAMETERS** - Modify task parameters
5. **SKIP_TASK** - Skip failed task
6. **ESCALATE_RESOURCES** - Increase resource limits

### Failure Types

1. **TIMEOUT** - Task exceeded time limits
2. **API_ERROR** - External API failures
3. **LOW_QUALITY** - Poor output quality
4. **RESOURCE_EXHAUSTION** - Memory/CPU/GPU limits

## Configuration

Add to your `.env` file:

```env
# OpenAI API Key for decision engine
OPENAI_API_KEY=your_openai_api_key

# Decision Engine Settings
DECISION_ENGINE_ENABLED=true
DECISION_ENGINE_MIN_RETRIES=1
DECISION_ENGINE_CONFIDENCE_THRESHOLD=0.7
```

## Database Schema Updates

The following fields were added to support the decision engine:

### Scene Model
- `retry_count` - Number of retry attempts
- `generation_cost` - Total cost for this scene
- `model_used` - AI model used for generation

### TaskStatus Enum
- `SKIPPED` - Task was skipped by decision engine

## Example Scenarios

### Scenario 1: API Timeout

**Input:**
```
- Error: "API timeout after 30 seconds"
- Retry count: 1
- Model: "stable-diffusion-xl"
```

**LLM Decision:**
```json
{
  "failure_type": "timeout",
  "reason": "API timeout detected, likely due to high server load",
  "action": "retry",
  "confidence": 0.8
}
```

### Scenario 2: Low Quality Output

**Input:**
```
- Error: "Quality score 0.2 below threshold 0.5"
- Quality score: 0.2
- Prompt: "A car"
```

**LLM Decision:**
```json
{
  "failure_type": "low_quality",
  "reason": "Prompt too simple, needs more detail for better quality",
  "action": "modify_prompt",
  "new_prompt": "A car, high quality, detailed, professional, 4K resolution",
  "confidence": 0.9
}
```

### Scenario 3: Multiple API Failures

**Input:**
```
- Error: "HTTP 503 Service Unavailable"
- Retry count: 3
- Model: "dall-e-3"
```

**LLM Decision:**
```json
{
  "failure_type": "api_error",
  "reason": "Multiple API failures, service likely overloaded",
  "action": "switch_model",
  "new_model": "dall-e-2",
  "confidence": 0.85
}
```

## Monitoring and Logging

The decision engine logs all decisions and executions:

```python
import logging

logger = logging.getLogger(__name__)

# Decision logs include:
# - LLM decision details
# - Execution results
# - Confidence scores
# - Processing time
```

## Testing

### Unit Tests

```python
import pytest
from app.services.decision_engine import DecisionEngine
from app.schemas.decision_engine import FailureContext, PipelineStage

@pytest.mark.asyncio
async def test_decision_engine_timeout():
    engine = DecisionEngine()
    context = FailureContext(
        task_name="test_task",
        stage=PipelineStage.IMAGE,
        error_logs="timeout after 30 seconds",
        retry_count=1,
        model_used="test-model",
        prompt_used="test prompt"
    )
    
    decision = await engine.analyze_failure(context)
    assert decision.action == "retry"
    assert decision.failure_type == "timeout"
```

### Integration Tests

```python
def test_task_failure_handling():
    # Test the full pipeline
    # Task failure -> Decision engine -> Execution
    pass
```

## Production Considerations

1. **Rate Limiting** - Monitor OpenAI API usage
2. **Cost Tracking** - Track decision engine costs
3. **Fallback Logic** - Ensure graceful degradation
4. **Monitoring** - Alert on decision engine failures
5. **A/B Testing** - Compare with rule-based approach

## Troubleshooting

### Common Issues

1. **OpenAI API Key Missing**
   ```
   Solution: Set OPENAI_API_KEY in environment
   ```

2. **Decision Engine Disabled**
   ```
   Solution: Set DECISION_ENGINE_ENABLED=true
   ```

3. **Invalid JSON Response**
   ```
   Solution: Check LLM response format, fallback to rule-based
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("app.services.decision_engine").setLevel(logging.DEBUG)
```

## Performance

- **Average decision time**: ~2-3 seconds
- **OpenAI API cost**: ~$0.002 per decision
- **Fallback time**: <100ms (rule-based)

## Future Enhancements

1. **Learning System** - Improve decisions from historical data
2. **Custom Models** - Fine-tuned models for specific domains
3. **Multi-LLM** - Compare decisions from multiple LLMs
4. **Cost Optimization** - Balance quality vs cost automatically
