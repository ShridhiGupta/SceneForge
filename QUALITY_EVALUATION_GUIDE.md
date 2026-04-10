# Quality Evaluation System Guide

## Overview

This document explains how to use the automatic quality evaluation system for your AI video pipeline. The system uses CLIP and LLM-based evaluation to ensure generated images meet quality standards.

## Architecture

```
Image Generation -> Quality Evaluation -> Score Calculation -> Threshold Check -> Decision Engine
```

### Components

1. **CLIP Evaluator** (`app/services/clip_evaluation.py`)
   - Text-image similarity scoring
   - Fast, lightweight evaluation
   - OpenAI CLIP model integration

2. **LLM Evaluator** (`app/services/llm_evaluation.py`)
   - Vision model evaluation
   - Detailed quality assessment
   - GPT-4 Vision integration

3. **Quality Evaluator** (`app/services/quality_evaluation.py`)
   - Combined scoring system
   - Threshold-based failure triggering
   - Decision engine integration

## Setup Instructions

### 1. Install Dependencies

```bash
pip install torch clip-by-openai transformers
```

### 2. Database Migration

```bash
python quality_evaluation_migration.py
```

### 3. Environment Configuration

Add to your `.env` file:

```env
# OpenAI API Key (required for LLM evaluation)
OPENAI_API_KEY=your_openai_api_key

# Quality Evaluation Settings
QUALITY_EVALUATION_ENABLED=true
QUALITY_THRESHOLD=0.5
CLIP_WEIGHT=0.6
LLM_WEIGHT=0.4
```

## Usage Examples

### 1. Automatic Integration (Recommended)

The quality evaluation is automatically integrated with your image generation tasks:

```python
@celery_app.task(bind=True, max_retries=5)
@with_failure_handling(PipelineStage.IMAGE)
def generate_single_image(self, scene_id: int):
    # Your existing task logic
    # Quality evaluation happens automatically after image generation
```

### 2. Manual Quality Evaluation

```python
from app.services.quality_evaluation import quality_evaluator
from app.schemas.quality_evaluation import QualityEvaluationRequest, EvaluationMethod

request = QualityEvaluationRequest(
    image_path="uploads/images/test.png",
    prompt="A beautiful sunset over mountains",
    model_used="stable-diffusion-xl",
    methods=[EvaluationMethod.COMBINED],
    min_quality_threshold=0.5
)

response = await quality_evaluator.evaluate_quality(request)
print(f"Quality Score: {response.result.final_score:.2f}")
print(f"Passes Threshold: {response.result.passes_threshold}")
```

### 3. Quick Evaluation

```python
# Synchronous quick evaluation for testing
result = quality_evaluator.quick_evaluate(
    image_path="uploads/images/test.png",
    prompt="A beautiful sunset",
    threshold=0.5
)

print(f"Score: {result.final_score:.2f}")
print(f"Quality: {result.quality_threshold}")
```

## API Endpoints

### Evaluate Image Quality

```bash
curl -X POST "http://localhost:8000/api/v1/quality-evaluation/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "uploads/images/test.png",
    "prompt": "A beautiful sunset over mountains",
    "model_used": "stable-diffusion-xl",
    "methods": ["combined"],
    "min_quality_threshold": 0.5
  }'
```

### Evaluate Uploaded Image

```bash
curl -X POST "http://localhost:8000/api/v1/quality-evaluation/evaluate-upload" \
  -F "file=@test.png" \
  -F "prompt=A beautiful sunset" \
  -F "threshold=0.5"
```

### Quick Evaluation

```bash
curl -X GET "http://localhost:8000/api/v1/quality-evaluation/quick-evaluate?image_path=test.png&prompt=A beautiful sunset&threshold=0.5"
```

### System Status

```bash
curl -X GET "http://localhost:8000/api/v1/quality-evaluation/system-status"
```

### Test Comparison

```bash
curl -X POST "http://localhost:8000/api/v1/quality-evaluation/test-comparison?image_path=test.png&prompt=A beautiful sunset&threshold=0.5"
```

## Quality Scoring

### CLIP Score (0-1)

- **Text-Image Similarity**: How well the image matches the prompt
- **Speed**: Fast evaluation (~100ms)
- **Use Case**: Initial quality screening

### LLM Score (0-1)

- **Visual Quality**: Aesthetics, composition, clarity
- **Prompt Matching**: Detailed interpretation analysis
- **Speed**: Slower evaluation (~2-3 seconds)
- **Use Case**: Final quality assessment

### Combined Score

```
Final Score = (CLIP Score × CLIP Weight) + (LLM Score × LLM Weight)
```

Default weights:
- CLIP: 60%
- LLM: 40%

### Quality Thresholds

| Score Range | Quality Level | Action |
|-------------|---------------|--------|
| 0.85 - 1.0  | Very High     | Accept |
| 0.70 - 0.85  | High          | Accept |
| 0.50 - 0.70  | Medium        | Accept |
| 0.30 - 0.50  | Low           | Trigger Decision Engine |
| 0.00 - 0.30  | Very Low      | Trigger Decision Engine |

## Decision Engine Integration

When quality score falls below threshold:

1. **Failure Classification**: `LOW_QUALITY`
2. **Context Extraction**: Image path, prompt, quality score
3. **Decision Making**: LLM decides on recovery action
4. **Common Actions**:
   - `modify_prompt`: Improve prompt for better quality
   - `retry`: Try generation again
   - `switch_model`: Use different AI model

### Example Decision Flow

```
Quality Score: 0.35 (below 0.5 threshold)
    |
    v
Decision Engine: "Low quality detected"
    |
    v
LLM Analysis: "Prompt too simple, needs more detail"
    |
    v
Action: MODIFY_PROMPT
    |
    v
New Prompt: "A beautiful sunset, high quality, detailed, professional"
```

## Performance Considerations

### Evaluation Speed

- **CLIP Only**: ~100ms
- **LLM Only**: ~2-3 seconds
- **Combined**: ~2-3 seconds
- **Quick Mode**: ~100ms (CLIP only for clear cases)

### Cost Optimization

- **CLIP**: Free (local model)
- **LLM**: ~$0.01 per evaluation (GPT-4 Vision)
- **Strategy**: Use CLIP for initial screening, LLM for ambiguous cases

### Resource Usage

- **Memory**: ~2GB for CLIP model
- **GPU**: Optional, but recommended for CLIP
- **CPU**: Sufficient for LLM evaluation

## Configuration Options

### Threshold Settings

```python
# In your task or configuration
QUALITY_THRESHOLD = 0.5  # Minimum acceptable quality
CLIP_WEIGHT = 0.6        # Weight for CLIP score
LLM_WEIGHT = 0.4         # Weight for LLM score
```

### Evaluation Methods

```python
from app.schemas.quality_evaluation import EvaluationMethod

# Available methods
methods = [
    EvaluationMethod.CLIP_SCORE,      # CLIP only
    EvaluationMethod.LLM_EVALUATION,  # LLM only
    EvaluationMethod.COMBINED         # Both methods
]
```

### Custom Weights

```python
request = QualityEvaluationRequest(
    image_path="test.png",
    prompt="A beautiful sunset",
    clip_weight=0.7,  # More weight to CLIP
    llm_weight=0.3    # Less weight to LLM
)
```

## Monitoring and Analytics

### Quality Metrics

```python
# Get quality statistics
stats = await quality_evaluator.get_quality_metrics(days=30)
print(f"Average Score: {stats.average_score:.2f}")
print(f"Failure Rate: {stats.failure_rate:.2%}")
```

### System Health

```bash
curl -X GET "http://localhost:8000/api/v1/quality-evaluation/health"
```

### Performance Tracking

- Average evaluation time
- Success/failure rates
- Score distribution
- Method performance

## Troubleshooting

### Common Issues

1. **CLIP Model Loading Error**
   ```bash
   pip install torch clip-by-openai
   # Ensure sufficient RAM/VRAM
   ```

2. **LLM API Rate Limits**
   - Implement rate limiting
   - Use quick evaluation mode
   - Cache evaluation results

3. **Low Quality Scores**
   - Check prompt quality
   - Verify image generation model
   - Adjust threshold if too strict

4. **Slow Evaluation**
   - Use CLIP-only mode for speed
   - Implement GPU acceleration
   - Use quick evaluation

### Debug Mode

```python
import logging
logging.getLogger("app.services.quality_evaluation").setLevel(logging.DEBUG)
```

## Best Practices

### 1. Prompt Engineering

- Use detailed, specific prompts
- Include quality descriptors
- Test multiple prompt variations

### 2. Threshold Tuning

- Start with 0.5 threshold
- Adjust based on your quality requirements
- Consider model capabilities

### 3. Cost Management

- Use CLIP for initial screening
- Implement evaluation caching
- Monitor API usage

### 4. Performance Optimization

- Use GPU for CLIP evaluation
- Implement batch processing
- Cache frequent evaluations

## Advanced Features

### 1. Custom Evaluation Logic

```python
class CustomQualityEvaluator(QualityEvaluator):
    def custom_evaluation_logic(self, image_path, prompt):
        # Add your custom evaluation logic
        pass
```

### 2. Batch Evaluation

```python
# Evaluate multiple images
results = quality_evaluator.batch_evaluate(
    image_paths=["img1.png", "img2.png"],
    prompts=["prompt1", "prompt2"]
)
```

### 3. Evaluation Caching

```python
# Cache evaluation results
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_evaluation(image_hash, prompt):
    return quality_evaluator.quick_evaluate(image_path, prompt)
```

## Integration Examples

### 1. Web Interface Integration

```javascript
// Frontend quality check
async function checkImageQuality(imagePath, prompt) {
    const response = await fetch('/api/v1/quality-evaluation/quick-evaluate?' + 
        new URLSearchParams({
            image_path: imagePath,
            prompt: prompt,
            threshold: 0.5
        }));
    
    const result = await response.json();
    return result.result;
}
```

### 2. Pipeline Integration

```python
# In your image generation service
def generate_with_quality_check(prompt, output_path):
    # Generate image
    generate_image(prompt, output_path)
    
    # Check quality
    quality_result = quality_evaluator.quick_evaluate(output_path, prompt)
    
    if not quality_result.passes_threshold:
        # Trigger regeneration
        raise Exception(f"Low quality: {quality_result.final_score:.2f}")
    
    return output_path
```

### 3. Monitoring Integration

```python
# Quality monitoring dashboard
def get_quality_dashboard():
    return {
        "total_evaluations": get_total_evaluations(),
        "average_quality": get_average_quality(),
        "failure_rate": get_failure_rate(),
        "recent_failures": get_recent_quality_failures()
    }
```

The quality evaluation system provides automated, intelligent quality assessment for your AI video pipeline, ensuring consistent output quality while integrating seamlessly with your existing decision engine and RAG memory systems.
