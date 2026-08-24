from __future__ import annotations
import hashlib, math
from .base import EmbeddingProvider

class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Offline deterministic vectors for tests and local smoke runs; not a semantic model."""
    def __init__(self, dimension: int = 64): self.dimension = dimension
    def embed(self, texts: list[str]) -> list[list[float]]:
        out=[]
        for text in texts:
            vals=[]
            seed=text.encode("utf-8")
            for i in range(self.dimension):
                h=hashlib.sha256(seed + i.to_bytes(4,"big")).digest()
                vals.append((int.from_bytes(h[:4],"big")/2**32)*2-1)
            norm=math.sqrt(sum(v*v for v in vals)) or 1
            out.append([v/norm for v in vals])
        return out
