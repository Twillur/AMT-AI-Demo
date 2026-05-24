import os, json
import chromadb
from openai import OpenAI

_client  = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_chroma  = chromadb.PersistentClient(path="db/chroma")
_THRESHOLD = 0.94  # cosine similarity — above this = cache hit
_COL_NAME  = "amt_response_cache_v4"

_col = None


def _collection():
    global _col
    if _col is None:
        existing = [c.name for c in _chroma.list_collections()]
        if _COL_NAME in existing:
            _col = _chroma.get_collection(_COL_NAME)
        else:
            _col = _chroma.create_collection(_COL_NAME, metadata={"hnsw:space": "cosine"})
    return _col


def _embed(text: str) -> list:
    return _client.embeddings.create(
        model="text-embedding-3-small", input=[text]
    ).data[0].embedding


def check(question: str, department: str) -> dict | None:
    col = _collection()
    if col.count() == 0:
        return None
    emb = _embed(question)
    results = col.query(query_embeddings=[emb], n_results=1, where={"department": department})
    if not results["ids"][0]:
        return None
    distance  = results["distances"][0][0]
    similarity = 1 - distance
    if similarity >= _THRESHOLD:
        meta = results["metadatas"][0][0]
        return {
            "response": meta["response"],
            "tools":    json.loads(meta["tools"]),
            "tokens":   json.loads(meta["tokens"]),
            "similarity": round(similarity * 100, 1),
        }
    return None


def store(question: str, department: str, response: str, tools: list, tokens: dict):
    col = _collection()
    import hashlib
    doc_id = hashlib.md5(f"{department}:{question}".encode()).hexdigest()
    emb = _embed(question)
    try:
        col.delete(ids=[doc_id])
    except Exception:
        pass
    col.add(
        ids=[doc_id],
        documents=[question],
        embeddings=[emb],
        metadatas=[{
            "department": department,
            "response":   response,
            "tools":      json.dumps(tools),
            "tokens":     json.dumps(tokens),
        }]
    )
