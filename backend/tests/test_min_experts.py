"""Tests for configurable minimum experts per room."""

import pytest


class TestMinExpertsModel:
    """Test that Event model has min_experts_per_room field."""

    def test_event_has_min_experts_field(self):
        from app.models.event import Event

        event = Event(
            name="Test DD",
            start_date="2026-02-22",
            end_date="2026-02-23",
            min_experts_per_room=3,
        )
        assert event.min_experts_per_room == 3

    def test_event_min_experts_column_exists(self):
        """Event model should have min_experts_per_room column with server_default=2."""
        from app.models.event import Event

        col = Event.__table__.columns["min_experts_per_room"]
        assert col is not None
        assert str(col.server_default.arg) == "2"


class TestCoverageWithMinExperts:
    """Test that coverage_level uses min_experts_per_room."""

    def test_covered_when_meets_minimum(self):
        from app.services.admin.coverage_service import _compute_coverage_level

        assert _compute_coverage_level(confirmed=3, min_required=3) == "covered"

    def test_partial_when_below_minimum(self):
        from app.services.admin.coverage_service import _compute_coverage_level

        assert _compute_coverage_level(confirmed=1, min_required=3) == "partial"

    def test_uncovered_when_zero(self):
        from app.services.admin.coverage_service import _compute_coverage_level

        assert _compute_coverage_level(confirmed=0, min_required=2) == "uncovered"

    def test_partial_when_one_below(self):
        from app.services.admin.coverage_service import _compute_coverage_level

        assert _compute_coverage_level(confirmed=2, min_required=3) == "partial"
