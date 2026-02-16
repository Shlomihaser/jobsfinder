from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.controllers import company_controller
from app.api.exception_handlers import register_exception_handlers


app = FastAPI(
    title=settings.PROJECT_NAME,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(company_controller.router, prefix="/api/companies", tags=["companies"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Finder API...")

@app.get("/")
def read_root():
    return {"message": "JobFinder API is running"}
