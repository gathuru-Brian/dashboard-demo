"""
RMIP-DSS Enterprise Roles -- display metadata only.

The authoritative list of roles and what each role can access lives in
auth/permissions.py (ROLE_PERMISSIONS). This module supplies color and
description metadata for the UI, and always derives its role list from
permissions.py so the two can never drift out of sync.

For permission checks, always import has_permission / get_permissions
from auth.permissions -- not from this module.
"""

from auth.permissions import get_all_roles

# Display metadata for roles that predate the full permission system.
# Roles from auth/permissions.py that aren't listed here fall back to a
# neutral color and a generic description (see get_role_color / 
# get_role_description below) -- add entries here as you want richer
# descriptions for the newer roles (Pricing Manager, Chief Underwriter, etc).
ROLE_METADATA = {

    "Administrator": {
        "color": "#dc2626",
        "description": "Full platform access, including user management and system settings.",
    },

    "Executive": {
        "color": "#2563eb",
        "description": "Senior stakeholder view across dashboard, market intelligence, pricing, and reports.",
    },

    "Research Manager": {
        "color": "#0891b2",
        "description": "Oversees market research and portfolio reporting.",
    },

    "Research Analyst": {
        "color": "#14b8a6",
        "description": "Analyses portfolio performance and market intelligence.",
    },

    "Chief Underwriter": {
        "color": "#f59e0b",
        "description": "Senior oversight of pricing, cedant relationships, and reinsurer terms.",
    },

    "Underwriting Manager": {
        "color": "#f59e0b",
        "description": "Manages the underwriting team's pricing and treaty decisions.",
    },

    "Underwriter": {
        "color": "#fbbf24",
        "description": "Handles cedant relationships and reinsurer terms.",
    },

    "Claims Manager": {
        "color": "#7c3aed",
        "description": "Oversees claims intelligence, aging, and settlement performance.",
    },

    "Claims Officer": {
        "color": "#8b5cf6",
        "description": "Handles day-to-day claims intelligence and reporting.",
    },

    "Finance Manager": {
        "color": "#10b981",
        "description": "Oversees financial reporting workflows.",
    },

    "Finance Officer": {
        "color": "#34d399",
        "description": "Prepares financial reports.",
    },

    "ICT Administrator": {
        "color": "#6366f1",
        "description": "Manages system configuration and user administration.",
    },

    "Guest": {
        "color": "#64748b",
        "description": "Limited read-only access to the main dashboard.",
    },

}

_DEFAULT_COLOR = "#64748b"
_DEFAULT_DESCRIPTION = "No description available."


def get_roles():
    """
    Returns every role in the system, sorted alphabetically. Always sourced
    from auth/permissions.py so this can never fall out of sync with the
    actual permission data.
    """
    return get_all_roles()


def role_exists(role):
    """
    Check if role exists.
    """
    return role in get_roles()


def get_role_description(role):
    """
    Returns the role's description, or a generic fallback for roles that
    don't yet have custom metadata defined.
    """
    if role in ROLE_METADATA:
        return ROLE_METADATA[role].get("description", _DEFAULT_DESCRIPTION)
    if role in get_roles():
        return _DEFAULT_DESCRIPTION
    return "Unknown Role"


def get_role_color(role):
    """
    Returns the role's display color, or a neutral default.
    """
    if role in ROLE_METADATA:
        return ROLE_METADATA[role].get("color", _DEFAULT_COLOR)
    return _DEFAULT_COLOR