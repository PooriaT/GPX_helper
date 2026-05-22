from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gpx_helper.api.config import API_VERSION, DEFAULT_ALLOWED_ORIGINS
from gpx_helper.api.routes.animation import router as animation_router
from gpx_helper.api.routes.telemetry import router as telemetry_router
from gpx_helper.api.routes.trim import router as trim_router
from gpx_helper.map_layers import frontend_map_layers


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title="GPX Helper API", version=API_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(DEFAULT_ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health_check() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "gpx-helper"})

    @app.get("/api/v1/capabilities")
    def capabilities() -> JSONResponse:
        return JSONResponse(
            {
                "version": API_VERSION,
                "endpoints": [
                    "POST /api/v1/gpx/trim-by-time",
                    "POST /api/v1/gpx/trim-by-video",
                    "POST /api/v1/gpx/trim-by-videos",
                    "POST /api/v1/gpx/map-animate/estimate",
                    "POST /api/v1/gpx/map-animate",
                    "POST /api/v1/gpx/telemetry-video/estimate",
                    "POST /api/v1/gpx/telemetry-video",
                ],
                "map_layers": frontend_map_layers(),
            }
        )

    app.include_router(trim_router, prefix="/api/v1")
    app.include_router(animation_router, prefix="/api/v1")
    app.include_router(telemetry_router, prefix="/api/v1")
    return app


app = create_app()
