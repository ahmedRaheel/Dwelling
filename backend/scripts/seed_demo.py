"""Create fictional demo agency/listings through public APIs.

Usage:
  API_URL=http://localhost:8080/api/v1 DEMO_PASSWORD='a-strong-dev-password' python scripts/seed_demo.py
Never use generated demo asking prices as verified sales evidence.
"""
import json
import mimetypes
import os
from pathlib import Path
import urllib.error
import urllib.request
from uuid import uuid4

API_URL = os.environ.get('API_URL', 'http://localhost:8080/api/v1').rstrip('/')
PASSWORD = os.environ['DEMO_PASSWORD']
slug = os.environ.get('DEMO_SLUG') or f'demo-estates-{uuid4().hex[:8]}'


def post(path: str, payload: dict, token: str | None = None) -> dict:
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(f'{API_URL}{path}', data=data,
                                     headers={'Content-Type': 'application/json',
                                              **({'Authorization': f'Bearer {token}'} if token else {})},
                                     method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


owner = post('/auth/tenant/register', {
    'agency_name': 'Fictional Demo Estates', 'slug': slug, 'full_name': 'Demo Owner',
    'email': 'demo-owner@example.com', 'password': PASSWORD,
})
token = owner['access_token']
base = {'status': 'draft', 'city': 'Karachi', 'currency': 'PKR',
        'description': 'Fictional sample listing for demonstrating the PropTech marketplace.',
        'bedrooms': 2, 'bathrooms': 2, 'furnished': False}
listings = [
    {'title': 'Family house with sunny courtyard', 'kind': 'house', 'purpose': 'sale',
     'area_name': 'Gulshan-e-Iqbal', 'price': 24500000, 'area_sqft': 2400, 'bedrooms': 4},
    {'title': 'Modern apartment near parks', 'kind': 'apartment', 'purpose': 'rent',
     'area_name': 'Clifton', 'price': 115000, 'area_sqft': 1400, 'furnished': True},
    {'title': 'Corner commercial office building', 'kind': 'commercial_building', 'purpose': 'sale',
     'area_name': 'Shahrah-e-Faisal', 'price': 68000000, 'area_sqft': 5300, 'bedrooms': 0},
    {'title': 'Residential plot in developing block', 'kind': 'plot', 'purpose': 'sale',
     'area_name': 'Scheme 33', 'price': 11200000, 'area_sqft': 1800, 'bedrooms': 0, 'bathrooms': 0},
    {'title': 'Airy upper portion with separate meter', 'kind': 'portion', 'purpose': 'rent',
     'area_name': 'North Nazimabad', 'price': 66000, 'area_sqft': 1300,
     'portion': {'portion_kind': 'upper', 'floor_number': 1, 'separate_electricity_meter': True,
                 'separate_gas_meter': True, 'separate_water_meter': False}},
    {'title': 'Spacious lower family portion', 'kind': 'portion', 'purpose': 'rent',
     'area_name': 'PECHS', 'price': 72000, 'area_sqft': 1450,
     'portion': {'portion_kind': 'lower', 'floor_number': 0, 'separate_electricity_meter': True}},
    {'title': 'Independent third-floor residence', 'kind': 'portion', 'purpose': 'rent',
     'area_name': 'Gulistan-e-Johar', 'price': 48000, 'area_sqft': 1100,
     'portion': {'portion_kind': 'floor', 'floor_number': 3, 'separate_water_meter': True}},
    {'title': 'Twin-sharing PG with meal service', 'kind': 'pg', 'purpose': 'rent',
     'area_name': 'DHA Phase 2', 'price': 30000, 'area_sqft': 310, 'bedrooms': 1,
     'pg': {'room_type': 'twin', 'total_beds': 2, 'available_beds': 1,
            'food_included': True, 'rules': {'quiet_hours': '22:00-07:00'}}},
    {'title': 'Private single PG room near university', 'kind': 'pg', 'purpose': 'rent',
     'area_name': 'University Road', 'price': 26000, 'area_sqft': 150, 'bedrooms': 1,
     'pg': {'room_type': 'single', 'total_beds': 1, 'available_beds': 1,
            'food_included': False, 'rules': {}}},
    {'title': 'Affordable dormitory bed space', 'kind': 'pg', 'purpose': 'rent',
     'area_name': 'Gulshan-e-Maymar', 'price': 15000, 'area_sqft': 550, 'bedrooms': 1,
     'pg': {'room_type': 'dormitory', 'total_beds': 8, 'available_beds': 5,
            'food_included': True, 'rules': {'visitors': 'Common area only'}}},
]
def upload_photo(listing_id: str, photo_path: Path) -> None:
    boundary = 'proptech-seed-' + uuid4().hex
    photo_content = photo_path.read_bytes()
    mime = mimetypes.guess_type(photo_path.name)[0] or 'image/jpeg'
    fields = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="alt_text"\r\n\r\n'
        f'Illustrative demo image: {photo_path.stem}\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{photo_path.name}"\r\nContent-Type: {mime}\r\n\r\n'
    ).encode('utf-8')
    content = fields + photo_content + f'\r\n--{boundary}--\r\n'.encode('utf-8')
    request = urllib.request.Request(f'{API_URL}/listings/{listing_id}/photos', data=content,
                                     headers={'Authorization': f'Bearer {token}',
                                              'Content-Type': f'multipart/form-data; boundary={boundary}'}, method='POST')
    with urllib.request.urlopen(request, timeout=45):
        pass


photo_dir = Path(os.environ.get('DEMO_PHOTO_DIR', '')).expanduser() if os.environ.get('DEMO_PHOTO_DIR') else None
for spec in listings:
    item = post('/listings', {**base, **spec}, token)
    image = next((path for extension in ('jpg', 'jpeg', 'png', 'webp')
                  if photo_dir and (path := photo_dir / f"{spec['kind']}.{extension}").is_file()), None)
    if image:
        upload_photo(item['id'], image)
        post(f"/listings/{item['id']}/publish", {}, token)
        print(f"Published {item['kind']}: {item['title']} with authorized photo {image.name}")
    else:
        print(f"Created draft {item['kind']}: {item['title']} (add a real photo in Listing Studio)")
print(f'Agency slug: {slug}\nOwner email: demo-owner@example.com\nFictional demo inventory. Prices are illustrative.')
