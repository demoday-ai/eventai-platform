"""Conversation states for bot handlers."""

# Conversation states (6 total)
(
    CHOOSE_ROLE,  # 0 - Role selection (4 buttons: student/applicant/business/other)
    ONBOARD_NL_PROFILE,  # 1 - NL profiling (free text → LLM agent)
    ONBOARD_CONFIRM,  # 2 - Profile confirmation + "show profile" button
    VIEW_PROGRAM,  # 3 - Program + agent mode
    VIEW_DETAIL,  # 4 - Project detail
    NL_REBUILD,  # 5 - Profile rebuild → ONBOARD_CONFIRM
) = range(6)
