"""Real multilingual semantic vectors. Disabled by default to avoid silent model downloads."""
import asyncio
from functools import lru_cache
from app.core.config import get_settings


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(get_settings().embedding_model)
    if model.get_sentence_embedding_dimension() != 384:
        raise RuntimeError('The configured model must produce 384-dimensional vectors')
    return model


async def encode(text: str) -> list[float] | None:
    if not get_settings().embeddings_enabled:
        return None
    # No fake hash vectors: if the model is unavailable, surface the configuration error.
    return await asyncio.to_thread(lambda: _model().encode(text, normalize_embeddings=True).tolist())


def property_text(payload) -> str:
    return ' '.join((payload.title, payload.description, payload.kind.value,
                     payload.purpose.value, payload.city, payload.area_name,
                     f'{payload.bedrooms} bedrooms', f'{payload.area_sqft} square feet'))
