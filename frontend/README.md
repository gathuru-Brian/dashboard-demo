# Frontend

This folder is reserved for the frontend application of the RMIP-DSS project.

## Suggested structure

- `src/` for React, Vue, or another SPA implementation
- `public/` for static assets
- `README.md` for frontend-specific setup

Currently, the project uses `dashboard/app.py` as the interactive analytics prototype.

## React Frontend

Install dependencies:
```powershell
cd frontend
npm install
```

Run the frontend:
```powershell
npm run dev
```

The frontend will hit the backend API at `http://127.0.0.1:8001`.
