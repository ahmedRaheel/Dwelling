"""Search predicates shared by saved searches and the public marketplace.

All incoming values have already been parsed with PropertySearchFilters.
Never interpolate user text into raw SQL or build a dynamic ORDER BY from input.
"""
from sqlalchemy import or_
from app.models.entities import Property, ListingStatus
from app.schemas.domain import PropertySearchFilters


def property_search_conditions(filters: PropertySearchFilters):
    conditions = [Property.status == ListingStatus.published]
    for column, key in ((Property.city, filters.city), (Property.society, filters.society),
                        (Property.block, filters.block)):
        if key:
            conditions.append(column.ilike(f'%{key.strip()}%'))
    if filters.q:
        expression = f'%{filters.q.strip()}%'
        conditions.append(or_(Property.title.ilike(expression), Property.description.ilike(expression),
                              Property.area_name.ilike(expression), Property.society.ilike(expression)))
    for column, key in ((Property.kind, filters.kind), (Property.purpose, filters.purpose)):
        if key is not None:
            conditions.append(column == key)
    for column, value, operator in (
        (Property.price, filters.min_price, '>='), (Property.price, filters.max_price, '<='),
        (Property.bedrooms, filters.minimum_bedrooms, '>='),
        (Property.bathrooms, filters.minimum_bathrooms, '>='),
        (Property.area_sqft, filters.min_area, '>='), (Property.area_sqft, filters.max_area, '<='),
    ):
        if value is not None:
            conditions.append(column >= value if operator == '>=' else column <= value)
    if filters.furnished is not None:
        conditions.append(Property.furnished.is_(filters.furnished))
    if filters.ready_to_move is not None:
        conditions.append(Property.ready_to_move.is_(filters.ready_to_move))
    if filters.amenity:
        conditions.append(Property.amenities.contains([filters.amenity.strip()]))
    return conditions
