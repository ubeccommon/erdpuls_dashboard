#!/usr/bin/env python3
"""
Erdpuls Collective Threshold Model - Run Script
"""
import uvicorn
from app.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    print(f"""
    🌱 Erdpuls Collective Threshold Model
    =====================================
    Running at http://0.0.0.0:8004
    API Docs at http://0.0.0.0:8004/api/docs
    Debug mode: {settings.debug}
    
    "The community holds each offering into being."
    """)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.debug
    )
