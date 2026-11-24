from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_models
from .routers import jobs, matches, resumes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title="Job Match MVP API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router)
app.include_router(matches.router)
app.include_router(jobs.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
