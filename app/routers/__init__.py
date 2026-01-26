"""
Erdpuls Collective Threshold Model - Routers
"""
from .api import router as api_router
from .web import router as web_router
from .auth import router as auth_router

__all__ = ['api_router', 'web_router', 'auth_router']
