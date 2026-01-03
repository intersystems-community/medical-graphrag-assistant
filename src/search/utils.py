"""
Utility functions for search services.
Provides parameterized SQL execution and connection handling.
"""

import os
import sys
from typing import Any, List, Optional, Tuple

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db.connection import get_connection

def execute_parameterized_query(cursor, sql: str, params: Optional[List[Any]] = None) -> List[Tuple]:
    """
    Execute a parameterized SQL query to prevent injection.
    
    Args:
        cursor: IRIS database cursor
        sql: SQL query string with ? placeholders
        params: List of parameters to bind to the placeholders
        
    Returns:
        List of result rows
    """
    if params is None:
        params = []
        
    cursor.execute(sql, params)
    return cursor.fetchall()

def get_iris_cursor():
    """
    Get a cursor to the IRIS database.
    
    Returns:
        Tuple of (connection, cursor)
    """
    conn = get_connection()
    return conn, conn.cursor()
