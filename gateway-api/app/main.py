from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.schemas.database import engine
from app.schemas.models import Base
from app.api.v1.models import router as models_router
from app.api.v1.chat import router as chat_router
from app.api.v1.usage import router as usage_router
from app.api.v1.admin import router as admin_router
from app.middleware.correlation_id import CorrelationIDMiddleware
from app.middleware.metrics import MetricsMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (Alembic handles migrations; this is a safety net)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Internal LLM Gateway",
    version="0.1.0",
    description="Multi-tenant OpenAI-compatible gateway with routing, budgets, and governance.",
    lifespan=lifespan,
)

# CORS – allow admin UI origin in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(MetricsMiddleware)

# Prometheus metrics – mount the ASGI app directly to avoid routing inspection bugs
app.mount("/metrics", make_asgi_app())

# Routers
app.include_router(models_router, prefix="/v1")
app.include_router(chat_router, prefix="/v1")
app.include_router(usage_router, prefix="/v1")
app.include_router(admin_router)


@app.get("/health", tags=["infra"])
def health_check():
    return {"status": "ok"}


