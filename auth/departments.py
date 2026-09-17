"""
RMIP-DSS Enterprise Departments
Acentria Group
"""
from auth.permissions import has_permission

DEPARTMENTS = {

    "Executive Office": {
        "head": "Chief Executive Officer",
        "description": "Executive leadership and strategy.",
        "code": "EXEC"
    },

    "Research & Development": {
        "head": "Research Manager",
        "description": "Market research, analytics and innovation.",
        "code": "R&D"
    },

    "Actuarial": {
        "head": "Chief Actuary",
        "description": "Pricing models and reserving.",
        "code": "ACT"
    },

    "Treaty Reinsurance": {
        "head": "Treaty Manager",
        "description": "Treaty portfolio management.",
        "code": "TREATY"
    },

    "Facultative Reinsurance": {
        "head": "Facultative Manager",
        "description": "Facultative underwriting.",
        "code": "FAC"
    },

    "Pricing": {
        "head": "Pricing Manager",
        "description": "Rate analysis and pricing.",
        "code": "PRICE"
    },

    "Claims": {
        "head": "Claims Manager",
        "description": "Claims management.",
        "code": "CLAIMS"
    },

    "Finance": {
        "head": "Finance Manager",
        "description": "Financial reporting.",
        "code": "FIN"
    },

    "ICT": {
        "head": "ICT Manager",
        "description": "System administration.",
        "code": "ICT"
    },

    "Human Resource": {
        "head": "HR Manager",
        "description": "Human capital management.",
        "code": "HR"
    },

    "Marketing": {
        "head": "Marketing Manager",
        "description": "Business development.",
        "code": "MKT"
    }

}


def get_departments():
    """
    Returns departments sorted alphabetically.
    """
    return sorted(DEPARTMENTS.keys())


def department_exists(department):
    """
    Checks whether a department exists.
    """
    return department in DEPARTMENTS


def get_department_code(department):
    """
    Returns department code. Never raises -- falls back gracefully for
    unknown departments or departments missing a code.
    """
    if department in DEPARTMENTS:
        return DEPARTMENTS[department].get("code", "UNKNOWN")
    return "UNKNOWN"


def get_department_head(department):
    """
    Returns the department head's title, or 'Unknown' if not found.
    """
    if department in DEPARTMENTS:
        return DEPARTMENTS[department].get("head", "Unknown")
    return "Unknown"


def get_department_description(department):
    """
    Returns the department description, or a fallback message if not found.
    """
    if department in DEPARTMENTS:
        return DEPARTMENTS[department].get("description", "No description available.")
    return "Unknown department."