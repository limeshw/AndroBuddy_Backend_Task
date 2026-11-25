from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.base import Base
from app.db.session import engine
from app.routers.auth import router as auth_router
from app.routers.cart import router as cart_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create tables on startup if not present
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ShopSphere — Customer, Cart & Orders API",
    description="Backend assignment for ShopSphere e-commerce (BE-2 Track)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers
app.include_router(auth_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(products_router)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "service": "ShopSphere Customer, Cart & Orders API",
        "status": "healthy",
        "docs": "/docs",
    }

