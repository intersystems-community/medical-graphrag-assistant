"""
Database connection module for IRIS.

Provides environment-aware connection management with sensible defaults
for local Docker IRIS instance (used on EC2 deployment).
"""

import os
from typing import Optional
import iris


class DatabaseConnection:
    """
    IRIS database connection manager with environment-based configuration.

    Defaults to localhost:32782 (Docker IRIS container) which is the
    standard deployment configuration on EC2.

    Environment Variables:
        IRIS_HOST: Database hostname (default: localhost)
        IRIS_PORT: Database port (default: 32782)
        IRIS_NAMESPACE: Database namespace (default: %SYS)
        IRIS_USERNAME: Database username (default: _SYSTEM)
        IRIS_PASSWORD: Database password (default: SYS)

    Example:
        # Use defaults (local Docker IRIS)
        conn = DatabaseConnection.get_connection()

        # Override with environment variables for different setup
        # export IRIS_HOST=192.168.1.100
        # export IRIS_PORT=1972
        conn = DatabaseConnection.get_connection()
    """

    # Default configuration (Local Docker IRIS)
    DEFAULT_CONFIG = {
        'hostname': 'localhost',
        'port': 32782,
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
    def get_connection(cls, **kwargs):
        """
        Create IRIS database connection.
        
        Args:
            **kwargs: Optional overrides for connection parameters (hostname, port, etc.)
        
        Returns:
            DBAPI connection object
            
        Raises:
            Exception: If connection fails
        """
        config = cls.get_config()
        # Only override with non-None kwargs
        for k, v in kwargs.items():
            if v is not None:
                config[k] = v
        
        try:
            import iris
            # Try standard import first
            if hasattr(iris, 'connect'):
                return iris.connect(**config)
            
            # Fallback to irissdk if iris.connect is missing
            # (Common issue with intersystems-irispython on some platforms)
            import iris.irissdk
            conn = iris.irissdk.IRISConnection()
            # Use _connect as connect() is not exposed in some versions
            conn._connect(
                config['hostname'], 
                config['port'], 
                config['namespace'], 
                config['username'], 
                config['password']
            )
            return conn

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
    def is_docker(cls) -> bool:
        """
        Check if configured database is using default Docker config.

        Returns:
            bool: True if using default localhost:32782 config
        """
        hostname = os.getenv('IRIS_HOST', cls.DEFAULT_CONFIG['hostname'])
        port = int(os.getenv('IRIS_PORT', cls.DEFAULT_CONFIG['port']))
        return hostname in ('localhost', '127.0.0.1') and port == 32782

    @classmethod
    def get_info(cls) -> str:
        """
        Get human-readable connection info string.

        Returns:
            str: Connection info
        """
        config = cls.get_config()
        if cls.is_docker():
            env = 'Docker'
        elif cls.is_local():
            env = 'Local'
        else:
            env = 'Remote'
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
