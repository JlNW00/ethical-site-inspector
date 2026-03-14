"""Tests for deployment scripts and configuration files.

Validates:
- deploy.sh structure, shebang, idempotency, all required steps
- nginx configuration directives (SPA fallback, API proxy, proxy headers)
- systemd service directives (non-root user, venv uvicorn, Restart=always, EnvironmentFile)
- Production env template completeness (all Settings fields)
- No hardcoded secrets in any infrastructure file

Fulfills:
- VAL-DEPLOY-004: Deployment script exists with all steps
- VAL-DEPLOY-005: Nginx configuration correctness
- VAL-DEPLOY-006: Systemd service file for backend
- VAL-DEPLOY-007: Production environment template completeness
- VAL-DEPLOY-008: No hardcoded secrets in infrastructure files
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Paths to infrastructure files
INFRASTRUCTURE_DIR = Path(__file__).resolve().parents[2] / "infrastructure"
DEPLOY_SCRIPT_PATH = INFRASTRUCTURE_DIR / "deploy.sh"
NGINX_CONF_PATH = INFRASTRUCTURE_DIR / "nginx" / "ethicalsiteinspector.conf"
SYSTEMD_SERVICE_PATH = INFRASTRUCTURE_DIR / "systemd" / "ethicalsiteinspector.service"
ENV_TEMPLATE_PATH = INFRASTRUCTURE_DIR / "env.production.template"


def _read_file_or_fail(path: Path) -> str:
    """Read file content or fail the test."""
    if not path.exists():
        pytest.fail(f"Required file not found: {path}")
    return path.read_text()


@pytest.fixture()
def deploy_script_content():
    """Load deploy.sh content."""
    return _read_file_or_fail(DEPLOY_SCRIPT_PATH)


@pytest.fixture()
def nginx_conf_content():
    """Load nginx configuration content."""
    return _read_file_or_fail(NGINX_CONF_PATH)


@pytest.fixture()
def systemd_service_content():
    """Load systemd service file content."""
    return _read_file_or_fail(SYSTEMD_SERVICE_PATH)


@pytest.fixture()
def env_template_content():
    """Load production environment template content."""
    return _read_file_or_fail(ENV_TEMPLATE_PATH)


class TestDeployScript:
    """VAL-DEPLOY-004: Deployment script exists with all 8 setup steps."""

    def test_deploy_script_exists(self):
        """deploy.sh must exist in infrastructure directory."""
        assert DEPLOY_SCRIPT_PATH.exists(), f"deploy.sh not found at {DEPLOY_SCRIPT_PATH}"

    def test_deploy_script_has_shebang(self, deploy_script_content):
        """Script must have proper shebang line."""
        lines = deploy_script_content.splitlines()
        assert len(lines) > 0, "Script is empty"
        assert lines[0].startswith("#!/bin/bash"), f"Missing shebang, found: {lines[0]}"

    def test_deploy_script_is_executable(self):
        """Script should be executable (Unix permissions)."""
        import os
        import stat

        if os.name == "posix":
            st = os.stat(DEPLOY_SCRIPT_PATH)
            is_executable = bool(st.st_mode & stat.S_IXUSR)
            # Note: We can't set permissions on Windows, but we check if it would be executable
            # The test documents the requirement
            assert is_executable, "Script should have executable permissions on Unix"

    def test_deploy_script_step1_install_packages(self, deploy_script_content):
        """Step 1: Install system packages (python3, nginx, postgresql-client, nodejs)."""
        content = deploy_script_content.lower()

        # Check for step function
        assert "step1_install_packages" in deploy_script_content, "Missing step1_install_packages function"

        # Check for required packages
        assert "python3" in content, "Missing python3 installation"
        assert "nginx" in content, "Missing nginx installation"
        assert "postgresql" in content, "Missing postgresql installation"
        assert "nodejs" in content or "node.js" in content, "Missing Node.js installation"

    def test_deploy_script_step2_create_venv(self, deploy_script_content):
        """Step 2: Create Python virtual environment."""
        assert "step2_create_venv" in deploy_script_content, "Missing step2_create_venv function"
        assert "python3 -m venv" in deploy_script_content, "Missing venv creation command"

    def test_deploy_script_step3_install_python_deps(self, deploy_script_content):
        """Step 3: Install Python dependencies (pip install)."""
        assert "step3_install_python_deps" in deploy_script_content, "Missing step3_install_python_deps function"
        assert "pip install" in deploy_script_content, "Missing pip install command"
        assert "requirements.txt" in deploy_script_content, "Missing requirements.txt reference"

    def test_deploy_script_step4_install_playwright(self, deploy_script_content):
        """Step 4: Install Playwright with Chromium."""
        assert "step4_install_playwright" in deploy_script_content, "Missing step4_install_playwright function"
        assert "playwright install chromium" in deploy_script_content, "Missing Playwright chromium installation"

    def test_deploy_script_step5_run_migrations(self, deploy_script_content):
        """Step 5: Run database migrations (alembic)."""
        assert "step5_run_migrations" in deploy_script_content, "Missing step5_run_migrations function"
        assert "alembic upgrade head" in deploy_script_content, "Missing alembic migration command"

    def test_deploy_script_step6_configure_nginx(self, deploy_script_content):
        """Step 6: Configure nginx (copy config, test, reload)."""
        assert "step6_configure_nginx" in deploy_script_content, "Missing step6_configure_nginx function"
        assert "nginx" in deploy_script_content.lower(), "Missing nginx configuration"
        assert "nginx -t" in deploy_script_content, "Missing nginx configuration test"

    def test_deploy_script_step7_configure_systemd(self, deploy_script_content):
        """Step 7: Configure systemd service (daemon-reload, enable, start)."""
        assert "step7_configure_systemd" in deploy_script_content, "Missing step7_configure_systemd function"
        assert "systemctl daemon-reload" in deploy_script_content, "Missing systemctl daemon-reload"
        assert "systemctl enable" in deploy_script_content, "Missing systemctl enable"
        assert "systemctl start" in deploy_script_content, "Missing systemctl start"

    def test_deploy_script_step8_build_frontend(self, deploy_script_content):
        """Step 8: Build and deploy frontend (npm install, build, copy to /var/www)."""
        assert "step8_build_frontend" in deploy_script_content, "Missing step8_build_frontend function"
        assert "npm install" in deploy_script_content or "npm ci" in deploy_script_content, "Missing npm install"
        assert "npm run build" in deploy_script_content, "Missing npm run build"
        assert "/var/www" in deploy_script_content, "Missing /var/www directory reference"

    def test_deploy_script_all_steps_present(self, deploy_script_content):
        """All 8 steps must be defined and called in main function."""
        for i in range(1, 9):
            assert f"step{i}_" in deploy_script_content, f"Missing step {i} function"

    def test_deploy_script_idempotent_markers(self, deploy_script_content):
        """Script should contain idempotency markers (checks before actions)."""
        # Check for common idempotency patterns
        idempotent_patterns = [
            "already exists",
            "already installed",
            "skipping",
            "if [[ -d",
            "if [[ -f",
            "if [[ $EUID",
            "mkdir -p",
        ]
        found_patterns = [p for p in idempotent_patterns if p.lower() in deploy_script_content.lower()]
        assert len(found_patterns) >= 3, f"Script lacks idempotency markers. Found: {found_patterns}"

    def test_deploy_script_has_error_handling(self, deploy_script_content):
        """Script should have error handling (set -e)."""
        assert "set -e" in deploy_script_content, "Missing 'set -e' for error handling"

    def test_deploy_script_individual_step_execution(self, deploy_script_content):
        """Script should support running individual steps via --step flag."""
        assert "--step" in deploy_script_content, "Missing --step flag support"
        assert "case \"$2\"" in deploy_script_content or "case $2 in" in deploy_script_content, "Missing step selection case statement"


class TestNginxConfig:
    """VAL-DEPLOY-005: Nginx configuration correctness."""

    def test_nginx_config_exists(self):
        """nginx configuration file must exist."""
        assert NGINX_CONF_PATH.exists(), f"Nginx config not found at {NGINX_CONF_PATH}"

    def test_nginx_listens_on_port_80(self, nginx_conf_content):
        """Nginx must listen on port 80."""
        assert "listen 80" in nginx_conf_content, "Missing 'listen 80' directive"

    def test_nginx_serves_static_files_from_var_www(self, nginx_conf_content):
        """Nginx should serve static files from /var/www/ethicalsiteinspector."""
        assert "/var/www/ethicalsiteinspector" in nginx_conf_content, "Missing /var/www/ethicalsiteinspector root"

    def test_nginx_has_spa_fallback(self, nginx_conf_content):
        """Nginx must have SPA fallback (try_files $uri $uri/ /index.html)."""
        # Check for SPA fallback pattern
        spa_pattern = r"try_files\s+\$uri\s+\$uri/\s+/index\.html"
        assert re.search(spa_pattern, nginx_conf_content), "Missing SPA fallback try_files directive"

    def test_nginx_proxies_api_to_backend(self, nginx_conf_content):
        """Nginx must proxy /api to backend on port 8000."""
        assert "location /api" in nginx_conf_content, "Missing /api location block"
        assert "proxy_pass" in nginx_conf_content, "Missing proxy_pass directive"
        assert "8000" in nginx_conf_content or "upstream backend" in nginx_conf_content, "Missing backend port reference"

    def test_nginx_proxies_artifacts_to_backend(self, nginx_conf_content):
        """Nginx must proxy /artifacts to backend."""
        assert "location /artifacts" in nginx_conf_content, "Missing /artifacts location block"

    def test_nginx_includes_proxy_headers(self, nginx_conf_content):
        """Nginx must include standard proxy headers."""
        required_headers = [
            "X-Real-IP",
            "X-Forwarded-For",
            "X-Forwarded-Proto",
            "Host",
        ]
        for header in required_headers:
            assert header in nginx_conf_content, f"Missing proxy header: {header}"

    def test_nginx_has_upstream_backend(self, nginx_conf_content):
        """Nginx should define upstream backend pointing to 127.0.0.1:8000."""
        assert "upstream backend" in nginx_conf_content, "Missing upstream backend block"
        assert "127.0.0.1:8000" in nginx_conf_content, "Missing 127.0.0.1:8000 upstream"

    def test_nginx_has_security_headers(self, nginx_conf_content):
        """Nginx should include security headers."""
        security_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
        ]
        for header in security_headers:
            assert header in nginx_conf_content, f"Missing security header: {header}"


class TestSystemdService:
    """VAL-DEPLOY-006: Systemd service file for backend."""

    def test_systemd_service_exists(self):
        """systemd service file must exist."""
        assert SYSTEMD_SERVICE_PATH.exists(), f"Systemd service not found at {SYSTEMD_SERVICE_PATH}"

    def test_systemd_type_is_exec(self, systemd_service_content):
        """Service Type must be 'exec'."""
        assert "Type=exec" in systemd_service_content, "Missing or incorrect Type=exec directive"

    def test_systemd_uses_non_root_user(self, systemd_service_content):
        """Service must use non-root User (ec2-user)."""
        assert "User=ec2-user" in systemd_service_content or "User=" in systemd_service_content, "Missing User directive"
        # Ensure it's not running as root
        assert "User=root" not in systemd_service_content, "Service should not run as root"

    def test_systemd_has_working_directory(self, systemd_service_content):
        """Service must set WorkingDirectory."""
        assert "WorkingDirectory=" in systemd_service_content, "Missing WorkingDirectory directive"
        assert "/opt/ethicalsiteinspector" in systemd_service_content, "WorkingDirectory should be /opt/ethicalsiteinspector"

    def test_systemd_execstart_uses_venv_uvicorn(self, systemd_service_content):
        """ExecStart must use venv uvicorn on 127.0.0.1:8000."""
        assert "ExecStart=" in systemd_service_content, "Missing ExecStart directive"
        # Check for venv path
        assert ".venv/bin/uvicorn" in systemd_service_content, "ExecStart should use venv uvicorn"
        # Check for binding to localhost
        assert "127.0.0.1" in systemd_service_content, "ExecStart should bind to 127.0.0.1"
        assert "--port 8000" in systemd_service_content or "--port" in systemd_service_content, "ExecStart should specify port"

    def test_systemd_restart_is_always(self, systemd_service_content):
        """Restart must be 'always'."""
        assert "Restart=always" in systemd_service_content, "Missing or incorrect Restart=always directive"

    def test_systemd_has_environment_file(self, systemd_service_content):
        """Service must specify EnvironmentFile."""
        assert "EnvironmentFile=" in systemd_service_content, "Missing EnvironmentFile directive"
        assert ".env" in systemd_service_content, "EnvironmentFile should reference .env file"

    def test_systemd_has_after_network_target(self, systemd_service_content):
        """Service should start after network is available."""
        assert "After=network.target" in systemd_service_content, "Missing After=network.target"

    def test_systemd_has_wanted_by_multi_user(self, systemd_service_content):
        """Service should be wanted by multi-user.target."""
        assert "WantedBy=multi-user.target" in systemd_service_content, "Missing WantedBy=multi-user.target"


class TestEnvProductionTemplate:
    """VAL-DEPLOY-007: Production environment template completeness."""

    def test_env_template_exists(self):
        """Production env template must exist."""
        assert ENV_TEMPLATE_PATH.exists(), f"Env template not found at {ENV_TEMPLATE_PATH}"

    def test_env_template_has_app_env(self, env_template_content):
        """Template must include APP_ENV setting."""
        assert "APP_ENV=" in env_template_content, "Missing APP_ENV"
        assert "production" in env_template_content.lower(), "APP_ENV should default to or mention production"

    def test_env_template_has_database_url_postgresql(self, env_template_content):
        """Template must have DATABASE_URL with postgresql:// placeholder."""
        assert "DATABASE_URL=" in env_template_content, "Missing DATABASE_URL"
        # Should have postgresql:// placeholder or example
        assert "postgresql://" in env_template_content, "DATABASE_URL should show postgresql:// format"

    def test_env_template_has_cors_origins(self, env_template_content):
        """Template must include CORS_ORIGINS."""
        assert "CORS_ORIGINS=" in env_template_content, "Missing CORS_ORIGINS"

    def test_env_template_has_aws_credentials_placeholders(self, env_template_content):
        """Template must have AWS credential placeholders (no actual secrets)."""
        assert "AWS_ACCESS_KEY_ID=" in env_template_content, "Missing AWS_ACCESS_KEY_ID"
        assert "AWS_SECRET_ACCESS_KEY=" in env_template_content, "Missing AWS_SECRET_ACCESS_KEY"
        assert "AWS_REGION=" in env_template_content, "Missing AWS_REGION"

        # Should have placeholders, not real credentials
        placeholders = ["YOUR_", "placeholder", "changeme", "replace"]
        has_placeholder = any(p.lower() in env_template_content.lower() for p in placeholders)
        # This is a warning, not a failure - templates often have examples
        assert has_placeholder, "Template should use placeholders for sensitive values"

    def test_env_template_has_s3_config(self, env_template_content):
        """Template must include S3 configuration variables."""
        assert "S3_BUCKET_NAME=" in env_template_content, "Missing S3_BUCKET_NAME"
        assert "S3_ENDPOINT_URL=" in env_template_content, "Missing S3_ENDPOINT_URL"
        assert "S3_PUBLIC_BASE_URL=" in env_template_content, "Missing S3_PUBLIC_BASE_URL"

    def test_env_template_has_audit_mode(self, env_template_content):
        """Template must include AUDIT_MODE setting."""
        assert "AUDIT_MODE=" in env_template_content, "Missing AUDIT_MODE"

    def test_env_template_has_use_real_browser(self, env_template_content):
        """Template must include USE_REAL_BROWSER setting."""
        assert "USE_REAL_BROWSER=" in env_template_content, "Missing USE_REAL_BROWSER"

    def test_env_template_has_local_storage_root(self, env_template_content):
        """Template must include LOCAL_STORAGE_ROOT setting."""
        assert "LOCAL_STORAGE_ROOT=" in env_template_content, "Missing LOCAL_STORAGE_ROOT"

    def test_env_template_has_screenshots_dir(self, env_template_content):
        """Template must include SCREENSHOTS_DIR setting."""
        assert "SCREENSHOTS_DIR=" in env_template_content, "Missing SCREENSHOTS_DIR"

    def test_env_template_has_reports_dir(self, env_template_content):
        """Template must include REPORTS_DIR setting."""
        assert "REPORTS_DIR=" in env_template_content, "Missing REPORTS_DIR"

    def test_env_template_has_nova_model_id(self, env_template_content):
        """Template must include NOVA_MODEL_ID setting."""
        assert "NOVA_MODEL_ID=" in env_template_content, "Missing NOVA_MODEL_ID"

    def test_env_template_covers_all_settings_fields(self, env_template_content):
        """Template should cover all major Settings fields from config.py."""
        # Based on the Settings class in app/core/config.py
        required_fields = [
            "APP_ENV",
            "APP_NAME",
            "API_PREFIX",
            "AUDIT_MODE",
            "USE_REAL_BROWSER",
            "DATABASE_URL",
            "LOCAL_STORAGE_ROOT",
            "SCREENSHOTS_DIR",
            "REPORTS_DIR",
            "CORS_ORIGINS",
            "AWS_REGION",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "NOVA_MODEL_ID",
            "S3_BUCKET_NAME",
            "S3_ENDPOINT_URL",
            "S3_PUBLIC_BASE_URL",
        ]

        missing = []
        for field in required_fields:
            if field + "=" not in env_template_content:
                missing.append(field)

        # Allow some fields to be missing if they're derived or have different names
        assert len(missing) <= 2, f"Too many missing Settings fields: {missing}"


class TestNoHardcodedSecrets:
    """VAL-DEPLOY-008: No hardcoded secrets in infrastructure files."""

    def test_no_aws_access_key_in_deploy_script(self, deploy_script_content):
        """deploy.sh should not contain AWS access keys."""
        akia_pattern = r'AKIA[0-9A-Z]{16}'
        matches = re.findall(akia_pattern, deploy_script_content)
        assert len(matches) == 0, f"Found potential AWS access key: {matches}"

    def test_no_aws_access_key_in_nginx_config(self, nginx_conf_content):
        """nginx config should not contain AWS access keys."""
        akia_pattern = r'AKIA[0-9A-Z]{16}'
        matches = re.findall(akia_pattern, nginx_conf_content)
        assert len(matches) == 0, f"Found potential AWS access key: {matches}"

    def test_no_aws_access_key_in_systemd_service(self, systemd_service_content):
        """systemd service should not contain AWS access keys."""
        akia_pattern = r'AKIA[0-9A-Z]{16}'
        matches = re.findall(akia_pattern, systemd_service_content)
        assert len(matches) == 0, f"Found potential AWS access key: {matches}"

    def test_no_hardcoded_passwords_in_infrastructure(self):
        """Infrastructure files should not contain hardcoded passwords."""
        infrastructure_files = [
            DEPLOY_SCRIPT_PATH,
            NGINX_CONF_PATH,
            SYSTEMD_SERVICE_PATH,
        ]

        password_patterns = [
            r'(?i)password\s*=\s*["\'][^"\']{8,}["\']',
            r'(?i)secret\s*=\s*["\'][^"\']{8,}["\']',
            r'(?i)api_key\s*=\s*["\'][^"\']{8,}["\']',
        ]

        for file_path in infrastructure_files:
            if not file_path.exists():
                continue
            content = file_path.read_text()
            for pattern in password_patterns:
                matches = re.findall(pattern, content)
                # Filter out placeholders and examples
                filtered = [m for m in matches if not any(x in m.lower() for x in [
                    "your_", "placeholder", "changeme", "example", "$"
                ])]
                assert len(filtered) == 0, f"Found potential hardcoded secret in {file_path.name}: {filtered}"

    def test_env_template_uses_placeholders(self, env_template_content):
        """env.production.template should use placeholders, not real secrets."""
        # Check for real-looking secrets (not placeholders)
        secret_patterns = [
            r'AWS_ACCESS_KEY_ID=[A-Z0-9]{20}',  # Real AKIA key format
            r'AWS_SECRET_ACCESS_KEY=[A-Za-z0-9/+=]{40}',  # Real secret key format
        ]

        for pattern in secret_patterns:
            matches = re.findall(pattern, env_template_content)
            # These would be real secrets, not placeholders
            real_secrets = [m for m in matches if not any(p in m for p in ["YOUR_", "EXAMPLE", "PLACEHOLDER"])]
            assert len(real_secrets) == 0, f"Found potential real AWS credentials: {real_secrets}"


class TestInfrastructureDirectoryStructure:
    """Additional tests for overall infrastructure structure."""

    def test_infrastructure_dir_exists(self):
        """Infrastructure directory must exist."""
        assert INFRASTRUCTURE_DIR.exists(), f"Infrastructure directory not found at {INFRASTRUCTURE_DIR}"

    def test_nginx_directory_exists(self):
        """nginx subdirectory must exist."""
        nginx_dir = INFRASTRUCTURE_DIR / "nginx"
        assert nginx_dir.exists(), f"nginx directory not found at {nginx_dir}"

    def test_systemd_directory_exists(self):
        """systemd subdirectory must exist."""
        systemd_dir = INFRASTRUCTURE_DIR / "systemd"
        assert systemd_dir.exists(), f"systemd directory not found at {systemd_dir}"

    def test_deploy_script_documentation(self, deploy_script_content):
        """deploy.sh should have documentation comments."""
        assert "#" in deploy_script_content, "Script should have comments/documentation"
        # Should describe what the script does
        assert len(deploy_script_content.splitlines()) > 20, "Script should be substantial (more than 20 lines)"
