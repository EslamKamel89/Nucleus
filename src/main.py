from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.db.main import dispose, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("startup: performing lightweight app checks and actions")
    await init_db()
    print("startup COMPLETED")
    yield
    print("shutdown: cleaning up")
    await dispose()
    print("shutdown COMPLETED")


app = FastAPI(title="Nucleus", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
