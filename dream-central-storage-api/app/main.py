import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("uvicorn").info("Dream Central Storage API started")
    yield


app = FastAPI(title="Dream Central Storage API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Using lifespan above instead of deprecated on_event startup
