"""
Erdpuls Collective Threshold Model - FastAPI Application

Routers:
- api_router   : JSON API endpoints (/api/...)
- web_router   : HTML page routes including OER Library (/library, /library/resource)
- auth_router  : Authentication routes (/login, /register, /logout)
- admin_router : Admin panel routes (/admin/...)
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import api_router, web_router, auth_router
from .routers import admin as admin_router
from .routers.solidarity import router as solidarity_router
from .routers.solidarity import chooser as solidarity_chooser
from .routers.initiative_pages import router as initiative_pages_router

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Collective Threshold Model - A community-held approach to reciprocal economics",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(api_router)
app.include_router(web_router)   # includes /library and /library/resource (OER)
app.include_router(auth_router)
app.include_router(admin_router.router)

# Solidarity Financing (working title) — internal module, mounted per
# initiative at /{initiative_slug}/solidarity, with a chooser at
# /solidarity. Behind Erdpuls login with role facilitator or higher;
# deliberately NOT linked from any public initiative page. Both routers
# are registered before the catch-all below, which they cannot shadow:
# the chooser is a literal path and the module's routes are two segments.
app.include_router(solidarity_chooser)
app.include_router(solidarity_router)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": settings.app_name}


# LAST of all: catch-all /{slug} for per-initiative pages. Registered after every
# other route (including inline @app routes like /health) so it can never shadow
# them; unknown paths fall through to its 404.
app.include_router(initiative_pages_router)
