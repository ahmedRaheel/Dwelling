# Dwelling — PropTech SaaS v3 (Marketplace & Agency Edition)

A multi-tenant **real-estate SaaS reference implementation** with FastAPI, PostgreSQL/pgvector, a React 19 frontend, English/Urdu language switching, saved searches, a public agency directory, viewing requests, floor plans, comparison tools, a broker CRM, and explainable AI-assisted matching/asking-price estimates. The source is supplied together; no external proprietary services are required for the core marketplace.

> **Release integrity:** This is a comprehensive implementation intended for engineering teams to deploy, extend, and harden. It has static syntax checks but has **not** been fully exercised against a running PostgreSQL, Docker, or browser environment in the author's build environment. Do not call it audited, production-certified, or assume financial predictions are accurate. Follow the production checklist below before exposing real customer data.


## v3: Improvements informed by a real-estate marketplace benchmark

This release keeps Dwelling's own **quiet editorial design**: purposeful property photography,
structured listing facts, restrained typography, and useful workspaces rather than a generic
AI dashboard. Zameen.com was reviewed for category/search workflows, housing-society discovery,
agency profiles, saved searches, seller media, and buyer calculators. We designed our own
components and implementation rather than copying their markup or licensed data.

### Included in v3

| Capability | API / screen | Notes |
| --- | --- | --- |
| Society, phase/block, bathrooms and bounding-box search | `GET /api/v1/listings` | Existing city/type/price/area filters remain; latitude/longitude optional and public |
| Verified-data-free locality hints | `GET /api/v1/discovery/locations` | Suggestions arise only from currently published listings |
| Saved searches | `/api/v1/discovery/saved-searches` and Customer Portal | In-app match counts and mark-reviewed; **no scheduled email** |
| Compare 2–4 advertisements | `GET /api/v1/discovery/compare?ids=...` and `/compare` | Device-local selection; same published data visible to customers |
| Public agency directory & opt-in profile | `/api/v1/agencies` and `/agencies/me` | Self-reported agency bio, public phone/email, live inventory count |
| Structured viewing requests | `/api/v1/viewings` and broker/customer workspaces | Agency confirms/declines; a request is never mislabeled as confirmed |
| Advertising enhancements | Listing Studio | Society, block, negotiable price, ready-to-move flag, HTTPS YouTube/Vimeo tour |
| Floor plan images | `POST /api/v1/listings/{id}/photos` (`category=floorplan`) | Private same as photo gallery; not valid as cover |
| Buyer tools | `/tools` | Local estimate of amortizing mortgage; regional area-unit converter |
| Mobile navigation | Navbar | Agencies, buyer tools, comparison and workspace reachable on mobile |

### New database migration

`0003_discovery_workspace.py` adds property and public agency attributes, categorized media,
user-owned `saved_searches`, and cross-tenant `viewing_requests`. The migration enables **FORCE
ROW LEVEL SECURITY** on both new tenant-scoped tables. Cross-agency requests are inserted by a
restricted `SECURITY DEFINER` function that derives the receiving agency from the published
property, not from a caller-supplied tenant ID. A broker sees appointments only for their own
properties; owners/admins may see their agency appointments. Saved searches are scoped to the
creator's tenant and user.

### New REST API summary

```text
GET     /api/v1/agencies?city=Karachi
GET     /api/v1/agencies/me                 (agency account)
PATCH   /api/v1/agencies/me                 (owner/admin)
GET     /api/v1/agencies/{slug}
GET     /api/v1/discovery/locations?q=DHA&city=Karachi
GET     /api/v1/discovery/compare?ids={uuid}&ids={uuid}
GET     /api/v1/discovery/saved-searches
POST    /api/v1/discovery/saved-searches
GET     /api/v1/discovery/saved-searches/{id}/matches
POST    /api/v1/discovery/saved-searches/{id}/check
DELETE  /api/v1/discovery/saved-searches/{id}
POST    /api/v1/viewings
GET     /api/v1/viewings/mine
GET     /api/v1/viewings/agency
PATCH   /api/v1/viewings/{id}
POST    /api/v1/listings/{id}/photos         (FormData category=gallery|floorplan)
```

Example saving a search:

```bash
curl -X POST http://localhost:8080/api/v1/discovery/saved-searches \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Family homes in DHA", "filters":{"city":"Karachi","society":"DHA","minimum_bedrooms":3}, "alerts_enabled":true}'
```

Example requesting a viewing (ISO 8601 timezone required):

```bash
curl -X POST http://localhost:8080/api/v1/viewings \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"property_id":"YOUR-PUBLISHED-PROPERTY-UUID", "preferred_at":"2026-11-07T14:00:00+05:00", "contact_name":"Customer", "contact_phone":"+923001234567", "note":"Afternoon visit requested"}'
```

The buyer financing calculator uses user-entered figures, not live lender rates. It excludes fees,
taxes, insurance and variable-rate adjustments. The unit converter explicitly distinguishes
225, 250 and 272.25 square-foot marla conventions because they differ by area/society.

**Not shipped:** statutory title verification, licensed cadastral/plot-finder overlays, independently
verified agents, full email/SMS/push alerts, payment-based premium placements, live bank financing,
web-based map drawing, end-to-end browser automation, or Urdu translation of every new screen.
These require trusted data, commercial integrations, moderation operations and more testing.
Do not make "verified" claims about self-reported agency profiles or advertised asking prices.

**Build checks:** Python compile + SQLAlchemy mapping configuration using a local pgvector type stub,
Pydantic validation smoke checks, and all frontend TS/TSX parsed without syntax errors. The
`backend/tests/test_discovery_workflows.py` integration suite is included but **cannot be claimed
passed** here because this environment has no running PostgreSQL, pgvector extension, Docker,
or installed frontend dependencies. Run migrations, integration tests and `npm run build` in your
proper environment before deployment.

## 1. Repository layout

```text
proptech_saas/
├── .env.example
├── compose.yaml
├── .github/workflows/ci.yml
├── docker/
│   ├── init-db.sh
│   └── nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-ai.txt
│   ├── requirements-dev.txt
│   ├── alembic.ini
│   ├── alembic/env.py
│   ├── alembic/versions/{0001_initial,0002_listing_media}.py
│   ├── app/
│   │   ├── main.py
│   │   ├── core/{config,database,security}.py
│   │   ├── models/entities.py
│   │   ├── schemas/domain.py
│   │   ├── api/deps.py
│   │   ├── api/v1/{auth,listings,media,leads,ai_engine,router}.py
│   │   └── services/{embeddings,pricing,recommendations,media}.py
│   ├── scripts/{import_trends,seed_demo,prune_media}.py
│   └── tests/{test_validation,test_media,test_api_integration}.py
└── frontend/
    ├── Dockerfile, nginx.conf, package.json, vite.config.ts
    ├── tailwind.config.js, components.json, tsconfig.json
    ├── src/api/{client,types}.ts
    ├── src/context/{AuthContext,LanguageContext}.tsx
    ├── src/components/{Navbar,LanguageToggle,PropertyCard}.tsx
    ├── src/components/listings/{PropertyImage,PhotoManager}.tsx
    ├── src/components/ui/{button,card,input}.tsx
    └── src/pages/{AuthPage,Marketplace,PropertyDetail,BrokerDashboard,CustomerPortal,ListingComposer}.tsx
```

## 2. Run locally with Docker Compose

Prerequisites: Docker Engine + Compose v2, around 2 GB of free RAM for the default app. Enabling the sentence-transformer model requires significantly more disk/RAM. Run commands from the project root:

```bash
cp .env.example .env
# Change the development passwords and JWT_SECRET before starting.
docker compose up --build -d
# Check migration, backend, and front end
docker compose ps
docker compose logs --tail=100 migrate backend frontend
```

- Frontend: **http://localhost:8080**
- OpenAPI / interactive Swagger: **http://localhost:8080/api/docs**
- Liveness: **http://localhost:8080/api/health/live**
- Readiness: **http://localhost:8080/api/health/ready**
- Database: `localhost:5432`, bound to loopback only

The `migrate` service executes `alembic upgrade head` before `backend` starts. The `postgres` service runs the *pgvector* extension image. `init-db.sh` creates a **non-superuser, NOBYPASSRLS** application role. Only the migration job uses PostgreSQL administrator credentials. Environment passwords are for development only.

**Existing PostgreSQL volume:** initialization scripts only run on an empty volume. To retain data, manually provision the application role and inspect migrations; do not destroy volumes in a live environment. To remove a *disposable local development* database: `docker compose down -v` (destructive).

### Optional fictional demo inventory

```bash
# Creates fictional DRAFT listings across all six property types.
export DEMO_PASSWORD='your-strong-demo-password'
python backend/scripts/seed_demo.py
# To publish demo ads, supply your own licensed/consented photos named:
# house.jpg, apartment.jpg, portion.jpg, pg.jpg, plot.jpg, commercial_building.jpg
DEMO_PHOTO_DIR=/path/to/your/photos python backend/scripts/seed_demo.py
```

The script prints an agency slug. Use that slug, `demo-owner@example.com`, and the chosen password on the sign-in page. With no photo folder it intentionally leaves all ads as drafts: published advertisements must have a genuine uploaded image. With a photo folder it uploads and publishes them. It intentionally adds fewer than twenty comparable items, so no cold-start valuation appears.

## 3. Developer mode without containers

Use PostgreSQL 16+ with pgvector installed; create the `proptech_app` role and configure `DATABASE_URL`/`MIGRATION_DATABASE_URL` (see Compose). Then:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export JWT_SECRET='replace-with-long-random-dev-only-secret'
export DATABASE_URL='postgresql+asyncpg://proptech_app:local_app_password@localhost:5432/proptech'
export MIGRATION_DATABASE_URL='postgresql+psycopg://postgres:local_db_admin_password@localhost:5432/proptech'
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173; Vite proxies /api to localhost:8000
```

## 4. Tenancy and data access

- An **agency** is a tenant with an immutable UUID and a unique `slug`.
- Tenant registration bootstraps an `owner` user; a customer registers with a known agency slug.
- Authenticated roles: **owner, admin, broker, customer**. Owners/admins can create broker/admin staff accounts.
- Every request opens a database transaction (committed before the HTTP response is sent) and sets `app.tenant_id` and `app.user_id` with transaction-local `set_config(..., true)`. The app's PostgreSQL role is not a superuser, table owner, or BYPASSRLS role.
- **Published listings** may be read across tenants for the public marketplace, whereas draft/archived listings, employee records, CRM records and predictions are scoped by RLS.
- Customers can send inquiries to listings belonging to other agencies through a **fixed-parameter `SECURITY DEFINER` database function**. The function obtains the signed-in customer identity from the trusted session context and chooses the listing's tenant itself. The customer can view their own inquiry status but does not receive broker-internal notes.
- User-event interactions are private at the row level; the recommender can access only **k-anonymized collaborative scores** across tenants (minimum three distinct peers), not users' interaction histories.
- Staff can create/update property listings and CRM leads; brokers can edit only listings they created, while owners/admins can edit all within their agency.
- `DELETE /listings/{id}` archives rather than permanently deleting the property. Updates require `expected_version` to reject stale edits.

**RLS security detail:** Custom PostgreSQL settings such as `app.tenant_id` are set by trusted application code. Never grant end users raw SQL access as the application DB role; lock down SQL injection and keep all SQL parameterized. Add separate administrative privileges for any background jobs and carefully review `SECURITY DEFINER` functions.

## 5. Property modeling

| Type | `kind` | `purpose` | Distinct detail model |
|---|---|---|---|
| Full house | `house` | sale/rent | None |
| Commercial building | `commercial_building` | sale/rent | None |
| Plot | `plot` | sale/rent | None |
| Standalone apartment | `apartment` | sale/rent | None |
| Upper/lower/floor portion | `portion` | sale/rent | `portion_details` with floor, optional parent and independent electricity/gas/water flags |
| Paying guest / shared room | `pg` | rent **only** | `pg_details` with single/twin/dormitory, bed occupancy, food inclusion and rules JSON |

All types share location, asking price, area, beds, baths, description, creator, publication status and a 384-dimension nullable vector. Rich advertisements additionally support editorial highlights, amenity lists, public opt-in contact phone, and optional map coordinates.

**Photo gallery and floor plans:** Each listing can carry up to 24 image files in `property_photos` with owner-tenant identity, ordering, cover selection, alt text, size and generated thumbnail. Image uploads are categorized as `gallery` or `floorplan` (a floor plan cannot be the listing cover). Images are uploaded through authenticated REST multipart requests, decoded and re-encoded as WebP using Pillow, with EXIF/GPS removed. Accepted formats are JPEG/PNG/WebP up to 12 MB and 30 megapixels. Draft images require bearer authorization; published images are public through an access-checked endpoint. Media is stored on a Docker-persisted **private** volume under `/srv/media` in Docker (`./.media` in local developer mode), not in the frontend's static directory. File removal is deferred to an orphan sweep after DB commits/rollbacks to prevent a failed transaction from destroying live media. This implementation deliberately does not present the local volume as a multi-node/object-store deployment solution.

## 6. REST API reference

All application resources use `/api/v1`. API schemas and live examples are in OpenAPI (`/api/docs`).

| Method | Endpoint | Auth/access | Summary |
|---|---|---|---|
| POST | `/auth/tenant/register` | Public | Create tenant + initial owner |
| POST | `/auth/register` | Public | Register customer under tenant slug |
| POST | `/auth/login` | Public | Log in with tenant slug, email, password |
| POST | `/auth/refresh` | Refresh token | Rotate/revoke refresh token |
| POST | `/auth/logout` | User | Revoke refresh token |
| GET | `/auth/me` | User | Current identity/role/preferences |
| PATCH | `/auth/me/preferences` | User | Customer matching preferences |
| POST | `/auth/staff` | Owner/admin | Invite/create broker or admin account |
| GET | `/listings` | Public | Paginate/filter by city, kind, purpose, text, price, bedrooms, area, amenities and sort |
| GET | `/listings/saved` | User | List a customer's bookmarked published ads |
| DELETE | `/listings/saved/{id}` | User | Remove own bookmarks |
| GET | `/listings/{id}` | Public for published | Full listing, portion/PG detail |
| POST | `/listings` | Broker/admin/owner | Create a **draft** listing |
| GET | `/listings/{id}/readiness` | Listing editor | Publication blockers, improvement tips and score |
| POST | `/listings/{id}/publish` | Listing editor | Publish after readiness validation |
| POST | `/listings/{id}/unpublish` | Listing editor | Return published ad to draft |
| POST | `/listings/{id}/photos` | Listing editor | Multipart JPEG/PNG/WebP upload + thumbnail + EXIF removal |
| GET | `/listings/{id}/photos` | Public for published, editor for draft | Ordered gallery metadata |
| GET | `/listings/{id}/photos/{photo_id}/file` | Public for published, editor for draft | WebP image (`?variant=thumb`) |
| PATCH | `/listings/{id}/photos/{photo_id}` | Listing editor | Set alt text and cover |
| PUT | `/listings/{id}/photos/order` | Listing editor | Set complete photo order |
| DELETE | `/listings/{id}/photos/{photo_id}` | Listing editor | Remove photo metadata, queue for orphan sweep |
| PATCH | `/listings/{id}` | Listing editor | Patch with optimistic version |
| DELETE | `/listings/{id}` | Listing editor | Archive listing |
| GET | `/leads` | Broker/admin/owner | Agency CRM leads |
| POST | `/leads` | Broker/admin/owner | Manually create agency lead |
| PATCH | `/leads/{id}` | Broker/admin/owner | Move CRM lead stage and edit notes |
| POST | `/leads/inquiries` | User | Send inquiry to any published agency listing |
| GET | `/leads/mine` | User | Own inquiries, with no private broker notes |
| POST | `/ai/predict` | User | Estimate PKR listing asking price from features |
| GET | `/ai/valuation/{id}` | Public for published | Estimate asking price; show sample count and MAE |
| GET | `/ai/rent-forecast/{id}` | Public for published | Capped monthly rental trend extrapolation |
| GET | `/ai/recommendations` | User | Ranked preferences + vector + collaborative matches |
| POST | `/ai/interactions` | User | Record view/save/inquiry action |
| GET | `/ai/broker/matches` | Broker/admin/owner | Rank lead-to-inventory candidates with reasons |
| GET | `/ai/trends` | Public | Reviewed monthly area market benchmarks |

### Example: create an agency, draft PG listing, add photo, and publish

```bash
curl -X POST http://localhost:8080/api/v1/auth/tenant/register \
  -H 'Content-Type: application/json' \
  -d '{"agency_name":"My Realty","slug":"my-realty","full_name":"Agency Owner", "email":"owner@example.com","password":"Choose-A-Strong-Password"}'
# Copy the returned access_token; API accepts it in Authorization: Bearer $TOKEN

curl -X POST http://localhost:8080/api/v1/listings \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Twin sharing room near university","kind":"pg","purpose":"rent","status":"draft","city":"Karachi","area_name":"Gulshan-e-Iqbal","description":"Bright shared room with a practical layout, convenient transport and clear house rules.","price":25000,"area_sqft":275,"bedrooms":1,"bathrooms":1,"highlights":["Short walk to bus route","Meals optional"],"amenities":["Internet","Water supply","Security"],"pg":{"room_type":"twin","total_beds":2,"available_beds":1,"food_included":true,"rules":{"quiet_hours":"22:00-07:00"}}}'
# Copy the `id` from the response into LISTING_ID.
curl -X POST "http://localhost:8080/api/v1/listings/$LISTING_ID/photos" \
  -H "Authorization: Bearer $TOKEN" -F "file=@/path/to/your/bedroom.jpg" -F 'alt_text=Bright shared bedroom'
curl -X GET "http://localhost:8080/api/v1/listings/$LISTING_ID/readiness" \
  -H "Authorization: Bearer $TOKEN"
curl -X POST "http://localhost:8080/api/v1/listings/$LISTING_ID/publish" \
  -H "Authorization: Bearer $TOKEN"
```

### Public marketplace query

```bash
curl 'http://localhost:8080/api/v1/listings?city=Karachi&kind=portion&purpose=rent&page=1&size=12'
```

## 7. AI behavior and limitations

**Asking-price estimator:** The service trains an in-process scikit-learn random forest on **published asking prices** for comparable `kind` and `purpose` in PKR. It log-transforms prices, uses structured categorical/numeric features, evaluates a holdout set, then fits a final model. Asking prices are **not** completed sales/leases and therefore do not prove a property's market value. `sample_count` and a holdout `MAE` are returned. A dataset of fewer than `MIN_TRAINING_SAMPLES` comparable records produces `status: insufficient_data`; it does not fabricate a number. The model is cached per API worker and refreshes when the observed listing count/latest update changes. Trained models and holdout metrics are not persisted as versioned artifacts yet.

**Rent outlook:** Requires at least four verified monthly rent benchmarks for the property's **city + area + kind**. Fits a log-linear monthly trend, bounds drift to ±3% per month and anchors the projection to current asking rent. This is a directional scenario, **not a guaranteed rental forecast**.

**Customer recommender:** Uses saved preference matching (city, property kind, purpose, budget, bedrooms), optionally multilingual semantic vector similarity, and privacy-thresholded item-to-item collaborative scores from peer saving/inquiry events. Reasons accompany rankings. Users' raw cross-tenant events are not exposed.

**Broker lead matching:** Scores lead-to-listing matches using the original inquiry's property characteristics and the stated budget; reports explainable heuristics, not trained conversion probabilities.

**Semantic vectors:** `EMBEDDINGS_ENABLED=false` by default, to avoid automatic large-model downloads or pretending embeddings exist. To switch on **actual multilingual semantic search**:

```bash
# Set in .env
INSTALL_AI=true
EMBEDDINGS_ENABLED=true
# Make the chosen 384-dimension multilingual MiniLM model accessible to containers.
docker compose up -d --build
```

The optional `requirements-ai.txt` installs SentenceTransformers with `paraphrase-multilingual-MiniLM-L12-v2` (384-dim) and encodes on a worker thread. Download/cache the model under your deployment artifact policy; do not rely on live downloads in restricted production networks. Update existing listings via the API to calculate vectors after enabling the service, or add a controlled backfill job. Without embedding support, recommendation ranking continues from structured preferences and collaborative signals, not fake vectors.

**Verified market trends:** Import your *own independently sourced data*. No fabricated market benchmarks are bundled:

```bash
cd backend
export MIGRATION_DATABASE_URL='postgresql+psycopg://postgres:...@localhost:5432/proptech'
python scripts/import_trends.py market-trends.csv --source 'Reviewed vendor + methodology' --approve
```

CSV header: `month,city,area_name,kind,median_sale_price,median_monthly_rent,sample_size`. Example `month`: `2026-10`. For security, the market-trend table is read-only to the app DB role; only a privileged import process can attest rows as verified.

## 8. React features

- Editorial-style marketplace with focused typography, original architectural placeholder artwork (when no user photos exist), category selectors, more granular search/sort, pagination and responsive photo cards.
- Photo-first property detail with a lightbox gallery, actual PG/portion data, amenities, selling points, opt-in WhatsApp contact, sharing, AI asking-price evidence, rent scenarios and authenticated inquiries.
- **Listing Studio:** a separate owner/broker ad editor with structured fields, portion/PG configuration, photographic upload with preview, gallery order/cover/alt management, listing readiness checks, and explicit publish/unpublish actions.
- Broker workspace: image-backed inventory, listing drafts, separate editing and photo screens, lead-stage transitions, qualified lead matches and verified trends.
- Customer workspace: preference editor, recommendations, a persistent shortlist and their own enquiry history.
- Header with English/Urdu switching; sets document `lang` and `dir` dynamically, uses RTL-aware logical utilities, and changes font stack for Urdu. Main marketplace copy and navigation are localized; secondary technical/broker admin strings currently remain English and require translation review to meet a fully bilingual release requirement.
- Three shadcn-style source-owned UI primitives (`button`, `card`, `input`) with Tailwind. The `components.json` is ready for CLI-generated shadcn component additions.

## 9. Tests and CI

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

`test_validation.py` tests kind-specific PG and portion input rules. `test_media.py` validates secure photo normalization, size/type checks, storage and path containment. `test_api_integration.py` uses `httpx.AsyncClient` against PostgreSQL with migrations applied and checks tenant isolation, inquiry routing, auth permissions and cold-start predictions. **Run tests against a disposable database only.** GitHub Actions provisions PostgreSQL with Docker Compose and performs backend tests and a React TypeScript/Vite build. Repository does not include an npm lockfile; generate and commit one before release for deterministic installs.

## 10. Production release checklist (not yet complete)

1. Confirm end-to-end migrations and RLS under the actual **NOBYPASSRLS** role. Add automated RLS adversarial tests for every table and security-definer function.
2. Deploy HTTPS/TLS at an ingress or load balancer with strict host checks, request size ceilings, security headers, and proper proxy trust settings.
3. Add a dedicated authorization rate limiter (Redis/WAF/edge) and account/email verification, invitation/activation, password reset, MFA and abuse controls.
4. Replace browser JavaScript-readable session token storage with a properly hardened HttpOnly Secure refresh-cookie/BFF flow and CSRF controls for your deployment. Add global session/device revocation if required.
5. Pin fully resolved Python/npm dependency versions, create/commit an npm lockfile, scan dependencies and container images, add reproducible builds and SBOMs.
6. Upgrade the initial Alembic snapshot (`Base.metadata.create_all`) to an immutable revision defining every column/constraint explicitly, and author future schema evolution as new Alembic operations.
7. Replace the single-node persisted private photo volume with managed S3-compatible object storage, asynchronous malware/fraud screening, lifecycle reconciliation, signed uploads/CDN, and content moderation. The local gallery pipeline is functional but not a distributed production media architecture.
8. Move AI inference/training/vector creation out of request paths to bounded background workers, add model registry, monitoring, validation, drift checks, trained-on timestamps, and fairness/quality evaluations on independently verified transactions.
9. Add real vendor/property verification, fraud moderation, lead consent/retention policies, audit trails, data export/delete, and privacy/legal review for every jurisdiction served.
10. Add pagination for high-volume CRM and agency inventory, query plan/index tuning, isolation-aware caching, queue-backed event ingestion, metrics/tracing, DB backups and tested restore procedures.
11. Add tenant provisioning review, billing/plan entitlement enforcement, email/SMS notifications, broker invitations, bulk import, duplicate detection, paid featured placement, verification workflow and support tooling as needed for commercial SaaS delivery.
12. Complete Urdu translations of all administrative and authentication strings, keyboard/screen-reader testing, automated browser E2E tests and mobile UX verification.

## 11. Architectural boundaries

This is **headless**: the browser exclusively consumes REST/JSON, with no direct DB access. The application separates auth/tenant dependencies, ORM persistence, request validation, controllers and ML services. The tenant identity is *never accepted as a request body parameter for arbitrary writes*. The platform intentionally does not include unrequested modules such as mortgage underwriting, payments, document e-signature, or property ownership verification.

## 12. Listing-photo operations & design system (2026-11 update)

The new editor is available at `/broker/listings/new` and `/broker/listings/:id/edit` for authenticated owners, admins and brokers. Owners/admins may manage any property in their own agency; a broker can edit only listings they created. Public marketplace visitors cannot upload. A listing is created as a **draft**, then photography is uploaded, and publication is allowed only if it has at least **one real uploaded photo**, a **50-character** description and a locality. The readiness endpoint also provides non-blocking recommendations for five photos, amenities, highlights and contact information. Existing published legacy ads are not forcibly unpublished during migration, but updates to published ads must meet the new readiness gate.

The frontend avoids fabricated property photography. Images uploaded by the advertiser become the gallery content. Draft previews retrieve their media using the authenticated API rather than exposing private storage. The visual system uses warm stone neutrals, deep ink, understated terracotta accents, editorial Newsreader headings and DM Sans interface typography; Urdu uses Noto Sans Arabic with document-level RTL mirroring. External web fonts are progressive enhancements with system fallbacks; full translation of the expanded ad studio still needs editorial/localization review.

**Media housekeeping:** Add a trusted periodic job on the single server that mounts the same media volume and has the privileged migration database credentials. Run in dry-run mode first:

```bash
cd backend
export MEDIA_DIR=./.media
python scripts/prune_media.py --min-age-hours 48
python scripts/prune_media.py --min-age-hours 48 --apply
```

The sweep removes only unreferenced WebP files older than 48 hours (configurable, minimum 24 hours). Do not make this endpoint accessible to customers. Do not execute cleanup before all active upload requests have completed or during a database recovery window. Add backups for both the Postgres DB and `media` volume.

**Important release limitations:** This repository is not yet certified production-ready. Full database-backed API integration tests, full npm/Vite build, browser interaction tests, multi-node object storage, media moderation, abuse-rate limiting, agency billing, and full Urdu admin translations require verification or further implementation in your deployment environment. No generated market prices or ad performance guarantees are presented.
