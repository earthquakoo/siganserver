from fastapi import Request
from fastapi.responses import JSONResponse

import src.application.exceptions.exceptions as exceptions

def exception_handler(request: Request, exc: exceptions.BaseCustomException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
