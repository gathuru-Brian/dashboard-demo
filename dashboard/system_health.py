"""
System Health
RMIP-DSS Admin Console
---------------------------------
Operational diagnostics: database size, default dataset stats, environment
info, and basic sanity checks. This lives in the standalone admin app only
-- it's not customer-facing and isn't needed in the main analytics app.
"""

import platform
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "users.db"
DEFAULT_DATA_PATH = ROOT / "data" / "acentria_dashboard_data.csv"
FALLBACK_LOG_PATH = ROOT / "data" / "notification_fallback.log"


def _format_bytes(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _file_status(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


def show_system_health() -> None:
    st.subheader("System health")

    col1, col2, col3 = st.columns(3)
    col1.metric("Python version", platform.python_version())
    col2.metric("Platform", platform.system())
    col3.metric("Server time", datetime.now().strftime("%Y-%m-%d %H:%M"))

    st.divider()
    st.markdown("**Database**")
    db_status = _file_status(DB_PATH)
    if db_status["exists"]:
        col1, col2 = st.columns(2)
        col1.metric("users.db size", _format_bytes(db_status["size"]))
        col2.metric("Last modified", db_status["modified"])
    else:
        st.warning(f"Database file not found at {DB_PATH}. It will be created on first run.")

    st.divider()
    st.markdown("**Default portfolio dataset**")
    data_status = _file_status(DEFAULT_DATA_PATH)
    if data_status["exists"]:
        col1, col2, col3 = st.columns(3)
        col1.metric("File size", _format_bytes(data_status["size"]))
        col2.metric("Last modified", data_status["modified"])
        try:
            df = pd.read_csv(DEFAULT_DATA_PATH, nrows=0)
            col3.metric("Columns", len(df.columns))
            with st.expander("View column names"):
                st.write(list(df.columns))
            row_count = sum(1 for _ in open(DEFAULT_DATA_PATH, encoding="utf-8")) - 1
            st.caption(f"Approximately {row_count:,} data rows in the default dataset.")
        except Exception as error:
            st.error(f"Could not read the default dataset: {error}")
    else:
        st.error(
            f"Default dataset not found at {DEFAULT_DATA_PATH}. "
            "The main app will fail to load until this file exists."
        )

    st.divider()
    st.markdown("**Email notification fallback log**")
    st.caption(
        "When SMTP isn't configured (or a send fails), notifications are written here "
        "instead of being emailed."
    )
    if FALLBACK_LOG_PATH.exists():
        size = FALLBACK_LOG_PATH.stat().st_size
        st.metric("Fallback log size", _format_bytes(size))
        if size > 0:
            with st.expander("View recent fallback log entries"):
                with open(FALLBACK_LOG_PATH, encoding="utf-8") as f:
                    lines = f.readlines()
                st.code("".join(lines[-50:]), language=None)
    else:
        st.caption("No fallback log yet -- either SMTP is configured and working, or no emails have been sent.")

    st.divider()
    st.markdown("**Installed package versions**")
    packages_to_check = ["streamlit", "pandas", "numpy", "plotly", "bcrypt", "requests"]
    rows = []
    for pkg in packages_to_check:
        try:
            module = sys.modules.get(pkg) or __import__(pkg)
            version = getattr(module, "__version__", "unknown")
        except Exception:
            version = "not installed"
        rows.append({"Package": pkg, "Version": version})
    st.dataframe(rows, hide_index=True, width='stretch')