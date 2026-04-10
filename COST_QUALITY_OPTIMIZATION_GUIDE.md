# Cost-Quality Optimization Layer Guide

## Overview

This cost-quality optimization layer intelligently balances cost and quality using a utility function approach. The system automatically selects the most cost-effective model that meets quality requirements, and switches to more expensive models only when necessary.

## Core Concept: Utility Function

The system uses a utility function to evaluate model choices:

```
U = alpha * quality - beta * cost
```

Where:
- **alpha**: Quality weight (0-1)
- **beta**: Cost weight (0-1)
- **quality**: Expected model quality (0-1)
- **cost**: Cost per call in USD

## Model Profiles

### Image Generation Models

| Model | Tier | Cost/Call | Quality | Speed | Reliability |
|-------|------|-----------|---------|-------|-------------|
| stable-diffusion-v1-5 | Basic | $0.01 | 0.65 | Fast | 95% |
| stable-diffusion-xl | Standard | $0.02 | 0.78 | Medium | 92% |
| dall-e-3 | Premium | $0.04 | 0.85 | Slow | 98% |
| midjourney | Ultra | $0.05 | 0.92 | Very Slow | 90% |

### Text Generation Models

| Model | Tier | Cost/Call | Quality | Speed | Context |
|-------|------|-----------|---------|-------|---------|
| gpt-3.5-turbo | Basic | $0.002 | 0.70 | Fast | 4K |
| gpt-4 | Standard | $0.03 | 0.85 | Medium | 8K |
| gpt-4-turbo | Premium | $0.01 | 0.88 | Fast | 128K |
| claude-3-opus | Ultra | $0.075 | 0.91 | Medium | 200K |

## Optimization Strategies

### 1. Minimize Cost
- **Goal**: Use cheapest models that meet minimum quality
- **Use Case**: Large-scale processing with budget constraints
- **Behavior**: Prioritizes cost over quality

### 2. Maximize Quality
- **Goal**: Use highest quality models regardless of cost
- **Use Case**: Critical tasks where quality is paramount
- **Behavior**: Prioritizes quality over cost

### 3. Balanced
- **Goal**: Balance cost and quality equally
- **Use Case**: General-purpose tasks
- **Behavior**: Equal weight to cost and quality

### 4. Budget Constrained
- **Goal**: Optimize within strict budget limits
- **Use Case**: Limited budget scenarios
- **Behavior**: Maximizes utility within budget

### 5. Quality Threshold
- **Goal**: Meet minimum quality at lowest cost
- **Use Case**: Tasks with minimum quality requirements
- **Behavior**: Cheapest model above quality threshold

## Implementation Examples

### Example 1: Basic Model Selection

```python
from app.services.cost_quality_optimizer import cost_quality_optimizer
from app.schemas.cost_optimization import CostQualityRequest, OptimizationStrategy

# Create request
request = CostQualityRequest(
    task_type="image_generation",
    prompt_complexity=0.6,
    quality_requirement=0.7,
    budget_constraint=0.05
)

# Get optimized decision
decision = cost_quality_optimizer.optimize_model_selection(
    request, 
    OptimizationStrategy.BALANCED
)

print(f"Selected model: {decision.selected_model}")
print(f"Expected cost: ${decision.expected_cost:.3f}")
print(f"Expected quality: {decision.expected_quality:.2f}")
print(f"Utility score: {decision.utility_score:.2f}")
print(f"Reasoning: {decision.reasoning}")
```

### Example 2: Utility Function Calculation

```python
from app.schemas.cost_optimization import UtilityParameters

# Set utility parameters
params = UtilityParameters(
    alpha=0.7,  # 70% weight on quality
    beta=0.3,   # 30% weight on cost
    quality_threshold=0.5
)

# Calculate utility for different models
models = ["stable-diffusion-v1-5", "stable-diffusion-xl", "dall-e-3"]

for model_name in models:
    model = cost_quality_optimizer.model_profiles[model_name]
    utility = cost_quality_optimizer.calculate_utility(model, request, params)
    
    print(f"{model_name}:")
    print(f"  Quality: {model.expected_quality:.2f}")
    print(f"  Cost: ${model.cost_per_call:.3f}")
    print(f"  Utility: {utility:.2f}")
    print()
```

### Example 3: Model Switching Logic

```python
from app.services.model_switching_logic import model_switching_logic
from app.schemas.decision_engine import FailureContext, PipelineStage

# Create failure context
failure_context = FailureContext(
    task_name="image_generation",
    stage=PipelineStage.IMAGE,
    error_logs="Low quality detected",
    retry_count=2,
    model_used="stable-diffusion-v1-5",
    prompt_used="A beautiful sunset over mountains"
)

# Get switching decision
should_switch, new_model, reasoning = await model_switching_logic.should_switch_model(
    current_model="stable-diffusion-v1-5",
    current_quality=0.3,
    failure_context=failure_context,
    budget_remaining=0.03
)

if should_switch:
    print(f"Switch to: {new_model}")
    print(f"Reason: {reasoning}")
else:
    print(f"Keep current model: {reasoning}")
```

### Example 4: Budget Constraint Handling

```python
from app.services.budget_constraint_handler import budget_constraint_handler

# Create budget plan
plan = budget_constraint_handler.create_budget_plan(
    total_budget=10.0,
    task_count=100,
    quality_requirements={
        "image_generation": 0.7,
        "text_generation": 0.8
    }
)

print(f"Total budget: ${plan['total_budget']}")
print(f"Task count: {plan['task_count']}")

for allocation in plan['allocations']:
    print(f"{allocation['tier']}: {allocation['allocation_percentage']:.1%} (${allocation['allocated_amount']:.2f})")

print("\nRecommendations:")
for rec in plan['recommendations']:
    print(f"- {rec}")
```

### Example 5: Cost-Aware Decision Engine Integration

```python
from app.services.cost_aware_decision_engine import cost_aware_decision_engine
from app.schemas.decision_engine import FailureContext, PipelineStage

# Create failure context
failure_context = FailureContext(
    task_name="image_generation",
    stage=PipelineStage.IMAGE,
    error_logs="Quality score too low",
    retry_count=1,
    model_used="stable-diffusion-v1-5",
    prompt_used="A detailed landscape painting",
    cost_so_far=0.05
)

# Get cost-aware decision
decision = await cost_aware_decision_engine.analyze_failure_with_cost_optimization(
    failure_context,
    budget_constraint=0.10,
    utility_params=UtilityParameters(alpha=0.6, beta=0.4)
)

print(f"Action: {decision.action}")
print(f"New model: {decision.new_model}")
print(f"Reasoning: {decision.reasoning}")
```

## API Usage Examples

### 1. Optimize Model Selection

```bash
curl -X POST "http://localhost:8000/api/v1/cost-optimization/optimize-model" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "image_generation",
    "prompt_complexity": 0.6,
    "quality_requirement": 0.7,
    "budget_constraint": 0.05,
    "strategy": "balanced"
  }'
```

### 2. Calculate Utility Scores

```bash
curl -X POST "http://localhost:8000/api/v1/cost-optimization/utility-calculation" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "image_generation",
    "prompt_complexity": 0.6,
    "quality_requirement": 0.7,
    "alpha": 0.7,
    "beta": 0.3
  }'
```

### 3. Get Model Switching Decision

```bash
curl -X POST "http://localhost:8000/api/v1/cost-optimization/model-switching-decision" \
  -H "Content-Type: application/json" \
  -d '{
    "current_model": "stable-diffusion-v1-5",
    "current_quality": 0.3,
    "failure_type": "low_quality",
    "retry_count": 2,
    "budget_remaining": 0.03
  }'
```

### 4. Create Budget Plan

```bash
curl -X POST "http://localhost:8000/api/v1/cost-optimization/budget-plan" \
  -H "Content-Type: application/json" \
  -d '{
    "total_budget": 10.0,
    "task_count": 100,
    "quality_requirements": {
      "image_generation": 0.7,
      "text_generation": 0.8
    }
  }'
```

## Switching Logic Examples

### Example 1: Quality-Based Switching

```python
# Low quality detected - switch to better model
current_quality = 0.3
target_quality = 0.7

if current_quality < target_quality:
    # Switch to premium model
    new_model = "dall-e-3"
    reasoning = f"Upgrading for quality improvement: {target_quality - current_quality:.2f} points"
```

### Example 2: Cost-Based Switching

```python
# Budget running low - switch to cheaper model
budget_remaining = 0.01
current_cost = 0.04

if current_cost > budget_remaining:
    # Switch to basic model
    new_model = "stable-diffusion-v1-5"
    savings = current_cost - 0.01
    reasoning = f"Downgrading for cost savings: ${savings:.3f} per call"
```

### Example 3: Retry-Based Switching

```python
# Multiple retries - upgrade to more reliable model
retry_count = 3

if retry_count >= 2:
    # Switch to ultra-reliable model
    new_model = "dall-e-3"
    reasoning = f"Upgrading after {retry_count} retries to improve success rate"
```

### Example 4: Failure-Type-Based Switching

```python
# Timeout failure - switch to faster model
if "timeout" in error_logs.lower():
    new_model = "stable-diffusion-v1-5"  # Fast model
    reasoning = "Switching to faster model to resolve timeout issues"

# Quality failure - switch to premium model
elif "quality" in error_logs.lower():
    new_model = "dall-e-3"  # Premium model
    reasoning = "Switching to premium quality model for better results"

# API error - switch to more reliable model
elif "api error" in error_logs.lower():
    new_model = "gpt-4-turbo"  # Reliable model
    reasoning = "Switching to more reliable model for API stability"
```

## Integration with Decision Engine

### 1. Cost-Aware Decision Making

```python
class CostAwareImageAgent:
    async def generate_image(self, prompt, budget_remaining):
        # Create cost-quality request
        request = CostQualityRequest(
            task_type="image_generation",
            prompt_complexity=self.calculate_complexity(prompt),
            quality_requirement=0.7,
            budget_constraint=budget_remaining
        )
        
        # Get optimized model selection
        decision = cost_quality_optimizer.optimize_model_selection(
            request, OptimizationStrategy.BALANCED
        )
        
        # Generate image with selected model
        return await self.generate_with_model(prompt, decision.selected_model)
```

### 2. Dynamic Model Switching

```python
class AdaptiveImageGenerator:
    async def generate_with_retry(self, prompt, max_retries=3):
        current_model = "stable-diffusion-v1-5"
        
        for attempt in range(max_retries):
            try:
                # Generate image
                result = await self.generate_image(prompt, current_model)
                
                # Check quality
                quality = await self.evaluate_quality(result.image_path)
                
                if quality >= 0.7:
                    return result
                
                # Decide if should switch model
                failure_context = self.create_failure_context(
                    current_model, quality, attempt
                )
                
                should_switch, new_model, reasoning = await model_switching_logic.should_switch_model(
                    current_model, quality, failure_context
                )
                
                if should_switch:
                    current_model = new_model
                    logger.info(f"Switched to {new_model}: {reasoning}")
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
        
        raise Exception("Max retries exceeded")
```

## Performance Considerations

### 1. Utility Function Optimization

```python
# Cache utility calculations
@lru_cache(maxsize=1000)
def cached_utility_calculation(model_name, request_hash, params_hash):
    model = cost_quality_optimizer.model_profiles[model_name]
    return cost_quality_optimizer.calculate_utility(model, request, params)
```

### 2. Model Selection Caching

```python
# Cache model selection decisions
decision_cache = {}

def get_cached_decision(request_key, strategy):
    if request_key in decision_cache:
        return decision_cache[request_key]
    
    decision = cost_quality_optimizer.optimize_model_selection(request, strategy)
    decision_cache[request_key] = decision
    return decision
```

### 3. Budget Monitoring

```python
# Real-time budget monitoring
class BudgetMonitor:
    def __init__(self, total_budget):
        self.total_budget = total_budget
        self.spent_budget = 0.0
        self.alert_thresholds = [0.5, 0.7, 0.9]
    
    def track_spending(self, cost):
        self.spent_budget += cost
        utilization = self.spent_budget / self.total_budget
        
        for threshold in self.alert_thresholds:
            if utilization >= threshold:
                self.send_alert(threshold, utilization)
```

## Best Practices

### 1. Parameter Tuning

```python
# Adjust alpha/beta based on use case
def get_utility_params(context):
    if context["budget_constrained"]:
        return UtilityParameters(alpha=0.4, beta=0.6)  # Cost-focused
    elif context["quality_critical"]:
        return UtilityParameters(alpha=0.8, beta=0.2)  # Quality-focused
    else:
        return UtilityParameters(alpha=0.6, beta=0.4)  # Balanced
```

### 2. Tier-Based Allocation

```python
# Allocate budget by tier
def allocate_budget_by_tier(total_budget, task_mix):
    allocations = {
        "basic": total_budget * 0.4,
        "standard": total_budget * 0.3,
        "premium": total_budget * 0.2,
        "ultra": total_budget * 0.1
    }
    
    # Adjust based on task requirements
    if task_mix["high_quality"] > 0.5:
        allocations["premium"] += allocations["basic"] * 0.5
        allocations["basic"] *= 0.5
    
    return allocations
```

### 3. Quality Threshold Management

```python
# Dynamic quality thresholds
def get_quality_threshold(context):
    base_threshold = 0.5
    
    # Increase threshold for critical tasks
    if context["importance"] == "high":
        base_threshold += 0.2
    
    # Decrease threshold for budget constraints
    if context["budget_pressure"] > 0.8:
        base_threshold -= 0.1
    
    return max(0.3, min(0.9, base_threshold))
```

## Monitoring and Analytics

### 1. Cost Tracking

```python
# Track cost per quality
cost_per_quality = total_cost / total_quality_score

# Track savings from optimization
optimization_savings = baseline_cost - optimized_cost

# Track model switching effectiveness
switching_success_rate = successful_switches / total_switches
```

### 2. Quality Metrics

```python
# Track quality improvement
quality_improvement = new_quality - original_quality

# Track quality consistency
quality_variance = calculate_variance(quality_scores)

# Track tier performance
tier_performance = {
    tier: calculate_avg_quality(tier_models)
    for tier in ["basic", "standard", "premium", "ultra"]
}
```

### 3. Budget Efficiency

```python
# Budget utilization rate
utilization_rate = spent_budget / total_budget

# Cost per task by tier
cost_by_tier = {
    tier: total_cost / task_count
    for tier, (total_cost, task_count) in tier_costs.items()
}

# Return on investment
quality_roi = quality_improvement / cost_increase
```

This cost-quality optimization layer provides intelligent, automated model selection that balances cost and quality requirements while maximizing utility and staying within budget constraints.
