# Deployment notes

## Portfolio deployment

A simple public deployment can use:

- frontend: any static host capable of serving the Vite build
- backend: a container host with HTTPS
- database: managed PostgreSQL

Set `VITE_API_BASE_URL` at frontend build time when the API is on another origin. Set `FORGE_FRONTEND_URL`, CORS origins, and the Atlassian callback URL to the public HTTPS domains.

## Minimum production controls

- HTTPS only
- organization and user authentication
- tenant-aware database queries
- managed secrets and key rotation
- Alembic migrations instead of automatic table creation
- request limits and abuse protection
- structured logs and monitoring
- encrypted backups and retention rules
- a data-processing disclosure for text sent to the LLM provider
