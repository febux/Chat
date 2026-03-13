"""
Database constants.

MAX_RETRIES: Max number of retries for database connection attempts.
RETRY_DELAY: Delay in seconds between database connection attempts.
POOL_RECYCLE: Number of seconds after which a connection should be recycled if it's idle.
ssl_context: SSL context for secure database connections.
"""

import ssl

MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
POOL_RECYCLE = 3600  # 1 hour
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.VerifyMode.CERT_OPTIONAL
