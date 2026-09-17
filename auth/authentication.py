"""
Authentication Module
RMIP-DSS
---------------------------------
Handles:

✓ SQLite Connection
✓ Password Hashing
✓ Admin Initialization
✓ User Registration
✓ User Login (with brute-force lockout protection)
✓ User Management
"""

import sqlite3
import bcrypt
import smtplib
import ssl
import secrets
from email.message import EmailMessage
from typing import Any
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from pathlib import Path
from datetime import datetime, timedelta

# ==========================================
# DATABASE
# ==========================================

ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "database" / "users.db"

# Preserve access for accounts created by earlier versions of RMIP-DSS.
ROLE_ALIASES = {
    "Admin": "Administrator",
    "Analyst": "Research Analyst",
    "Finance": "Finance Manager",
    "IT Support": "ICT Administrator",
    "Intern": "Guest",
}

# Brute-force protection settings
MAX_FAILED_ATTEMPTS = 20
LOCKOUT_MINUTES = 15


def get_connection():
    """
    Returns SQLite connection.
    """

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)

    conn.row_factory = sqlite3.Row

    return conn


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def initialize_database():
    """
    Creates users table if it does not exist, and migrates older databases
    that predate the failed_attempts / locked_until columns.
    """

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            fullname TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT NOT NULL,

            department TEXT,

            status TEXT DEFAULT 'Active',

            created_at TEXT,

            last_login TEXT,

            failed_attempts INTEGER DEFAULT 0,

            locked_until TEXT,

            is_superuser INTEGER DEFAULT 0

        )
        """
    )

    conn.commit()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()

    # Migrate existing databases created before lockout / superuser columns existed.
    existing_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(users)")}
    if "failed_attempts" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
    if "locked_until" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
    if "is_superuser" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_superuser INTEGER DEFAULT 0")
    conn.commit()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_log(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            email TEXT,

            action TEXT NOT NULL,

            details TEXT,

            created_at TEXT NOT NULL

        )
        """
    )
    conn.commit()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS access_requests(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            fullname TEXT NOT NULL,

            email TEXT NOT NULL,

            department TEXT,

            message TEXT,

            status TEXT NOT NULL DEFAULT 'pending',

            created_at TEXT NOT NULL,

            reviewed_at TEXT,

            reviewed_by TEXT

        )
        """
    )
    conn.commit()

    conn.close()


# ==========================================
# ACTIVITY / AUDIT LOG
# ==========================================

def log_activity(user_id, email, action: str, details: str = "") -> None:
    """
    Records an auditable event: logins (success/failure), account creation,
    role or status changes, deletions, password changes, access requests,
    etc. Safe to call even if initialize_database() hasn't run yet in this
    process.
    """
    initialize_database()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO activity_log(user_id, email, action, details, created_at)
        VALUES(?,?,?,?,?)
        """,
        (
            user_id,
            email,
            action,
            details,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def get_activity_log(limit: int = 200):
    """
    Returns the most recent audit log entries, newest first, for the admin
    console's monitoring view.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, email, action, details, created_at
        FROM activity_log
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_admin_email() -> str:
    """
    Returns the configured admin email. Raises if it is not set, rather than
    silently falling back to a hardcoded address.
    """
    try:
        admin_settings = st.secrets.get("admin", {})
    except StreamlitSecretNotFoundError:
        admin_settings = {}
    email = admin_settings.get("email")
    if not email:
        raise RuntimeError(
            "admin.email is not configured in Streamlit secrets. "
            "Set [admin] email = \"...\" in .streamlit/secrets.toml before running in production."
        )
    return str(email).strip().lower()


def get_smtp_settings() -> dict[str, Any] | None:
    try:
        smtp_settings = st.secrets.get("smtp", {})
    except StreamlitSecretNotFoundError:
        smtp_settings = {}
    if not smtp_settings:
        return None
    result: dict[str, Any] = {
        "host": smtp_settings.get("host"),
        "port": int(smtp_settings.get("port", 465)),
        "username": smtp_settings.get("username"),
        "password": smtp_settings.get("password"),
        "sender": smtp_settings.get("sender", smtp_settings.get("username")),
        "use_ssl": bool(smtp_settings.get("use_ssl", True)),
    }
    return result


def send_email(subject: str, body: str, recipients: list[str], allow_fallback: bool = True) -> bool:
    settings = get_smtp_settings()
    if settings is None or not settings.get("host") or not settings.get("username") or not settings.get("password"):
        if allow_fallback:
            log_path = ROOT / "data" / "notification_fallback.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"{datetime.now().isoformat()} | To: {recipients} | Subject: {subject}\n{body}\n\n")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["sender"]
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    try:
        if settings["use_ssl"]:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings["host"], settings["port"], context=context) as smtp:
                smtp.login(settings["username"], settings["password"])
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings["host"], settings["port"]) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(settings["username"], settings["password"])
                smtp.send_message(message)
        return True
    except Exception as error:
        if allow_fallback:
            log_path = ROOT / "data" / "notification_fallback.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"{datetime.now().isoformat()} | Email send failed: {error} | To: {recipients} | Subject: {subject}\n{body}\n\n")
        return False


def notify_admin_login(user: dict) -> None:
    try:
        admin_email = get_admin_email()
    except RuntimeError:
        # Admin email not configured — skip notification rather than crash login.
        return
    subject = f"RMIP-DSS login notification: {user['fullname']}"
    body = (
        f"User {user['fullname']} ({user['email']}) logged in as {user['role']} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
    send_email(subject, body, [admin_email])


def notify_user_registration(email: str, fullname: str) -> None:
    subject = "Your RMIP-DSS account has been created"
    body = (
        f"Hello {fullname},\n\n"
        "Your RMIP-DSS account has been successfully created. You can now log in using your email and password.\n\n"
        "If you did not create this account, please contact your system administrator immediately.\n\n"
        "Thank you,\nAcentria Reinsurance & Claims Intelligence Navigator"
    )
    send_email(subject, body, [email])


def request_access(fullname: str, email: str, department: str, message: str = "") -> bool:
    """
    Sends an access request to the administrator and records it in the
    access_requests table so it can be reviewed and actioned from the
    admin console's Notifications tab. Does NOT create an account --
    self-registration remains disabled. An administrator must approve the
    request and create the account manually (or via the Notifications
    tab's quick-approve flow) if they choose to.

    Returns True if the notification was sent (or logged to the fallback
    log if SMTP isn't configured); the request is always recorded either
    way.
    """
    initialize_database()

    try:
        admin_email = get_admin_email()
    except RuntimeError:
        admin_email = None

    subject = f"RMIP-DSS access request: {fullname}"
    body = (
        f"{fullname} ({email}) has requested access to RMIP-DSS.\n\n"
        f"Department: {department or 'Not specified'}\n"
        f"Message: {message or 'None provided'}\n\n"
        "Review this request and, if approved, create the account from the admin console."
    )

    sent = False
    if admin_email:
        sent = send_email(subject, body, [admin_email])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO access_requests(fullname, email, department, message, status, created_at)
        VALUES (?,?,?,?,'pending',?)
        """,
        (fullname, email, department, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()

    log_activity(
        None, email, "access_requested",
        f"fullname={fullname}; department={department}; notified_admin={sent}",
    )
    return sent


def get_access_requests(status: str | None = "pending", limit: int = 200):
    """
    Returns access requests, newest first. Pass status=None for every
    request regardless of status, or "pending"/"approved"/"rejected" to
    filter.
    """
    initialize_database()
    conn = get_connection()
    cursor = conn.cursor()
    if status is None:
        cursor.execute(
            "SELECT * FROM access_requests ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    else:
        cursor.execute(
            "SELECT * FROM access_requests WHERE status=? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        )
    rows = cursor.fetchall()
    conn.close()
    return rows


def count_pending_requests() -> int:
    initialize_database()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM access_requests WHERE status='pending'")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def update_access_request_status(request_id: int, status: str, reviewed_by: str = "") -> None:
    """
    Marks a request as approved/rejected/pending. Also logs the action for
    the audit trail.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE access_requests SET status=?, reviewed_at=?, reviewed_by=? WHERE id=?",
        (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reviewed_by, request_id),
    )
    conn.commit()

    cursor.execute("SELECT email, fullname FROM access_requests WHERE id=?", (request_id,))
    row = cursor.fetchone()
    conn.close()

    if row is not None:
        log_activity(
            None, row["email"], "access_request_reviewed",
            f"fullname={row['fullname']}; status={status}; reviewed_by={reviewed_by}",
        )


# ==========================================
# PASSWORD FUNCTIONS
# ==========================================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    """

    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password.
    """

    return bcrypt.checkpw(
        password.encode(),
        hashed.encode()
    )


# ==========================================
# PASSWORD STRENGTH POLICY
# ==========================================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforces a minimum enterprise password policy:
      - at least 10 characters
      - at least one uppercase letter
      - at least one lowercase letter
      - at least one digit
      - at least one special character

    Returns (is_valid, message). message explains the first failed rule,
    or is empty if the password passes.
    """
    import re as _re

    if len(password) < 10:
        return False, "Password must be at least 10 characters long."
    if not _re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter."
    if not _re.search(r"[a-z]", password):
        return False, "Password must include at least one lowercase letter."
    if not _re.search(r"[0-9]", password):
        return False, "Password must include at least one digit."
    if not _re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must include at least one special character."
    return True, ""


# ==========================================
# PASSWORD RESET
# ==========================================

RESET_CODE_TTL_MINUTES = 15


def request_password_reset(email: str) -> bool:
    """Email a short-lived reset code without revealing whether an account exists."""
    initialize_database()
    normalized_email = email.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, fullname, email, status FROM users WHERE email=?", (normalized_email,)
    )
    user = cursor.fetchone()
    if user is None or user["status"] not in {"Active", "Approved"}:
        conn.close()
        log_activity(None, normalized_email, "password_reset_requested", "no eligible account")
        return False

    # Only one valid code may exist per account at a time.
    cursor.execute("UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL", (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"]
    ))
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now() + timedelta(minutes=RESET_CODE_TTL_MINUTES)
    cursor.execute(
        """INSERT INTO password_reset_tokens(user_id, token_hash, expires_at, created_at)
           VALUES(?,?,?,?)""",
        (user["id"], hash_password(code), expires_at.strftime("%Y-%m-%d %H:%M:%S"),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()

    delivered = send_email(
        "Your RMIP-DSS password reset code",
        f"Hello {user['fullname']},\n\nYour password reset code is: {code}\n\n"
        f"This code expires in {RESET_CODE_TTL_MINUTES} minutes. If you did not request it, you can ignore this email.\n\n"
        "RMIP-DSS Security",
        [user["email"]],
        allow_fallback=False,
    )
    log_activity(user["id"], normalized_email, "password_reset_requested", f"email_delivered={delivered}")
    return delivered


def reset_password_with_code(email: str, code: str, new_password: str) -> tuple[bool, str]:
    """Validate a one-time reset code, set a strong password, and clear lockouts."""
    valid, message = validate_password_strength(new_password)
    if not valid:
        return False, message

    initialize_database()
    normalized_email = email.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email FROM users WHERE email=?", (normalized_email,))
    user = cursor.fetchone()
    if user is None:
        conn.close()
        return False, "The code is invalid or has expired."

    cursor.execute(
        """SELECT id, token_hash FROM password_reset_tokens
           WHERE user_id=? AND used_at IS NULL AND expires_at >= ?
           ORDER BY id DESC LIMIT 1""",
        (user["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    token = cursor.fetchone()
    if token is None or not verify_password(code.strip(), token["token_hash"]):
        conn.close()
        log_activity(user["id"], normalized_email, "password_reset_failed", "invalid or expired code")
        return False, "The code is invalid or has expired."

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE users SET password=?, failed_attempts=0, locked_until=NULL WHERE id=?",
        (hash_password(new_password), user["id"]),
    )
    cursor.execute("UPDATE password_reset_tokens SET used_at=? WHERE id=?", (now, token["id"]))
    conn.commit()
    conn.close()
    log_activity(user["id"], normalized_email, "password_reset_completed")
    return True, "Your password has been reset. You can now sign in."


# ==========================================
# ADMIN INITIALIZATION
# ==========================================

def initialize_admin():
    """
    Creates the initial administrator. Requires [admin] email and password
    to be supplied through Streamlit secrets — no default/fallback
    credentials are used. Deployments without secrets configured will fail
    loudly here rather than silently creating a guessable admin account.
    """

    initialize_database()

    try:
        admin_settings = st.secrets.get("admin", {})
    except StreamlitSecretNotFoundError:
        admin_settings = {}

    admin_email = get_admin_email()
    admin_password = admin_settings.get("password")
    if not admin_password:
        raise RuntimeError(
            "admin.password is not configured in Streamlit secrets. "
            "Set [admin] password = \"...\" in .streamlit/secrets.toml before running in production."
        )
    admin_fullname = admin_settings.get("fullname", "System Administrator")

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email=?
        """,
        (admin_email,)
    )

    admin = cursor.fetchone()

    if admin is None:

        cursor.execute(
            """
            INSERT INTO users(

                fullname,

                email,

                password,

                role,

                department,

                status,

                created_at,

                is_superuser

            )

            VALUES(?,?,?,?,?,?,?,1)
            """,
            (
                admin_fullname,

                admin_email,

                hash_password(str(admin_password)),

                "Administrator",

                "Administration",

                "Active",

                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            )
        )

        conn.commit()
    else:
        # Ensure the configured admin account is always flagged as superuser,
        # even if it was created before this flag existed.
        cursor.execute("UPDATE users SET is_superuser=1 WHERE id=?", (admin["id"],))
        conn.commit()

    conn.close()


# ==========================================
# CREATE USER
# ==========================================

def create_user(

        fullname,

        email,

        password,

        role,

        department

):

    email = email.strip().lower()
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT id FROM users WHERE email=?",

        (email,)

    )

    exists = cursor.fetchone()

    if exists:

        conn.close()

        return False

    hashed = hash_password(password)

    cursor.execute(
        """
        INSERT INTO users(

            fullname,

            email,

            password,

            role,

            department,

            status,

            created_at

        )

        VALUES(?,?,?,?,?,?,?)
        """,

        (

            fullname,

            email,

            hashed,

            role,

            department,

            "Active",

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        )

    )

    conn.commit()

    conn.close()

    log_activity(None, email, "user_created", f"fullname={fullname}; role={role}; department={department}")

    return True
# ==========================================
# LOGIN USER
# ==========================================

def login_user(email, password):
    """
    Authenticate user using email and password.

    Applies brute-force lockout protection: after MAX_FAILED_ATTEMPTS
    consecutive wrong passwords, the account is locked for LOCKOUT_MINUTES.

    Returns:
        dict -> user information
        None -> login failed (wrong credentials, inactive account, or locked)
    """

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *

        FROM users

        WHERE email=?
        """,
        (email,)
    )

    user = cursor.fetchone()

    if user is None:
        conn.close()
        log_activity(None, email, "login_failed", "no account with this email")
        return None

    # Check for an active lockout before checking the password.
    locked_until_raw = user["locked_until"]
    if locked_until_raw:
        try:
            locked_until = datetime.strptime(locked_until_raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            locked_until = None
        if locked_until and datetime.now() < locked_until:
            conn.close()
            log_activity(user["id"], email, "login_blocked", "account temporarily locked")
            return None

    if user["status"] not in {"Active", "Approved"}:
        conn.close()
        log_activity(user["id"], email, "login_failed", f"account status={user['status']}")
        return None

    if verify_password(password, user["password"]):
        # Successful login — reset any failed-attempt counter and lockout.
        cursor.execute(
            "UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=?",
            (user["id"],),
        )
        conn.commit()
        conn.close()

        update_last_login(user["id"])
        log_activity(user["id"], email, "login_success")

        return {

            "id": user["id"],

            "fullname": user["fullname"],

            "email": user["email"],

            "role": ROLE_ALIASES.get(user["role"], user["role"]),

            "department": user["department"],

            "status": user["status"],

            "is_superuser": bool(user["is_superuser"])
        }

    # Wrong password — increment the failed-attempt counter, locking the
    # account once the threshold is reached.
    attempts = (user["failed_attempts"] or 0) + 1
    if attempts >= MAX_FAILED_ATTEMPTS:
        lock_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
            (attempts, lock_until, user["id"]),
        )
        conn.commit()
        conn.close()
        log_activity(user["id"], email, "account_locked", f"{attempts} failed attempts; locked until {lock_until}")
        return None

    cursor.execute(
        "UPDATE users SET failed_attempts=? WHERE id=?",
        (attempts, user["id"]),
    )
    conn.commit()
    conn.close()
    log_activity(user["id"], email, "login_failed", f"wrong password; attempt {attempts}/{MAX_FAILED_ATTEMPTS}")
    return None


# ==========================================
# UPDATE LAST LOGIN
# ==========================================

def update_last_login(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users

        SET last_login=?

        WHERE id=?
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id
        )
    )

    conn.commit()

    conn.close()


# ==========================================
# LOGOUT USER
# ==========================================

def logout_user():

    keys = [

        "logged_in",

        "user",

        "email",

        "role",

        "department",

        "page"

    ]

    for key in keys:

        if key in st.session_state:

            del st.session_state[key]

    st.rerun()


# ==========================================
# GET ALL USERS
# ==========================================

def get_all_users():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

        SELECT

            id,

            fullname,

            email,

            role,

            department,

            status,

            created_at,

            last_login,

            is_superuser

        FROM users

        ORDER BY is_superuser DESC, fullname

    """)

    users = cursor.fetchall()

    conn.close()

    return users


# ==========================================
# GET USER BY EMAIL
# ==========================================

def get_user(email):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT * FROM users WHERE email=?",

        (email,)

    )

    user = cursor.fetchone()

    conn.close()

    return user

# ==========================================
# CHANGE PASSWORD
# ==========================================

def change_password(email, new_password):

    conn = get_connection()

    cursor = conn.cursor()

    hashed = hash_password(new_password)

    cursor.execute(

        """

        UPDATE users

        SET password=?

        WHERE email=?

        """,

        (

            hashed,

            email

        )

    )

    conn.commit()

    conn.close()

    log_activity(None, email, "password_changed")


# ==========================================
# UPDATE USER
# ==========================================

def update_user(

        user_id,

        fullname,

        role,

        department,

        status

):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT is_superuser, role, status FROM users WHERE id=?", (user_id,))
    target = cursor.fetchone()

    if target is not None and target["is_superuser"]:
        # The superuser account can have its name/department updated, but its
        # role and status are locked -- no one, including other
        # administrators, can demote or suspend the superuser through this
        # function.
        role = target["role"]
        status = target["status"]
        log_activity(user_id, None, "superuser_protected_update", "role/status change blocked")

    cursor.execute(

        """

        UPDATE users

        SET

            fullname=?,

            role=?,

            department=?,

            status=?

        WHERE id=?

        """,

        (

            fullname,

            role,

            department,

            status,

            user_id

        )

    )

    conn.commit()

    conn.close()

    log_activity(
        user_id, None, "user_updated",
        f"fullname={fullname}; role={role}; department={department}; status={status}",
    )


# ==========================================
# DELETE USER
# ==========================================

def delete_user(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    # Capture identifying details before deletion so the audit trail still
    # shows who was removed.
    cursor.execute("SELECT email, fullname, is_superuser FROM users WHERE id=?", (user_id,))
    target = cursor.fetchone()

    if target is not None and target["is_superuser"]:
        conn.close()
        log_activity(user_id, target["email"], "superuser_delete_blocked", "attempted deletion of protected superuser account")
        return False

    cursor.execute(

        "DELETE FROM users WHERE id=?",

        (user_id,)

    )

    conn.commit()

    conn.close()

    if target is not None:
        log_activity(user_id, target["email"], "user_deleted", f"fullname={target['fullname']}")
    else:
        log_activity(user_id, None, "user_deleted")

    return True


# ==========================================
# USER EXISTS
# ==========================================

def user_exists(email):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT id FROM users WHERE email=?",

        (email,)

    )

    exists = cursor.fetchone()

    conn.close()

    return exists is not None


# ==========================================
# TOTAL USERS
# ==========================================

def total_users():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT COUNT(*) FROM users"

    )

    total = cursor.fetchone()[0]

    conn.close()

    return total
