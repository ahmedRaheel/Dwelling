# Dwelling — Public Listings and Registration Reliability

## Changes

- `/` is a published-properties marketplace, **not** an account registration page. Property search and published listing cards appear before secondary marketing content. Browsing requires no account.
- Public actions: `Sign in` (`/auth`) and `Create account` (`/auth?mode=register`). Navbar and `Post your property` CTA deep-link to registration.
- Removed invalid HTML `pattern` from workspace slug input. Client-side validation uses a JavaScript regex and shows a readable message. The FastAPI/Pydantic schema remains the authoritative validation boundary.
- Registration checks the required `tenants.account_type` column introduced by Alembic `0004_account_types_and_videos` and returns 503 with clear detail if the migration is not applied.
- Database errors during account creation **and refresh-token issuance** are recorded in backend logs and return a non-sensitive 503 rather than a generic internal error. Duplicate identity conflicts return 409.
- Existing listing route already restricts public search to `published` and reserves `mine` for authenticated owners/brokers.

## Deployment (existing external PostgreSQL container is untouched)

Back up your existing PostgreSQL database and media storage before migration/deployment. Copy the new source, keep your production `.env`.

```sh
docker compose -f compose.yaml config -q
docker compose -f compose.yaml build migrate
docker compose -f compose.yaml run --rm --no-deps migrate
# only once migrations succeed:
docker compose -f compose.yaml build backend
docker compose -f compose.yaml build frontend
docker compose -f compose.yaml up -d --no-build
docker compose -f compose.yaml ps
```

Check endpoint and logs:

```sh
curl -i http://127.0.0.1/api/health/ready
docker compose -f compose.yaml logs --tail=150 backend
docker exec postgres psql -U postgres -d proptech -c "SELECT version_num FROM alembic_version;"
docker exec postgres psql -U postgres -d proptech -c "SELECT column_name FROM information_schema.columns WHERE table_name='tenants' AND column_name='account_type';"
```

Important: `postgres` and `proptech` must be the actual database container/database used by `MIGRATION_DATABASE_URL`; check your `.env` before relying on those sample verification commands.

## Acceptance checks

1. Open `/` in a private browser window, verify published listing cards and search work without login. Draft/archived listings must not appear.
2. Open `/auth?mode=register`, choose each of customer, owner, broker, dealer, agency and verify account form. Use a slug such as `my-estate-company` for professional accounts.
3. Invalid slug (`ABC!`) shows a client-side warning without browser regex exception.
4. Create a customer and a professional account. Confirm 201 + stored workspace slug; sign in again.
5. If registration returns 503, inspect backend tracebacks and confirm migrations including `0004` succeeded. Do not change/drop PostgreSQL volumes or use `alembic stamp head` to hide migration failures.
6. Create a draft with images/video. Verify anonymous access is denied until `published`, and returns to private after unpublish.

## Verification limitations

Python compilation passed. The frontend TypeScript production build could not be run because packages were not installed and `npm install` timed out in this environment. Database migrations, registration, and publisher workflow require a live configured PostgreSQL environment. This release does not claim to fix every pre-existing database migration inconsistency.
