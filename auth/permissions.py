"""
RMIP-DSS Enterprise Permissions
"""

ROLE_PERMISSIONS = {

    "Administrator": [
        "dashboard",
        "market_intelligence",
        "pricing",
        "cedants",
        "reinsurers",
        "claims",
        "reports",
        "upload",
        "system",
        "users"
    ],

    "Executive": [
        "dashboard",
        "market_intelligence",
        "pricing",
        "reports"
    ],

    "Research Manager": [
        "dashboard",
        "market_intelligence",
        "reports"
    ],

    "Research Analyst": [
        "market_intelligence",
        "reports"
    ],

    "Pricing Manager": [
        "pricing",
        "reports"
    ],

    "Pricing Analyst": [
        "pricing"
    ],

    "Chief Underwriter": [
        "dashboard",
        "pricing",
        "cedants",
        "reinsurers"
    ],

    "Underwriting Manager": [
        "pricing",
        "cedants",
        "reinsurers"
    ],

    "Underwriter": [
        "cedants",
        "reinsurers"
    ],

    "Claims Manager": [
        "claims",
        "reports"
    ],

    "Claims Officer": [
        "claims",
        "reports"
    ],

    "Finance Manager": [
        "reports"
    ],

    "Finance Officer": [
        "reports"
    ],

    "Business Development Manager": [
        "market_intelligence",
        "reports"
    ],

    "Business Development Officer": [
        "market_intelligence"
    ],

    "ICT Administrator": [
        "system",
        "users"
    ],

    "Data Scientist": [
        "dashboard",
        "market_intelligence",
        "pricing"
    ],

    "Risk Analyst": [
        "dashboard",
        "reports"
    ],

    "Compliance Officer": [
        "reports"
    ],

    "Guest": [
        "dashboard"
    ],

    # Roles exposed by the registration form in earlier releases.
    "Finance": ["reports"],
    "IT Support": ["system"],
    "Intern": ["dashboard"],
    "Admin": [
        "dashboard", "market_intelligence", "pricing", "cedants",
        "reinsurers", "claims", "reports", "upload", "system", "users",
    ],
    "Analyst": ["market_intelligence", "reports"],

}


def has_permission(role, permission):

    permissions = ROLE_PERMISSIONS.get(role, [])

    return permission in permissions


def get_permissions(role):

    return ROLE_PERMISSIONS.get(role, [])


def get_all_roles():
    """
    Returns every role defined in the permission system, sorted alphabetically.
    This is the authoritative role list -- auth/roles.py's get_roles() should
    stay in sync with this rather than maintaining a separate, shorter list.
    """
    return sorted(ROLE_PERMISSIONS.keys())