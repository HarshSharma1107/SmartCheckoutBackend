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
