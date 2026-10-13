from fastapi import FastAPI

app = FastAPI(
    title="STARA Customer Service API",
    description="Customer management and AI reply service",
    version="1.0.0",
)


@app.get("/")
def home():
    return {"message": "STARA API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}