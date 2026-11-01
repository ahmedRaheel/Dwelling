import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Interaction, InteractionKind, Lead, ListingStatus, Property, Role, User
from app.schemas.domain import BrokerMatch, LeadResponse, PropertyResponse, Recommendation
from app.services.embeddings import encode


async def customer_recommendations(db: AsyncSession, user: User, limit: int = 12) -> list[Recommendation]:
    preferences = user.preferences or {}
    already_saved = set((await db.scalars(select(Interaction.property_id).where(
        Interaction.user_id == user.id, Interaction.action.in_([InteractionKind.save, InteractionKind.inquiry])))).all())
    # Only aggregate, k-anonymized collaboration scores are returned by the DB function.
    peer_scores = dict((await db.execute(text('SELECT property_id, score FROM public.collaborative_scores()'))).all())
    query = ' '.join(str(preferences.get(key, '')) for key in ('city', 'kind', 'purpose'))
    vector = await encode(query) if query.strip() else None
    statement = select(Property).where(Property.status == ListingStatus.published, Property.currency == 'PKR')
    if vector is not None:
        statement = statement.order_by(Property.embedding.cosine_distance(vector).asc().nulls_last())
    else:
        statement = statement.order_by(Property.created_at.desc())
    candidates = (await db.scalars(statement.limit(150))).all()
    selected = []
    for item in candidates:
        if item.id in already_saved:
            continue
        score, reasons = 0.10, []
        if preferences.get('city') and item.city.casefold() == str(preferences['city']).casefold():
            score += 0.24
            reasons.append('Preferred city')
        if preferences.get('kind') and item.kind.value == preferences['kind']:
            score += 0.20
            reasons.append('Matching property type')
        if preferences.get('purpose') and item.purpose.value == preferences['purpose']:
            score += 0.15
            reasons.append('Matching sale/rent preference')
        try:
            budget = float(preferences.get('max_price') or 0)
            if budget > 0 and item.price <= budget:
                score += 0.14
                reasons.append('Within budget')
        except (ValueError, TypeError):
            pass
        if item.bedrooms >= int(preferences.get('minimum_bedrooms') or 0):
            score += 0.04
        popularity = float(peer_scores.get(item.id, 0))
        if popularity:
            score += 0.13 * popularity
            reasons.append('Similar users showed interest')
        if vector is not None and item.embedding is not None:
            candidate = np.asarray(item.embedding, dtype=float)
            query_vector = np.asarray(vector, dtype=float)
            denominator = np.linalg.norm(candidate) * np.linalg.norm(query_vector)
            relevance = float(candidate @ query_vector / denominator) if denominator else 0.0
            score += 0.15 * max(relevance, 0.0)
            if relevance > 0.5:
                reasons.append('Semantic relevance')
        selected.append(Recommendation(property=PropertyResponse.model_validate(item),
                                       score=round(min(1, score), 3), reasons=reasons or ['Recently listed']))
    return sorted(selected, key=lambda row: row.score, reverse=True)[:limit]


async def broker_matches(db: AsyncSession, user: User) -> list[BrokerMatch]:
    properties = (await db.scalars(select(Property).where(Property.tenant_id == user.tenant_id,
                                                         Property.status == ListingStatus.published))).all()
    leads = (await db.scalars(select(Lead).where(Lead.tenant_id == user.tenant_id,
                                                   Lead.status.in_(['new', 'contacted', 'qualified']))
                                    .order_by(Lead.created_at.desc()).limit(100))).all()
    by_id = {item.id: item for item in properties}
    matches = []
    for lead in leads:
        source = by_id.get(lead.property_id)
        for item in properties:
            score, reasons = 0.0, []
            if lead.property_id == item.id:
                score += 0.40
                reasons.append('Original property of interest')
            if source and source.kind == item.kind:
                score += 0.18
                reasons.append('Same type as inquiry')
            if source and source.purpose == item.purpose:
                score += 0.10
            if source and source.city.casefold() == item.city.casefold():
                score += 0.12
                reasons.append('Same city as inquiry')
            if lead.budget and item.price <= lead.budget:
                score += 0.20
                reasons.append('Within stated budget')
            if lead.budget and item.price > lead.budget * 1.25:
                continue
            if score < 0.20:
                continue
            matches.append(BrokerMatch(lead=LeadResponse.model_validate(lead),
                                       property=PropertyResponse.model_validate(item),
                                       score=round(min(1, score), 2), reasons=reasons))
    return sorted(matches, key=lambda row: row.score, reverse=True)[:30]
