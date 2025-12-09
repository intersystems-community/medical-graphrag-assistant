"""
Database connection module for IRIS.

Provides environment-aware connection management with sensible defaults
for AWS production IRIS instance.
"""

import os
from typing import Optional
import iris


class DatabaseConnection:
    """
    IRIS database connection manager with environment-based configuration.
    
    Defaults to AWS production IRIS (3.84.250.46:1972/%SYS) unless
    environment variables override.
    
    Environment Variables:
        IRIS_HOST: Database hostname (default: 3.84.250.46)
        IRIS_PORT: Database port (default: 1972)
        IRIS_NAMESPACE: Database namespace (default: %SYS)
        IRIS_USERNAME: Database username (default: _SYSTEM)
        IRIS_PASSWORD: Database password (default: SYS)
    
    Example:
        # Use defaults (AWS IRIS)
        conn = DatabaseConnection.get_connection()
        
        # Override with environment variables
        # export IRIS_HOST=localhost
        # export IRIS_PORT=32782
        conn = DatabaseConnection.get_connection()
    """
    
    # Default configuration (AWS Production IRIS)
    DEFAULT_CONFIG = {
        'hostname': '3.84.250.46',
        'port': 1972,
        'namespace': '%SYS',
        'username': '_SYSTEM',
        'password': 'SYS'
    }
    
    @classmethod
    def get_config(cls) -> dict:
        """
        Get database configuration from environment variables with defaults.
        
        Returns:
            dict: IRIS connection parameters
        """
        return {
            'hostname': os.getenv('IRIS_HOST', cls.DEFAULT_CONFIG['hostname']),
            'port': int(os.getenv('IRIS_PORT', cls.DEFAULT_CONFIG['port'])),
            'namespace': os.getenv('IRIS_NAMESPACE', cls.DEFAULT_CONFIG['namespace']),
            'username': os.getenv('IRIS_USERNAME', cls.DEFAULT_CONFIG['username']),
            'password': os.getenv('IRIS_PASSWORD', cls.DEFAULT_CONFIG['password'])
        }
    
    @classmethod
    def get_connection(cls):
        """
        Create IRIS database connection.
        
        Returns:
            DBAPI connection object
            
        Raises:
            Exception: If connection fails
            
        Example:
            >>> conn = DatabaseConnection.get_connection()
            >>> cursor = conn.cursor()
            >>> cursor.execute("SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages")
            >>> count = cursor.fetchone()[0]
            >>> print(f"Images: {count}")
            >>> conn.close()
        """
        config = cls.get_config()
        try:
            return iris.connect(**config)
        except Exception as e:
            # Add context to error message
            raise ConnectionError(
                f"Failed to connect to IRIS at {config['hostname']}:{config['port']}/{config['namespace']}. "
                f"Error: {str(e)}"
            ) from e
    
    @classmethod
    def is_local(cls) -> bool:
        """
        Check if configured database is on localhost.
        
        Returns:
            bool: True if hostname is localhost or 127.0.0.1
        """
        hostname = os.getenv('IRIS_HOST', cls.DEFAULT_CONFIG['hostname']).lower()
        return hostname in ('localhost', '127.0.0.1', '::1')
    
    @classmethod
    def is_aws(cls) -> bool:
        """
        Check if configured database is AWS production instance.
        
        Returns:
            bool: True if using default AWS config
        """
        hostname = os.getenv('IRIS_HOST', cls.DEFAULT_CONFIG['hostname'])
        return hostname == cls.DEFAULT_CONFIG['hostname']
    
    @classmethod
    def get_info(cls) -> str:
        """
        Get human-readable connection info string.
        
        Returns:
            str: Connection info (hostname masked for security)
        """
        config = cls.get_config()
        env = 'AWS' if cls.is_aws() else ('Local' if cls.is_local() else 'Custom')
        return f"{env} IRIS @ {config['hostname']}:{config['port']}/{config['namespace']}"


# Convenience function for backward compatibility
def get_connection():
    """
    Create IRIS database connection.
    
    This is a convenience wrapper around DatabaseConnection.get_connection()
    for simpler imports.
    
    Returns:
        DBAPI connection object
        
    Example:
        >>> from src.db.connection import get_connection
        >>> conn = get_connection()
        >>> cursor = conn.cursor()
    """
    return DatabaseConnection.get_connection()


if __name__ == '__main__':
    # Test connection
    print("Testing IRIS database connection...")
    print(f"Config: {DatabaseConnection.get_info()}")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages")
        count = cursor.fetchone()[0]
        
        print(f"✅ Connected successfully!")
        print(f"Images in database: {count:,}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check network connectivity to AWS IRIS")
        print("2. Verify credentials are correct")
        print("3. Check if VPN/bastion is required")
        print("4. Try setting environment variables:")
        print("   export IRIS_HOST=localhost")
        print("   export IRIS_PORT=32782")
