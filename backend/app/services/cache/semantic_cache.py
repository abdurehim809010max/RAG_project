"""
backend/app/services/cache/semantic_cache.py

Caches RAG pipeline responses to reduce Gemini API calls and latency.
"""
import hashlib
import json
from backend.app.services.cache.redis_client import RedisClient

class SemanticCache:
    def __init__(self):
        self.redis = RedisClient()

    def _generate_key(self, query: str, case_number: str) -> str:
        """
        Creates a deterministic hash based on the normalized query and case.
        """
        normalized_query = query.strip().lower()
        raw_key = f"{normalized_query}_{case_number}"
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    def get_cached_answer(self, query: str, case_number: str):
        """Returns the parsed JSON response if it exists in cache."""
        key = self._generate_key(query, case_number)
        cached_data = self.redis.get(key)
        
        if cached_data:
            return json.loads(cached_data)
        return None

    def set_cached_answer(self, query: str, case_number: str, text_response: str):
        """Stores the model's response in Redis for 24 hours."""
        key = self._generate_key(query, case_number)
        
        data = {
            "answer": text_response,
            "cached": True
        }
        
        self.redis.set(key, json.dumps(data, ensure_ascii=False))