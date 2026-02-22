"""organization multitenancy

Revision ID: 0002_organization_multitenancy
Revises: 0001_initial_schema
Create Date: 2026-02-22
"""

import re
import secrets

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_organization_multitenancy"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "organization"


def _next_slug(base: str, seen: set[str]) -> str:
    slug = base
    i = 2
    while slug in seen:
        slug = f"{base}-{i}"
        i += 1
    seen.add(slug)
    return slug


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("org_type", sa.String(length=40), nullable=False),
        sa.Column("invite_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_id"), "organizations", ["id"], unique=False)
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)
    op.create_index(op.f("ix_organizations_invite_code"), "organizations", ["invite_code"], unique=True)

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("clinician_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinician_id"], ["clinicians.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "clinician_id", name="uq_organization_membership_org_clinician"),
    )
    op.create_index(op.f("ix_organization_memberships_id"), "organization_memberships", ["id"], unique=False)
    op.create_index(op.f("ix_organization_memberships_organization_id"), "organization_memberships", ["organization_id"], unique=False)
    op.create_index(op.f("ix_organization_memberships_clinician_id"), "organization_memberships", ["clinician_id"], unique=False)

    op.add_column("patients", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("encounters", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("organization_id", sa.Integer(), nullable=True))

    bind = op.get_bind()
    clinicians = bind.execute(sa.text("SELECT id, name, org FROM clinicians ORDER BY id")).mappings().all()

    seen_slugs: set[str] = set()
    organizations: dict[str, tuple[int, str]] = {}
    clinician_org_map: dict[int, int] = {}
    fallback_org_id: int | None = None

    for clinician in clinicians:
        clinician_id = int(clinician["id"])
        clinician_name = str(clinician["name"] or "").strip() or f"Clinician {clinician_id}"
        provided_org = str(clinician["org"] or "").strip()

        if provided_org:
            group_key = f"hospital::{provided_org.casefold()}"
            org_name = provided_org
            org_type = "hospital"
        else:
            group_key = f"solo::{clinician_id}"
            org_name = f"{clinician_name} Practice"
            org_type = "solo_practice"

        if group_key not in organizations:
            slug = _next_slug(_slugify(org_name), seen_slugs)
            invite_code = secrets.token_urlsafe(8) if org_type == "hospital" else None
            org_id = bind.execute(
                sa.text(
                    """
                    INSERT INTO organizations (name, slug, org_type, invite_code)
                    VALUES (:name, :slug, :org_type, :invite_code)
                    RETURNING id
                    """
                ),
                {"name": org_name, "slug": slug, "org_type": org_type, "invite_code": invite_code},
            ).scalar_one()
            organizations[group_key] = (int(org_id), org_type)
            if fallback_org_id is None:
                fallback_org_id = int(org_id)

        organization_id, created_org_type = organizations[group_key]
        clinician_org_map[clinician_id] = organization_id

        if created_org_type == "hospital":
            existing_members = bind.execute(
                sa.text("SELECT 1 FROM organization_memberships WHERE organization_id = :organization_id LIMIT 1"),
                {"organization_id": organization_id},
            ).first()
            role = "owner" if not existing_members else "clinician"
        else:
            role = "owner"

        bind.execute(
            sa.text(
                """
                INSERT INTO organization_memberships (organization_id, clinician_id, role)
                VALUES (:organization_id, :clinician_id, :role)
                """
            ),
            {"organization_id": organization_id, "clinician_id": clinician_id, "role": role},
        )
        bind.execute(
            sa.text("UPDATE clinicians SET org = :org WHERE id = :clinician_id"),
            {"org": org_name, "clinician_id": clinician_id},
        )

    if fallback_org_id is None:
        fallback_org_id = bind.execute(
            sa.text(
                """
                INSERT INTO organizations (name, slug, org_type, invite_code)
                VALUES (:name, :slug, :org_type, :invite_code)
                RETURNING id
                """
            ),
            {"name": "Legacy Organization", "slug": "legacy-organization", "org_type": "hospital", "invite_code": secrets.token_urlsafe(8)},
        ).scalar_one()

    for clinician_id, organization_id in clinician_org_map.items():
        bind.execute(
            sa.text(
                "UPDATE encounters SET organization_id = :organization_id WHERE clinician_id = :clinician_id AND organization_id IS NULL"
            ),
            {"organization_id": organization_id, "clinician_id": clinician_id},
        )

    bind.execute(
        sa.text("UPDATE encounters SET organization_id = :fallback_org_id WHERE organization_id IS NULL"),
        {"fallback_org_id": int(fallback_org_id)},
    )

    patient_org_rows = bind.execute(
        sa.text(
            """
            SELECT DISTINCT ON (patient_id) patient_id, organization_id
            FROM encounters
            WHERE organization_id IS NOT NULL
            ORDER BY patient_id, created_at DESC
            """
        )
    ).mappings().all()
    for row in patient_org_rows:
        bind.execute(
            sa.text("UPDATE patients SET organization_id = :organization_id WHERE id = :patient_id AND organization_id IS NULL"),
            {"organization_id": int(row["organization_id"]), "patient_id": int(row["patient_id"])},
        )

    bind.execute(
        sa.text("UPDATE patients SET organization_id = :fallback_org_id WHERE organization_id IS NULL"),
        {"fallback_org_id": int(fallback_org_id)},
    )

    for clinician_id, organization_id in clinician_org_map.items():
        bind.execute(
            sa.text(
                """
                UPDATE audit_logs
                SET organization_id = :organization_id
                WHERE organization_id IS NULL AND actor_clinician_id = :clinician_id
                """
            ),
            {"organization_id": organization_id, "clinician_id": clinician_id},
        )

    bind.execute(
        sa.text(
            """
            UPDATE audit_logs AS a
            SET organization_id = e.organization_id
            FROM encounters AS e
            WHERE a.organization_id IS NULL
              AND a.entity_type = 'encounter'
              AND a.entity_id = e.id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE audit_logs AS a
            SET organization_id = p.organization_id
            FROM patients AS p
            WHERE a.organization_id IS NULL
              AND a.entity_type = 'patient'
              AND a.entity_id = p.id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE audit_logs AS a
            SET organization_id = m.organization_id
            FROM organization_memberships AS m
            WHERE a.organization_id IS NULL
              AND a.entity_type = 'clinician'
              AND a.entity_id = m.clinician_id
            """
        )
    )
    bind.execute(
        sa.text("UPDATE audit_logs SET organization_id = :fallback_org_id WHERE organization_id IS NULL"),
        {"fallback_org_id": int(fallback_org_id)},
    )

    op.create_index(op.f("ix_patients_organization_id"), "patients", ["organization_id"], unique=False)
    op.create_index(op.f("ix_encounters_organization_id"), "encounters", ["organization_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False)

    op.create_foreign_key("fk_patients_organization_id", "patients", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_encounters_organization_id", "encounters", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_audit_logs_organization_id", "audit_logs", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")

    op.alter_column("patients", "organization_id", nullable=False)
    op.alter_column("encounters", "organization_id", nullable=False)
    op.alter_column("audit_logs", "organization_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_audit_logs_organization_id", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_encounters_organization_id", "encounters", type_="foreignkey")
    op.drop_constraint("fk_patients_organization_id", "patients", type_="foreignkey")

    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_encounters_organization_id"), table_name="encounters")
    op.drop_index(op.f("ix_patients_organization_id"), table_name="patients")

    op.drop_column("audit_logs", "organization_id")
    op.drop_column("encounters", "organization_id")
    op.drop_column("patients", "organization_id")

    op.drop_index(op.f("ix_organization_memberships_clinician_id"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_organization_id"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_id"), table_name="organization_memberships")
    op.drop_table("organization_memberships")

    op.drop_index(op.f("ix_organizations_invite_code"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_id"), table_name="organizations")
    op.drop_table("organizations")
