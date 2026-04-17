"""
Ingestion script — reads files from DOCS_DIR, chunks them,
creates embeddings and stores them in ChromaDB.

Supported file types: .txt, .md, .pdf, .csv, .json
"""

import logging
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)

COLLECTION_NAME = "arcadia_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _get_collection(chroma_dir: str):
    client = chromadb.PersistentClient(path=chroma_dir)
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


def _read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning(f"Could not read PDF {path}: {e}")
            return ""
    if suffix == ".csv":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".json":
        return path.read_text(encoding="utf-8", errors="ignore")
    logger.warning(f"Unsupported file type, skipping: {path}")
    return ""


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks


def run_ingest(docs_dir: str, chroma_dir: str, chunk_size: int, chunk_overlap: int):
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        logger.warning(f"Docs directory does not exist: {docs_dir}")
        return

    files = [
        p for p in docs_path.rglob("*")
        if p.is_file() and p.suffix.lower() in (".txt", ".md", ".pdf", ".csv", ".json")
    ]
    if not files:
        logger.info("No supported files found in docs directory")
        return

    collection = _get_collection(chroma_dir)

    total_chunks = 0
    for file_path in files:
        logger.info(f"Ingesting: {file_path}")
        text = _read_file(file_path)
        if not text.strip():
            continue
        chunks = _chunk_text(text, chunk_size, chunk_overlap)
        if not chunks:
            continue

        ids       = [f"{file_path.name}::chunk{i}" for i in range(len(chunks))]
        metadatas = [{"source": file_path.name, "chunk": i} for i in range(len(chunks))]

        # Upsert so re-ingesting updated files replaces old chunks
        collection.upsert(documents=chunks, ids=ids, metadatas=metadatas)
        total_chunks += len(chunks)
        logger.info(f"  → {len(chunks)} chunks from {file_path.name}")

    logger.info(f"Ingestion complete. Total chunks upserted: {total_chunks}")


def query_context(query: str, chroma_dir: str, top_k: int) -> list[str]:
    """Return the top-k most relevant text chunks for a query."""
    try:
        collection = _get_collection(chroma_dir)
        if collection.count() == 0:
            return []
        results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))
        return results["documents"][0] if results["documents"] else []
    except Exception as e:
        logger.warning(f"ChromaDB query failed: {e}")
        return []
