"""Full-text search (SQLite FTS5) and vector search for case library.

FullTextIndex: SQLite FTS5 virtual table for keyword search.
VectorIndex: sentence-transformers embeddings + numpy cosine similarity.
"""
import json
import os
import sqlite3
import numpy as np
from pathlib import Path
from typing import Optional

from config import BASE_DIR, DATA_DIR

FTS_DB_PATH = Path(os.getenv("FTS_DB_PATH", DATA_DIR / "case_search.db"))
VECTOR_DB_PATH = Path(os.getenv("VECTOR_DB_PATH", DATA_DIR / "case_vectors.npz"))
VECTOR_META_PATH = Path(os.getenv("VECTOR_META_PATH", DATA_DIR / "case_vectors_meta.json"))


def _expand_search_query(q: str) -> str:
    """Expand search query for better recall.

    Chinese: progressively shorten terms ("价格战" → "价格" OR "价格战")
    English: add wildcard suffix for prefix matching ("price" → "price*")
    """
    q = q.strip()
    if not q:
        return q

    terms = [q]

    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in q)

    if has_chinese:
        # Progressively shorten Chinese characters
        for i in range(len(q) - 1, 1, -1):
            sub = q[:i]
            if any("\u4e00" <= c <= "\u9fff" for c in sub):
                terms.append(sub)
    else:
        # English: add wildcard for prefix matching
        terms.append(f"{q}*")

    # Build FTS5 OR query with quoted terms (except wildcards)
    parts = []
    seen = set()
    for t in terms:
        if t in seen:
            continue
        seen.add(t)
        if t.endswith("*"):
            parts.append(t)
        else:
            parts.append(f'"{t}"')

    return " OR ".join(parts)

# Lazy-loaded embedding model
_model = None


def _get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


class FullTextIndex:
    """SQLite FTS5 full-text search index."""

    def __init__(self, db_path: str = ""):
        self._db_path = db_path or str(FTS_DB_PATH)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS case_fts
            USING fts5(doc_id, brand_name, filename, content, tags)
        """)
        conn.commit()
        conn.close()

    def add_document(self, doc_id: str, brand_name: str, filename: str,
                     content: str, tags: str = ""):
        conn = sqlite3.connect(self._db_path)
        # Remove existing entry for this doc_id
        conn.execute("DELETE FROM case_fts WHERE doc_id = ?", (doc_id,))
        conn.execute(
            "INSERT INTO case_fts (doc_id, brand_name, filename, content, tags) VALUES (?, ?, ?, ?, ?)",
            (doc_id, brand_name, filename, content[:100000], tags),
        )
        conn.commit()
        conn.close()

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search the FTS index.

        Returns:
            [{"doc_id", "brand_name", "filename", "snippet", "rank"}]
        """
        expanded = _expand_search_query(query)
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute("""
                SELECT doc_id, brand_name, filename,
                       snippet(case_fts, 3, '<b>', '</b>', '...', 40) as snippet,
                       rank
                FROM case_fts
                WHERE case_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (expanded, limit)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        conn.close()

        return [
            {
                "doc_id": r[0],
                "brand_name": r[1],
                "filename": r[2],
                "snippet": r[3],
                "rank": r[4],
            }
            for r in rows
        ]

    def clear(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("DELETE FROM case_fts")
        conn.commit()
        conn.close()


class VectorIndex:
    """Numpy-based vector similarity search using sentence-transformers."""

    def __init__(self, vectors_path: str = "", meta_path: str = ""):
        self._vectors_path = vectors_path or str(VECTOR_DB_PATH)
        self._meta_path = meta_path or str(VECTOR_META_PATH)
        self._vectors: Optional[np.ndarray] = None
        self._meta: list[dict] = []
        self._load()

    def _load(self):
        if Path(self._vectors_path).exists() and Path(self._meta_path).exists():
            data = np.load(self._vectors_path)
            self._vectors = data["vectors"]
            with open(self._meta_path) as f:
                self._meta = json.load(f)
        else:
            self._vectors = None
            self._meta = []

    def _save(self):
        if self._vectors is not None and len(self._meta) > 0:
            np.savez_compressed(self._vectors_path, vectors=self._vectors)
            with open(self._meta_path, "w") as f:
                json.dump(self._meta, f)

    def add_document(self, doc_id: str, brand_name: str, filename: str, text: str):
        """Embed and store a document."""
        model = _get_embedding_model()
        # Truncate text for embedding
        embedding = model.encode(text[:2000], normalize_embeddings=True)

        entry = {"doc_id": doc_id, "brand_name": brand_name, "filename": filename}

        # Check if doc_id already exists
        existing_idx = next(
            (i for i, m in enumerate(self._meta) if m["doc_id"] == doc_id), None
        )

        if existing_idx is not None:
            self._vectors[existing_idx] = embedding
            self._meta[existing_idx] = entry
        else:
            if self._vectors is None:
                self._vectors = embedding.reshape(1, -1)
            else:
                self._vectors = np.vstack([self._vectors, embedding])
            self._meta.append(entry)

        self._save()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Semantic similarity search.

        Returns:
            [{"doc_id", "brand_name", "filename", "score"}]
        """
        if self._vectors is None or len(self._meta) == 0:
            return []

        model = _get_embedding_model()
        query_vec = model.encode(query, normalize_embeddings=True)

        # Cosine similarity (vectors are already normalized)
        scores = self._vectors @ query_vec
        top_indices = np.argsort(scores)[::-1][:limit]

        results = []
        for idx in top_indices:
            if scores[idx] < 0.1:
                break
            results.append({
                **self._meta[idx],
                "score": float(scores[idx]),
            })

        return results

    def clear(self):
        self._vectors = None
        self._meta = []
        for p in [self._vectors_path, self._meta_path]:
            path = Path(p)
            if path.exists():
                path.unlink()
