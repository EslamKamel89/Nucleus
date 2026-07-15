from fastapi import FastAPI

app = FastAPI(title="Nucleus")


@app.get("/health")
def health():
    return {"status": "ok"}
