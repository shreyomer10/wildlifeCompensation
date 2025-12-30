# app/utils/pinecone_store.py
import os
import logging
from typing import List, Dict, Any, Optional

from pinecone import Pinecone, ServerlessSpec
from app.config import Config

API_KEY = Config.PINECONE_API_KEY
ENV = Config.PINECONE_ENV  # e.g. "us-east-1" or "gcp-starter"
INDEX_NAME = Config.PINECONE_INDEX or "compensation-forms"

# Model embedding dimension for all-MiniLM-L6-v2
EMBED_DIM = 384

# Create a single Pinecone client instance
# Map ENV -> cloud provider if needed
def _env_to_cloud_and_region(env: str):
    if not env:
        return ("aws", "us-east-1")
    env = env.lower()
    if env.startswith("gcp"):
        # examples: gcp-starter, gcp-us-west1
        return ("gcp", env.replace("gcp-", ""))
    if env.startswith("aws"):
        return ("aws", env.replace("aws-", ""))
    # if user provided direct region like 'us-east-1', assume AWS
    return ("aws", env)

_cloud, _region = _env_to_cloud_and_region(ENV)
pc = Pinecone(api_key=API_KEY)


def ensure_index(dim: int = EMBED_DIM) -> Pinecone.Index:
    """
    Ensure the index exists and return a Pinecone Index object.
    """
    try:
        existing = pc.list_indexes().names()
    except Exception as e:
        logging.error(f"Failed to list Pinecone indexes: {e}")
        existing = []

    if INDEX_NAME not in existing:
        logging.info(f"Creating Pinecone index '{INDEX_NAME}' with dim={dim}, metric=cosine")
        try:
            spec = ServerlessSpec(cloud=_cloud, region=_region)
            pc.create_index(
                name=INDEX_NAME,
                dimension=dim,
                metric="cosine",
                spec=spec
            )
        except Exception as e:
            logging.exception("Failed to create Pinecone index:")
            raise

    return pc.Index(INDEX_NAME)


def fetch_vector(form_id: int) -> Optional[List[float]]:
    """
    Fetch stored vector for a given form_id from the index.
    Returns None if not found.
    """
    idx = ensure_index()
    try:
        res = idx.fetch(ids=[str(form_id)])
    except Exception as e:
        logging.error(f"Pinecone fetch error for id {form_id}: {e}")
        return None

    vectors = res.get("vectors") or {}
    entry = vectors.get(str(form_id))
    if not entry:
        return None
    return entry.get("values")


def upsert_form_vector(form_id: int, vector: List[float], metadata: Dict[str, Any]) -> None:
    """
    Upsert a single vector + metadata into the index.
    """
    idx = ensure_index(len(vector))
    try:
        idx.upsert([(str(form_id), vector, metadata)])
    except Exception as e:
        logging.exception(f"Pinecone upsert failed for id {form_id}: {e}")
        raise


def query_similar(vector: List[float], top_k: int = 10, filter: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Query the index for nearest neighbors.
    Returns list of dicts: {formID, score, metadata}
    """
    idx = ensure_index(len(vector))
    try:
        result = idx.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            include_values=False,
            filter=filter
        )
    except Exception as e:
        logging.exception("Pinecone query failed:")
        return []

    out = []
    matches = result.get("matches") or []
    for m in matches:
        out.append({
            "formID": m.get("id"),
            "score": m.get("score"),
            "metadata": m.get("metadata", {})
        })
    return out
