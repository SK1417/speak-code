from fastapi import FastAPI
from .api import endpoints

app = FastAPI(title="Financial Dashboard API")

app.include_router(endpoints.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Financial Dashboard API"}
