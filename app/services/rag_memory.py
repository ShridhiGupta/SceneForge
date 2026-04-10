import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from app.core.database import SessionLocal
from app.schemas.rag_memory import FailureMemory, MemoryQuery, MemoryResult, MemorySearchResponse, MemoryStats
from app.models.memory import FailureMemoryDB as FailureMemoryModel
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGMemoryService:
    """
    RAG-based memory service for storing and retrieving failure experiences
    """
    
    def __init__(self):
        self.vector_store = vector_store
    
    async def store_failure_memory(self, memory: FailureMemory) -> Optional[str]:
        """
        Store a failure experience in both database and vector store
        """
        db = SessionLocal()
        try:
            # Create database record
            db_memory = FailureMemoryModel(
                failure_type=memory.failure_type,
                stage=memory.stage,
                error_logs=memory.error_logs,
                prompt_used=memory.prompt_used,
                model_used=memory.model_used,
                action_taken=memory.action_taken,
                new_prompt=memory.new_prompt,
                new_model=memory.new_model,
                parameter_changes=memory.parameter_changes,
                success=memory.success,
                final_quality_score=memory.final_quality_score,
                total_cost=memory.total_cost,
                retry_count=memory.retry_count,
                timestamp=memory.timestamp,
                task_id=memory.task_id,
                video_id=memory.video_id,
                scene_id=memory.scene_id,
                error_summary=memory.error_logs[:100],
                prompt_summary=memory.prompt_used[:100]
            )
            
            db.add(db_memory)
            db.commit()
            db.refresh(db_memory)
            
            # Store in vector store
            memory.id = db_memory.id
            embedding_id = await self.vector_store.add_memory(memory)
            
            if embedding_id:
                # Update database with embedding ID
                db_memory.embedding_id = embedding_id
                db.commit()
            
            logger.info(f"Stored failure memory {db_memory.id} with embedding {embedding_id}")
            return str(db_memory.id)
            
        except Exception as e:
            logger.error(f"Failed to store failure memory: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    async def search_similar_failures(self, query: MemoryQuery) -> MemorySearchResponse:
        """
        Search for similar past failures using vector similarity
        """
        start_time = time.time()
        
        try:
            # Search vector store
            vector_results = await self.vector_store.search_similar(query)
            
            # Complement with database search for exact matches
            db_results = self._search_database_fallback(query)
            
            # Combine and deduplicate results
            all_results = self._combine_results(vector_results, db_results)
            
            search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return MemorySearchResponse(
                query=query,
                results=all_results[:query.top_k],
                total_found=len(all_results),
                search_time_ms=search_time
            )
            
        except Exception as e:
            logger.error(f"Failed to search similar failures: {e}")
            return MemorySearchResponse(
                query=query,
                results=[],
                total_found=0,
                search_time_ms=(time.time() - start_time) * 1000
            )
    
    def _search_database_fallback(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Fallback database search for exact matches
        """
        db = SessionLocal()
        try:
            # Build query filters
            filters = [
                FailureMemoryModel.failure_type == query.failure_type,
                FailureMemoryModel.stage == query.stage
            ]
            
            if query.require_success:
                filters.append(FailureMemoryModel.success == True)
            
            # Search for similar error patterns
            error_keywords = self._extract_keywords(query.error_logs)
            if error_keywords:
                error_filter = []
                for keyword in error_keywords[:3]:  # Limit to top 3 keywords
                    error_filter.append(FailureMemoryModel.error_logs.contains(keyword))
                if error_filter:
                    filters.append(or_(*error_filter))
            
            # Execute query
            memories = db.query(FailureMemoryModel).filter(
                and_(*filters)
            ).order_by(desc(FailureMemoryModel.timestamp)).limit(query.top_k * 2).all()
            
            # Convert to results with similarity scores
            results = []
            for memory in memories:
                schema_memory = self._db_to_schema(memory)
                similarity = self._calculate_text_similarity(schema_memory, query)
                
                if similarity >= query.min_similarity:
                    result = MemoryResult(
                        memory=schema_memory,
                        similarity_score=similarity,
                        relevance_explanation="Database fallback match"
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Database fallback search failed: {e}")
            return []
        finally:
            db.close()
    
    def _combine_results(self, vector_results: List[MemoryResult], db_results: List[MemoryResult]) -> List[MemoryResult]:
        """
        Combine vector and database results, removing duplicates
        """
        seen_ids = set()
        combined = []
        
        # Add vector results first (higher priority)
        for result in vector_results:
            memory_id = result.memory.id if hasattr(result.memory, 'id') else None
            if memory_id and memory_id not in seen_ids:
                seen_ids.add(memory_id)
                combined.append(result)
        
        # Add database results (lower priority)
        for result in db_results:
            memory_id = result.memory.id if hasattr(result.memory, 'id') else None
            if memory_id and memory_id not in seen_ids:
                seen_ids.add(memory_id)
                combined.append(result)
        
        # Sort by similarity score
        combined.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return combined
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from error text"""
        # Simple keyword extraction - could be enhanced with NLP
        import re
        
        # Remove special characters and split
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'error', 'failed', 'timeout', 'exception'}
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Return most frequent keywords
        from collections import Counter
        word_counts = Counter(keywords)
        return [word for word, count in word_counts.most_common(10)]
    
    def _calculate_text_similarity(self, memory: FailureMemory, query: MemoryQuery) -> float:
        """
        Calculate simple text similarity for database fallback
        """
        # Simple Jaccard similarity on error keywords
        memory_keywords = set(self._extract_keywords(memory.error_logs))
        query_keywords = set(self._extract_keywords(query.error_logs))
        
        if not memory_keywords or not query_keywords:
            return 0.0
        
        intersection = memory_keywords.intersection(query_keywords)
        union = memory_keywords.union(query_keywords)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _db_to_schema(self, memory_record: FailureMemoryModel) -> FailureMemory:
        """Convert database record to schema"""
        return FailureMemory(
            id=memory_record.id,
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
    
    async def get_memory_stats(self, days: int = 30) -> MemoryStats:
        """
        Get memory statistics for the past N days
        """
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Total memories
            total_memories = db.query(FailureMemoryModel).filter(
                FailureMemoryModel.timestamp >= cutoff_date
            ).count()
            
            # Memories by stage
            stage_stats = db.query(FailureMemoryModel.stage, db.func.count(FailureMemoryModel.id)).filter(
                FailureMemoryModel.timestamp >= cutoff_date
            ).group_by(FailureMemoryModel.stage).all()
            
            memories_by_stage = {stage.value: count for stage, count in stage_stats}
            
            # Memories by failure type
            failure_stats = db.query(FailureMemoryModel.failure_type, db.func.count(FailureMemoryModel.id)).filter(
                FailureMemoryModel.timestamp >= cutoff_date
            ).group_by(FailureMemoryModel.failure_type).all()
            
            memories_by_failure_type = {failure_type.value: count for failure_type, count in failure_stats}
            
            # Success rate by action
            action_stats = db.query(
                FailureMemoryModel.action_taken,
                db.func.count(FailureMemoryModel.id).label('total'),
                db.func.sum(db.cast(FailureMemoryModel.success, db.Integer)).label('successful')
            ).filter(
                FailureMemoryModel.timestamp >= cutoff_date
            ).group_by(FailureMemoryModel.action_taken).all()
            
            success_rate_by_action = {}
            for action, total, successful in action_stats:
                success_rate = successful / total if total > 0 else 0.0
                success_rate_by_action[action.value] = success_rate
            
            # Average similarity (from vector store)
            vector_stats = self.vector_store.get_stats()
            avg_similarity = 0.7  # Default fallback
            
            return MemoryStats(
                total_memories=total_memories,
                memories_by_stage=memories_by_stage,
                memories_by_failure_type=memories_by_failure_type,
                success_rate_by_action=success_rate_by_action,
                average_similarity_score=avg_similarity,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return MemoryStats(
                total_memories=0,
                memories_by_stage={},
                memories_by_failure_type={},
                success_rate_by_action={},
                average_similarity_score=0.0,
                last_updated=datetime.utcnow()
            )
        finally:
            db.close()
    
    def get_successful_strategies(self, failure_type: str, stage: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get most successful strategies for a specific failure type and stage
        """
        db = SessionLocal()
        try:
            # Query successful memories for this failure type and stage
            memories = db.query(FailureMemoryModel).filter(
                and_(
                    FailureMemoryModel.failure_type == failure_type,
                    FailureMemoryModel.stage == stage,
                    FailureMemoryModel.success == True
                )
            ).order_by(desc(FailureMemoryModel.final_quality_score)).limit(limit).all()
            
            strategies = []
            for memory in memories:
                strategy = {
                    "action": memory.action_taken.value,
                    "new_prompt": memory.new_prompt,
                    "new_model": memory.new_model,
                    "parameter_changes": memory.parameter_changes,
                    "quality_score": memory.final_quality_score,
                    "retry_count": memory.retry_count,
                    "timestamp": memory.timestamp
                }
                strategies.append(strategy)
            
            return strategies
            
        except Exception as e:
            logger.error(f"Failed to get successful strategies: {e}")
            return []
        finally:
            db.close()
    
    def is_available(self) -> bool:
        """Check if RAG memory service is available"""
        return self.vector_store.is_available()


# Singleton instance
rag_memory_service = RAGMemoryService()
