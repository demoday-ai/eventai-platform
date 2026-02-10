"""Admin service — facade that delegates to dashboard, tag, and guest_admin services.

Kept for backward-compatibility of imports like `from app.services.admin import admin_service`.
"""

from app.services.admin.dashboard_service import (  # noqa: F401
    get_coverage_stats,
    get_dashboard_stats,
    get_pipeline_status,
    get_projects_list,
    get_room_detail,
    update_room_theme,
)
from app.services.admin.guest_admin_service import (  # noqa: F401
    get_guest_detail,
    list_guests,
)
from app.services.admin.tag_service import (  # noqa: F401
    add_tags,
    delete_tag,
    list_tags,
    replace_tags,
    seed_default_tags,
    suggest_tags,
)
