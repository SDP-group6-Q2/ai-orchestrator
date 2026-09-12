"""Manual retrieval helpers used by the manuals agent.

Retrieval is a real RAG pipeline over the machine manuals: each PDF is chunked,
embedded, and stored in Postgres (manual_chunks, via pgvector) scoped by
company_id + machine_id, with indexed_manuals tracking which manuals have
already been chunked/embedded. The index is built once per machine and reused
across runs; the first query for a given machine bears the embedding/insert
cost, later ones just query the persisted rows.

Runs against src/db/db.py's "assistant" Postgres database (plain psycopg2,
same connection the rest of the assistant's DB layer uses) -- see
src/db/startup.py's create_manuals_tables for the schema setup.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.tools import tool
from pgvector.psycopg2 import register_vector
from pypdf import PdfReader
from sentence_transformers import CrossEncoder, SentenceTransformer

from src.db.db import get_db
from src.tools.fleet_directory import machine_lookup

logger = logging.getLogger(__name__)

_MANUALS_DIR = Path(__file__).resolve().parents[2] / "data" / "manuals"
_MANUAL_FILENAME_SUFFIX = "_manual_EN.pdf"
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 200

_CANDIDATE_K = 20  # pulled from pgvector before reranking
_TOP_K = 5  # kept after reranking, what actually reaches the LLM
_MIN_VALID_CHARS = 20

_embedder = SentenceTransformer(_EMBEDDING_MODEL)
_reranker = CrossEncoder(_RERANKER_MODEL)

# Last retrieval, kept for inspection/testing (see show_last_retrieval below).
# Not thread-safe -- fine for the single-session terminal/test use this serves.
_last_retrieval: dict = {}


def _get_connection():
    conn = get_db()
    register_vector(conn)
    return conn


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


def _load_manual_chunks(pdf_path: Path) -> list[tuple[str, int]]:
    """Returns (chunk_text, page_number) pairs for a manual's PDF."""
    reader = PdfReader(str(pdf_path))
    chunks: list[tuple[str, int]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for chunk in _chunk_text(text):
            chunks.append((chunk, page_number))
    return chunks


def _is_indexed(conn, company_id: str, machine_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM indexed_manuals WHERE company_id = %s AND machine_id = %s;",
            (company_id, machine_id),
        )
        return cur.fetchone() is not None


def _index_manual(conn, company_id: str, machine_id: str, serial_number: str, pdf_path: Path) -> None:
    logger.info("Indexing manual for machine_id %s (first run, this may take a while)...", machine_id)
    chunks = _load_manual_chunks(pdf_path)
    if not chunks:
        logger.warning("Manual for machine_id %s produced no extractable text", machine_id)
        return

    texts = [text for text, _ in chunks]
    embeddings = _embedder.encode(texts, batch_size=32, show_progress_bar=False)

    with conn.cursor() as cur:
        for (text, page), embedding in zip(chunks, embeddings):
            cur.execute(
                """
                INSERT INTO manual_chunks (company_id, machine_id, source, page, content, embedding)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (company_id, machine_id, pdf_path.name, page, text, embedding),
            )
        cur.execute(
            """
            INSERT INTO indexed_manuals (company_id, machine_id, serial_number)
            VALUES (%s, %s, %s)
            ON CONFLICT (company_id, machine_id) DO NOTHING;
            """,
            (company_id, machine_id, serial_number),
        )
    conn.commit()

    logger.info("Indexed %d chunks for machine_id %s", len(chunks), machine_id)


def index_all_manuals() -> None:
    """Eagerly index every manual PDF found under data/manuals (idempotent -- skips already-indexed ones).

    Driven by what's actually on disk, not by the machines table: each
    "{serial_number}_manual_EN.pdf" file is matched back to its owning machine(s) via
    a serial_number lookup, so a machine with no PDF yet is simply never indexed (no
    wasted per-machine lookup/failure), and a PDF with no matching machine is reported
    and skipped. Called from src/db/startup.py so indexing cost is paid at setup time,
    not on the first live query for a machine (get_manual_excerpts is read-only).
    """
    conn = _get_connection()
    try:
        for pdf_path in sorted(_MANUALS_DIR.glob(f"*{_MANUAL_FILENAME_SUFFIX}")):
            serial_number = pdf_path.name[: -len(_MANUAL_FILENAME_SUFFIX)]

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT machineid, companyid FROM machines WHERE serialnumber = %s;",
                    (serial_number,),
                )
                matches = cur.fetchall()

            if not matches:
                logger.warning("Manual %s has no matching machine (serial_number=%r)", pdf_path.name, serial_number)
                continue

            for row in matches:
                machine_id, company_id = row["machineid"], row["companyid"]
                if _is_indexed(conn, company_id, machine_id):
                    continue
                _index_manual(conn, company_id, machine_id, serial_number, pdf_path)
    finally:
        conn.close()


def _is_valid_excerpt(content: str) -> bool:
    """Reject empty/garbage retrieval results (e.g. from a scanned or malformed page)."""
    return bool(content) and len(content.strip()) >= _MIN_VALID_CHARS


@tool
def get_manual_excerpts(query: str, machine_id: str) -> list[dict] | str:
    """Semantic (RAG) search over a machine's manual documents; retrieves the excerpts most relevant to a query.

    Returns a list of {source, page, content} dicts on success, or a plain
    string message for the no-query/not-indexed/no-results edge cases.
    """
    # TODO: no visibility-tier check here -- only company_id tenant scoping (implicit,
    # since company_id is derived from machine_id below, not attacker/LLM-controlled).
    # A commercial-only user should still be denied manuals of a company they don't
    # belong to; visibility tiers (technician/full) aren't enforced at all yet.
    if not query.strip():
        return "No query was provided. Please ask a specific question about the manual."

    machine = machine_lookup(machine_id)
    if machine is None:
        return f"No manual is registered for machine_id {machine_id}."
    company_id = machine["company_id"]

    conn = _get_connection()
    try:
        if not _is_indexed(conn, company_id, machine_id):
            logger.warning("get_manual_excerpts: machine_id=%s has not been indexed yet", machine_id)
            return f"The manual for machine_id {machine_id} has not been indexed yet. Run the fleet indexing step (src/db/startup.py) to make it available."

        query_embedding = _embedder.encode(query)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source, page, content, embedding <=> %s AS distance
                FROM manual_chunks
                WHERE company_id = %s AND machine_id = %s
                ORDER BY embedding <=> %s
                LIMIT %s;
                """,
                (query_embedding, company_id, machine_id, query_embedding, _CANDIDATE_K),
            )
            candidates = cur.fetchall()
    finally:
        conn.close()

    if not candidates:
        _last_retrieval.clear()
        _last_retrieval.update(query=query, machine_id=machine_id, company_id=company_id, candidates=[], reranked=[])
        logger.warning("get_manual_excerpts: no candidates for machine_id=%s query=%r", machine_id, query)
        return "No relevant manual excerpts were found for that query."

    pairs = [(query, row["content"]) for row in candidates]
    rerank_scores = _reranker.predict(pairs)

    reranked = sorted(
        (
            (row["source"], row["page"], row["content"], float(row["distance"]), float(score))
            for row, score in zip(candidates, rerank_scores)
        ),
        key=lambda row: row[4],
        reverse=True,
    )[:_TOP_K]

    _last_retrieval.clear()
    _last_retrieval.update(
        query=query,
        machine_id=machine_id,
        company_id=company_id,
        candidates=[
            {"source": row["source"], "page": row["page"], "distance": float(row["distance"]), "content": row["content"]}
            for row in candidates
        ],
        reranked=[
            {"source": s, "page": p, "distance": d, "rerank_score": score, "content": c}
            for s, p, c, d, score in reranked
        ],
    )

    valid = [(source, page, content) for source, page, content, _, _ in reranked if _is_valid_excerpt(content)]
    if not valid:
        logger.warning("get_manual_excerpts: no valid excerpts for machine_id=%s query=%r", machine_id, query)
        return "No relevant manual excerpts were found for that query."

    return [{"source": source, "page": page, "content": content} for source, page, content in valid]


def show_last_retrieval() -> str:
    """Print/return the pre- and post-rerank chunks from the most recent get_manual_excerpts call.

    For testing/debugging: shows exactly what evidence was retrieved from
    pgvector, and how reranking reordered it, before it was sent to the LLM.
    """
    if not _last_retrieval:
        return "No retrieval has happened yet."

    lines = [
        f"Query: {_last_retrieval['query']!r} (machine_id={_last_retrieval['machine_id']}, company_id={_last_retrieval['company_id']})",
        "",
        f"-- {len(_last_retrieval['candidates'])} candidates from pgvector (pre-rerank, by cosine distance) --",
    ]
    for i, c in enumerate(_last_retrieval["candidates"], start=1):
        lines.append(f"{i}. distance={c['distance']:.4f} | {c['source']} p{c['page']}: {c['content'][:120]}")

    lines.append("")
    lines.append(f"-- {len(_last_retrieval['reranked'])} chunks after reranking (sent to LLM) --")
    for i, r in enumerate(_last_retrieval["reranked"], start=1):
        lines.append(
            f"{i}. rerank_score={r['rerank_score']:.4f} (distance={r['distance']:.4f}) | "
            f"{r['source']} p{r['page']}: {r['content'][:120]}"
        )

    return "\n".join(lines)
