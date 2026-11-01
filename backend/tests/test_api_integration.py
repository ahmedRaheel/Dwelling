"""Run against a fresh disposable Postgres/pgvector DB with Alembic migrations applied."""
from io import BytesIO
from uuid import uuid4
from PIL import Image
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


def jpeg_payload() -> bytes:
    out = BytesIO()
    Image.new('RGB', (70, 60), (130, 150, 140)).save(out, format='JPEG')
    return out.getvalue()


@pytest.mark.asyncio
async def test_tenant_isolation_pg_and_customer_inquiry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        async def agency(label):
            slug = f'{label}-{uuid4().hex[:12]}'
            response = await client.post('/api/v1/auth/tenant/register', json={
                'agency_name': label, 'slug': slug, 'full_name': 'Agency Owner',
                'email': 'owner@example.com', 'password': 'SafePassword-12345',
            })
            assert response.status_code == 201, response.text
            return slug, response.json()['access_token']

        _, token_a = await agency('agency-a')
        slug_b, token_b = await agency('agency-b')
        headers_a = {'Authorization': f'Bearer {token_a}'}
        headers_b = {'Authorization': f'Bearer {token_b}'}
        payload = {'title': 'Quiet shared room by park', 'kind': 'pg', 'purpose': 'rent',
                   'status': 'draft', 'city': 'Karachi', 'area_name': 'Clifton',
                   'price': '22000', 'area_sqft': '180', 'bedrooms': 1, 'bathrooms': 1,
                   'description': 'An actual room advertisement with quiet hours, shared access, and meals offered on request.',
                   'pg': {'room_type': 'twin', 'total_beds': 2, 'available_beds': 1,
                          'food_included': True, 'rules': {'curfew': '23:00'}}}
        created = await client.post('/api/v1/listings', headers=headers_a, json=payload)
        assert created.status_code == 201, created.text
        item = created.json()
        assert item['pg']['food_included'] is True
        assert item['photos'] == []
        out = BytesIO()
        Image.new('RGB', (160, 120), (150, 145, 130)).save(out, format='JPEG')
        out.seek(0)
        upload = await client.post(f"/api/v1/listings/{item['id']}/photos", headers=headers_a,
                                   files={'file': ('bedroom.jpg', out, 'image/jpeg')},
                                   data={'alt_text': 'Bedroom by the window'})
        assert upload.status_code == 201, upload.text
        photo = upload.json()
        assert photo['is_cover'] is True
        # A private draft gallery cannot be opened anonymously or by a different tenant.
        draft_file = await client.get(photo['url'])
        assert draft_file.status_code == 404
        private_file = await client.get(photo['url'], headers=headers_a)
        assert private_file.status_code == 200 and private_file.headers['content-type'].startswith('image/webp')
        readiness = await client.get(f"/api/v1/listings/{item['id']}/readiness", headers=headers_a)
        assert readiness.json()['ready'] is True
        published = await client.post(f"/api/v1/listings/{item['id']}/publish", headers=headers_a)
        assert published.status_code == 200, published.text
        assert published.json()['status'] == 'published'
        assert (await client.get(photo['thumbnail_url'])).status_code == 200
        item = published.json()
        assert (await client.get(f"/api/v1/listings/{item['id']}")).status_code == 200
        forbidden_upload = await client.post(f"/api/v1/listings/{item['id']}/photos", headers=headers_b,
                                             files={'file': ('a.jpg', jpeg_payload(), 'image/jpeg')})
        assert forbidden_upload.status_code == 403
        forbidden_update = await client.patch(f"/api/v1/listings/{item['id']}", headers=headers_b,
                                              json={'expected_version': item['version'], 'title': 'Hijacked listing'})
        assert forbidden_update.status_code == 403
        # Cross-agency customer inquiry must route to listing agency, not leak broker CRM.
        signup = await client.post('/api/v1/auth/register', json={
            'tenant_slug': slug_b, 'full_name': 'Interested Customer',
            'email': 'customer@example.com', 'password': 'SafePassword-12345',
        })
        assert signup.status_code == 201, signup.text
        headers_customer = {'Authorization': f"Bearer {signup.json()['access_token']}"}
        inquiry = await client.post('/api/v1/leads/inquiries', headers=headers_customer, json={
            'property_id': item['id'], 'contact_name': 'Interested Customer',
            'contact_email': 'customer@example.com', 'message': 'Please share viewing slots',
        })
        assert inquiry.status_code == 201, inquiry.text
        own_inquiries = await client.get('/api/v1/leads/mine', headers=headers_customer)
        assert own_inquiries.status_code == 200 and len(own_inquiries.json()) == 1
        broker_leads = await client.get('/api/v1/leads', headers=headers_a)
        assert broker_leads.status_code == 200 and len(broker_leads.json()) == 1
        customer_crm = await client.get('/api/v1/leads', headers=headers_customer)
        assert customer_crm.status_code == 403
        # No invented valuation for cold start.
        valuation = await client.get(f"/api/v1/ai/valuation/{item['id']}")
        assert valuation.status_code == 200
        assert valuation.json()['status'] == 'insufficient_data'


@pytest.mark.asyncio
async def test_anonymous_cannot_publish():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/api/v1/listings', json={
            'title': 'A small rental house', 'kind': 'house', 'purpose': 'rent',
            'city': 'Karachi', 'price': '50000', 'area_sqft': '850',
        })
        assert response.status_code == 401
