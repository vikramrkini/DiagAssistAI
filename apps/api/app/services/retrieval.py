from dataclasses import dataclass
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.guideline import GuidelineChunk, GuidelineDoc
from app.services.embeddings import cosine_similarity, embed_text


@dataclass
class RetrievedChunk:
    chunk_id: int
    doc_id: int
    title: str
    source: str
    excerpt: str
    specialty_tags: list[str]
    fused_score: float


def _tokenize(text: str) -> list[str]:
    return [t.strip(".,:;!?()[]{}\"'").lower() for t in text.split() if len(t) > 2]


def _bm25_scores(query_text: str, docs: list[str]) -> list[float]:
    q_terms = _tokenize(query_text)
    if not q_terms or not docs:
        return [0.0 for _ in docs]

    doc_tokens = [_tokenize(doc) for doc in docs]
    doc_lens = [len(toks) for toks in doc_tokens]
    avgdl = (sum(doc_lens) / len(doc_lens)) if doc_lens else 1.0
    N = len(doc_tokens)
    df = Counter()
    for toks in doc_tokens:
        for term in set(toks):
            df[term] += 1

    scores = []
    k1 = 1.2
    b = 0.75
    for toks, dl in zip(doc_tokens, doc_lens):
        tf = Counter(toks)
        score = 0.0
        for term in q_terms:
            n_q = df.get(term, 0)
            if n_q == 0:
                continue
            idf = max(0.0, (N - n_q + 0.5) / (n_q + 0.5))
            freq = tf.get(term, 0)
            denom = freq + k1 * (1 - b + b * (dl / (avgdl or 1.0)))
            score += idf * ((freq * (k1 + 1)) / (denom or 1.0))
        scores.append(score)
    max_score = max(scores) if scores else 1.0
    if max_score <= 0:
        return [0.0 for _ in scores]
    return [s / max_score for s in scores]


def retrieve_chunks(db: Session, query_text: str, specialty: str, top_k: int = 8) -> list[RetrievedChunk]:
    query_embedding = embed_text(query_text)
    rows = db.execute(select(GuidelineChunk, GuidelineDoc).join(GuidelineDoc, GuidelineDoc.id == GuidelineChunk.doc_id)).all()
    bm25 = _bm25_scores(query_text, [chunk.chunk_text for chunk, _ in rows])

    scored: list[RetrievedChunk] = []
    for i, (chunk, doc) in enumerate(rows):
        emb_score = cosine_similarity(query_embedding, chunk.embedding or [])
        lex_score = bm25[i]
        boost = 0.2 if specialty in (chunk.specialty_tags or []) else 0.0
        fused = (0.45 * lex_score) + (0.45 * emb_score) + boost
        scored.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                doc_id=doc.id,
                title=doc.title,
                source=doc.source,
                excerpt=chunk.chunk_text[:280],
                specialty_tags=chunk.specialty_tags or [],
                fused_score=fused,
            )
        )

    scored.sort(key=lambda c: c.fused_score, reverse=True)
    return scored[:top_k]
