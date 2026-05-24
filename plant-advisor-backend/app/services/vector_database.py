from typing import List, Dict, Any, Optional
import logging

class VectorDatabase:
    """
    Legacy VectorDatabase class. 
    Note: The project has largely migrated to EnhancedQdrantVectorDatabase 
    within data_collector.py for better Qdrant integration.
    """
    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "plants"):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.logger = logging.getLogger("vector_db")

    def connect(self):
        self.logger.info(f"Connecting to legacy VectorDatabase at {self.host}:{self.port}")
        return True

    def search(self, query_vector: Any, limit: int = 5):
        self.logger.warning("Legacy search called. No results returned.")
        return []

    def add_points(self, points: List[Any]):
        self.logger.warning("Legacy add_points called. Nothing added.")
        return False
