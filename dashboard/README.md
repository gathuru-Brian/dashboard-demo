# Dashboard

This Streamlit dashboard uses sample reinsurance data from `data/reinsurance_sample.csv` and calls the backend API for live pricing and market/AI endpoints.

## Run dashboard

1. Activate the Python environment:
```powershell
.\venv\Scripts\Activate.ps1
```
2. Run Streamlit:
```powershell
streamlit run dashboard/app.py
```

## Notes

- The app loads sample data from the local dataset.
- If backend is running, it also shows live API health, pricing, market signal, and AI insight.
