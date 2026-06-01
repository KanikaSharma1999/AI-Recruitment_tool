import os
import json
import asyncio
import pickle
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ── Dependency Checks ────────────────────────────────────────────────────────
HAS_FAISS = False
import sys
# On Windows, faiss-cpu has a known OpenMP deadlock issue that causes imports to hang.
# We check the DISABLE_FAISS env variable (defaulting to true on Windows to prevent hanging).
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

# ── Lazy global model (loaded once) ──────────────────────────────────────────
_model = None
_model_lock = asyncio.Lock()

def get_embedding_model():
    """Return cached SentenceTransformer model (loaded once)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[VectorStore] Loading embedding model all-MiniLM-L6-v2 ...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[VectorStore] Embedding model ready.")
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

class _Store:
    def __init__(self):
        self.resume_index   = None
        self.resume_meta: List[Dict] = []
        self.jd_index       = None
        self.jd_meta: List[Dict]     = []
        self.dim            = 384
        self._lock          = asyncio.Lock()
        self.is_ready       = False

_store = _Store()

def _create_index(dim: int):
    if not HAS_FAISS: return None
    try:
        import faiss
        return faiss.IndexFlatIP(dim)
    except Exception as e:
        logger.error(f"[VectorStore] Index creation failed: {e}")
        return None

def _save_index(index, meta: list, index_path: str, meta_path: str):
    if not HAS_FAISS or index is None: return
    try:
        import faiss
        os.makedirs(_INDEX_DIR, exist_ok=True)
        faiss.write_index(index, index_path)
        with open(meta_path, "wb") as f:
            pickle.dump(meta, f)
    except Exception as e:
        logger.error(f"[VectorStore] Save failed: {e}")

def _load_index(index_path: str, meta_path: str):
    if not HAS_FAISS: return None, []
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

async def init_vector_store():
    """Initialise on startup with dependency check."""
    if not HAS_FAISS:
        _store.is_ready = False
        return
    
    async with _store._lock:
        idx, meta = _load_index(RESUME_INDEX_PATH, RESUME_META_PATH)
        _store.resume_index = idx or _create_index(_store.dim)
        _store.resume_meta  = meta
        
        idx2, meta2 = _load_index(JD_INDEX_PATH, JD_META_PATH)
        _store.jd_index = idx2 or _create_index(_store.dim)
        _store.jd_meta  = meta2
        
        _store.is_ready = True
    logger.info("[VectorStore] Ready with %d resumes.", len(_store.resume_meta))

def _embed(text: str):
    if not HAS_FAISS: return None
    try:
        import numpy as np
        model = get_embedding_model()
        if not model: return None
        vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vec.astype("float32").reshape(1, -1)
    except Exception as e:
        logger.error(f"[VectorStore] Embed failed: {e}")
        return None

async def index_resume(candidate_id: str, name: str, text: str, extra: dict = None):
    if not _store.is_ready or not text: return
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, text)
    if vec is None: return

    async with _store._lock:
        idx = -1
        for i, m in enumerate(_store.resume_meta):
            if m.get("id") == candidate_id:
                idx = i
                break
        
        import numpy as np
        if idx != -1:
            try:
                _store.resume_index.remove_ids(np.array([idx], dtype='int64'))
                _store.resume_meta.pop(idx)
            except Exception as e:
                logger.error(f"[VectorStore] Failed to remove stale candidate vector during update: {e}")
        
        _store.resume_meta.append({"id": candidate_id, "name": name, **(extra or {})})
        _store.resume_index.add(vec)
        _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)

async def index_job(job_id: str, title: str, description: str):
    if not _store.is_ready or not title: return
    text = f"{title} {description[:500]}"
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, text)
    if vec is None: return

    async with _store._lock:
        idx = -1
        for i, m in enumerate(_store.jd_meta):
            if m.get("id") == job_id:
                idx = i
                break
        
        import numpy as np
        if idx != -1:
            try:
                _store.jd_index.remove_ids(np.array([idx], dtype='int64'))
                _store.jd_meta.pop(idx)
            except Exception as e:
                logger.error(f"[VectorStore] Failed to remove stale job vector during update: {e}")
                
        _store.jd_meta.append({"id": job_id, "title": title})
        _store.jd_index.add(vec)
        _save_index(_store.jd_index, _store.jd_meta, JD_INDEX_PATH, JD_META_PATH)


async def search_jobs(query: str, top_k: int = 5) -> List[Dict]:
    if not _store.is_ready or not query: return []
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, query)
    if vec is None: return []

    async with _store._lock:
        if not _store.jd_index or _store.jd_index.ntotal == 0: return []
        k = min(top_k, _store.jd_index.ntotal)
        scores, indices = _store.jd_index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(_store.jd_meta):
                m = dict(_store.jd_meta[idx])
                m["similarity"] = round(float(score), 4)
                results.append(m)
        return results

async def bulk_index_jobs(jobs: List[Dict]):
    if not _store.is_ready or not jobs: return
    texts = [f"{j.get('title', '')} {j.get('description', '')[:500]}" for j in jobs]
    
    def _batch_embed(ts):
        try:
            m = get_embedding_model()
            if not m: return None
            import numpy as np
            v = m.encode(ts, normalize_embeddings=True, batch_size=32)
            return v.astype("float32")
        except: return None

    vecs = await asyncio.get_event_loop().run_in_executor(None, _batch_embed, texts)
    if vecs is None: return

    async with _store._lock:
        for i, j in enumerate(jobs):
            jid = str(j.get("id") or j.get("_id", ""))
            if not jid: continue
            _store.jd_meta.append({"id": jid, "title": j.get("title", "Unknown")})
            _store.jd_index.add(vecs[i].reshape(1, -1))
        _save_index(_store.jd_index, _store.jd_meta, JD_INDEX_PATH, JD_META_PATH)

async def search_resumes(query: str, top_k: int = 10) -> List[Dict]:
    if not _store.is_ready or not query: return []
    vec = await asyncio.get_event_loop().run_in_executor(None, _embed, query)
    if vec is None: return []

    async with _store._lock:
        if not _store.resume_index or _store.resume_index.ntotal == 0: return []
        k = min(top_k, _store.resume_index.ntotal)
        scores, indices = _store.resume_index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(_store.resume_meta):
                m = dict(_store.resume_meta[idx])
                m["similarity"] = round(float(score), 4)
                results.append(m)
        return results

async def bulk_index_resumes(candidates: List[Dict]):
    if not _store.is_ready or not candidates: return
    texts = [c.get("raw_text", "") or "" for c in candidates]
    
    def _batch_embed(ts):
        try:
            m = get_embedding_model()
            if not m: return None
            import numpy as np
            v = m.encode(ts, normalize_embeddings=True, batch_size=32)
            return v.astype("float32")
        except: return None

    vecs = await asyncio.get_event_loop().run_in_executor(None, _batch_embed, texts)
    if vecs is None: return

    async with _store._lock:
        for i, c in enumerate(candidates):
            cid = str(c.get("id") or c.get("_id", ""))
            if not cid: continue
            _store.resume_meta.append({"id": cid, "name": c.get("name", "Unknown")})
            _store.resume_index.add(vecs[i].reshape(1, -1))
        _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)

def get_store_stats() -> Dict:
    return {
        "ready": _store.is_ready,
        "resumes": _store.resume_index.ntotal if _store.resume_index else 0,
        "faiss_installed": HAS_FAISS
    }

def get_indexed_candidate_ids() -> set:
    """Return a set of candidate IDs that are already indexed in FAISS."""
    if not _store.is_ready:
        return set()
    return {m.get("id") for m in _store.resume_meta if m.get("id")}

async def delete_candidate_vector(candidate_id: str):
    """Safely remove a candidate's vector and metadata from the FAISS index."""
    if not _store.is_ready:
        return
    async with _store._lock:
        idx = -1
        for i, m in enumerate(_store.resume_meta):
            if m.get("id") == candidate_id:
                idx = i
                break
        if idx != -1:
            try:
                import numpy as np
                _store.resume_index.remove_ids(np.array([idx], dtype='int64'))
                _store.resume_meta.pop(idx)
                _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)
                logger.info(f"[VectorStore] Successfully deleted candidate {candidate_id} from vector index.")
            except Exception as e:
                logger.error(f"[VectorStore] Failed to delete candidate vector {candidate_id}: {e}")

async def delete_job_vector(job_id: str):
    """Safely remove a job vector and all of its associated candidate vectors from FAISS."""
    if not _store.is_ready:
        return
    async with _store._lock:
        # 1. Cascade delete candidates associated with this job in a single batch
        import numpy as np
        indices_to_remove = [i for i, m in enumerate(_store.resume_meta) if m.get("job_id") == job_id]
        if indices_to_remove:
            try:
                indices_set = set(indices_to_remove)
                # Batch remove matching candidate vectors
                _store.resume_index.remove_ids(np.array(indices_to_remove, dtype='int64'))
                # Filter metadata list in one step
                _store.resume_meta = [m for i, m in enumerate(_store.resume_meta) if i not in indices_set]
                _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)
                logger.info(f"[VectorStore] Cascade deleted {len(indices_to_remove)} candidate vectors for job {job_id}.")
            except Exception as e:
                logger.error(f"[VectorStore] Failed to cascade delete candidates for job {job_id}: {e}")

        # 2. Delete the job vector itself
        idx_job = -1
        for i, m in enumerate(_store.jd_meta):
            if m.get("id") == job_id:
                idx_job = i
                break
        if idx_job != -1:
            try:
                _store.jd_index.remove_ids(np.array([idx_job], dtype='int64'))
                _store.jd_meta.pop(idx_job)
                _save_index(_store.jd_index, _store.jd_meta, JD_INDEX_PATH, JD_META_PATH)
                logger.info(f"[VectorStore] Successfully deleted job {job_id} from JD vector index.")
            except Exception as e:
                logger.error(f"[VectorStore] Failed to delete job vector {job_id}: {e}")

async def rebuild_resume_index(candidates: List[Dict]):
    """Completely reconstruct the FAISS resume index and metadata from scratch."""
    if not _store.is_ready: return
    logger.info(f"[VectorStore] Rebuilding resume index from scratch with {len(candidates)} candidates...")
    
    async with _store._lock:
        _store.resume_index = _create_index(_store.dim)
        _store.resume_meta = []
        _save_index(_store.resume_index, _store.resume_meta, RESUME_INDEX_PATH, RESUME_META_PATH)
    
    if candidates:
        chunk_size = 20
        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i+chunk_size]
            await bulk_index_resumes(chunk)
        logger.info("[VectorStore] Resume index rebuild complete.")


