"""bge-m3 임베딩 (1024차원 고정). 모델은 처음 쓸 때 한 번만 불러온다."""

from functools import lru_cache
from typing import Any, Protocol

from app.config import get_settings


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class BgeM3Embedder:
    def __init__(self, model_name: str, dim: int) -> None:
        self._model_name = model_name
        self._dim = dim
        self._model: Any = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        vectors = self._model.encode(texts, normalize_embeddings=True, batch_size=16)
        out = [[float(x) for x in v] for v in vectors]
        if any(len(v) != self._dim for v in out):
            raise ValueError(f"embedding model returned vectors that are not {self._dim}-dimensional")
        return out


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return BgeM3Embedder(settings.embedding_model, settings.embedding_dim)
