from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routes import router

app = FastAPI(title="RMIP-DSS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def home():
    return {"message": "Reinsurance Market Intelligence & Pricing Decision Support System"}
