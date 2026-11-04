import logging
from contextvars import ContextVar
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError, SQLAlchemyError
from sqlalchemy import text
from app.api.v1.router import router
from app.core.config import get_settings
from app.core.database import SessionLocal

settings = get_settings()
logger = logging.getLogger("dwelling.api")
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="unknown")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
app = FastAPI(title=settings.app_name, version='1.0.0', docs_url='/api/docs', openapi_url='/api/openapi.json')
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type', 'Accept-Language', 'X-Request-ID'])


def problem(status: int, code: str, message: str, *, details=None) -> JSONResponse:
    payload = {"error": {"code": code, "message": message, "request_id": request_id_ctx.get()}}
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(payload, status_code=status)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else 'Request rejected'
    return problem(exc.status_code, f'HTTP_{exc.status_code}', message,
                   details=exc.detail if isinstance(exc.detail, dict) else None)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = [{"field": ".".join(map(str, error["loc"])), "message": error["msg"]}
              for error in exc.errors()]
    return problem(422, 'VALIDATION_ERROR', 'Please correct the highlighted fields.', details=fields)


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    logger.warning('Database constraint violation request_id=%s route=%s', request_id_ctx.get(), request.url.path)
    return problem(409, 'DATA_CONFLICT', 'This operation conflicts with existing data or a database constraint.')


@app.exception_handler((OperationalError))
async def operational_exception_handler(request: Request, exc: OperationalError):
    logger.exception('Database unavailable request_id=%s', request_id_ctx.get())
    return problem(503, 'DATABASE_UNAVAILABLE', 'The database is temporarily unavailable. Please retry.')


@app.exception_handler(ProgrammingError)
async def programming_exception_handler(request: Request, exc: ProgrammingError):
    logger.exception('Database schema mismatch request_id=%s', request_id_ctx.get())
    return problem(503, 'DATABASE_SCHEMA_MISMATCH', 'Database schema is not ready. An administrator must apply the migrations.')


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception('Unexpected API failure request_id=%s route=%s', request_id_ctx.get(), request.url.path)
    return problem(500, 'INTERNAL_ERROR', 'An unexpected error occurred. Contact support with the request ID.')


@app.middleware('http')
async def request_correlation(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid4())
    if len(request_id) > 80 or any(ord(ch) < 32 for ch in request_id):
        request_id = str(uuid4())
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    finally:
        request_id_ctx.reset(token)


@app.get('/api/health/live', tags=['Health'])
async def liveness():
    return {'status': 'ok'}


@app.get('/api/health/ready', tags=['Health'])
async def readiness():
    try:
        async with SessionLocal() as session:
            await session.execute(text('SELECT 1'))
        return {'status': 'ready'}
    except Exception:
        return JSONResponse({'status': 'unavailable'}, status_code=503)


app.include_router(router)
