"""Normalize dirty tags: split multi-tags, map synonyms, remove garbage.

Revision ID: 018
Revises: 017
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

# Dirty tag → canonical tag mapping
SYNONYM_MAP: dict[str, str] = {
    # CV
    "Computer Vision": "CV",
    "CV (Computer Vision)": "CV",
    "\u0421omputer vision": "CV",  # Cyrillic С
    "OCR": "CV",
    # Agents
    "Автономные агенты": "Agents",
    "мульти-агентные системы": "Agents",
    "Агентные системы": "Agents",
    "MCP": "Agents",
    "AI-сервисы": "Agents",
    "Автономные модели": "Agents",
    # FinTech
    "ML в Fintech": "FinTech",
    "финтех": "FinTech",
    "RegTech": "FinTech",
    # RecSys
    "Recsys": "RecSys",
    "Recsys / предиктивная аналитика": "RecSys",
    "Classic ML + AB-тесты": "RecSys",
    # ASR
    "Распознавание речи": "ASR",
    "Распознавание речи (Automated...)": "ASR",
    "Распознавание речи (Automated Speech Recognition (ASR) / speech-to-text (STT))": "ASR",
    "Speech Recognition": "ASR",
    "Распознавание и синтез речи": "ASR",
    # TTS / Audio
    "Синтез речи": "TTS",
    "Синтез речи (Speech Synthesis...)": "TTS",
    "Синтез речи (Speech Synthesis / text-to-speech (TTS))": "TTS",
    "транскрибация)": "Audio",
    "ИИ в музыке (сепарация": "Audio",
    # EdTech
    "edtech": "EdTech",
    "Edtech": "EdTech",
    # LLM
    "LLM/VLM": "LLM",
    "LLM и VLM": "LLM",
    "RAG и LLM": "LLM",
    "RAG": "LLM",
    "ML": "LLM",
    # Industrial
    "ML в промышленности": "Industrial",
    "DL в промышленности": "Industrial",
    # TimeSeries
    "Временные ряды": "TimeSeries",
    # Science
    "Естественные науки + ML": "Science",
    "GeoML": "Science",
    "агротех": "Science",
    # RL
    "Обучение с подкреплением": "RL",
    "MARL": "RL",
    # Security
    "MLSec": "Security",
    "Red Teaming": "Security",
    "LLM-агенты в области ИБ": "Security",
    "LLM-агенты в области информационной безопасности": "Security",
    "Информационная безопасность (IAM) + LLM": "Security",
}

# Tags to delete entirely (garbage)
GARBAGE_TAGS: set[str] = {
    "описание",
    "описание проекта",
    "parsing",
    "Backend",
    "Data",
    "Процессы",
}


def upgrade() -> None:
    conn = op.get_bind()

    # --- Step 1: Split multi-tags (contain \t) ---
    multi_rows = conn.execute(
        sa.text("SELECT id, name FROM tags WHERE name LIKE :pat"),
        {"pat": "%\t%"},
    ).fetchall()

    for tag_id, tag_name in multi_rows:
        subtags = [s.strip() for s in tag_name.split("\t") if s.strip()]

        # Get all project_ids linked to this multi-tag
        project_ids = [
            row[0]
            for row in conn.execute(
                sa.text("SELECT project_id FROM project_tags WHERE tag_id = :tid"),
                {"tid": tag_id},
            ).fetchall()
        ]

        for subtag_raw in subtags:
            # Normalize the subtag through synonym map
            canonical = SYNONYM_MAP.get(subtag_raw, subtag_raw)

            # Find or create the canonical tag
            row = conn.execute(
                sa.text("SELECT id FROM tags WHERE name = :n"),
                {"n": canonical},
            ).fetchone()
            if row:
                canonical_id = row[0]
            else:
                conn.execute(
                    sa.text("INSERT INTO tags (id, name) VALUES (gen_random_uuid(), :n)"),
                    {"n": canonical},
                )
                canonical_id = conn.execute(
                    sa.text("SELECT id FROM tags WHERE name = :n"),
                    {"n": canonical},
                ).fetchone()[0]

            # Link all projects to canonical tag
            for pid in project_ids:
                conn.execute(
                    sa.text(
                        "INSERT INTO project_tags (id, project_id, tag_id) "
                        "VALUES (gen_random_uuid(), :pid, :tid) "
                        "ON CONFLICT (project_id, tag_id) DO NOTHING"
                    ),
                    {"pid": pid, "tid": canonical_id},
                )

        # Remove old multi-tag links and the tag itself
        conn.execute(
            sa.text("DELETE FROM project_tags WHERE tag_id = :tid"),
            {"tid": tag_id},
        )
        conn.execute(
            sa.text("DELETE FROM tags WHERE id = :tid"),
            {"tid": tag_id},
        )

    # --- Step 2: Map synonyms to canonical tags ---
    for dirty_name, canonical_name in SYNONYM_MAP.items():
        dirty_row = conn.execute(
            sa.text("SELECT id FROM tags WHERE name = :n"),
            {"n": dirty_name},
        ).fetchone()
        if not dirty_row:
            continue
        dirty_id = dirty_row[0]

        # Find or create canonical tag
        canon_row = conn.execute(
            sa.text("SELECT id FROM tags WHERE name = :n"),
            {"n": canonical_name},
        ).fetchone()
        if canon_row:
            canonical_id = canon_row[0]
        else:
            conn.execute(
                sa.text("INSERT INTO tags (id, name) VALUES (gen_random_uuid(), :n)"),
                {"n": canonical_name},
            )
            canonical_id = conn.execute(
                sa.text("SELECT id FROM tags WHERE name = :n"),
                {"n": canonical_name},
            ).fetchone()[0]

        # Move project_tags from dirty to canonical
        conn.execute(
            sa.text(
                "UPDATE project_tags SET tag_id = :new_id "
                "WHERE tag_id = :old_id "
                "AND project_id NOT IN ("
                "  SELECT project_id FROM project_tags WHERE tag_id = :new_id"
                ")"
            ),
            {"new_id": canonical_id, "old_id": dirty_id},
        )
        # Delete remaining duplicate links
        conn.execute(
            sa.text("DELETE FROM project_tags WHERE tag_id = :tid"),
            {"tid": dirty_id},
        )
        # Delete dirty tag
        conn.execute(
            sa.text("DELETE FROM tags WHERE id = :tid"),
            {"tid": dirty_id},
        )

    # --- Step 3: Delete garbage tags ---
    for garbage_name in GARBAGE_TAGS:
        garbage_row = conn.execute(
            sa.text("SELECT id FROM tags WHERE name = :n"),
            {"n": garbage_name},
        ).fetchone()
        if not garbage_row:
            continue
        garbage_id = garbage_row[0]
        conn.execute(
            sa.text("DELETE FROM project_tags WHERE tag_id = :tid"),
            {"tid": garbage_id},
        )
        conn.execute(
            sa.text("DELETE FROM tags WHERE id = :tid"),
            {"tid": garbage_id},
        )

    # --- Step 4: Delete orphan tags (no project_tags) ---
    conn.execute(
        sa.text(
            "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM project_tags)"
        )
    )

    # --- Step 5: Normalize selected_tags in guest_profiles ---
    # Build full reverse map for profile tag normalization
    all_synonyms = dict(SYNONYM_MAP)
    profiles = conn.execute(
        sa.text("SELECT id, selected_tags FROM guest_profiles WHERE selected_tags IS NOT NULL")
    ).fetchall()

    for profile_id, selected_tags in profiles:
        if not selected_tags:
            continue
        normalized = []
        seen = set()
        for tag in selected_tags:
            canonical = all_synonyms.get(tag, tag)
            if canonical not in seen and canonical not in GARBAGE_TAGS:
                normalized.append(canonical)
                seen.add(canonical)
        if normalized != selected_tags:
            import json
            conn.execute(
                sa.text("UPDATE guest_profiles SET selected_tags = :tags WHERE id = :pid"),
                {"tags": json.dumps(normalized), "pid": profile_id},
            )


def downgrade() -> None:
    # Data migration — no automatic rollback. Tag data before migration is not preserved.
    pass
