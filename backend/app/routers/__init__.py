from app.routers.fruits import router as fruits_router
from app.routers.product_feedback import router as product_feedback_router
from app.routers.recommendations import router as recommendations_router
from app.routers.users import router as users_router

__all__ = [
    "fruits_router",
    "product_feedback_router",
    "recommendations_router",
    "users_router",
]
