# Multi-Agent Architecture Guide

## Architecture Diagram

```
                    Multi-Agent Workflow (LangGraph)
                              |
                              v
    +------------------+    +-----------------+    +------------------+
    |   Scene Agent    | -> | Image Gen Agent | -> | Quality Agent    |
    +------------------+    +-----------------+    +------------------+
                              |                     |
                              v                     v
    +------------------+    +-----------------+    +------------------+
    | Decision Agent   | <- | Cost Opt Agent  | <- |  RAG Memory      |
    +------------------+    +-----------------+    +------------------+
                              |
                              v
    +------------------+    +-----------------+    +------------------+
    |  Error Handler   | -> |  Completion     | -> |   Pipeline End   |
    +------------------+    +-----------------+    +------------------+
```

## Agent Responsibilities

### 1. Scene Agent
- **Purpose**: Parse video scripts into individual scenes
- **Responsibilities**:
  - Extract scene descriptions from scripts
  - Generate AI prompts for each scene
  - Estimate scene durations
  - Manage scene ordering and dependencies

### 2. Image Generation Agent
- **Purpose**: Generate images using various AI models
- **Responsibilities**:
  - Select optimal model for each scene
  - Generate images with retry logic
  - Handle model switching and fallbacks
  - Track generation costs and performance

### 3. Quality Evaluation Agent
- **Purpose**: Evaluate generated image quality
- **Responsibilities**:
  - CLIP-based text-image similarity scoring
  - LLM-based visual quality assessment
  - Combined quality scoring with thresholds
  - Trigger decision agent for low-quality images

### 4. Decision Agent
- **Purpose**: Make intelligent recovery decisions
- **Responsibilities**:
  - LLM-powered decision making with RAG memory
  - Retrieve similar past failures
  - Execute recovery actions (retry, modify prompt, switch model)
  - Coordinate retry loops and parameter adjustments

### 5. Cost Optimization Agent
- **Purpose**: Optimize costs while maintaining quality
- **Responsibilities**:
  - Monitor and track generation costs
  - Suggest cost-saving strategies
  - Optimize model selection for budget constraints
  - Provide real-time cost analysis

## State Schema

### Core Pipeline State
```python
class PipelineState:
    # Core data
    video_id: int
    title: str
    script: str
    total_budget: Optional[float]
    
    # Scene management
    scenes: List[Scene]
    current_scene_index: int
    completed_scenes: int
    
    # Results tracking
    generation_results: List[GenerationResult]
    quality_results: List[QualityResult]
    decision_results: List[DecisionResult]
    
    # Cost tracking
    total_cost: float
    cost_breakdown: Dict[str, float]
    cost_optimization: Optional[CostOptimization]
    
    # Pipeline status
    status: PipelineStatus
    current_agent: Optional[str]
    agent_statuses: Dict[str, AgentStatus]
    
    # Retry and error handling
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    error_history: List[str]
```

### Scene Schema
```python
class Scene:
    id: int
    scene_number: int
    description: str
    duration: float
    prompt: Optional[str]
    image_path: Optional[str]
    quality_score: Optional[float]
    retry_count: int
    cost: float
    model_used: Optional[str]
    status: AgentStatus
```

## Execution Flow

### 1. Initialization
```
Start -> Scene Agent -> Parse Script -> Create Scenes
```

### 2. Image Generation Loop
```
For Each Scene:
    Image Generation Agent -> Select Model -> Generate Image
    Quality Evaluation Agent -> CLIP Score -> LLM Score -> Combined Score
    Decision Agent -> Check Quality -> Make Decision if Needed
```

### 3. Retry Logic
```
If Quality < Threshold:
    Decision Agent -> Analyze with RAG -> Choose Action
    Actions: RETRY, MODIFY_PROMPT, SWITCH_MODEL, ADJUST_PARAMETERS
    Loop back to appropriate agent
```

### 4. Cost Optimization
```
After Quality Checks:
    Cost Optimization Agent -> Analyze Costs -> Suggest Optimizations
    Decision Agent -> Review Suggestions -> Apply if Beneficial
```

### 5. Completion
```
All Scenes Completed -> Update Database -> Return Results
```

## LangGraph Implementation

### Workflow Graph
```python
workflow = StateGraph(PipelineState)

# Nodes
workflow.add_node("scene_processing", scene_processing_node)
workflow.add_node("image_generation", image_generation_node)
workflow.add_node("quality_evaluation", quality_evaluation_node)
workflow.add_node("decision_making", decision_making_node)
workflow.add_node("cost_optimization", cost_optimization_node)
workflow.add_node("error_handling", error_handling_node)
workflow.add_node("completion", completion_node)

# Conditional Edges
workflow.add_conditional_edges("scene_processing", route_after_scene_processing)
workflow.add_conditional_edges("image_generation", route_after_image_generation)
workflow.add_conditional_edges("quality_evaluation", route_after_quality_evaluation)
workflow.add_conditional_edges("decision_making", route_after_decision_making)
```

### State Passing
- **Immutable State**: Each node receives a copy of the state
- **State Updates**: Nodes return modified state
- **Shared Context**: `shared_context` dictionary for cross-agent communication
- **Message Passing**: Agents communicate through structured messages

## Retry Loops

### Retry Triggers
1. **Quality Failure**: Score below threshold
2. **Generation Error**: API failure, timeout, etc.
3. **Decision Agent**: Explicit retry decision
4. **Cost Optimization**: Retry with cheaper model

### Retry Logic
```python
if state.retry_count < state.max_retries:
    state.status = PipelineStatus.RETRYING
    state.retry_count += 1
    # Route back to appropriate agent
else:
    state.status = PipelineStatus.FAILED
```

### Exponential Backoff
```python
retry_delay = 2 ** state.retry_count  # 2^n seconds
await asyncio.sleep(retry_delay)
```

## API Usage

### Execute Complete Pipeline
```bash
curl -X POST "http://localhost:8000/api/v1/multi-agent/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": 123,
    "script": "SCENE 1: A beautiful sunset over mountains...",
    "title": "Nature Documentary",
    "total_budget": 10.0,
    "quality_threshold": 0.5
  }'
```

### Monitor Execution
```bash
curl -X GET "http://localhost:8000/api/v1/multi-agent/status/123"
```

### Cancel Execution
```bash
curl -X POST "http://localhost:8000/api/v1/multi-agent/cancel/123"
```

### Get System Status
```bash
curl -X GET "http://localhost:8000/api/v1/multi-agent/system-status"
```

## Integration with Existing Pipeline

### Migration Steps
1. **Install LangGraph**: `pip install langgraph`
2. **Add Agents**: Import and initialize agent classes
3. **Replace Tasks**: Use multi-agent workflow instead of individual Celery tasks
4. **Update Database**: Add new fields for agent communication
5. **Monitor Performance**: Track agent execution times and success rates

### Benefits Over Traditional Pipeline
1. **Intelligent Decision Making**: LLM-powered decisions with RAG memory
2. **Adaptive Retry Logic**: Context-aware retry strategies
3. **Cost Optimization**: Real-time cost monitoring and optimization
4. **Better Error Handling**: Graceful degradation and recovery
5. **Scalability**: Independent agent scaling

## Performance Considerations

### Agent Parallelization
- **Scene Processing**: Sequential (depends on script parsing)
- **Image Generation**: Parallel (multiple scenes can be processed)
- **Quality Evaluation**: Parallel (independent evaluations)
- **Decision Making**: Sequential (depends on context)

### Resource Management
- **Memory**: Each agent maintains minimal state
- **CPU**: LLM agents are CPU-intensive
- **GPU**: Image generation benefits from GPU acceleration
- **Network**: API calls for external services

### Optimization Strategies
1. **Batch Processing**: Group similar scenes for batch generation
2. **Caching**: Cache LLM decisions and RAG results
3. **Load Balancing**: Distribute agents across multiple workers
4. **Resource Pooling**: Share expensive resources between agents

## Monitoring and Debugging

### Agent Metrics
```python
{
    "scene_agent": {
        "status": "completed",
        "processing_time": 1500,
        "scenes_created": 5
    },
    "image_generation_agent": {
        "status": "running",
        "processing_time": 12000,
        "images_generated": 3,
        "success_rate": 0.8
    }
}
```

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger("app.agents").setLevel(logging.DEBUG)

# Execute single step
state = await workflow.execute_step(initial_state, "scene_processing")
```

### Error Tracking
```python
# Error context
{
    "agent": "image_generation_agent",
    "error": "API timeout",
    "state": {...},
    "retry_count": 2,
    "suggested_action": "switch_model"
}
```

## Future Enhancements

### 1. Advanced Agent Communication
- Message passing protocols
- Agent negotiation
- Dynamic agent creation

### 2. Learning and Adaptation
- Agent performance learning
- Dynamic threshold adjustment
- Predictive decision making

### 3. Distributed Execution
- Multi-machine agent deployment
- Load balancing across agents
- Fault-tolerant agent clusters

### 4. Real-time Monitoring
- Live agent status dashboard
- Performance analytics
- Cost optimization alerts

The multi-agent architecture provides a sophisticated, intelligent, and scalable solution for video generation with adaptive decision making, cost optimization, and robust error handling.
