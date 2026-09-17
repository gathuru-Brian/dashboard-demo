"""
Admin Console
RMIP-DSS
---------------------------------
Super-admin workspace for:
  - System overview: live metrics on users, roles, logins, and lockouts
  - Creating new users (replaces public self-registration)
  - Managing existing users (role, department, status, deletion)
  - Reviewing the audit/activity log
"""

from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from auth.authentication import (
    create_user,
    delete_user,
    get_activity_log,
    get_all_users,
    notify_user_registration,
    update_user,
    user_exists,
    validate_password_strength,
)
from auth.data_store import (
    delete_upload,
    delete_uploads_older_than,
    get_upload_dataframe,
    list_uploads,
    total_upload_storage_bytes,
)
from auth.departments import get_departments
from auth.permissions import get_permissions
from auth.roles import get_role_color, get_role_description, get_roles


def _system_overview_section() -> None:
    st.subheader("System overview")
    users = get_all_users()
    activity = get_activity_log(limit=2000)

    total = len(users)
    active = sum(1 for u in users if u["status"] == "Active")
    suspended = sum(1 for u in users if u["status"] == "Suspended")
    superusers = sum(1 for u in users if u["is_superuser"])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total users", f"{total:,}")
    col2.metric("Active", f"{active:,}")
    col3.metric("Suspended", f"{suspended:,}")
    col4.metric("Superusers", f"{superusers:,}")
    recent_failed = sum(
        1 for e in activity
        if e["action"] in ("login_failed", "login_blocked", "account_locked")
        and _within_hours(e["created_at"], 24)
    )
    col5.metric("Failed logins (24h)", f"{recent_failed:,}")

    st.divider()

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("**Users by role**")
        role_counts = Counter(u["role"] for u in users)
        role_df = pd.DataFrame(
            [{"Role": role, "Users": count} for role, count in role_counts.items()]
        ).sort_values("Users", ascending=False)
        if not role_df.empty:
            fig = px.bar(
                role_df, x="Users", y="Role", orientation="h",
                color="Role", color_discrete_map={
                    role: get_role_color(role) for role in role_df["Role"]
                },
            )
            fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No users yet.")

    with right:
        st.markdown("**Login activity (last 14 days)**")
        daily = _daily_login_counts(activity, days=14)
        if daily.empty:
            st.info("No login activity recorded yet.")
        else:
            fig2 = px.bar(
                daily, x="Date", y="Count", color="Event",
                barmode="group",
                color_discrete_map={"Success": "#22c55e", "Failed": "#ef4444"},
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.markdown("**Currently locked-out accounts**")
    locked_rows = [
        {
            "Name": u["fullname"],
            "Email": u["email"],
            "Role": u["role"],
        }
        for u in users
        if _is_locked_now(u)
    ]
    if locked_rows:
        st.dataframe(locked_rows, hide_index=True, width="stretch")
    else:
        st.caption("No accounts are currently locked out.")


def _is_locked_now(user) -> bool:
    locked_until_raw = user["locked_until"] if "locked_until" in user.keys() else None
    if not locked_until_raw:
        return False
    try:
        locked_until = datetime.strptime(locked_until_raw, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return False
    return datetime.now() < locked_until


def _within_hours(timestamp_str: str, hours: int) -> bool:
    try:
        ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return False
    return datetime.now() - ts <= timedelta(hours=hours)


def _daily_login_counts(activity, days: int) -> pd.DataFrame:
    cutoff = datetime.now() - timedelta(days=days)
    rows = []
    for entry in activity:
        try:
            ts = datetime.strptime(entry["created_at"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
        if ts < cutoff:
            continue
        if entry["action"] == "login_success":
            rows.append({"Date": ts.date().isoformat(), "Event": "Success"})
        elif entry["action"] in ("login_failed", "login_blocked", "account_locked"):
            rows.append({"Date": ts.date().isoformat(), "Event": "Failed"})
    if not rows:
        return pd.DataFrame(columns=["Date", "Event", "Count"])
    df = pd.DataFrame(rows)
    return df.groupby(["Date", "Event"], as_index=False).size().rename(columns={"size": "Count"})


def _create_user_section() -> None:
    st.subheader("Create a new user")
    st.caption(
        "Self-registration is disabled. New accounts are created here by the "
        "administrator, who sets the person's initial role and department."
    )
    with st.form("admin_create_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fullname = st.text_input("Full name")
            email = st.text_input("Work email", placeholder="name@company.com")
            department = st.selectbox("Department", get_departments())
        with col2:
            role = st.selectbox("Role", get_roles())
            password = st.text_input(
                "Temporary password", type="password",
                help="At least 10 characters, with uppercase, lowercase, a digit, and a special character.",
            )
            confirm = st.text_input("Confirm password", type="password")
        st.caption(f"**{role}** grants: {', '.join(get_permissions(role)) or 'no permissions'}")
        st.caption(get_role_description(role))
        send_notification = st.checkbox("Email the user their account details", value=True)
        submitted = st.form_submit_button("Create user", type="primary", icon=":material/person_add:")

    if submitted:
        password_ok, password_message = validate_password_strength(password)
        if not fullname.strip() or not email.strip():
            st.error("Enter a full name and a valid email.")
        elif not password_ok:
            st.error(password_message)
        elif password != confirm:
            st.error("The passwords do not match.")
        elif user_exists(email.strip().lower()):
            st.error("An account already exists for this email address.")
        else:
            created = create_user(fullname.strip(), email.strip().lower(), password, role, department)
            if not created:
                st.error("Could not create the account. It may already exist.")
            else:
                st.success(f"Account created for {fullname.strip()} ({email.strip().lower()}) as {role}.")
                if send_notification:
                    notify_user_registration(email.strip().lower(), fullname.strip())


def _manage_users_section() -> None:
    st.subheader("Manage users")
    users = get_all_users()
    if not users:
        st.info("No users found.")
        return

    for user in users:
        is_super = bool(user["is_superuser"])
        with st.container(border=True):
            header_cols = st.columns([3, 1])
            label = f"**{user['fullname']}**"
            if is_super:
                label += "  🛡️ *Superuser — protected*"
            header_cols[0].markdown(label)
            header_cols[0].caption(user["email"])

            cols = st.columns([2, 1.4, 1.2, 1, 1])
            new_role = cols[0].selectbox(
                "Role", get_roles(),
                index=get_roles().index(user["role"]) if user["role"] in get_roles() else 0,
                key=f"role_{user['id']}",
                disabled=is_super,
            )
            new_department = cols[1].selectbox(
                "Department", get_departments(),
                index=get_departments().index(user["department"]) if user["department"] in get_departments() else 0,
                key=f"dept_{user['id']}",
            )
            new_status = cols[2].selectbox(
                "Status", ["Active", "Suspended", "Pending"],
                index=["Active", "Suspended", "Pending"].index(user["status"]) if user["status"] in ["Active", "Suspended", "Pending"] else 0,
                key=f"status_{user['id']}",
                disabled=is_super,
            )
            if cols[3].button("Save", key=f"save_{user['id']}", icon=":material/save:"):
                update_user(user["id"], user["fullname"], new_role, new_department, new_status)
                st.success(f"Updated {user['fullname']}.")
                st.rerun()

            delete_disabled = is_super
            if cols[4].button("Delete", key=f"delete_{user['id']}", icon=":material/delete:", disabled=delete_disabled):
                st.session_state[f"confirm_delete_{user['id']}"] = True

            if st.session_state.get(f"confirm_delete_{user['id']}"):
                st.warning(f"Delete {user['fullname']} ({user['email']})? This cannot be undone.")
                confirm_cols = st.columns(2)
                if confirm_cols[0].button("Confirm delete", key=f"confirm_yes_{user['id']}", type="primary"):
                    deleted = delete_user(user["id"])
                    del st.session_state[f"confirm_delete_{user['id']}"]
                    if deleted:
                        st.success(f"Deleted {user['fullname']}.")
                    else:
                        st.error("This account is protected and cannot be deleted.")
                    st.rerun()
                if confirm_cols[1].button("Cancel", key=f"confirm_no_{user['id']}"):
                    del st.session_state[f"confirm_delete_{user['id']}"]
                    st.rerun()

            st.caption(f"Created: {user['created_at'] or '—'} • Last login: {user['last_login'] or 'Never'}")


def _activity_log_section() -> None:
    st.subheader("Activity log")
    st.caption("Recent logins, lockouts, and account changes across the platform.")
    limit = st.slider("Entries to show", min_value=25, max_value=500, value=100, step=25)
    entries = get_activity_log(limit=limit)
    if not entries:
        st.info("No activity recorded yet.")
        return

    action_labels = {
        "login_success": "✅ Login succeeded",
        "login_failed": "❌ Login failed",
        "login_blocked": "🔒 Login blocked (locked)",
        "account_locked": "🔒 Account locked",
        "user_created": "➕ User created",
        "user_updated": "✏️ User updated",
        "user_deleted": "🗑️ User deleted",
        "password_changed": "🔑 Password changed",
        "superuser_protected_update": "🛡️ Superuser update blocked",
        "superuser_delete_blocked": "🛡️ Superuser delete blocked",
    }

    rows = [
        {
            "When": entry["created_at"],
            "Event": action_labels.get(entry["action"], entry["action"]),
            "Email": entry["email"] or "—",
            "Details": entry["details"] or "",
        }
        for entry in entries
    ]
    st.dataframe(rows, hide_index=True, width="stretch")


def _format_bytes(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _data_uploads_section() -> None:
    st.subheader("Data uploads")
    st.caption(
        "Every dataset loaded through 'Upload portfolio data' -- portfolio files, "
        "internal claims, remote URLs, and Kaggle downloads -- is persisted here, "
        "across all users, so it can be reviewed centrally."
    )

    uploads = list_uploads(limit=500)
    total_bytes = total_upload_storage_bytes()
    col1, col2 = st.columns(2)
    col1.metric("Total uploads on record", f"{len(uploads):,}")
    col2.metric("Total storage used", _format_bytes(total_bytes))

    with st.expander("Data retention"):
        st.caption(
            "Uploads older than the threshold below can be permanently removed "
            "to control storage growth and align with your data retention policy."
        )
        retention_days = st.number_input(
            "Delete uploads older than (days)", min_value=1, max_value=3650, value=90
        )
        if st.button("Run cleanup now", icon=":material/auto_delete:"):
            removed = delete_uploads_older_than(int(retention_days))
            st.success(f"Removed {removed} upload(s) older than {retention_days} days.")
            st.rerun()

    if not uploads:
        st.info("No uploads have been recorded yet.")
        return

    source_labels = {
        "portfolio_file": "📁 Portfolio file",
        "internal_claims": "🗂️ Internal claims",
        "remote_url": "🌐 Remote URL",
        "kaggle": "📊 Kaggle dataset",
    }

    rows = [
        {
            "id": u["id"],
            "When": u["uploaded_at"],
            "Uploaded by": f"{u['uploader_name']} ({u['uploader_email']})" if u["uploader_email"] else "Unknown",
            "Source": source_labels.get(u["source"], u["source"]),
            "File": u["original_filename"] or "—",
            "Rows": u["row_count"],
            "Columns": u["column_count"],
        }
        for u in uploads
    ]
    st.dataframe(
        [{k: v for k, v in r.items() if k != "id"} for r in rows],
        hide_index=True, use_container_width=True,
    )

    st.markdown("**Inspect or remove a specific upload**")
    options = {f"{r['When']} — {r['Uploaded by']} — {r['File'] or r['Source']}": r["id"] for r in rows}
    if options:
        selected_label = st.selectbox("Select an upload", list(options.keys()))
        selected_id = options[selected_label]

        preview_col, delete_col = st.columns([3, 1])
        with preview_col:
            if st.button("Preview data", icon=":material/visibility:", key=f"preview_{selected_id}"):
                df = get_upload_dataframe(selected_id)
                if df is None:
                    st.error("This upload's data file could not be found on disk.")
                else:
                    st.dataframe(df.head(100), hide_index=True, use_container_width=True)
                    st.download_button(
                        "Download full dataset",
                        df.to_csv(index=False),
                        f"upload_{selected_id}.csv",
                        "text/csv",
                        key=f"download_{selected_id}",
                    )
        with delete_col:
            if st.button("Delete", icon=":material/delete:", key=f"delete_upload_{selected_id}"):
                if delete_upload(selected_id):
                    st.success("Upload deleted.")
                    st.rerun()
                else:
                    st.error("Could not delete this upload.")


def admin_page() -> None:
    st.title("Admin console")
    st.caption("System monitoring, user management, and platform activity.")

    tab_overview, tab_create, tab_manage, tab_uploads, tab_activity = st.tabs(
        ["System overview", "Create user", "Manage users", "Data uploads", "Activity log"]
    )
    with tab_overview:
        _system_overview_section()
    with tab_create:
        _create_user_section()
    with tab_manage:
        _manage_users_section()
    with tab_uploads:
        _data_uploads_section()
    with tab_activity:
        _activity_log_section()s