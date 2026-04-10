# RAG Memory System Integration Guide

## Overview

This document explains how to use the RAG-based memory system for intelligent failure recovery in your AI video pipeline. The system learns from past failures and provides context-aware recommendations.

## Architecture

```
Failure Occurs -> RAG Memory Search -> LLM Decision with Context -> Action Execution -> Memory Storage
```

### Components

1. **Vector Store** (`app/services/vector_store.py`)
   - FAISS-based vector database for similarity search
   - OpenAI embeddings for semantic similarity
   - Efficient retrieval of similar past failures

2. **RAG Memory Service** (`app/services/rag_memory.py`)
   - High-level memory management
   - Database and vector store integration
   - Statistics and analytics

3. **Enhanced Decision Engine** (`app/services/decision_engine.py`)
   - RAG-aware decision making
   - Historical context injection
   - Learning from past outcomes

## Setup Instructions

### 1. Install Dependencies

```bash
pip install faiss-cpu numpy
```

### 2. Environment Configuration

Add to your `.env` file:

```env
# OpenAI API Key (required for embeddings)
OPENAI_API_KEY=your_openai_api_key

# Decision Engine Settings
DECISION_ENGINE_ENABLED=true
DECISION_ENGINE_MIN_RETRIES=1
DECISION_ENGINE_CONFIDENCE_THRESHOLD=0.7
```

### 3. Database Migration

```bash
python rag_memory_migration.py
```

This will:
- Create failure memory tables
- Add necessary indexes
- Create sample data for testing

## Usage Examples

### 1. Automatic Integration (Recommended)

The RAG memory system is automatically integrated with your existing decision engine:

```python
@celery_app.task(bind=True, max_retries=5)
@with_failure_handling(PipelineStage.IMAGE)
def generate_single_image(self, scene_id: int):
    # Your existing task logic
    # Failures now automatically use RAG memory for context
```

### 2. Manual Memory Search

```python
from app.schemas.rag_memory import MemoryQuery, FailureType, PipelineStage
from app.services.rag_memory import rag_memory_service

# Search for similar failures
query = MemoryQuery(
    failure_type=FailureType.TIMEOUT,
    stage=PipelineStage.IMAGE,
    error_logs="API timeout after 30 seconds",
    prompt_used="A beautiful sunset",
    model_used="stable-diffusion-xl",
    top_k=5,
    min_similarity=0.7,
    require_success=True
)

response = await rag_memory_service.search_similar_failures(query)
print(f"Found {len(response.results)} similar failures")
```

### 3. Store Memory Manually

```python
from app.schemas.rag_memory import FailureMemory, RecoveryAction, FailureType, PipelineStage

memory = FailureMemory(
    failure_type=FailureType.TIMEOUT,
    stage=PipelineStage.IMAGE,
    error_logs="API timeout after 30 seconds",
    prompt_used="A beautiful sunset",
    model_used="stable-diffusion-xl",
    action_taken=RecoveryAction.RETRY,
    success=True,
    final_quality_score=0.8,
    total_cost=0.05,
    retry_count=1
)

memory_id = await rag_memory_service.store_failure_memory(memory)
```

## API Endpoints

### Search Similar Failures

```bash
curl -X POST "http://localhost:8000/api/v1/rag-memory/search" \
  -H "Content-Type: application/json" \
  -d '{
    "failure_type": "timeout",
    "stage": "image",
    "error_logs": "API timeout after 30 seconds",
    "prompt_used": "A beautiful sunset",
    "model_used": "stable-diffusion-xl",
    "top_k": 5,
    "min_similarity": 0.7,
    "require_success": true
  }'
```

### Get Memory Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/rag-memory/stats?days=30"
```

### Get Successful Strategies

```bash
curl -X GET "http://localhost:8000/api/v1/rag-memory/successful-strategies?failure_type=timeout&stage=image&limit=5"
```

### Test Memory Search

```bash
curl -X POST "http://localhost:8000/api/v1/rag-memory/test-search" \
  -H "Content-Type: application/json" \
  -d '{
    "error_logs": "API timeout after 30 seconds",
    "stage": "image",
    "prompt": "A beautiful sunset",
    "model": "stable-diffusion-xl",
    "top_k": 5
  }'
```

## How It Works

### 1. Failure Analysis

When a failure occurs:
- Error logs are analyzed for patterns
- Failure type is automatically classified
- Context is extracted (stage, model, prompt, etc.)

### 2. Memory Retrieval

- Vector similarity search finds similar past failures
- Top 5 most relevant failures are retrieved
- Results are ranked by similarity score

### 3. Context Injection

- Historical failures are injected into LLM prompt
- Success rates and quality scores are provided
- Previously successful strategies are highlighted

### 4. Decision Making

LLM receives enhanced prompt:
```
CURRENT FAILURE:
- Error: API timeout after 30 seconds
- Stage: image
- Model: stable-diffusion-xl

SIMILAR PAST FAILURES:
1. Similar Failure (similarity: 0.92):
   - Error: API timeout after 30 seconds
   - Action Taken: retry
   - Success: true
   - Quality Score: 0.8

DECISION GUIDANCE:
If similar successful recoveries exist, strongly bias toward those strategies.
```

### 5. Memory Storage

After recovery action execution:
- Decision and outcome are stored in memory
- Future failures can learn from this experience
- System continuously improves over time

## Embedding Strategy

### Text Representation

Embeddings are created from structured text:

```
Failure Type: timeout | Stage: image | Error: API timeout after 30 seconds | Prompt: A beautiful sunset | Model: stable-diffusion-xl | Action: retry | Success: true | Quality Score: 0.8 | Retry Count: 1
```

### Similarity Calculation

- Cosine similarity on embeddings
- Threshold: 0.6 (configurable)
- Normalized vectors for consistent results

### Vector Store

- FAISS IndexFlatIP for inner product similarity
- Persistent storage on disk
- Automatic index saving and loading

## Performance Considerations

### Vector Store Performance

- **Index Size**: Scales linearly with number of memories
- **Search Time**: O(log n) for FAISS index
- **Memory Usage**: ~1536 dimensions per embedding

### Optimization Tips

1. **Batch Embeddings**: Process multiple memories together
2. **Regular Cleanup**: Remove old/irrelevant memories
3. **Threshold Tuning**: Adjust similarity thresholds based on results
4. **Index Optimization**: Rebuild index periodically for performance

## Monitoring and Analytics

### Memory Statistics

```python
stats = await rag_memory_service.get_memory_stats(days=30)
print(f"Total memories: {stats.total_memories}")
print(f"Success rates: {stats.success_rate_by_action}")
```

### Vector Store Health

```python
stats = vector_store.get_stats()
print(f"Total vectors: {stats['total_vectors']}")
print(f"Available: {vector_store.is_available()}")
```

## Troubleshooting

### Common Issues

1. **FAISS Import Error**
   ```bash
   pip install faiss-cpu
   # or for GPU support
   pip install faiss-gpu
   ```

2. **OpenAI API Rate Limits**
   - Implement rate limiting
   - Use embedding caching
   - Consider alternative embedding models

3. **Low Similarity Results**
   - Check embedding quality
   - Adjust similarity thresholds
   - Improve text representation

4. **Memory Storage Failures**
   - Check database connection
   - Verify vector store permissions
   - Check OpenAI API key

### Debug Mode

```python
import logging
logging.getLogger("app.services.rag_memory").setLevel(logging.DEBUG)
logging.getLogger("app.services.vector_store").setLevel(logging.DEBUG)
```

## Advanced Features

### 1. Custom Embedding Models

Replace OpenAI embeddings with custom models:

```python
# In vector_store.py
class CustomVectorStore(VectorStore):
    def __init__(self):
        # Initialize custom embedding model
        self.embedding_model = YourCustomModel()
```

### 2. Hybrid Search

Combine vector search with keyword search:

```python
# Results are automatically combined in RAG memory service
vector_results = await vector_store.search_similar(query)
db_results = self._search_database_fallback(query)
combined = self._combine_results(vector_results, db_results)
```

### 3. Memory Pruning

Automatically remove old or low-quality memories:

```python
# Add to RAG memory service
async def prune_memories(self, days: int = 90, min_quality: float = 0.3):
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    # Remove old and low-quality memories
```

## Production Deployment

### 1. Resource Requirements

- **Memory**: ~2MB per 1000 embeddings
- **Storage**: Vector index file grows with memories
- **CPU**: FAISS search is CPU-intensive
- **GPU**: Optional, for faster embeddings

### 2. Scaling Considerations

- **Horizontal Scaling**: Shared vector store storage
- **Caching**: Redis for frequently accessed memories
- **Load Balancing**: Multiple decision engine instances

### 3. Backup Strategy

```bash
# Backup vector index
cp uploads/vector_index uploads/vector_index.backup

# Backup database
sqlite3 sceneforge.db .dump > backup.sql
```

## Future Enhancements

1. **Learning Loop**: Automatic strategy improvement
2. **Multi-Modal**: Support for image/video embeddings
3. **Distributed Search**: Multiple vector stores
4. **Real-time Updates**: Live memory updates
5. **Explainability**: Better decision explanations

## Best Practices

1. **Start Simple**: Begin with basic RAG, add complexity gradually
2. **Monitor Quality**: Track decision success rates
3. **Regular Maintenance**: Prune old memories, rebuild indexes
4. **Test Thoroughly**: Validate with historical failure data
5. **Document Decisions**: Keep track of system improvements

The RAG memory system provides a powerful foundation for learning from past failures and continuously improving your AI pipeline's reliability and efficiency.
