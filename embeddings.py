"""Shared helpers for creating Ollama embedding vectors."""

import json
from urllib.request import Request, urlopen

from config import EMBEDDING_MODEL, EMBED_URL


def create_embeddings(texts):
    """Return one embedding vector for every string in *texts*."""
    data = json.dumps({"model": EMBEDDING_MODEL, "input": texts}).encode("utf-8")
    request = Request(
        EMBED_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        return json.load(response)["embeddings"]
