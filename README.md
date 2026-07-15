# RMIP-DSS

This workspace contains the initial structure for the RMIP DSS project.

## Project Structure
- backend/
- frontend/
- database/
- data/
- docs/
- notebooks/
- models/
- api/
- dashboard/

## Dashboard Prototype

A Streamlit dashboard prototype is available in `dashboard/app.py`.

### Run the dashboard

1. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. Run Streamlit:
   ```powershell
   streamlit run dashboard/app.py
   ```

### Run the backend

The backend API is in `backend/app/main.py`.

```powershell
& "C:\Users\bkuria\RMIP-DSS\venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8001
```

### Run the React frontend

Install node dependencies in the frontend folder:

```powershell
cd frontend
npm install
```

Start the frontend:

```powershell
npm run dev
```
