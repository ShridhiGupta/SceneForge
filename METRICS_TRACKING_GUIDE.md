# Production Metrics Tracking Guide

## Overview

This comprehensive metrics tracking system provides structured JSON logging and detailed analytics to prove your AI pipeline improvements. The system tracks all key metrics including failures, actions, retries, costs, execution times, and quality improvements.

## Architecture

```
Pipeline Components
        |
        v
Structured Logger (JSON Output)
        |
        v
Metrics Tracker (Real-time Collection)
        |
        v
Log Analyzer (Post-processing)
        |
        v
API Endpoints (Real-time Monitoring)
        |
        v
Dashboard (Visual Analytics)
```

## Tracked Metrics

### 1. Task Execution Metrics
- **Task Start/End**: Timestamps and duration
- **Success/Failure**: Binary outcome tracking
- **Execution Time**: Millisecond precision timing
- **Agent Performance**: Per-agent execution metrics

### 2. Quality Metrics
- **Quality Before/After**: Pre/post intervention scores
- **Improvement Tracking**: Delta calculations
- **CLIP Scores**: Text-image similarity
- **LLM Scores**: Visual quality assessment
- **Combined Scores**: Weighted quality metrics

### 3. Failure Analysis
- **Failure Types**: Categorized failure classification
- **Error Messages**: Detailed error tracking
- **Failure Patterns**: Trend analysis
- **Recovery Actions**: Taken interventions

### 4. Decision Making Metrics
- **Actions Taken**: Specific recovery actions
- **Confidence Scores**: LLM decision confidence
- **RAG Usage**: Memory system utilization
- **Similar Failures**: Context retrieval metrics

### 5. Cost Metrics
- **Per-Task Costs**: Individual task expenses
- **Total Costs**: Aggregate spending
- **Cost by Model**: Model-specific cost analysis
- **Cost Optimization**: Savings tracking

### 6. Retry Metrics
- **Retry Attempts**: Number of retries per task
- **Retry Success Rate**: Recovery effectiveness
- **Retry Patterns**: Failure recurrence analysis
- **Escalation**: Resource escalation tracking

## JSON Log Format

### Task Start Log
```json
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
```

### Task Success Log
```json
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
```

### Decision Log
```json
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
```

### Quality Metrics Log
```json
{
  "timestamp": "2024-01-15T10:30:15.000Z",
  "event_type": "quality_metrics",
  "request_id": "uuid-1234",
  "quality_before": 0.3,
  "quality_after": 0.8,
  "improvement": 0.5,
  "task_id": "uuid-5678"
}
```

### Cost Metrics Log
```json
{
  "timestamp": "2024-01-15T10:30:20.000Z",
  "event_type": "cost_metrics",
  "request_id": "uuid-1234",
  "cost": 0.02,
  "task_name": "image_generation",
  "task_id": "uuid-5678"
}
```

### Retry Log
```json
{
  "timestamp": "2024-01-15T10:30:25.000Z",
  "event_type": "retry",
  "request_id": "uuid-1234",
  "task_name": "image_generation",
  "retry_count": 2,
  "original_error": "API timeout",
  "task_id": "uuid-5678"
}
```

## Integration Guide

### 1. Basic Integration

```python
from app.logging.agent_metrics import track_agent_metrics
from app.logging.metrics_tracker import metrics_tracker

class YourAgent:
    @track_agent_metrics("your_agent_name")
    async def your_method(self, state):
        # Your existing logic
        result = await self.process_data(state)
        
        # Metrics are automatically tracked
        return result
```

### 2. Manual Tracking

```python
from app.logging.agent_metrics import MetricsContext

async def manual_tracking():
    with MetricsContext("custom_task", video_id=123) as ctx:
        result = await your_operation()
        
        # Track quality improvement
        ctx.log_quality_before_after(quality_before=0.3, quality_after=0.8)
        
        # Track cost
        ctx.log_cost(cost=0.05)
        
        return result
```

### 3. Decision Tracking

```python
from app.logging.agent_metrics import track_decision_metrics

class DecisionAgent:
    @track_decision_metrics()
    async def make_decision(self, failure_context):
        decision = await self.analyze_failure(failure_context)
        
        # Automatically tracks decision metrics
        return decision
```

## API Endpoints

### Overview Metrics
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/overview"
```

### Quality Metrics
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/quality"
```

### Failure Analysis
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/failures"
```

### Decision Metrics
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/decisions"
```

### Cost Analysis
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/costs"
```

### Performance Metrics
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/performance"
```

### Improvement Metrics
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/improvement"
```

### Dashboard Data
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/dashboard"
```

## Log Analysis

### 1. Basic Analysis

```python
from app.logging.log_analyzer import LogAnalyzer

# Load logs
analyzer = LogAnalyzer()
analyzer.load_logs_from_file("pipeline_logs.json")

# Generate report
report = analyzer.generate_report()
print(json.dumps(report, indent=2))
```

### 2. Specific Analysis

```python
# Failure patterns
failure_analysis = analyzer.analyze_failure_patterns()

# Quality improvements
quality_analysis = analyzer.analyze_quality_metrics()

# Cost analysis
cost_analysis = analyzer.analyze_cost_metrics()

# Decision effectiveness
action_analysis = analyzer.analyze_action_effectiveness()
```

### 3. Improvement Metrics

```python
# Calculate improvement scores
improvement_metrics = analyzer.calculate_improvement_metrics()

# Key metrics:
# - quality_improvement_score: 0-100
# - failure_reduction_score: 0-100
# - cost_efficiency_score: 0-100
# - time_efficiency_score: 0-100
# - overall_improvement_score: 0-100
```

## Proving System Improvements

### 1. Quality Improvement Proof

```python
# Before/After Comparison
quality_before = 0.45  # Average quality before system
quality_after = 0.78   # Average quality after system
improvement = (quality_after - quality_before) / quality_before * 100

print(f"Quality improved by {improvement:.1f}%")
```

### 2. Failure Reduction Proof

```python
# Failure Rate Analysis
total_tasks_before = 1000
failed_tasks_before = 250
failure_rate_before = failed_tasks_before / total_tasks_before

total_tasks_after = 1000
failed_tasks_after = 100
failure_rate_after = failed_tasks_after / total_tasks_after

reduction = (failure_rate_before - failure_rate_after) / failure_rate_before * 100
print(f"Failures reduced by {reduction:.1f}%")
```

### 3. Cost Efficiency Proof

```python
# Cost Analysis
avg_cost_before = 0.08  # $0.08 per task
avg_cost_after = 0.05   # $0.05 per task
cost_reduction = (avg_cost_before - avg_cost_after) / avg_cost_before * 100

print(f"Costs reduced by {cost_reduction:.1f}%")
```

### 4. Decision Effectiveness Proof

```python
# Decision Success Rate
total_decisions = 500
successful_decisions = 425
success_rate = successful_decisions / total_decisions * 100

print(f"Decision success rate: {success_rate:.1f}%")
```

## Dashboard KPIs

### Key Performance Indicators

1. **Overall Health Score** (0-100)
   - Weighted: Success Rate (40%) + Quality Score (30%) + Cost Efficiency (30%)

2. **Quality Score** (0-100)
   - Average quality score × 100

3. **Cost Efficiency** (0-100)
   - Normalized cost efficiency (lower cost = higher score)

4. **Success Rate** (0-100)
   - (Successful Tasks / Total Tasks) × 100

5. **Improvement Trend**
   - Based on quality, success, and cost trends

### Dashboard Response Example

```json
{
  "kpis": {
    "overall_health": 85.2,
    "quality_score": 78.0,
    "cost_efficiency": 75.0,
    "success_rate": 92.5,
    "improvement_trend": "improving"
  },
  "aggregate_metrics": {
    "total_tasks": 1250,
    "successful_tasks": 1156,
    "failure_rate": 0.075,
    "average_execution_time_ms": 4500,
    "average_cost_per_task": 0.045,
    "total_cost": 56.25
  },
  "improvement_metrics": {
    "quality_improvement": {
      "with_decision_engine": 0.32,
      "without_decision_engine": 0.08,
      "improvement_difference": 0.24
    },
    "success_rate": {
      "with_decision_engine": 0.94,
      "without_decision_engine": 0.78,
      "improvement": 0.16
    },
    "cost_efficiency": {
      "with_decision_engine": 0.042,
      "without_decision_engine": 0.068,
      "cost_reduction": 0.026
    }
  }
}
```

## Production Deployment

### 1. Environment Configuration

```env
# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
METRICS_ENABLED=true
LOG_FILE_PATH=/app/logs/pipeline.log

# Metrics Configuration
METRICS_RETENTION_DAYS=30
METRICS_EXPORT_INTERVAL=300
DASHBOARD_REFRESH_RATE=60
```

### 2. Docker Configuration

```yaml
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

  # Optional: ELK Stack for log aggregation
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
```

### 3. Log Rotation

```bash
# Logrotate configuration
/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 app app
}
```

## Monitoring and Alerting

### 1. Health Checks

```bash
# System health
curl -X GET "http://localhost:8000/api/v1/metrics/health"

# Expected response:
{
  "status": "healthy",
  "active_tasks": 5,
  "completed_tasks": 1250,
  "total_decisions": 342,
  "total_cost": 56.25,
  "system_health": "operational"
}
```

### 2. Alert Thresholds

```python
# Example alert conditions
alerts = {
    "high_failure_rate": failure_rate > 0.1,
    "low_quality_score": avg_quality < 0.5,
    "high_cost_per_task": avg_cost > 0.1,
    "slow_execution": avg_time > 10000,
    "decision_confidence_low": avg_confidence < 0.6
}
```

### 3. Automated Reporting

```python
# Daily report generation
def generate_daily_report():
    metrics = metrics_tracker.get_improvement_metrics()
    
    report = f"""
    Daily Pipeline Report
    ====================
    
    Overall Health: {metrics['improvement_scores']['overall_improvement_score']:.1f}/100
    Quality Improvement: {metrics['quality_improvement']['improvement_difference']:.3f}
    Failure Reduction: {metrics['success_rate']['improvement']:.1%}
    Cost Savings: ${metrics['cost_efficiency']['cost_reduction']:.4f}
    
    Recommendations:
    {chr(10).join(f"- {rec}" for rec in generate_recommendations())}
    """
    
    return report
```

## Best Practices

### 1. Logging Best Practices
- Use structured logging with consistent field names
- Include request IDs for traceability
- Log at appropriate levels (INFO, WARNING, ERROR)
- Avoid logging sensitive data

### 2. Metrics Best Practices
- Track metrics at key decision points
- Include context for better analysis
- Use consistent units and formats
- Monitor metric collection overhead

### 3. Analysis Best Practices
- Regularly review failure patterns
- Track improvement trends over time
- Compare before/after metrics
- Use statistical significance testing

### 4. Dashboard Best Practices
- Focus on actionable KPIs
- Use visual representations
- Include trend analysis
- Provide drill-down capabilities

This comprehensive metrics tracking system provides the data and analytics needed to prove your AI pipeline improvements with concrete evidence and detailed analysis.
