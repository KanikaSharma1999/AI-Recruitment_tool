"""
services/vector_store.py
=========================
FAISS-based vector store for semantic resume & JD search.

Embedding model: BAAI/bge-large-en-v1.5
  - Dimension: 1024 (upgraded from 384 / all-MiniLM-L6-v2)
  - Better semantic understanding for resume ranking
  - Better JD matching and FAISS retrieval

Migration safety:
  - If an existing index has dimension != 1024, it is auto-discarded and rebuilt.
  - Old embeddings (384-dim) are NEVER mixed with new 1024-dim embeddings.

Workflow:
  Resume → bge-large-en-v1.5 → Embedding (1024-dim) → FAISS → Cosine Similarity → Semantic Score
"""

import os
import json
import asyncio
import pickle
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ── FAISS availability ────────────────────────────────────────────────────────
HAS_FAISS = False
import sys

disable_faiss_env = os.getenv("DISABLE_FAISS", "true" if sys.platform == "win32" else "false")
if disable_faiss_env.lower() != "true":
    try:
        import faiss
        import numpy as np
        HAS_FAISS = True
    except Exception as e:
        logger.warning(f"⚠️ [VectorStore] Failed to import FAISS: {e}. Vector search will be disabled.")
else:
    logger.info("[VectorStore] FAISS is disabled via environment variable or platform default.")

# ── BGE-large embedding model ─────────────────────────────────────────────────
_model = None
_model_lock = asyncio.Lock()

# New embedding dimension: bge-large-en-v1.5 outputs 1024-dim vectors
EMBEDDING_DIM = 1024
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"


def get_embedding_model():
    """
    Return cached SentenceTransformer model (loaded once).
    Uses BAAI/bge-large-en-v1.5 (1024-dim) instead of all-MiniLM-L6-v2 (384-dim).
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[VectorStore] Loading embedding model %s ...", EMBEDDING_MODEL_NAME)
            _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info("[VectorStore] Embedding model ready (dim=%d).", EMBEDDING_DIM)
        except Exception as e:
            logger.error(f"[VectorStore] Could not load embedding model: {e}")
            _model = None
    return _model


# ── Index paths ───────────────────────────────────────────────────────────────
_INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "faiss_index")
RESUME_INDEX_PATH = os.path.join(_INDEX_DIR, "resumes.index")
RESUME_META_PATH  = os.path.join(_INDEX_DIR, "resumes_meta.pkl")
JD_INDEX_PATH     = os.path.join(_INDEX_DIR, "jobs.index")
JD_META_PATH      = os.path.join(_INDEX_DIR, "jobs_meta.pkl")
# Dimension manifest — tracks what dim the current index was built with
DIM_MANIFEST_PATH = os.path.join(_INDEX_DIR, "index_dim.json")


class _Store:
    def __init__(self):
        self.resume_index   = None
        self.resume_meta: List[Dict] = []
        self.jd_index       = None
        self.jd_meta: List[Dict]     = []
        self.dim            = EMBEDDING_DIM
        self._lock          = asyncio.Lock()
        self.is_ready       = False


_store = _Store()


# ── Index helpers ─────────────────────────────────────────────────────────────

def _create_index(dim: int):
    if not HAS_FAISS:
        return None
    try:
        import faiss
        # IndexFlatIP = inner-product (cosine similarity when vectors are normalized)
        return faiss.IndexFlatIP(dim)
    except Exception as e:
        logger.error(f"[VectorStore] Index creation failed: {e}")
        return None


def _save_index(index, meta: list, index_path: str, meta_path: str):
    if not HAS_FAISS or index is None:
        return
    try:
        import faiss
        os.makedirs(_INDEX_DIR, exist_ok=True)
        faiss.write_index(index, index_path)
        with open(meta_path, "wb") as f:
            pickle.dump(meta, f)
    except Exception as e:
        logger.error(f"[VectorStore] Save failed: {e}")


def _load_index(index_path: str, meta_path: str):
    if not HAS_FAISS:
        return None, []
    try:
        import faiss
        if os.path.exists(index_path) and os.path.exists(meta_path):
            idx  = faiss.read_index(index_path)
            with open(meta_path, "rb") as f:
                meta = pickle.load(f)
            return idx, meta
    except Exception as e:
        logger.error(f"[VectorStore] Load failed: {e}")
    return None, []


def _read_stored_dim() -> Optional[int]:
    """Read the dimension the current on-disk index was built with."""
    try:
        if os.path.exists(DIM_MANIFEST_PATH):
            with open(DIM_MANIFEST_PATH) as f:
                data = json.load(f)
            return int(data.get("dim", 0))
    except Exception:
        pass
    return None


def _write_dim_manifest(dim: int):
    """Persist the embedding dimension to disk."""
    os.makedirs(_INDEX_DIR, exist_ok=True)
    with open(DIM_MANIFEST_PATH, "w") as f:
        json.dump({"dim": dim, "model": EMBEDDING_MODEL_NAME}, f)


def _needs_rebuild() -> bool:
    """
    Check if the on-disk FAISS index was built with a different dimension.
    Old all-MiniLM-L6-v2 indices are 384-dim; new BGE indices are 1024-dim.
    If dimensions differ, the old index MUST be discarded.
    """
    stored_dim = _read_stored_dim()
    if stored_dim is None:
        # No manifest: check the actual index dimension if it exists
        try:
            if os.path.exists(RESUME_INDEX_PATH):
                import faiss
                idx = faiss.read_index(RESUME_INDEX_PATH)
                if idx.d != EMBEDDING_DIM:
                    logger.warning(
                        "[VectorStore] Existing index has dim=%d, expected %d. "
                        "Will discard and rebuild.",
                        idx.d, EMBEDDING_DIM,
                    )
                    return True
        except Exception:
            pass
        return False
    return stored_dim != EMBEDDING_DIM


def _discard_old_indices():
    """Remove stale index files to force a clean rebuild."""
    for path in [RESUME_INDEX_PATH, RESUME_META_PATH, JD_INDEX_PATH, JD_META_PATH]:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info("[VectorStore] Discarded stale index file: %s", path)
        except Exception:
            pass


# ── Initialization ────────────────────────────────────────────────────────────

async def init_vector_store():
    """
    Initialise FAISS store on startup.
    Automatically rebuilds if embedding dimension has changed.
    """
    if not HAS_FAISS:
        _store.is_ready = False
        return

    async with _store._lock:
        # Dimension migration check
        if _needs_rebuild():
            logger.warning(
                "[VectorStore] Embedding model changed to %s (dim=%d). "
                "Discarding old index and starting fresh.",
                EMBEDDING_MODEL_NAME, EMBEDDING_DIM,
            )
            _discard_old_indices()

        idx, meta = _load_index(RESUME_INDEX_PATH, RESUME_META_PATH)
        _store.resume_index = idx or _create_index(EMBEDDING_DIM)
        _store.resume_meta  = meta

        idx2, meta2 = _load_index(JD_INDEX_PATH, JD_META_PATH)
        _store.jd_index = idx2 or _create_index(EMBEDDING_DIM)
        _store.jd_meta  = meta2

        _write_dim_manifest(EMBEDDING_DIM)
        _store.is_ready = True

    logger.info("[VectorStore] Ready (model=%s, dim=%d, resumes=%d).",
                EMBEDDING_MODEL_NAME, EMBEDDING_DIM, len(_store.resume_meta))


# ── Embedding ─────────────────────────────────────────────────────────────────

def _embed(text: str):
    if not HAS_FAISS:
        return None
    try:
        import numpy as np
        model = get_embedding_model()
        if not model:
            return None
        # BGE models benefit from a query prefix for retrieval tasks
        prefixed = f"Represent this resume for retrieval: {text}"
        vec = model.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True)
        return vec.astype("float32").reshape(1, -1)
    except Exception as e:
        logger.error(f"[VectorStore] Embed failed: {e}")
        return None


def _embed_batch(texts: List[str]) -> Optional[Any]:
    """Batch embedding for performance when indexing multiple resumes."""
    if not HAS_FAISS:
        return None
    try:
        import numpy as np
        model = get_embedding_model()
        if not model:
            return None
        prefixed = [f"Represent this resume for retrieval: {t}" for t in texts]
        vecs = model.encode(
            prefixed,
            normalize_embeddings=True,
            batch_size=16,
            show_progress_bar=False,
        )
        return vecs.astype("float32")
    except Exception as e:
        logger.error(f"[VectorStore] Batch embed failed: {e}")
        return None


# ── Indexing ──────────────────────────────────────────────────────────────────

async def index_resume(candidate_id: str, name: str, text: str, extra: dict = None):
    if not _store.is_ready or not text:
        return
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, text)
    if vec is None:
        return

    async with _store._lock:
        # Remove existing entry if present (to avoid duplicates on re-index)
        idx = next((i for i, m in enumerate(_store.resume_meta) if m.get("id") == candidate_id), -1)

        import numpy as np
        if idx != -1:
            try:
                _store.resume_index.remove_ids(np.array([idx], dtype="int64"))
                _store.resume_meta.pop(idx)
            except Exception as e:
                logger.error(f"[VectorStore] Failed to remove stale candidate vector: {e}")

        _store.resume_meta.append({"id": candidate_id, "name": name, **(extra or {})})
        _store.resume_index.add(vec)
        _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)


async def index_job(job_id: str, title: str, description: str):
    if not _store.is_ready or not title:
        return
    text = f"{title} {description[:800]}"
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, text)
    if vec is None:
        return

    async with _store._lock:
        idx = next((i for i, m in enumerate(_store.jd_meta) if m.get("id") == job_id), -1)

        import numpy as np
        if idx != -1:
            try:
                _store.jd_index.remove_ids(np.array([idx], dtype="int64"))
                _store.jd_meta.pop(idx)
            except Exception as e:
                logger.error(f"[VectorStore] Failed to remove stale job vector: {e}")

        _store.jd_meta.append({"id": job_id, "title": title})
        _store.jd_index.add(vec)
        _save_index(_store.jd_index, _store.jd_meta, JD_INDEX_PATH, JD_META_PATH)


# ── Search ────────────────────────────────────────────────────────────────────

async def search_resumes(query: str, top_k: int = 10) -> List[Dict]:
    if not _store.is_ready or not query:
        return []
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, query)
    if vec is None:
        return []

    async with _store._lock:
        if not _store.resume_index or _store.resume_index.ntotal == 0:
            return []
        k = min(top_k, _store.resume_index.ntotal)
        scores, indices = _store.resume_index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(_store.resume_meta):
                m = dict(_store.resume_meta[idx])
                m["similarity"] = round(float(score), 4)
                results.append(m)
        return results


async def search_jobs(query: str, top_k: int = 5) -> List[Dict]:
    if not _store.is_ready or not query:
        return []
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, query)
    if vec is None:
        return []

    async with _store._lock:
        if not _store.jd_index or _store.jd_index.ntotal == 0:
            return []
        k = min(top_k, _store.jd_index.ntotal)
        scores, indices = _store.jd_index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(_store.jd_meta):
                m = dict(_store.jd_meta[idx])
                m["similarity"] = round(float(score), 4)
                results.append(m)
        return results


# ── Bulk operations (for performance with 500+ resumes) ───────────────────────

async def bulk_index_resumes(candidates: List[Dict]):
    """Batch-embed and index multiple candidates for performance."""
    if not _store.is_ready or not candidates:
        return

    texts = [c.get("raw_text", "") or "" for c in candidates]
    vecs = await asyncio.get_event_loop().run_in_executor(None, _embed_batch, texts)
    if vecs is None:
        return

    async with _store._lock:
        for i, c in enumerate(candidates):
            cid = str(c.get("id") or c.get("_id", ""))
            if not cid:
                continue
            _store.resume_meta.append({"id": cid, "name": c.get("name", "Unknown")})
            _store.resume_index.add(vecs[i].reshape(1, -1))
        _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)


async def bulk_index_jobs(jobs: List[Dict]):
    """Batch-embed and index multiple job descriptions."""
    if not _store.is_ready or not jobs:
        return

    texts = [f"{j.get('title', '')} {j.get('description', '')[:800]}" for j in jobs]
    vecs = await asyncio.get_event_loop().run_in_executor(None, _embed_batch, texts)
    if vecs is None:
        return

    async with _store._lock:
        for i, j in enumerate(jobs):
            jid = str(j.get("id") or j.get("_id", ""))
            if not jid:
                continue
            _store.jd_meta.append({"id": jid, "title": j.get("title", "Unknown")})
            _store.jd_index.add(vecs[i].reshape(1, -1))
        _save_index(_store.jd_index, _store.jd_meta, JD_INDEX_PATH, JD_META_PATH)


# ── Deletion ──────────────────────────────────────────────────────────────────

async def delete_candidate_vector(candidate_id: str):
    """Safely remove a candidate's vector and metadata from the FAISS index."""
    if not _store.is_ready:
        return
    async with _store._lock:
        idx = next((i for i, m in enumerate(_store.resume_meta) if m.get("id") == candidate_id), -1)
        if idx != -1:
            try:
                import numpy as np
                _store.resume_index.remove_ids(np.array([idx], dtype="int64"))
                _store.resume_meta.pop(idx)
                _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)
                logger.info("[VectorStore] Deleted candidate %s from vector index.", candidate_id)
            except Exception as e:
                logger.error(f"[VectorStore] Failed to delete candidate vector {candidate_id}: {e}")


async def delete_job_vector(job_id: str):
    """Safely remove a job and its associated candidate vectors from FAISS."""
    if not _store.is_ready:
        return
    async with _store._lock:
        import numpy as np

        # Cascade delete candidates associated with this job
        indices_to_remove = [
            i for i, m in enumerate(_store.resume_meta) if m.get("job_id") == job_id
        ]
        if indices_to_remove:
            try:
                indices_set = set(indices_to_remove)
                _store.resume_index.remove_ids(np.array(indices_to_remove, dtype="int64"))
                _store.resume_meta = [
                    m for i, m in enumerate(_store.resume_meta) if i not in indices_set
                ]
                _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)
                logger.info("[VectorStore] Cascade deleted %d candidate vectors for job %s.",
                            len(indices_to_remove), job_id)
            except Exception as e:
                logger.error(f"[VectorStore] Failed to cascade delete candidates for job {job_id}: {e}")

        # Delete the job vector itself
        idx_job = next((i for i, m in enumerate(_store.jd_meta) if m.get("id") == job_id), -1)
        if idx_job != -1:
            try:
                _store.jd_index.remove_ids(np.array([idx_job], dtype="int64"))
                _store.jd_meta.pop(idx_job)
                _save_index(_store.jd_index, _store.jd_meta, JD_INDEX_PATH, JD_META_PATH)
                logger.info("[VectorStore] Deleted job %s from JD vector index.", job_id)
            except Exception as e:
                logger.error(f"[VectorStore] Failed to delete job vector {job_id}: {e}")


async def rebuild_resume_index(candidates: List[Dict]):
    """
    Completely reconstruct the FAISS resume index from scratch.
    Used after embedding model migration.
    """
    if not _store.is_ready:
        return
    logger.info("[VectorStore] Rebuilding resume index from scratch with %d candidates ...", len(candidates))

    async with _store._lock:
        _store.resume_index = _create_index(EMBEDDING_DIM)
        _store.resume_meta  = []
        _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)

    if candidates:
        chunk_size = 20
        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i + chunk_size]
            await bulk_index_resumes(chunk)
    logger.info("[VectorStore] Resume index rebuild complete.")


# ── Stats & utilities ─────────────────────────────────────────────────────────

def get_store_stats() -> Dict:
    return {
        "ready":            _store.is_ready,
        "resumes":          _store.resume_index.ntotal if _store.resume_index else 0,
        "jobs":             _store.jd_index.ntotal if _store.jd_index else 0,
        "faiss_installed":  HAS_FAISS,
        "embedding_model":  EMBEDDING_MODEL_NAME,
        "embedding_dim":    EMBEDDING_DIM,
    }


def get_indexed_candidate_ids() -> set:
    """Return a set of candidate IDs that are already indexed in FAISS."""
    if not _store.is_ready:
        return set()
    return {m.get("id") for m in _store.resume_meta if m.get("id")}
