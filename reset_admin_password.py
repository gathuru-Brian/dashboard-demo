"""
reset_admin_password.py
------------------------
Run this ONCE from your project root to update the password on an admin
account that was already created. This does NOT create a new account --
it only updates the password on the account matching [admin].email in
.streamlit/secrets.toml, and clears any active lockout on that account.

Usage:
    python reset_admin_password.py
"""

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auth.authentication import (
    get_admin_email,
    get_user,
    change_password,
    get_connection,
)


def main():
    try:
        admin_email = get_admin_email()
    except RuntimeError as error:
        print(f"ERROR: {error}")
        print("Make sure [admin] email is set in .streamlit/secrets.toml first.")
        sys.exit(1)

    user = get_user(admin_email)
    if user is None:
        print(f"No account found for {admin_email}.")
        print("Run the app normally instead -- initialize_admin() will create it fresh.")
        sys.exit(1)

    print(f"Found account: {user['fullname']} ({user['email']}), role={user['role']}")
    new_password = getpass.getpass("Enter the new password: ")
    confirm_password = getpass.getpass("Confirm the new password: ")

    if len(new_password) < 10:
        print("ERROR: Password must be at least 10 characters.")
        sys.exit(1)
    if new_password != confirm_password:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    change_password(admin_email, new_password)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET failed_attempts=0, locked_until=NULL WHERE email=?",
        (admin_email,),
    )
    conn.commit()
    conn.close()

    print(f"Password updated successfully for {admin_email}.")
    print("Any existing lockout on this account has also been cleared.")


if __name__ == "__main__":
    main()