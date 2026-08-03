# RMIP-DSS

RMIP-DSS is a Streamlit decision-support workspace for reinsurance portfolio monitoring, market intelligence, and pricing analysis.

## What is included

- Secure local sign-in and account registration with bcrypt password hashing
- Role-based dashboard navigation
- Portfolio filters for source, period, line of business, region, and risk category
- Executive KPIs, premium and claims trends, pricing analysis, cedant and reinsurer views
- CSV/Excel upload validation, session-scoped uploaded data, and CSV export
- A production-ready Streamlit theme and deployment configuration

## Run locally

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open the local address printed by Streamlit (normally `http://localhost:8501`). On a clean local database, the first run initializes the development administrator `admin@acentria.com` with password `Admin@123`. Existing user records are preserved; change or remove the development account before sharing the app.

## Data uploads

Upload CSV, XLSX, or XLS files with these required columns:

`policy_id`, `period`, `region`, `line_of_business`, `gross_written_premium`, `net_earned_premium`, `claims_paid`, `loss_ratio`, and `combined_ratio`.

Dates must be parseable. Uploaded data is retained only for the current browser session and is not written to disk.

## Deploy to Streamlit Community Cloud

1. Commit and push this project to a GitHub repository. Do not commit `.streamlit/secrets.toml`, `database/users.db`, or production data.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app** and select the repository and branch.
3. Set the main file path to `app.py`. Community Cloud reads `requirements.txt`, `runtime.txt`, and `.streamlit/config.toml` automatically.
4. Deploy. Set any production secrets in **App settings → Secrets**, never in source control.
5. Immediately replace the development administrator account and use a managed database for production. SQLite on Community Cloud is ephemeral and is suitable only for demos.

## Production notes

The repository currently uses SQLite for a self-contained demo. For a multi-user deployment, move users and application data to a managed database, set credentials via Streamlit secrets, enforce an approved identity provider, and keep audit logging outside the app container.
