#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "apps" / "api"))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.guideline import GuidelineChunk, GuidelineDoc
from app.services.embeddings import embed_text

GUIDELINES_DIR = ROOT / "data" / "guidelines"

SPECIALTY_MAP = {
    "general": ["general"],
    "pediatrics": ["pediatrics"],
    "physio": ["physiotherapy"],
    "dermatology": ["dermatology"],
}


def infer_specialty_tags(filename: str) -> list[str]:
    lower = filename.lower()
    tags = []
    for key, mapped in SPECIALTY_MAP.items():
        if key in lower:
            tags.extend(mapped)
    if not tags:
        tags.append("general")
    return sorted(set(tags))


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks = []
    i = 0
    while i < len(cleaned):
        chunks.append(cleaned[i : i + chunk_size])
        i += chunk_size
    return chunks


def main() -> None:
    db = SessionLocal()
    created_docs = 0
    created_chunks = 0
    try:
        for path in sorted(GUIDELINES_DIR.glob("*.md")):
            content = path.read_text()
            title = content.splitlines()[0].replace("#", "").strip() if content.strip() else path.stem
            source = f"repo://data/guidelines/{path.name}"
            specialty_tags = infer_specialty_tags(path.name)

            doc = db.execute(select(GuidelineDoc).where(GuidelineDoc.source == source)).scalar_one_or_none()
            if not doc:
                doc = GuidelineDoc(title=title, source=source, specialty_tags=specialty_tags)
                db.add(doc)
                db.flush()
                created_docs += 1

            for chunk in chunk_text(content):
                chunk_hash = hashlib.sha256(f"{source}:{chunk}".encode("utf-8")).hexdigest()
                exists = db.execute(
                    select(GuidelineChunk).where(GuidelineChunk.chunk_hash == chunk_hash)
                ).scalar_one_or_none()
                if exists:
                    continue
                row = GuidelineChunk(
                    doc_id=doc.id,
                    chunk_text=chunk,
                    chunk_hash=chunk_hash,
                    specialty_tags=specialty_tags,
                    bm25_terms=chunk.lower(),
                    embedding=embed_text(chunk),
                )
                db.add(row)
                created_chunks += 1

        db.commit()
        print(f"Ingestion complete. docs_created={created_docs} chunks_created={created_chunks}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
