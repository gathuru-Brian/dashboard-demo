from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

output_path = Path("RMIP-DSS_Project_Report.pdf")

sections = [
    {
        "title": "Project Overview",
        "body": [
            "RMIP-DSS is a Streamlit-based decision-support workspace for reinsurance portfolio monitoring, market intelligence, and pricing analysis.",
            "The app is designed to help reinsurance companies upload, normalize, analyze, and report on insurance portfolio data across multiple years.",
            "It supports CSV/Excel uploads, flexible column mapping, remote dataset loading, executive summary generation, and a portfolio assistant.",
        ],
    },
    {
        "title": "Key Components",
        "body": [
            "Front-end: Streamlit app in app.py provides navigation, upload flows, analytics display, and charting.",
            "Authentication: Secure local sign-in and account registration using bcrypt password hashing.",
            "Data handling: pandas and numpy are used for parsing, normalization, filtering, and calculating derived analytics.",
            "Visualization: plotly.express builds interactive charts for premium trends, line-of-business share, geographic exposure, and risk monitoring.",
            "Remote dataset support: requests downloads a dataset from a URL and reuses the upload parsing pipeline.",
        ],
    },
    {
        "title": "Algorithms and Data Flow",
        "body": [
            "Data normalization uses a canonical column mapping dictionary to accept widely varying insurance file headers.",
            "Date parsing converts date fields into pandas datetime values and supports all available years or a custom reporting period.",
            "Derived metrics compute GWP, NEP, claims paid, loss ratio, combined ratio, and exposure across uploaded portfolio records.",
            "Grouped analytics summarize portfolio performance by line of business, region, client, and risk category.",
            "Executive reporting creates a narrative summary from portfolio aggregates, highlighting top regions, concentration, and recommended actions.",
            "A pricing simulator calculates indicated rate changes from loss, expense, and margin assumptions for underwriting scenario testing.",
        ],
    },
    {
        "title": "Frameworks and Tools",
        "body": [
            "Streamlit: UI framework for browser-based analytics and interactive controls.",
            "pandas: Core data ingestion, cleaning, normalization, and aggregation engine.",
            "numpy: Numerical conversions and safe ratio calculations.",
            "plotly.express: Interactive chart rendering within Streamlit.",
            "requests: Remote dataset download and ingestion support.",
            "bcrypt: Secure password hashing for authentication.",
            "sqlalchemy and psycopg2-binary: Included for managed database connectivity and production-ready backend support.",
            "fastapi and uvicorn: Present for API service architecture and future backend deployment.",
            "xgboost and scikit-learn: Available for future predictive underwriting, pricing, and risk scoring models.",
        ],
    },
    {
        "title": "Why This Project Matters for Reinsurance",
        "body": [
            "Reinsurance companies need a unified portfolio view to monitor premium, claims, exposure, and profitability across treaties and regions.",
            "RMIP-DSS reduces manual effort by normalizing incoming cedant and carrier data, enabling faster analytics and decision making.",
            "Multi-year analysis and custom date ranges are essential for treaty renewals, loss development review, and capital planning.",
            "Executive summaries, exportable reports, and risk category monitoring help underwriters and portfolio managers communicate insights to stakeholders.",
            "Remote dataset loading and flexible upload handling support large enterprise datasets and distributed reinsurance workflows.",
        ],
    },
    {
        "title": "Deployment and Hosting",
        "body": [
            "Streamlit configuration is provided for hosted deployment with requirements.txt, runtime.txt, and .streamlit settings.",
            "The app can be deployed on Streamlit Community Cloud or a managed containerized environment.",
            "For enterprise deployment, move authentication and data persistence to a managed database and secure secrets outside source control.",
        ],
    },
    {
        "title": "Project Structure",
        "body": [
            "app.py: Main Streamlit app entry point and active analytics interface.",
            "auth/: Authentication, login, registration, roles, and permissions.",
            "dashboard/: Supporting dashboard modules and pages for broader analytics flows.",
            "backend/: API services, pricing engine, market intelligence, and database models.",
            "utils/: Shared helpers for data loading, charting, exporting, and styling.",
            "data/: Sample datasets and user data used by the application.",
        ],
    },
]

c = canvas.Canvas(str(output_path), pagesize=letter)
width, height = letter
margin = 0.75 * inch
text_x = margin
text_y = height - margin

for section in sections:
    c.setFont("Helvetica-Bold", 16)
    c.drawString(text_x, text_y, section["title"])
    text_y -= 0.35 * inch
    c.setFont("Helvetica", 11)
    for paragraph in section["body"]:
        words = paragraph.split()
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if c.stringWidth(test_line, "Helvetica", 11) <= width - 2 * margin:
                line = test_line
            else:
                c.drawString(text_x, text_y, line)
                text_y -= 0.22 * inch
                line = word
                if text_y < margin + inch:
                    c.showPage()
                    text_y = height - margin
                    c.setFont("Helvetica", 11)
        if line:
            c.drawString(text_x, text_y, line)
            text_y -= 0.22 * inch
        text_y -= 0.15 * inch
        if text_y < margin + inch:
            c.showPage()
            text_y = height - margin
            c.setFont("Helvetica", 11)
    c.showPage()
    text_y = height - margin

c.save()
print(f"Report generated at: {output_path.resolve()}")
