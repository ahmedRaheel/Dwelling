import logging
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api.v1.router import router
from app.core.config import get_settings
from app.core.database import SessionLocal

settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
app = FastAPI(title=settings.app_name, version='1.0.0', docs_url='/api/docs', openapi_url='/api/openapi.json')
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type', 'Accept-Language', 'X-Request-ID'])


@app.middleware('http')
async def request_correlation(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid4())
    if len(request_id) > 80 or any(ord(ch) < 32 for ch in request_id):
        request_id = str(uuid4())
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


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
