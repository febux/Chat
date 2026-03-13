"""
Context Variables:
- `cid`: A context variable representing the client ID.
- `tenant`: A context variable representing the tenant ID.
"""

import contextvars

cid = contextvars.ContextVar("cid", default="-")
tenant = contextvars.ContextVar("tenant", default="-")
