"""Search refinement, agency directory, saved searches and visit scheduling.

Revision ID: 0003_discovery_workspace
Revises: 0002_listing_media

This migration tolerates objects already created by an earlier revision, but
refuses to silently accept incompatible column definitions or missing tables.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_discovery_workspace"
down_revision = "0002_listing_media"
branch_labels = None
depends_on = None

SCHEMA = "public"


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table):
    return _inspector().has_table(table, schema=SCHEMA)


def _columns(table):
    if not _table_exists(table):
        raise RuntimeError(f"Required table {SCHEMA}.{table} does not exist")
    return {col["name"]: col for col in _inspector().get_columns(table, schema=SCHEMA)}


def _add_column(table, column):
    columns = _columns(table)
    existing = columns.get(column.name)
    if existing is None:
        op.add_column(table, column, schema=SCHEMA)
        return

    # A name collision is not proof of a compatible schema. Confirm the
    # basic PostgreSQL type and nullability before accepting the column.
    expected_type = column.type.compile(dialect=postgresql.dialect()).lower()
    found_type = existing["type"].compile(dialect=postgresql.dialect()).lower()
    aliases = {
        "boolean": {"boolean", "bool"},
        "text": {"text"},
    }
    allowed = aliases.get(expected_type, {expected_type})
    if found_type not in allowed or existing["nullable"] != column.nullable:
        raise RuntimeError(
            f"Existing {table}.{column.name} differs from migration: "
            f"found {found_type}, nullable={existing['nullable']}; "
            f"expected {expected_type}, nullable={column.nullable}. "
            "Review and reconcile manually before proceeding."
        )


def _create_index(name, table, columns):
    indexes = {index["name"]: index for index in _inspector().get_indexes(table, schema=SCHEMA)}
    existing = indexes.get(name)
    if existing is None:
        op.create_index(name, table, columns, schema=SCHEMA)
    elif existing["column_names"] != columns or existing.get("unique", False):
        raise RuntimeError(f"Existing index {name} has an unexpected definition")


def _create_check(name, table, expression):
    checks = {item["name"]: item for item in _inspector().get_check_constraints(table, schema=SCHEMA)}
    if name not in checks:
        op.create_check_constraint(name, table, expression, schema=SCHEMA)
    else:
        # Merely matching the constraint name does not establish equivalence.
        # Compare the normalized condition for the one expected constraint.
        found = "".join(checks[name]["sqltext"].lower().split())
        expected_values = ("gallery", "floorplan")
        if not all(value in found for value in expected_values) or "category" not in found:
            raise RuntimeError(f"Existing check {name} needs manual review: {checks[name]['sqltext']}")


def _create_table_if_missing(name, *columns):
    if not _table_exists(name):
        op.create_table(name, *columns, schema=SCHEMA)
    else:
        actual = _columns(name)
        expected_names = {column.name for column in columns if isinstance(column, sa.Column)}
        if not expected_names.issubset(actual):
            missing = sorted(expected_names - actual.keys())
            raise RuntimeError(f"Existing table {name} lacks required columns: {missing}")
        # Existing tables with matching names require further schema validation.
        # Guard against silently accepting missing tenant/RLS-critical constraints.
        expected_pk = [c.name for c in columns if isinstance(c, sa.Column) and c.primary_key]
        primary = _inspector().get_pk_constraint(name, schema=SCHEMA)
        if sorted(primary.get("constrained_columns") or []) != sorted(expected_pk):
            raise RuntimeError(f"Existing table {name} has an incompatible primary key")


def _ensure_policy(name, table, operation, clause):
    # PostgreSQL does not support CREATE POLICY IF NOT EXISTS.
    existing = op.get_bind().execute(
        sa.text("""
            SELECT qual, with_check FROM pg_policies
            WHERE schemaname = :schema AND tablename = :table AND policyname = :name
        """),
        {"schema": SCHEMA, "table": table, "name": name},
    ).one_or_none()
    if existing is not None:
        # Existing policies might be materially different. Do not silently
        # preserve a wider policy because its name happens to match.
        raise RuntimeError(
            f"Existing policy {name} on {table} requires manual review "
            "before reapplying migration 0003"
        )
    op.execute(f"CREATE POLICY {name} ON {table} FOR {operation} {clause}")


def upgrade():
    for name, column in [
        ("tenants", sa.Column("public_description", sa.Text(), nullable=False, server_default="")),
        ("tenants", sa.Column("public_city", sa.String(100), nullable=False, server_default="")),
        ("tenants", sa.Column("public_phone", sa.String(40), nullable=True)),
        ("tenants", sa.Column("public_email", sa.String(255), nullable=True)),
        ("properties", sa.Column("society", sa.String(120), nullable=False, server_default="")),
        ("properties", sa.Column("block", sa.String(100), nullable=False, server_default="")),
        ("properties", sa.Column("price_negotiable", sa.Boolean(), nullable=False, server_default=sa.text("false"))),
        ("properties", sa.Column("ready_to_move", sa.Boolean(), nullable=False, server_default=sa.text("false"))),
        ("properties", sa.Column("video_url", sa.String(350), nullable=True)),
        ("property_photos", sa.Column("category", sa.String(20), nullable=False, server_default="gallery")),
    ]:
        _add_column(name, column)

    _create_index("ix_properties_society", "properties", ["city", "society"])
    _create_check("ck_photo_category", "property_photos", "category IN ('gallery','floorplan')")

    _create_table_if_missing(
        "saved_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("alerts_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_index("ix_saved_searches_owner", "saved_searches", ["tenant_id", "user_id"])

    _create_table_if_missing(
        "viewing_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("customer_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("preferred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contact_name", sa.String(160), nullable=False),
        sa.Column("contact_phone", sa.String(40), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('requested','confirmed','declined','completed','cancelled')",
            name="ck_viewing_status",
        ),
    )
    _create_index("ix_viewings_agency_time", "viewing_requests", ["tenant_id", "preferred_at"])
    _create_index("ix_viewings_customer", "viewing_requests", ["customer_user_id", "created_at"])

    tid = "nullif(current_setting('app.tenant_id', true), '')::uuid"
    uid = "nullif(current_setting('app.user_id', true), '')::uuid"
    for table in ("saved_searches", "viewing_requests"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

    _ensure_policy("search_select", "saved_searches", "SELECT", f"USING (tenant_id = {tid} AND user_id = {uid})")
    _ensure_policy("search_insert", "saved_searches", "INSERT", f"WITH CHECK (tenant_id = {tid} AND user_id = {uid})")
    _ensure_policy("search_update", "saved_searches", "UPDATE", f"USING (tenant_id = {tid} AND user_id = {uid}) WITH CHECK (tenant_id = {tid} AND user_id = {uid})")
    _ensure_policy("search_delete", "saved_searches", "DELETE", f"USING (tenant_id = {tid} AND user_id = {uid})")
    _ensure_policy("viewing_select", "viewing_requests", "SELECT", f"USING (tenant_id = {tid} OR customer_user_id = {uid})")
    _ensure_policy("viewing_insert", "viewing_requests", "INSERT", f"WITH CHECK (tenant_id = {tid} AND customer_user_id = {uid})")
    _ensure_policy("viewing_update", "viewing_requests", "UPDATE", f"USING (tenant_id = {tid} OR customer_user_id = {uid}) WITH CHECK (tenant_id = {tid} OR (customer_user_id = {uid} AND status = 'cancelled'))")

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON public.saved_searches TO proptech_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON public.viewing_requests TO proptech_app")

    # SECURITY DEFINER runs under the privileged migration owner, with a fixed
    # search_path. Validate existing definitions rather than replacing blindly.
    existing = op.get_bind().execute(sa.text("""
        SELECT to_regprocedure('public.request_property_viewing(uuid,timestamp with time zone,text,text,text)')
    """)).scalar()
    if existing is not None:
        raise RuntimeError("request_property_viewing already exists: inspect its security definition before proceeding")

    op.execute("""
      CREATE FUNCTION public.request_property_viewing(
          p_property uuid, p_when timestamptz, p_name text, p_phone text, p_note text)
      RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      DECLARE v_tenant uuid; v_customer uuid; v_viewing uuid;
      BEGIN
        v_customer := nullif(current_setting('app.user_id', true), '')::uuid;
        IF v_customer IS NULL OR v_customer = '00000000-0000-0000-0000-000000000000'
          OR NOT EXISTS (SELECT 1 FROM public.users WHERE id=v_customer AND active) THEN
          RAISE EXCEPTION 'Authenticated account required' USING ERRCODE='28000';
        END IF;
        IF p_when < now() + interval '1 hour' OR p_when > now() + interval '90 days'
          OR length(p_name) NOT BETWEEN 2 AND 160 OR length(p_phone) NOT BETWEEN 7 AND 40
          OR length(p_note) > 1000 THEN
          RAISE EXCEPTION 'Invalid viewing request' USING ERRCODE='22023';
        END IF;
        SELECT tenant_id INTO v_tenant FROM public.properties WHERE id=p_property AND status='published';
        IF v_tenant IS NULL THEN RAISE EXCEPTION 'Property unavailable' USING ERRCODE='22023'; END IF;
        INSERT INTO public.viewing_requests(id,tenant_id,property_id,customer_user_id,preferred_at,contact_name,contact_phone,note)
        VALUES (gen_random_uuid(),v_tenant,p_property,v_customer,p_when,p_name,p_phone,p_note)
        RETURNING id INTO v_viewing;
        RETURN v_viewing;
      END; $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.request_property_viewing(uuid,timestamptz,text,text,text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.request_property_viewing(uuid,timestamptz,text,text,text) TO proptech_app")


def downgrade():
    # Objects may have existed before 0003 because older migrations included
    # some of these definitions. A destructive downgrade cannot reliably tell
    # which data it owns. Fail closed rather than silently erase customer data.
    raise RuntimeError(
        "Downgrade of 0003 is intentionally blocked: columns and tables may "
        "predate this migration. Restore a verified database backup or "
        "write a schema-specific, reviewed rollback instead."
    )
