from fastapi import FastAPI, Request
from app.config import get_settings
from app.database import init_db
from app.api.routes import students, sms
from app.utils.logger import setup_logger
from contextlib import asynccontextmanager
import time
from starlette.middleware.cors import CORSMiddleware

settings = get_settings()

logger = setup_logger(settings.log_level)

origins = [
    "http://localhost:5173",  # Your frontend's origin for development
    "https://bee.juniorflamebet.workers.dev",  # Your React app on Cloudflare Workers
    "https://api-proxy.juniorflamebet.workers.dev",  # Your proxy worker
    "https://*.juniorflamebet.workers.dev",  # Any subdomain of your workers
    "https://internally-alive-bream.ngrok-free.app",
    "https://bee-669.pages.dev"
    # You can add other origins if needed
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.settings = settings
    await init_db()
    setup_logger(settings.log_level)
    yield
    # Shutdown
    # Add any shutdown logic here if needed

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(sms.router, prefix="/api/sms", tags=["sms"])
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"Registered route: {route.path}")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the School Management System"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

