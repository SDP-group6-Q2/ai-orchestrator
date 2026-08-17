"""Manual retrieval helpers used by the manuals agent.

Retrieval is a real RAG pipeline over the machine manuals: each PDF is
chunked, embedded, and stored in a persistent Chroma collection keyed by
the machine's serial number (the join key used in manuals/<serialNumber>.pdf,
see the Project-Q2-Database dataset README). The index is built once and
reused across runs; the first run for a given manual bears the embedding
cost, later ones just query the persisted collection.
"""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from langchain_core.tools import tool
from pypdf import PdfReader

from src.tools.fleet_directory import MACHINE_TO_SERIAL

logger = logging.getLogger(__name__)

_MANUALS_DIR = Path(__file__).resolve().parents[2] / "data" / "manuals"
_CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "chroma"
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 200

_TOP_K = 5
_MIN_VALID_CHARS = 20

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=_EMBEDDING_MODEL)
_client = chromadb.PersistentClient(path=str(_CHROMA_DIR))


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks


def _load_manual_chunks(serial_number: str) -> list[tuple[str, dict]]:
    pdf_path = _MANUALS_DIR / f"{serial_number}_manual_EN.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"No manual found for serial number {serial_number!r} at {pdf_path}")

    reader = PdfReader(str(pdf_path))
    chunks: list[tuple[str, dict]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for chunk in _chunk_text(text):
            chunks.append((chunk, {"source": pdf_path.name, "page": page_number}))
    return chunks


def _get_or_build_collection(serial_number: str):
    collection_name = f"manual_{serial_number}"
    collection = _client.get_or_create_collection(name=collection_name, embedding_function=_embedding_fn)

    if collection.count() > 0:
        return collection

    logger.info("Indexing manual for serial number %s (first run, this may take a while)...", serial_number)
    chunks = _load_manual_chunks(serial_number)
    if not chunks:
        logger.warning("Manual for serial number %s produced no extractable text", serial_number)
        return collection

    documents = [chunk for chunk, _ in chunks]
    metadatas = [meta for _, meta in chunks]
    ids = [f"{serial_number}-{i}" for i in range(len(chunks))]

    batch_size = 100
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        collection.add(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )

    logger.info("Indexed %d chunks for serial number %s", len(chunks), serial_number)
    return collection


def _is_valid_excerpt(document: str, metadata: dict) -> bool:
    """Reject empty/garbage retrieval results (e.g. from a scanned or malformed page)."""
    if not document or len(document.strip()) < _MIN_VALID_CHARS:
        return False
    if "source" not in metadata or "page" not in metadata:
        return False
    return True


@tool
def get_manual_excerpts(query: str, machine_id: str) -> str:
    """Retrieve the manual excerpts most relevant to a query, for a specific machine."""
    # TODO: MACHINE_TO_SERIAL is a hardcoded stopgap. Replace with a real lookup
    # (DB-backed, or an upstream identity-resolution step) once one exists.
    # TODO: no access-control check here -- nothing verifies the requesting user
    # is allowed to see this machine's manual (tenant/visibility boundary).
    serial_number = MACHINE_TO_SERIAL.get(machine_id)
    if serial_number is None:
        return f"No manual is registered for machine_id {machine_id}."

    try:
        collection = _get_or_build_collection(serial_number)
    except FileNotFoundError as exc:
        logger.warning("Manual lookup failed: %s", exc)
        return str(exc)

    if collection.count() == 0:
        return f"The manual for machine_id {machine_id} has no extractable content."

    results = collection.query(query_texts=[query], n_results=min(_TOP_K, collection.count()))
    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]

    valid_pairs = [
        (doc, meta)
        for doc, meta in zip(documents[0], metadatas[0])
        if _is_valid_excerpt(doc, meta)
    ]
    if not valid_pairs:
        logger.warning("get_manual_excerpts: no valid excerpts for machine_id=%s query=%r", machine_id, query)
        return "No relevant manual excerpts were found for that query."

    excerpts = [f"- {meta['source']} (page {meta['page']}): {doc}" for doc, meta in valid_pairs]
    return "\n".join(excerpts)
