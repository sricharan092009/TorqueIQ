
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.dataset_routes import router as dataset_router
app = FastAPI(
    title="TorqueIQ API",
    description="Automotive Engine Performance Analytics",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router)
app.include_router(dataset_router)


@app.get("/")
def home():
    return {
        "message": "TorqueIQ API is running",
        "status": "operational"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
