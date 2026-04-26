"""Vector search tool — queries ChromaDB for matching candidates."""

import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

# Load once, reuse across calls
_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
        except:
            pass
        _model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        db_path = "db/chroma"
        client = chromadb.PersistentClient(path=db_path)
        _collection = client.get_collection("candidates")
    return _collection


def reset_vector_cache():
    """Reset the cached collection reference. Call after clearing ChromaDB."""
    global _collection
    _collection = None


def search_candidates(parsed_jd: dict, top_k: int = 15) -> list:
    """
    Semantic search: embed the JD requirements and find
    closest candidate profiles in ChromaDB.
    Returns list of full candidate dicts with similarity distance.
    """
    model = _get_model()
    collection = _get_collection()

    # Build search query from parsed JD
    skills = ", ".join(parsed_jd.get("must_have_skills", []))
    nice_skills = ", ".join(parsed_jd.get("nice_to_have_skills", []))
    query_text = (
        f"Role: {parsed_jd.get('job_title', '')}. "
        f"Required skills: {skills}. "
        f"Nice to have: {nice_skills}. "
        f"Experience: {parsed_jd.get('min_experience_years', 0)}-"
        f"{parsed_jd.get('max_experience_years', 10)} years. "
        f"Education: {parsed_jd.get('education_required', '')}. "
        f"Domain: {parsed_jd.get('industry_domain', '')}"
    )

    # Embed and search
    query_embedding = model.encode(query_text).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    # Load full candidate profiles from JSON files
    candidates = []
    candidate_dir = "data/candidates"

    for i in range(len(results["ids"][0])):
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        # Load full profile from file
        filepath = os.path.join(candidate_dir, metadata.get("file", ""))
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                full_profile = json.load(f)
        else:
            full_profile = dict(metadata)

        full_profile["_search_distance"] = distance
        full_profile["_search_rank"] = i + 1
        candidates.append(full_profile)

    return candidates
