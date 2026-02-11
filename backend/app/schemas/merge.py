"""Schemas for smart merge (preview + apply) of imports."""

from pydantic import BaseModel

from app.schemas.expert import RowError


class ChangedField(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None


class UpdatedItem(BaseModel):
    name: str
    db_id: str
    changed_fields: list[ChangedField]


class NewItem(BaseModel):
    name: str
    telegram: str | None = None


class MergePreview(BaseModel):
    new_count: int
    duplicate_count: int
    updated_count: int
    error_count: int
    new_items: list[NewItem] = []
    updated_items: list[UpdatedItem] = []
    errors: list[RowError] = []
    # projects only
    with_tags_in_db: int | None = None
    missing_tags_in_db: int | None = None


class MergeApplyRequest(BaseModel):
    add_new: bool = True
    update_existing: bool = True


class MergeApplyResult(BaseModel):
    added: int
    updated: int
    skipped: int
    errors: int
    error_details: list[RowError] = []
