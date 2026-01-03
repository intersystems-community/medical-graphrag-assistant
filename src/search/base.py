"""
Base search service class for medical GraphRAG.
Handles configuration and database connections.
"""

import os
import sys
import yaml
from typing import Dict, Any

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db.connection import get_connection

class BaseSearchService:
    """Base class for search services providing shared infrastructure."""
    
    def __init__(self, config_path: str = "config/fhir_graphrag_config.yaml"):
        """
        Initialize base search service.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.connection = None
        self.cursor = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            # Fallback to AWS config if local config doesn't exist
            aws_config = "config/fhir_graphrag_config.aws.yaml"
            if os.path.exists(aws_config):
                self.config_path = aws_config
            else:
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def connect(self):
        """Connect to IRIS database."""
        if not self.connection:
            self.connection = get_connection()
            self.cursor = self.connection.cursor()
        return self.connection, self.cursor

    def close(self):
        """Close database connections."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            self.connection = None
