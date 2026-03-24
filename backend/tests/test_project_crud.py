"""Tests for project CRUD: create project and update author/title."""

import pytest
from pydantic import ValidationError


class TestProjectUpdateSchema:
    """ProjectUpdateRequest should accept author and telegram_contact."""

    def test_update_accepts_author(self):
        from app.schemas.admin import ProjectUpdateRequest

        req = ProjectUpdateRequest(author="Иванов Иван")
        assert req.author == "Иванов Иван"

    def test_update_accepts_telegram_contact(self):
        from app.schemas.admin import ProjectUpdateRequest

        req = ProjectUpdateRequest(telegram_contact="@ivanov")
        assert req.telegram_contact == "@ivanov"

    def test_update_all_fields(self):
        from app.schemas.admin import ProjectUpdateRequest

        req = ProjectUpdateRequest(
            title="New Title",
            description="New desc",
            author="Петров",
            telegram_contact="@petrov",
            tags=["NLP"],
        )
        assert req.title == "New Title"
        assert req.author == "Петров"

    def test_update_empty_is_valid(self):
        from app.schemas.admin import ProjectUpdateRequest

        req = ProjectUpdateRequest()
        assert req.title is None
        assert req.author is None
        assert req.telegram_contact is None


class TestProjectCreateSchema:
    """ProjectCreateRequest for adding new projects from admin."""

    def test_create_requires_title(self):
        from app.schemas.admin import ProjectCreateRequest

        with pytest.raises(ValidationError):
            ProjectCreateRequest()

    def test_create_rejects_empty_title(self):
        from app.schemas.admin import ProjectCreateRequest

        with pytest.raises(ValidationError):
            ProjectCreateRequest(title="")

    def test_create_with_all_fields(self):
        from app.schemas.admin import ProjectCreateRequest

        req = ProjectCreateRequest(
            title="My Project",
            description="About ML",
            author="Сидоров",
            telegram_contact="@sidorov",
        )
        assert req.title == "My Project"
        assert req.author == "Сидоров"
