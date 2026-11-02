# Dwelling: account onboarding and listing media update

## What changed

- A restrained, responsive account-creation experience. Account choices: home seeker, property owner, broker, property dealer, real-estate agency. Neutral backgrounds, DM Sans for interface copy, Newsreader for editorial display headings, considered spacing and reusable existing controls.
- Registration for independent home seekers without an agency slug. They receive a unique personal workspace; its address is displayed in their dashboard and stored on the registering device. The application still requires workspace address + email + password at sign-in. This is an intentional limitation of the existing tenant-scoped authentication design, not a global login implementation.
- Separate professional self-service account type recorded on tenant (`account_type`). All professional workspace founders retain the existing `owner` authorization role **within their own tenant**. Employees' existing `broker` role and permissions are retained.
- Existing draft → publish → unpublish workflow remains; public list/details and photos enforce publication on the backend. No customer-facing editor rights.
- MP4/WebM upload API and React video manager; private media before publication. 80 MB maximum, one video per listing. Existing external video-tour URL remains supported.
- New migration `0004_account_types_and_videos.py` and orphan-media sweeper support for replaced/removed videos.
- The existing `app-net` external PostgreSQL Docker network is unchanged. No database or volumes are created by this application Compose project.

## Deployment to your EC2

1. **Back up** your `proptech` database and your persistent `media` Docker volume before replacing source files. Do not run `docker compose down -v`.
2. Extract to a separate directory, compare changes, and keep your existing `.env`. The ZIP intentionally excludes `.env` and Git history.
3. Confirm `POSTGRES_DOCKER_NETWORK` (or Compose external `app-net`) matches the network where the existing `postgres` container runs. Review `CORS_ORIGINS` and `FRONTEND_PORT`.
4. From `Dwelling`:
   ```sh
   docker compose -f compose.yaml config -q
   docker compose -f compose.yaml build migrate
   docker compose -f compose.yaml run --rm --no-deps migrate
   docker compose -f compose.yaml build backend
   docker compose -f compose.yaml build frontend
   docker compose -f compose.yaml up -d --no-build
   docker compose -f compose.yaml ps
   ```
5. Only deploy if migration `0001`–`0004` runs successfully against a **staging restore** and the API and UI tests succeed. An existing live database may have schema drift from previously edited `0001`–`0003` migrations.
6. Test: create a customer, create a property-owner workspace, create a property draft, upload photos/video, verify another browser cannot access draft or its video, publish, verify public listing and media, unpublish, verify public media access is denied.

## Important limitations and production acceptance

- **Database migration chain is not fully production-certified.** The uploaded `0001_initial.py` creates tables from the current SQLAlchemy ORM rather than an immutable historical schema. Uploaded `0002_listing_media.py` includes a provisional ORM-derived photo-table repair. These should be reconciled into frozen SQL migration operations with a reviewed database backup before onboarding real customers.
- No live PostgreSQL or EC2 migration test was possible here.
- TypeScript/React build was not verified here: dependency installation could not complete in the sandbox. Validate using `npm install && npm run build` in `frontend` or via its Docker build.
- Locally stored property media requires backups and capacity planning. This update does not implement S3 storage, malware scanning, video transcoding, content moderation, tenant identity verification, rate-limited signup, anti-abuse protections or global email-only login.
- The existing application allows direct self-publication after listing readiness checks; no separate staff moderation/verification is enforced. Validate user-generated listings before allowing unrestricted public traffic.
- Sign-in still requires the workspace slug; customers receive a personal slug and can copy it in their dashboard. Long-term, a verified global identity and account-membership model would support email-only login and multiple agency memberships more cleanly.
- Existing access/refresh token storage strategy is retained, pending a separate security review.

## API changes

`POST /api/v1/auth/register` accepts a customer without `tenant_slug` (existing tenant slug is still supported).

`POST /api/v1/auth/tenant/register` accepts `account_type`: `agency | owner | broker | dealer`.

`GET /api/v1/auth/me` now returns `account_type` and `workspace_slug`.

`PUT /api/v1/listings/{id}/video` accepts multipart `file` (MP4/WebM, max 80 MB).

`GET /api/v1/listings/{id}/video` returns visibility-checked video metadata.

`GET /api/v1/listings/{id}/video/file` serves visibility-checked video media.

`DELETE /api/v1/listings/{id}/video` removes the metadata, with file cleanup by the existing sweeper.
