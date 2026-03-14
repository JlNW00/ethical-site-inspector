# Deployment Architecture

Production deployment conventions discovered during the deployment milestone.

**What belongs here:** Deployment-specific paths, service configuration, and infrastructure conventions.

---

## Target Environment
- **OS:** Amazon Linux 2023 (AL2023) on EC2
- **Infrastructure:** CloudFormation (infrastructure/cloudformation.yaml)

## Directory Layout (Production)
- **App root:** `/opt/ethicalsiteinspector/`
- **Backend:** `/opt/ethicalsiteinspector/backend/`
- **Frontend build:** `/var/www/ethicalsiteinspector/dist/`
- **Virtual env:** `/opt/ethicalsiteinspector/backend/.venv/`
- **Data dir:** `/opt/ethicalsiteinspector/data/`
- **Env file:** `/opt/ethicalsiteinspector/.env`

## Service User
- **User:** `ec2-user` (non-root)
- Systemd service runs as ec2-user
- Nginx runs as system nginx user

## Services
- **Backend:** uvicorn on `127.0.0.1:8000` (systemd managed)
- **Frontend:** Static files served by nginx from `/var/www/ethicalsiteinspector/dist/`
- **Reverse proxy:** nginx on port 80, proxies `/api` and `/artifacts` to backend
- **Database:** RDS PostgreSQL (not local SQLite)
- **Storage:** S3 bucket for artifacts/videos

## Key Files
- `infrastructure/cloudformation.yaml` — AWS resource definitions
- `infrastructure/deploy.sh` — Idempotent setup script (supports `--step N`)
- `infrastructure/nginx/ethicalsiteinspector.conf` — Nginx config
- `infrastructure/systemd/ethicalsiteinspector.service` — Backend service unit
- `infrastructure/env.production.template` — Environment variable template
