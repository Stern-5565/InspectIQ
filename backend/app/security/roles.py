"""
Centralized role-name constants. Route/service code must compare against these, never
against raw role-name string literals scattered through the codebase (PROJECT_PLAN.md §7) -
one place to change if a role is ever renamed.
"""

ADMINISTRATOR = "Administrator"
MANAGER = "Manager"
INSPECTOR = "Inspector"
MAINTENANCE = "Maintenance"
VIEWER = "Viewer"

ALL_ROLES = [ADMINISTRATOR, MANAGER, INSPECTOR, MAINTENANCE, VIEWER]
