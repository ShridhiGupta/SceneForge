import os
import json
import uuid
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from openai import OpenAI
from app.core.config import settings
from app.schemas.rag_memory import FailureMemory, MemoryQuery, MemoryResult
from app.models.memory import FailureMemoryDB as FailureMemoryModel
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector database for RAG-based memory using FAISS
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_dimension = 1536
        self.index_path = os.path.join(settings.upload_dir, "vector_index")
        self.metadata_path = os.path.join(settings.upload_dir, "vector_metadata.json")
        
        # Initialize FAISS index
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize or load FAISS index"""
        try:
            import faiss
            self.faiss = faiss
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            
            # Load existing index or create new one
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
            else:
                self.index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product for cosine similarity
                logger.info("Created new FAISS index")
            
            # Load metadata
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {"embeddings": {}, "next_id": 0}
                
        except ImportError:
            logger.error("FAISS not installed. Install with: pip install faiss-cpu")
            raise ImportError("FAISS is required for vector store functionality")
    
    def _save_index(self):
        """Save FAISS index and metadata"""
        try:
            self.faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _create_embedding_text(self, memory: FailureMemory) -> str:
        """Create text representation for embedding"""
        text_parts = [
            f"Failure Type: {memory.failure_type.value}",
            f"Stage: {memory.stage.value}",
            f"Error: {memory.error_logs[:500]}",  # Limit to first 500 chars
            f"Prompt: {memory.prompt_used[:300]}",  # Limit to first 300 chars
            f"Model: {memory.model_used}",
            f"Action: {memory.action_taken.value}",
            f"Success: {memory.success}",
            f"Quality Score: {memory.final_quality_score or 0}",
            f"Retry Count: {memory.retry_count}"
        ]
        
        if memory.new_prompt:
            text_parts.append(f"New Prompt: {memory.new_prompt[:300]}")
        if memory.new_model:
            text_parts.append(f"New Model: {memory.new_model}")
        
        return " | ".join(text_parts)
    
    async def add_memory(self, memory: FailureMemory) -> str:
        """Add a memory to the vector store"""
        if not self.client:
            logger.warning("OpenAI client not available, skipping vector storage")
            return None
        
        try:
            # Create embedding text
            embedding_text = self._create_embedding_text(memory)
            
            # Generate embedding
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=embedding_text
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            
            # Generate embedding ID
            embedding_id = str(uuid.uuid4())
            
            # Add to FAISS index
            self.index.add(np.array([embedding]))
            
            # Store metadata
            self.metadata["embeddings"][embedding_id] = {
                "memory_id": memory.id if hasattr(memory, 'id') else None,
                "failure_type": memory.failure_type.value,
                "stage": memory.stage.value,
                "action_taken": memory.action_taken.value,
                "success": memory.success,
                "timestamp": memory.timestamp.isoformat(),
                "embedding_text": embedding_text
            }
            
            # Save index and metadata
            self._save_index()
            
            logger.info(f"Added memory {embedding_id} to vector store")
            return embedding_id
            
        except Exception as e:
            logger.error(f"Failed to add memory to vector store: {e}")
            return None
    
    async def search_similar(self, query: MemoryQuery) -> List[MemoryResult]:
        """Search for similar failures"""
        if not self.client or self.index.ntotal == 0:
            return []
        
        try:
            # Create query embedding text
            query_text = self._create_query_text(query)
            
            # Generate embedding
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=query_text
            )
            query_embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Normalize for cosine similarity
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            
            # Search in FAISS
            k = min(query.top_k, self.index.ntotal)
            similarities, indices = self.index.search(np.array([query_embedding]), k)
            
            # Convert to results
            results = []
            db = SessionLocal()
            
            try:
                for i, idx in enumerate(indices[0]):
                    similarity = float(similarities[0][i])
                    
                    # Skip if below threshold
                    if similarity < query.min_similarity:
                        continue
                    
                    # Find embedding metadata
                    embedding_id = None
                    for eid, meta in self.metadata["embeddings"].items():
                        if meta.get("index_position") == int(idx):
                            embedding_id = eid
                            break
                    
                    if not embedding_id:
                        continue
                    
                    # Get memory from database
                    memory_data = self.metadata["embeddings"][embedding_id]
                    memory_id = memory_data.get("memory_id")
                    
                    if memory_id:
                        memory_record = db.query(FailureMemoryModel).filter(
                            FailureMemoryModel.id == memory_id
                        ).first()
                        
                        if memory_record:
                            # Convert to schema
                            memory = self._db_to_schema(memory_record)
                            
                            # Apply filters
                            if query.require_success and not memory.success:
                                continue
                            
                            # Create result
                            result = MemoryResult(
                                memory=memory,
                                similarity_score=similarity,
                                relevance_explanation=self._explain_relevance(memory, query, similarity)
                            )
                            results.append(result)
                
            finally:
                db.close()
            
            # Sort by similarity
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            return results[:query.top_k]
            
        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            return []
    
    def _create_query_text(self, query: MemoryQuery) -> str:
        """Create text representation for query embedding"""
        text_parts = [
            f"Failure Type: {query.failure_type.value}",
            f"Stage: {query.stage.value}",
            f"Error: {query.error_logs[:500]}",
            f"Prompt: {query.prompt_used[:300]}",
            f"Model: {query.model_used}"
        ]
        
        return " | ".join(text_parts)
    
    def _db_to_schema(self, memory_record: FailureMemoryModel) -> FailureMemory:
        """Convert database record to schema"""
        return FailureMemory(
            failure_type=memory_record.failure_type,
            stage=memory_record.stage,
            error_logs=memory_record.error_logs,
            prompt_used=memory_record.prompt_used,
            model_used=memory_record.model_used,
            action_taken=memory_record.action_taken,
            new_prompt=memory_record.new_prompt,
            new_model=memory_record.new_model,
            parameter_changes=memory_record.parameter_changes,
            success=memory_record.success,
            final_quality_score=memory_record.final_quality_score,
            total_cost=memory_record.total_cost,
            retry_count=memory_record.retry_count,
            timestamp=memory_record.timestamp,
            task_id=memory_record.task_id,
            video_id=memory_record.video_id,
            scene_id=memory_record.scene_id,
            embedding_id=memory_record.embedding_id
        )
    
    def _explain_relevance(self, memory: FailureMemory, query: MemoryQuery, similarity: float) -> str:
        """Generate explanation for relevance"""
        explanations = []
        
        # Same failure type
        if memory.failure_type == query.failure_type:
            explanations.append("Same failure type")
        
        # Same stage
        if memory.stage == query.stage:
            explanations.append("Same pipeline stage")
        
        # Similar error patterns
        if any(word in memory.error_logs.lower() for word in query.error_logs.lower().split()[:5]):
            explanations.append("Similar error patterns")
        
        # Similar prompts
        if any(word in memory.prompt_used.lower() for word in query.prompt_used.lower().split()[:3]):
            explanations.append("Similar prompt content")
        
        # Same model
        if memory.model_used == query.model_used:
            explanations.append("Same AI model")
        
        # Success bias
        if memory.success:
            explanations.append("Previously successful recovery")
        
        if explanations:
            return f"Relevant due to: {', '.join(explanations)} (similarity: {similarity:.2f})"
        else:
            return f"General similarity match (similarity: {similarity:.2f})"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            "total_vectors": self.index.ntotal,
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension,
            "index_path": self.index_path,
            "metadata_count": len(self.metadata["embeddings"])
        }
    
    def is_available(self) -> bool:
        """Check if vector store is available"""
        return self.client is not None and hasattr(self, 'index')


# Singleton instance
vector_store = VectorStore()
