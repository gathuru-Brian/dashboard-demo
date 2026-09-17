"""
Dashboard Entry Point
Routes to the main dashboard application
"""

import sys
from pathlib import Path
import streamlit as st

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dashboard.app import build_dashboard
except ImportError:
    from app import build_dashboard

if __name__ == "__main__":
    build_dashboard()