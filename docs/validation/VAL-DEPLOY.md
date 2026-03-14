# Validation Contract: AWS Deployment (VAL-DEPLOY)

Feature area: AWS Deployment infrastructure for EthicalSiteInspector
Scope: CloudFormation template, deployment scripts, nginx/systemd configs, production env template, mypy fixes

---

### VAL-DEPLOY-001: CloudFormation Template Syntactic Validity

The CloudFormation template (`infrastructure/cloudformation.yaml` or equivalent) must be syntactically valid YAML and conform to the AWS CloudFormation specification. Running `cfn-lint` (or `aws cloudformation validate-template --template-body`) against the template must produce zero errors.

**Pass condition:** `cfn-lint infrastructure/cloudformation.yaml` exits with code 0 and emits no errors (warnings acceptable).
**Evidence:** `cfn-lint` stdout/stderr output; exit code.

---

### VAL-DEPLOY-002: CloudFormation Template Contains All Required Resources

The CloudFormation template must declare at minimum the following AWS resource types:
- `AWS::EC2::Instance` (Amazon Linux 2023 AMI)
- `AWS::RDS::DBInstance` (PostgreSQL engine)
- `AWS::S3::Bucket`
- `AWS::ElasticLoadBalancingV2::LoadBalancer` (Application Load Balancer)
- `AWS::EC2::SecurityGroup` (at least one for EC2, one for RDS, one for ALB)
- `AWS::Route53::RecordSet` (optional — must exist with a `Condition` or be in a conditional block)

**Pass condition:** Grep/parse the template Resources section; each resource type above appears at least once. Route 53 resource exists but is gated by a `Condition`.
**Evidence:** List of `Type:` values extracted from the template's `Resources` block.

---

### VAL-DEPLOY-003: Security Groups Enforce Least-Privilege Networking

Security group ingress rules in the CloudFormation template must enforce:
- ALB SG: allows inbound 80 and 443 from `0.0.0.0/0` only.
- EC2 SG: allows inbound traffic only from the ALB security group (no direct public access on port 8000).
- RDS SG: allows inbound on port 5432 only from the EC2 security group.

**Pass condition:** Parsing the `SecurityGroupIngress` rules for each SG confirms the above constraints. No SG rule opens `0.0.0.0/0` to backend or database ports.
**Evidence:** Extracted ingress rules from each `AWS::EC2::SecurityGroup` resource.

---

### VAL-DEPLOY-004: Deployment Script Exists and Is Well-Structured

A deployment/setup script (e.g., `infrastructure/deploy.sh` or `scripts/setup-ec2.sh`) must exist and contain, at minimum, the following logical steps:
1. System package installation (Python 3.11+, nginx, postgresql-client or equivalent)
2. Python virtual environment creation (`python3 -m venv`)
3. `pip install -r requirements.txt` inside the venv
4. Playwright browser installation (`playwright install chromium --with-deps`)
5. Alembic migration execution (`alembic upgrade head`)
6. Nginx configuration deployment (copy/symlink to `/etc/nginx/`)
7. Systemd service file installation and `systemctl daemon-reload && systemctl enable`
8. Frontend build (`npm install && npm run build`) or artifact deployment

**Pass condition:** The script file exists, is executable (`chmod +x` or shebang present), and contains commands or comments covering all 8 steps above.
**Evidence:** Script file path; grep output for each keyword/step.

---

### VAL-DEPLOY-005: Nginx Configuration Correctness

An nginx configuration file (e.g., `infrastructure/nginx/ethicalsiteinspector.conf`) must:
- Serve static frontend files from the React build directory (e.g., `root /opt/ethicalsiteinspector/frontend/dist;` with `try_files $uri $uri/ /index.html;`)
- Proxy `/api` requests to the uvicorn backend (e.g., `proxy_pass http://127.0.0.1:8000;`)
- Include proxy headers (`X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `Host`)
- Listen on port 80 (HTTP) for ALB health checks (HTTPS terminated at ALB)

**Pass condition:** The nginx config file exists and contains: a `location /` block serving static files with `try_files` including `/index.html` fallback; a `location /api` block with `proxy_pass http://127.0.0.1:8000`; proxy header directives; `listen 80`.
**Evidence:** Full content of the nginx config file; grep matches for each directive.

---

### VAL-DEPLOY-006: Systemd Service File for Backend

A systemd unit file (e.g., `infrastructure/systemd/ethicalsiteinspector.service`) must:
- Set `Type=exec` or `Type=simple`
- Set `User=` to a non-root user
- Set `WorkingDirectory=` to the backend directory
- Set `ExecStart=` to invoke uvicorn via the venv Python (e.g., `/opt/.../venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`)
- Include `Restart=always` or `Restart=on-failure`
- Include `EnvironmentFile=` pointing to the production `.env` path

**Pass condition:** The `.service` file exists and contains all listed directives. The `User=` value is not `root`. `ExecStart=` references uvicorn within a virtualenv path.
**Evidence:** Full content of the systemd service file; grep matches for each directive.

---

### VAL-DEPLOY-007: Production Environment Template Completeness

A production `.env` template (e.g., `infrastructure/env.production.template`) must declare all environment variables required by the application's `Settings` class (`backend/app/core/config.py`), including at minimum:
- `APP_ENV=production`
- `DATABASE_URL` (PostgreSQL connection string placeholder, not SQLite)
- `CORS_ORIGINS` (production domain)
- `AWS_REGION`, `NOVA_MODEL_ID`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (placeholder only, not actual values)
- `S3_BUCKET_NAME`, `S3_ENDPOINT_URL`, `S3_PUBLIC_BASE_URL`
- `LOCAL_STORAGE_ROOT`, `SCREENSHOTS_DIR`, `REPORTS_DIR`
- `AUDIT_MODE`

**Pass condition:** The template file exists and contains a key for every field in the `Settings` class. `DATABASE_URL` placeholder uses `postgresql://` scheme, not `sqlite`. No variable contains an actual secret value (only placeholders like `changeme`, `<your-key>`, or empty).
**Evidence:** Template file content; diff against `Settings` fields extracted from `config.py`.

---

### VAL-DEPLOY-008: No Hardcoded Secrets in Infrastructure Files

All files under the `infrastructure/` directory (or wherever deployment artifacts live) must not contain hardcoded secrets. Specifically:
- No AWS access keys (pattern: `AKIA[0-9A-Z]{16}`)
- No hardcoded passwords (pattern: `password\s*[:=]\s*\S+` where value is not a placeholder)
- No private keys (`-----BEGIN.*PRIVATE KEY-----`)
- No database connection strings with embedded credentials

**Pass condition:** A regex scan of all infrastructure files for the above patterns returns zero true-positive matches. Placeholder values (e.g., `<YOUR_KEY>`, `changeme`, empty string) are not flagged.
**Evidence:** Grep/regex scan output across all `infrastructure/**` files.

---

### VAL-DEPLOY-009: CloudFormation Outputs Export Essential Values

The CloudFormation template must define `Outputs` that export:
- ALB DNS name or URL (for accessing the application)
- RDS endpoint address (for DATABASE_URL construction)
- S3 bucket name
- EC2 instance public IP or ID (for SSH access during maintenance)

**Pass condition:** The template's `Outputs` section contains at least 4 entries covering ALB DNS, RDS endpoint, S3 bucket name, and EC2 identifier.
**Evidence:** Extracted `Outputs` block from the template.

---

### VAL-DEPLOY-010: CloudFormation Parameters Enable Customization

The CloudFormation template must accept parameters for deployment-time customization:
- Instance type (e.g., `t3.small`, with a sensible default)
- RDS instance class and allocated storage
- Key pair name (for SSH access)
- Domain name (for optional Route 53 setup)
- Environment name or stage identifier

**Pass condition:** The template's `Parameters` section contains entries for instance sizing, key pair, domain, and environment. Each parameter has a `Default` or is marked as required with a `Description`.
**Evidence:** Extracted `Parameters` block from the template.

---

### VAL-DEPLOY-011: Mypy Type Errors Fully Resolved

All 35 pre-existing mypy type errors in the backend must be fixed. Running `mypy app/ --ignore-missing-imports` from the `backend/` directory must exit with code 0 and report "Success: no issues found".

**Pass condition:** `mypy app/ --ignore-missing-imports` exits with code 0; stdout contains "Success: no issues found" or shows zero errors.
**Evidence:** Full mypy stdout/stderr output; exit code.

---

### VAL-DEPLOY-012: ALB Health Check Target Configured

The CloudFormation template must configure the ALB target group with a health check pointing to the application's health endpoint:
- Health check path: `/api/health` (matching the existing FastAPI health route)
- Health check protocol: HTTP
- Healthy threshold and interval set to reasonable values

**Pass condition:** The `AWS::ElasticLoadBalancingV2::TargetGroup` resource includes `HealthCheckPath: /api/health` and `HealthCheckProtocol: HTTP`.
**Evidence:** Extracted target group resource definition from the template.
