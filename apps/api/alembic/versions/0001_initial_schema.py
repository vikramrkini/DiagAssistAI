"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "clinicians",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("specialty", sa.String(length=50), nullable=False),
        sa.Column("sub_specialty", sa.String(length=120), nullable=True),
        sa.Column("org", sa.String(length=255), nullable=True),
        sa.Column("preferences_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinicians_email"), "clinicians", ["email"], unique=True)
    op.create_index(op.f("ix_clinicians_id"), "clinicians", ["id"], unique=False)

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("sex", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patients_id"), "patients", ["id"], unique=False)

    op.create_table(
        "guideline_docs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("specialty_tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guideline_docs_id"), "guideline_docs", ["id"], unique=False)

    op.create_table(
        "encounters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("clinician_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("structured_intake_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("final_diagnosis_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["clinician_id"], ["clinicians.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_encounters_id"), "encounters", ["id"], unique=False)
    op.create_index(op.f("ix_encounters_clinician_id"), "encounters", ["clinician_id"], unique=False)
    op.create_index(op.f("ix_encounters_patient_id"), "encounters", ["patient_id"], unique=False)

    op.create_table(
        "guideline_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_hash", sa.String(length=64), nullable=False),
        sa.Column("specialty_tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("bm25_terms", sa.Text(), nullable=True),
        sa.Column("tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["guideline_docs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guideline_chunks_chunk_hash"), "guideline_chunks", ["chunk_hash"], unique=True)
    op.create_index(op.f("ix_guideline_chunks_doc_id"), "guideline_chunks", ["doc_id"], unique=False)
    op.create_index(op.f("ix_guideline_chunks_id"), "guideline_chunks", ["id"], unique=False)
    op.create_index("ix_guideline_chunks_specialty_tags", "guideline_chunks", ["specialty_tags"], unique=False, postgresql_using="gin")
    op.execute("CREATE INDEX ix_guideline_chunks_tsv ON guideline_chunks USING GIN (tsv)")
    op.execute("CREATE INDEX ix_guideline_chunks_embedding ON guideline_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

    op.create_table(
        "ai_outputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("specialty_used", sa.Text(), nullable=False),
        sa.Column("differential_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("red_flags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("followups_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tests_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("citations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("uncertainty_notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_outputs_encounter_id"), "ai_outputs", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_ai_outputs_id"), "ai_outputs", ["id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_clinician_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_clinician_id"], ["clinicians.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_actor_clinician_id"), "audit_logs", ["actor_clinician_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)

    op.execute(
        """
        CREATE FUNCTION guideline_chunks_tsv_trigger() RETURNS trigger AS $$
        begin
            new.tsv := to_tsvector('english', coalesce(new.chunk_text, ''));
            return new;
        end
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
        ON guideline_chunks FOR EACH ROW EXECUTE FUNCTION guideline_chunks_tsv_trigger();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tsvectorupdate ON guideline_chunks")
    op.execute("DROP FUNCTION IF EXISTS guideline_chunks_tsv_trigger")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_clinician_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_ai_outputs_id"), table_name="ai_outputs")
    op.drop_index(op.f("ix_ai_outputs_encounter_id"), table_name="ai_outputs")
    op.drop_table("ai_outputs")
    op.execute("DROP INDEX IF EXISTS ix_guideline_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS ix_guideline_chunks_tsv")
    op.drop_index("ix_guideline_chunks_specialty_tags", table_name="guideline_chunks")
    op.drop_index(op.f("ix_guideline_chunks_id"), table_name="guideline_chunks")
    op.drop_index(op.f("ix_guideline_chunks_doc_id"), table_name="guideline_chunks")
    op.drop_index(op.f("ix_guideline_chunks_chunk_hash"), table_name="guideline_chunks")
    op.drop_table("guideline_chunks")
    op.drop_index(op.f("ix_encounters_patient_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_clinician_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_id"), table_name="encounters")
    op.drop_table("encounters")
    op.drop_index(op.f("ix_guideline_docs_id"), table_name="guideline_docs")
    op.drop_table("guideline_docs")
    op.drop_index(op.f("ix_patients_id"), table_name="patients")
    op.drop_table("patients")
    op.drop_index(op.f("ix_clinicians_id"), table_name="clinicians")
    op.drop_index(op.f("ix_clinicians_email"), table_name="clinicians")
    op.drop_table("clinicians")
