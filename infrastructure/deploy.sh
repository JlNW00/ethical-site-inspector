#!/bin/bash
# EthicalSiteInspector Deployment Script
# Idempotent deployment script for Amazon Linux 2023
# Safe to re-run — will skip already-completed steps

set -e

# Configuration
APP_NAME="ethicalsiteinspector"
APP_DIR="/opt/${APP_NAME}"
APP_USER="ec2-user"
VENV_DIR="${APP_DIR}/backend/.venv"
WWW_DIR="/var/www/${APP_NAME}"
NGINX_CONF_SRC="${APP_DIR}/infrastructure/nginx/ethicalsiteinspector.conf"
NGINX_CONF_DST="/etc/nginx/conf.d/ethicalsiteinspector.conf"
SYSTEMD_SERVICE_SRC="${APP_DIR}/infrastructure/systemd/ethicalsiteinspector.service"
SYSTEMD_SERVICE_DST="/etc/systemd/system/ethicalsiteinspector.service"
ENV_FILE="${APP_DIR}/.env"

# Logging
LOG_FILE="/var/log/ethicalsiteinspector-deploy.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== EthicalSiteInspector Deployment Script ==="
echo "Started at: $(date)"
echo "Running as: $(whoami)"
echo ""

# Check if running as root for system-level operations
if [[ $EUID -ne 0 ]]; then
   echo "Warning: Not running as root. System package installation and systemd operations will fail."
   echo "Run with sudo for full deployment, or run individual steps manually."
fi

# -----------------------------------------------------------------------------
# Step 1: Install system packages (idempotent)
# -----------------------------------------------------------------------------
step1_install_packages() {
    echo "=== Step 1: Installing system packages ==="
    
    # Update system packages
    if ! dnf update -y 2>/dev/null; then
        echo "Warning: dnf update failed or not available (may already be up to date)"
    fi
    
    # Install required system packages
    local packages=("python3" "python3-pip" "python3-venv" "nginx" "postgresql15" "git" "jq")
    for pkg in "${packages[@]}"; do
        if ! rpm -q "$pkg" &>/dev/null; then
            echo "Installing $pkg..."
            dnf install -y "$pkg" || echo "Warning: Failed to install $pkg (may already be present)"
        else
            echo "$pkg already installed, skipping"
        fi
    done
    
    # Install Node.js 20 if not present
    if ! command -v node &>/dev/null || [[ $(node --version | cut -d'v' -f2 | cut -d'.' -f1) -lt 20 ]]; then
        echo "Installing Node.js 20..."
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
        dnf install -y nodejs || echo "Warning: Node.js installation may have partially completed"
    else
        echo "Node.js $(node --version) already installed, skipping"
    fi
    
    # Verify installations
    echo "Verifying installations:"
    echo "  Python3: $(python3 --version 2>/dev/null || echo 'NOT FOUND')"
    echo "  Nginx: $(nginx -v 2>&1 | head -1 || echo 'NOT FOUND')"
    echo "  PostgreSQL client: $(psql --version 2>/dev/null | head -1 || echo 'NOT FOUND')"
    echo "  Node.js: $(node --version 2>/dev/null || echo 'NOT FOUND')"
    echo "  NPM: $(npm --version 2>/dev/null || echo 'NOT FOUND')"
    echo "Step 1 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Step 2: Create virtual environment (idempotent)
# -----------------------------------------------------------------------------
step2_create_venv() {
    echo "=== Step 2: Creating Python virtual environment ==="
    
    # Ensure app directory exists
    mkdir -p "${APP_DIR}"
    
    # Check if venv already exists
    if [[ -d "$VENV_DIR" ]]; then
        echo "Virtual environment already exists at ${VENV_DIR}, skipping creation"
    else
        echo "Creating virtual environment at ${VENV_DIR}..."
        python3 -m venv "$VENV_DIR"
        echo "Virtual environment created successfully"
    fi
    
    echo "Step 2 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Step 3: Install Python dependencies (idempotent)
# -----------------------------------------------------------------------------
step3_install_python_deps() {
    echo "=== Step 3: Installing Python dependencies ==="
    
    # Check if we're in the right directory
    if [[ ! -f "${APP_DIR}/backend/requirements.txt" ]]; then
        echo "Error: requirements.txt not found at ${APP_DIR}/backend/requirements.txt"
        echo "Please ensure the application code is deployed to ${APP_DIR} first"
        return 1
    fi
    
    # Activate venv and install requirements
    source "${VENV_DIR}/bin/activate"
    
    echo "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    echo "Installing requirements from requirements.txt..."
    pip install -r "${APP_DIR}/backend/requirements.txt"
    
    echo "Installing development requirements (for alembic, etc.)..."
    if [[ -f "${APP_DIR}/backend/requirements-dev.txt" ]]; then
        pip install -r "${APP_DIR}/backend/requirements-dev.txt"
    fi
    
    deactivate
    echo "Step 3 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Step 4: Install Playwright with Chromium (idempotent)
# -----------------------------------------------------------------------------
step4_install_playwright() {
    echo "=== Step 4: Installing Playwright with Chromium ==="
    
    source "${VENV_DIR}/bin/activate"
    
    # Install playwright browser dependencies
    echo "Installing Playwright Chromium browser and dependencies..."
    playwright install chromium --with-deps || {
        echo "Warning: Playwright install with deps failed, trying without system deps..."
        playwright install chromium
    }
    
    # Verify installation
    if python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')" 2>/dev/null; then
        echo "Playwright installation verified"
    else
        echo "Warning: Could not verify Playwright installation"
    fi
    
    deactivate
    echo "Step 4 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Step 5: Run database migrations (idempotent)
# -----------------------------------------------------------------------------
step5_run_migrations() {
    echo "=== Step 5: Running database migrations ==="
    
    # Check if env file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "Warning: Environment file not found at ${ENV_FILE}"
        echo "Database migrations require DATABASE_URL to be set"
        echo "Please create ${ENV_FILE} from the template before running migrations"
        return 1
    fi
    
    # Navigate to backend directory and run migrations
    cd "${APP_DIR}/backend"
    source "${VENV_DIR}/bin/activate"
    
    echo "Running Alembic migrations..."
    alembic upgrade head
    
    deactivate
    cd - > /dev/null
    
    echo "Step 5 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Step 6: Configure Nginx (idempotent)
# -----------------------------------------------------------------------------
step6_configure_nginx() {
    echo "=== Step 6: Configuring Nginx ==="
    
    # Check if nginx config source exists
    if [[ ! -f "$NGINX_CONF_SRC" ]]; then
        echo "Warning: Nginx config source not found at ${NGINX_CONF_SRC}"
        echo "Please ensure the infrastructure files are deployed"
        return 1
    fi
    
    # Copy nginx configuration
    echo "Copying Nginx configuration to ${NGINX_CONF_DST}..."
    cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
    
    # Create www directory for static files
    mkdir -p "$WWW_DIR"
    chown -R "${APP_USER}:${APP_USER}" "$WWW_DIR"
    chmod 755 "$WWW_DIR"
    
    # Test nginx configuration
    echo "Testing Nginx configuration..."
    nginx -t || {
        echo "Error: Nginx configuration test failed"
        return 1
    }
    
    echo "Step 6 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Step 7: Configure Systemd service (idempotent)
# -----------------------------------------------------------------------------
step7_configure_systemd() {
    echo "=== Step 7: Configuring Systemd service ==="
    
    # Check if service file source exists
    if [[ ! -f "$SYSTEMD_SERVICE_SRC" ]]; then
        echo "Warning: Systemd service file source not found at ${SYSTEMD_SERVICE_SRC}"
        echo "Please ensure the infrastructure files are deployed"
        return 1
    fi
    
    # Copy service file
    echo "Copying systemd service file to ${SYSTEMD_SERVICE_DST}..."
    cp "$SYSTEMD_SERVICE_SRC" "$SYSTEMD_SERVICE_DST"
    
    # Reload systemd daemon
    echo "Reloading systemd daemon..."
    systemctl daemon-reload
    
    # Enable service to start on boot
    echo "Enabling ethicalsiteinspector service..."
    systemctl enable ethicalsiteinspector.service
    
    # Start or restart the service
    echo "Starting ethicalsiteinspector service..."
    if systemctl is-active --quiet ethicalsiteinspector.service 2>/dev/null; then
        echo "Service is already running, restarting..."
        systemctl restart ethicalsiteinspector.service
    else
        systemctl start ethicalsiteinspector.service
    fi
    
    # Check service status
    sleep 2
    if systemctl is-active --quiet ethicalsiteinspector.service; then
        echo "Service is running successfully"
    else
        echo "Warning: Service may not have started properly. Check: systemctl status ethicalsiteinspector.service"
    fi
    
    echo "Step 7 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Step 8: Build and deploy frontend (idempotent)
# -----------------------------------------------------------------------------
step8_build_frontend() {
    echo "=== Step 8: Building and deploying frontend ==="
    
    # Check if frontend directory exists
    if [[ ! -d "${APP_DIR}/frontend" ]]; then
        echo "Error: Frontend directory not found at ${APP_DIR}/frontend"
        return 1
    fi
    
    # Navigate to frontend directory
    cd "${APP_DIR}/frontend"
    
    # Install dependencies
    echo "Installing frontend dependencies..."
    npm ci || npm install
    
    # Build the frontend
    echo "Building frontend..."
    npm run build
    
    # Create www directory if it doesn't exist
    mkdir -p "$WWW_DIR"
    
    # Copy build output to www directory
    echo "Copying build output to ${WWW_DIR}..."
    if [[ -d "${APP_DIR}/frontend/dist" ]]; then
        rm -rf "${WWW_DIR}"/*
        cp -r "${APP_DIR}/frontend/dist"/* "$WWW_DIR/"
    else
        echo "Error: Build output not found at ${APP_DIR}/frontend/dist"
        return 1
    fi
    
    # Set correct ownership
    chown -R "${APP_USER}:${APP_USER}" "$WWW_DIR"
    chmod -R 755 "$WWW_DIR"
    
    cd - > /dev/null
    
    # Reload nginx to serve new files
    echo "Reloading Nginx..."
    systemctl reload nginx || systemctl restart nginx
    
    echo "Step 8 complete."
    echo ""
}

# -----------------------------------------------------------------------------
# Main execution
# -----------------------------------------------------------------------------
main() {
    echo "Starting deployment..."
    echo ""
    
    # Run all steps
    step1_install_packages
    step2_create_venv
    step3_install_python_deps
    step4_install_playwright
    step5_run_migrations
    step6_configure_nginx
    step7_configure_systemd
    step8_build_frontend
    
    echo "=== Deployment Complete ==="
    echo "Finished at: $(date)"
    echo ""
    echo "Services status:"
    echo "  Nginx: $(systemctl is-active nginx 2>/dev/null || echo 'unknown')"
    echo "  EthicalSiteInspector: $(systemctl is-active ethicalsiteinspector 2>/dev/null || echo 'unknown')"
    echo ""
    echo "URLs:"
    echo "  - Application: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'your-server-ip')"
    echo "  - API Health: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'your-server-ip')/api/health"
    echo ""
    echo "Logs:"
    echo "  - Deployment: ${LOG_FILE}"
    echo "  - Application: journalctl -u ethicalsiteinspector -f"
    echo "  - Nginx: /var/log/nginx/"
}

# Allow running individual steps
if [[ "${1:-}" == "--step" && -n "${2:-}" ]]; then
    case "$2" in
        1) step1_install_packages ;;
        2) step2_create_venv ;;
        3) step3_install_python_deps ;;
        4) step4_install_playwright ;;
        5) step5_run_migrations ;;
        6) step6_configure_nginx ;;
        7) step7_configure_systemd ;;
        8) step8_build_frontend ;;
        *) echo "Unknown step: $2. Valid steps are 1-8." ;;
    esac
else
    main
fi
