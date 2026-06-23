"""
NEXUS Memory System
ChromaDB persistent vector store with sentence-transformer embeddings.
Supports per-agent namespacing, semantic recall, and memory pruning.
"""

import hashlib
import time
import logging
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger("nexus.memory")

# Lazy-load to avoid slow startup
_collection = None
_embed_fn = None


def _get_collection():
    global _collection, _embed_fn
    if _collection is not None:
        return _collection

    import chromadb
    from chromadb.utils import embedding_functions
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config import CFG

    mem_cfg = CFG["memory"]

    # Use sentence-transformers for local, offline embeddings
    try:
        _embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=mem_cfg["embedding_model"]
        )
        logger.info(f"Embedding model loaded: {mem_cfg['embedding_model']}")
    except Exception as e:
        logger.warning(f"SentenceTransformer failed ({e}), using default embeddings")
        _embed_fn = None

    client = chromadb.PersistentClient(path=mem_cfg["persist_path"])
    _collection = client.get_or_create_collection(
        name=mem_cfg["collection_name"],
        embedding_function=_embed_fn,
    )
    logger.info(f"Memory collection ready: {_collection.count()} docs")
    return _collection


def save_memory(
    agent_name: str,
    content: str,
    category: str = "general",
    job_id: Optional[int] = None,
) -> str:
    """Persist a memory entry with metadata."""
    try:
        col = _get_collection()
        doc_id = hashlib.sha256(
            f"{agent_name}{content[:100]}{time.time()}".encode()
        ).hexdigest()[:32]

        col.add(
            documents=[content[:2000]],  # cap size
            metadatas=[{
                "agent": agent_name,
                "category": category,
                "job_id": str(job_id) if job_id else "none",
                "timestamp": str(time.time()),
            }],
            ids=[doc_id],
        )
        logger.debug(f"Memory saved [{agent_name}/{category}]: {content[:80]}...")
        return doc_id
    except Exception as e:
        logger.error(f"save_memory failed: {e}")
        return ""


def recall_memory(
    query: str,
    agent_name: Optional[str] = None,
    category: Optional[str] = None,
    n: int = 4,
    min_relevance: float = 0.0,
) -> str:
    """Semantic recall from memory. Returns formatted string."""
    try:
        col = _get_collection()
        if col.count() == 0:
            return "Memory is empty."

        where_conditions = []
        if agent_name:
            where_conditions.append({"agent": {"$eq": agent_name}})
        if category:
            where_conditions.append({"category": {"$eq": category}})

        where = None
        if len(where_conditions) == 1:
            where = where_conditions[0]
        elif len(where_conditions) > 1:
            where = {"$and": where_conditions}

        results = col.query(
            query_texts=[query],
            n_results=min(n, col.count()),
            where=where,
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        if not docs:
            return "No relevant memories found."

        formatted = []
        for doc, meta in zip(docs, metas):
            ts = float(meta.get("timestamp", 0))
            age = time.time() - ts
            age_str = _format_age(age)
            formatted.append(
                f"[{meta.get('agent', '?')}|{meta.get('category', '?')}|{age_str}]\n{doc}"
            )
        return "\n---\n".join(formatted)

    except Exception as e:
        logger.error(f"recall_memory failed: {e}")
        return f"Memory recall error: {e}"


def list_memories(agent_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """Return raw memory entries for inspection."""
    try:
        col = _get_collection()
        if col.count() == 0:
            return []
        where = {"agent": {"$eq": agent_name}} if agent_name else None
        results = col.get(where=where, limit=limit)
        return [
            {"id": i, "doc": d[:200], "meta": m}
            for i, d, m in zip(
                results["ids"], results["documents"], results["metadatas"]
            )
        ]
    except Exception as e:
        logger.error(f"list_memories failed: {e}")
        return []


def clear_memories(agent_name: Optional[str] = None):
    """Clear all or agent-specific memories."""
    try:
        col = _get_collection()
        if agent_name:
            results = col.get(where={"agent": {"$eq": agent_name}})
            if results["ids"]:
                col.delete(ids=results["ids"])
                logger.info(f"Cleared {len(results['ids'])} memories for {agent_name}")
        else:
            col.delete(where={})
            logger.info("Cleared all memories")
    except Exception as e:
        logger.error(f"clear_memories failed: {e}")


def memory_stats() -> Dict:
    """Return memory usage statistics."""
    try:
        col = _get_collection()
        count = col.count()
        all_meta = col.get()["metadatas"] if count > 0 else []
        agents = {}
        for m in all_meta:
            a = m.get("agent", "unknown")
            agents[a] = agents.get(a, 0) + 1
        return {"total": count, "by_agent": agents}
    except Exception as e:
        return {"error": str(e)}


def _format_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds/60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds/3600)}h ago"
    else:
        return f"{int(seconds/86400)}d ago"
