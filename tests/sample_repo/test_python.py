"""Sample Python file for testing extraction."""

import asyncio
from typing import List, Optional

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, connection_string: str):
        self.connection = connection_string
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Establish database connection."""
        self.is_connected = True
        return True
    
    def disconnect(self):
        """Close database connection."""
        self.is_connected = False
    
    def query(self, sql: str, params: Optional[List] = None) -> List[dict]:
        """Execute SQL query and return results."""
        return []
    
    class Transaction:
        """Nested class for transaction management."""
        
        def __init__(self, db_manager):
            self.db = db_manager
        
        def commit(self) -> bool:
            """Commit transaction."""
            return True
        
        def rollback(self):
            """Rollback transaction."""
            pass

def calculate_statistics(data: List[float]) -> dict:
    """Calculate basic statistics for a dataset."""
    if not data:
        return {}
    
    def _mean(values):
        return sum(values) / len(values)
    
    return {
        'mean': _mean(data),
        'min': min(data),
        'max': max(data)
    }

async def process_batch(items: List[str]) -> int:
    """Process a batch of items asynchronously."""
    processed = 0
    for item in items:
        await asyncio.sleep(0.1)
        processed += 1
    return processed