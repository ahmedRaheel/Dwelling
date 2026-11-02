"""Initial schema, tenant RLS and constrained security-definer functions.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from app.core.database import Base
from app.models import *  # noqa: F401,F403

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


TENANT_TABLES = ('users', 'refresh_tokens', 'properties', 'pg_details', 'portion_details',
                 'leads', 'ai_predictions', 'interactions')
ORIGINAL_TABLES = frozenset(('tenants', 'market_trends', *TENANT_TABLES))


def upgrade():
    bind = op.get_bind()
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    # Pinned initial metadata snapshot; future schema evolution uses new revisions.
    Base.metadata.create_all(bind=bind, tables=[table for table in Base.metadata.sorted_tables
        if table.name in ORIGINAL_TABLES], checkfirst=False)
    op.execute('CREATE INDEX ix_properties_embedding_hnsw ON properties USING hnsw (embedding vector_cosine_ops)')
    for table in ('tenants', *TENANT_TABLES, 'market_trends'):
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')

    tid = "nullif(current_setting('app.tenant_id', true), '')::uuid"
    uid = "nullif(current_setting('app.user_id', true), '')::uuid"
    op.execute(f"CREATE POLICY tenant_read ON tenants FOR SELECT USING (active OR id = {tid})")
    op.execute(f"CREATE POLICY tenant_write ON tenants FOR INSERT WITH CHECK (id = {tid})")
    op.execute(f"CREATE POLICY tenant_update ON tenants FOR UPDATE USING (id = {tid}) WITH CHECK (id = {tid})")

    for table in TENANT_TABLES:
        if table in ('properties', 'pg_details', 'portion_details', 'leads', 'interactions', 'refresh_tokens', 'ai_predictions'):
            continue
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (tenant_id = {tid})")
        op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK (tenant_id = {tid})")
        op.execute(f"CREATE POLICY {table}_update ON {table} FOR UPDATE USING (tenant_id = {tid}) WITH CHECK (tenant_id = {tid})")
        op.execute(f"CREATE POLICY {table}_delete ON {table} FOR DELETE USING (tenant_id = {tid})")

    for table, owned_column in (('refresh_tokens', 'user_id'), ('ai_predictions', 'user_id')):
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (tenant_id = {tid} AND {owned_column} = {uid})")
        op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK (tenant_id = {tid} AND {owned_column} = {uid})")
        op.execute(f"CREATE POLICY {table}_update ON {table} FOR UPDATE USING (tenant_id = {tid} AND {owned_column} = {uid}) WITH CHECK (tenant_id = {tid} AND {owned_column} = {uid})")
        op.execute(f"CREATE POLICY {table}_delete ON {table} FOR DELETE USING (tenant_id = {tid} AND {owned_column} = {uid})")

    op.execute(f"CREATE POLICY property_select ON properties FOR SELECT USING (status = 'published' OR tenant_id = {tid})")
    for command in ('INSERT', 'UPDATE', 'DELETE'):
        if command == 'INSERT':
            op.execute(f'CREATE POLICY property_insert ON properties FOR INSERT WITH CHECK (tenant_id = {tid})')
        elif command == 'UPDATE':
            op.execute(f'CREATE POLICY property_update ON properties FOR UPDATE USING (tenant_id = {tid}) WITH CHECK (tenant_id = {tid})')
        else:
            op.execute(f'CREATE POLICY property_delete ON properties FOR DELETE USING (tenant_id = {tid})')

    for child in ('pg_details', 'portion_details'):
        op.execute(f"""CREATE POLICY {child}_select ON {child} FOR SELECT USING (
            tenant_id = {tid} OR EXISTS (
                SELECT 1 FROM properties p WHERE p.id = property_id AND p.status = 'published'))""")
        op.execute(f'CREATE POLICY {child}_insert ON {child} FOR INSERT WITH CHECK (tenant_id = {tid})')
        op.execute(f'CREATE POLICY {child}_update ON {child} FOR UPDATE USING (tenant_id = {tid}) WITH CHECK (tenant_id = {tid})')
        op.execute(f'CREATE POLICY {child}_delete ON {child} FOR DELETE USING (tenant_id = {tid})')

    op.execute(f'CREATE POLICY leads_select ON leads FOR SELECT USING (tenant_id = {tid} OR customer_user_id = {uid})')
    op.execute(f'CREATE POLICY leads_insert ON leads FOR INSERT WITH CHECK (tenant_id = {tid})')
    op.execute(f'CREATE POLICY leads_update ON leads FOR UPDATE USING (tenant_id = {tid}) WITH CHECK (tenant_id = {tid})')
    op.execute(f'CREATE POLICY leads_delete ON leads FOR DELETE USING (tenant_id = {tid})')

    op.execute(f'CREATE POLICY interactions_select ON interactions FOR SELECT USING (tenant_id = {tid} AND user_id = {uid})')
    op.execute(f'CREATE POLICY interactions_insert ON interactions FOR INSERT WITH CHECK (tenant_id = {tid} AND user_id = {uid})')
    op.execute(f'CREATE POLICY interactions_delete ON interactions FOR DELETE USING (tenant_id = {tid} AND user_id = {uid})')

    op.execute("CREATE POLICY trend_read ON market_trends FOR SELECT USING (verified = true)")

    # Customer enquiries across agencies: fixed authenticated identity, no arbitrary tenant/user parameter.
    op.execute("""
      CREATE FUNCTION public.submit_property_inquiry(
          p_property uuid, p_name text, p_email text, p_phone text, p_message text, p_budget numeric)
      RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      DECLARE v_tenant uuid; v_lead uuid; v_user uuid;
      BEGIN
        v_user := nullif(current_setting('app.user_id', true), '')::uuid;
        IF v_user IS NULL OR v_user = '00000000-0000-0000-0000-000000000000' THEN
          RAISE EXCEPTION 'Authentication required' USING ERRCODE = '28000';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM public.users WHERE id = v_user AND active) THEN
          RAISE EXCEPTION 'Inactive user' USING ERRCODE = '28000';
        END IF;
        SELECT tenant_id INTO v_tenant FROM public.properties
          WHERE id = p_property AND status = 'published';
        IF v_tenant IS NULL THEN RAISE EXCEPTION 'Listing unavailable' USING ERRCODE = '22023'; END IF;
        INSERT INTO public.leads(id, tenant_id, property_id, customer_user_id, contact_name,
                                 contact_email, contact_phone, message, budget, status)
        VALUES (gen_random_uuid(), v_tenant, p_property, v_user, p_name, p_email, p_phone,
                p_message, p_budget, 'new') RETURNING id INTO v_lead;
        RETURN v_lead;
      END; $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.submit_property_inquiry(uuid,text,text,text,text,numeric) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.submit_property_inquiry(uuid,text,text,text,text,numeric) TO proptech_app")

    # Only anonymized aggregate popularity escapes interaction-level RLS; at least 3 distinct peers.
    op.execute("""
      CREATE FUNCTION public.collaborative_scores()
      RETURNS TABLE(property_id uuid, score numeric)
      LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        WITH mine AS (
          SELECT DISTINCT i.property_id FROM public.interactions i
          WHERE i.user_id = nullif(current_setting('app.user_id', true), '')::uuid
            AND i.action IN ('save', 'inquiry')
        ), neighbors AS (
          SELECT DISTINCT i.user_id FROM public.interactions i JOIN mine m USING (property_id)
          WHERE i.user_id <> nullif(current_setting('app.user_id', true), '')::uuid
            AND i.action IN ('save', 'inquiry')
        ), candidates AS (
          SELECT i.property_id, count(DISTINCT i.user_id)::int AS peers
          FROM public.interactions i JOIN neighbors n USING (user_id)
            JOIN public.properties p ON p.id = i.property_id
          WHERE p.status = 'published' AND i.action IN ('save', 'inquiry')
            AND NOT EXISTS (SELECT 1 FROM mine m WHERE m.property_id = i.property_id)
          GROUP BY i.property_id HAVING count(DISTINCT i.user_id) >= 3
        )
        SELECT c.property_id, least(c.peers::numeric / 10, 1.0) AS score
        FROM candidates c ORDER BY c.peers DESC LIMIT 40;
      $$
    """)
    op.execute('REVOKE ALL ON FUNCTION public.collaborative_scores() FROM PUBLIC')
    op.execute('GRANT EXECUTE ON FUNCTION public.collaborative_scores() TO proptech_app')

    op.execute('GRANT USAGE ON SCHEMA public TO proptech_app')
    for table in ('tenants', *TENANT_TABLES):
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO proptech_app')
    op.execute('GRANT SELECT ON market_trends TO proptech_app')


def downgrade():
    op.execute('DROP FUNCTION IF EXISTS public.collaborative_scores()')
    op.execute('DROP FUNCTION IF EXISTS public.submit_property_inquiry(uuid,text,text,text,text,numeric)')
    Base.metadata.drop_all(bind=op.get_bind(), tables=[table for table in Base.metadata.sorted_tables
        if table.name in ORIGINAL_TABLES])
