from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import runs, health

app = FastAPI(title="Sentinel Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your dashboard's real URL once deployed
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(runs.router)