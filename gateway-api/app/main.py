from fastapi import FastAPI

app = FastAPI(title="Internal LLM Gateway")


@app.get("/health")
def health_check():
    return {"status": "ok"}
