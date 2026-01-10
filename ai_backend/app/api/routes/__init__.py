# API Routes
from app.api.routes.complaint_routes import router as complaint_router
from app.api.routes.verification_routes import router as verification_router
from app.api.routes.analytics_routes import router as analytics_router

__all__ = ["complaint_router", "verification_router", "analytics_router"]
