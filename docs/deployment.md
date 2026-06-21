# Deployment

## Local Backend

1. Create a PostgreSQL database.
2. Ensure required schema and enum types exist.
3. Set `DATABASE_URL`.
4. Install dependencies from root `requirements.txt`.
5. Run Uvicorn.

Example:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

If running from inside `backend/`, imports may need the module path adjusted. Prefer running from repository root.

## Local Frontend

```bash
cd frontend
npm install
npm start
```

Set the API URL:

```bash
EXPO_PUBLIC_API_URL=http://<machine-ip>:8000
```

For physical devices, use the computer's LAN IP rather than `localhost`.

## Environment Variables

Backend:

- `DATABASE_URL`: PostgreSQL async SQLAlchemy URL, for example `postgresql+asyncpg://user:password@host:5432/dbname`

Frontend:

- `EXPO_PUBLIC_API_URL`: backend base URL

## Production Considerations

Before production:

- Replace startup table creation with migrations.
- Restrict CORS origins.
- Add authentication and authorization.
- Configure HTTPS termination.
- Move secrets out of local `.env` files.
- Add structured logging.
- Add health and readiness probes.
- Add backups and restore procedures for PostgreSQL.
- Add CI/CD and automated test gates.

## Rollback Strategy

No deployment automation exists yet. When adding it, define rollback for:

- Backend application release
- Frontend app release
- Database migrations
- Configuration changes

Database rollback is especially important once inventory and payment flows become real.

## Fly.io Backend Deployment

This repository includes a Fly.io configuration for the FastAPI backend:

- `fly.toml`
- `infra/api/Dockerfile`
- `.dockerignore`

The Expo frontend is not deployed by this Fly app. Point the frontend to the deployed backend URL with `EXPO_PUBLIC_API_URL`.

### 1. Install and log in

```powershell
iwr https://fly.io/install.ps1 -useb | iex
fly auth login
```

If PowerShell cannot find `fly` after installation, close and reopen the terminal.

### 2. Pick an app name

Edit `fly.toml` and replace this placeholder with a globally unique Fly app name:

```toml
app = "smartcheckout-backend"
```

Example:

```toml
app = "smartcheckout-backend-yourname"
```

The default region is Mumbai:

```toml
primary_region = "bom"
```

### 3. Create the Fly app

```powershell
fly apps create smartcheckout-backend-yourname
```

Use the same app name you placed in `fly.toml`.

### 4. Configure PostgreSQL

Create a PostgreSQL database from the Fly dashboard or another managed PostgreSQL provider.

Set the async SQLAlchemy database URL as a secret:

```powershell
fly secrets set DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME"
```

Do not put `DATABASE_URL` in `fly.toml`; keep it as a secret.

### 5. Deploy

```powershell
fly deploy
```

### 6. Verify

```powershell
fly status
fly open
```

Health endpoints:

```text
https://<your-app-name>.fly.dev/health
https://<your-app-name>.fly.dev/api/v1/ready
```

### 7. Point Expo to the backend

Set the frontend API URL:

```env
EXPO_PUBLIC_API_URL=https://<your-app-name>.fly.dev
```

Restart Expo after changing this value.

## Render Backend Deployment

This repository includes `render.yaml` for deploying the FastAPI backend as a Render Python web service.

If you create the service manually in the Render dashboard, use these settings:

```text
Root Directory: SmartCheckoutBackend
Runtime: Python
Region: Singapore
Instance Type: Free
Build Command: pip install -r requirements.txt
Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

If the Git repository root is already `SmartCheckoutBackend`, leave Root Directory empty.

Set these environment variables in Render:

```text
DATABASE_URL=<your Render PostgreSQL internal database URL>
PYTHON_VERSION=3.11.9
WHATSAPP_GRAPH_VERSION=v19.0
```

Render PostgreSQL URLs can use `postgres://` or `postgresql://`. The backend normalizes those values to the async SQLAlchemy driver URL required by this app.

After the backend deploys, point the Expo frontend to the Render URL:

```env
EXPO_PUBLIC_API_URL=https://<your-render-service>.onrender.com
```
