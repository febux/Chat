"""
Context manager for managing the lifespan of FastAPI applications and their mounted applications.
"""

import contextlib

import fastapi.routing
from fastapi import FastAPI
from socketio import ASGIApp
from starlette.staticfiles import StaticFiles


@contextlib.asynccontextmanager
async def cascade_lifespan(parent: FastAPI):
    """
    Context manager for managing the lifespan of FastAPI applications and their mounted applications.

    :param parent: The FastAPI application instance to which the lifespan is being applied.
    """
    async with contextlib.AsyncExitStack() as stack:
        for route in parent.router.routes:
            if isinstance(route.app, StaticFiles) or isinstance(route.app, ASGIApp):
                continue
            if isinstance(route, fastapi.routing.Mount):
                await stack.enter_async_context(route.app.router.lifespan_context(route.app))
        yield
