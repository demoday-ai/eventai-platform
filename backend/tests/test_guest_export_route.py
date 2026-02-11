"""Test that GET /admin/guests/export resolves correctly (not as /guests/{user_id}).

Before the fix, FastAPI matched /guests/export against /guests/{user_id}
and tried to parse 'export' as UUID, causing 422.
"""

from starlette.routing import Match

from app.main import app


def test_export_route_resolves_to_export_endpoint():
    """Verify that /api/v1/admin/guests/export matches the export_guests handler,
    not the get_guest_detail handler with user_id='export'.
    """
    scope = {"type": "http", "method": "GET", "path": "/api/v1/admin/guests/export"}

    matched_route = None
    for route in app.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            matched_route = route
            break

    assert matched_route is not None, "No route matched /api/v1/admin/guests/export"

    # Walk nested routers to find the final endpoint name
    # The endpoint should be export_guests, NOT get_guest_detail
    endpoint_name = _get_endpoint_name(matched_route, scope)
    assert "export" in endpoint_name, (
        f"Expected export_guests endpoint, but matched '{endpoint_name}'. "
        "This means /guests/export is being captured by /guests/{{user_id}}."
    )


def _get_endpoint_name(route, scope) -> str:
    """Recursively resolve the final endpoint name from nested routers."""
    if hasattr(route, "endpoint"):
        return route.endpoint.__name__
    if hasattr(route, "app") and hasattr(route.app, "routes"):
        for sub_route in route.app.routes:
            match, _ = sub_route.matches(scope)
            if match == Match.FULL:
                return _get_endpoint_name(sub_route, scope)
    return str(route)
