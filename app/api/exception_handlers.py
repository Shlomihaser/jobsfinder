from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.exceptions import CompanyNotFoundError, CompanyAlreadyExistsError, CompanyValidationError


def register_exception_handlers(app: FastAPI):
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        messages = [f"{e['loc'][-1]}: {e['msg']}" for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": ", ".join(messages)})

    @app.exception_handler(CompanyNotFoundError)
    async def company_not_found_handler(request: Request, exc: CompanyNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(CompanyAlreadyExistsError)
    async def company_already_exists_handler(request: Request, exc: CompanyAlreadyExistsError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(CompanyValidationError)
    async def company_validation_handler(request: Request, exc: CompanyValidationError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error on {request.method} {request.url}: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
