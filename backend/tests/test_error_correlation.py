"""No database needed: confirm error trace IDs survive Starlette's exception task boundary."""
import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from app.main import app, get_request_id, problem


@pytest.mark.asyncio
async def test_request_id_present_in_validation_errors():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/api/v1/listings', json={}, headers={'X-Request-ID': 'trace-test-42'})
    assert response.status_code == 422
    assert response.json()['error']['request_id'] == 'trace-test-42'
    assert response.headers['X-Request-ID'] == 'trace-test-42'


@pytest.mark.asyncio
async def test_request_id_present_in_unexpected_errors():
    # Only mounted for test; no database interaction or production exception disclosure.
    @app.get('/__test_fail_correlation')
    async def fail():
        raise RuntimeError('simulated unexpected error')

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url='http://test') as client:
        response = await client.get('/__test_fail_correlation', headers={'X-Request-ID': 'trace-failure-99'})
    assert response.status_code == 500
    assert response.json()['error']['request_id'] == 'trace-failure-99'
    assert response.headers['X-Request-ID'] == 'trace-failure-99'
