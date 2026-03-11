#!/bin/bash
# ============================================================================
# Team1 Fullstack Application - Bare Metal Deployment Script
# ============================================================================
# This script installs all dependencies and configures the system for
# the Team1 fullstack application.
#
# Usage:
#   sudo ./install.sh [environment]
#
# Arguments:
#   environment - Environment to deploy (production|staging|development)
#                 Default: production
# ============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly ENVIRONMENT="${1:-production}"
readonly DEPLOY_USER="${DEPLOY_USER:-team1}"
readonly DEPLOY_GROUP="${DEPLOY_GROUP:-team1}"
readonly INSTALL_DIR="/opt/team1"
readonly BACKUP_DIR="/var/backups/team1"
readonly LOG_DIR="/var/log/team1"

# ============================================================================
# Logging Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# ============================================================================
# Utility Functions
# ============================================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        log_error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
    log_info "Detected OS: $OS $OS_VERSION"
}

prompt_confirm() {
    local prompt="$1"
    local response

    while true; do
        read -r -p "$prompt [y/N] " response
        case "$response" in
            [yY][eE][sS]|[yY])
                return 0
                ;;
            [nN][oO]|[nN]|"")
                return 1
                ;;
            *)
                echo "Please answer yes or no."
                ;;
        esac
    done
}

# ============================================================================
# System Preparation
# ============================================================================

create_user() {
    log_info "Creating deployment user: $DEPLOY_USER"

    if id "$DEPLOY_USER" &>/dev/null; then
        log_warning "User $DEPLOY_USER already exists"
    else
        useradd -r -m -s /bin/bash -d "$INSTALL_DIR" "$DEPLOY_USER"
        log_success "Created user: $DEPLOY_USER"
    fi
}

create_directories() {
    log_info "Creating directory structure"

    mkdir -p "$INSTALL_DIR"/{backend,frontend,uploads,logs}
    mkdir -p "$BACKUP_DIR"/{database,uploads}
    mkdir -p "$LOG_DIR"
    mkdir -p /etc/team1

    chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$INSTALL_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$BACKUP_DIR"
    chown -R "$DEPLOY_USER:adm" "$LOG_DIR"
    chmod 775 "$LOG_DIR"

    log_success "Directory structure created"
}

# ============================================================================
# PostgreSQL Installation
# ============================================================================

install_postgresql() {
    log_info "Installing PostgreSQL with pgvector extension"

    case "$OS" in
        ubuntu|debian)
            # Install PostgreSQL
            apt-get update -qq
            apt-get install -y postgresql postgresql-contrib python3-psycopg2

            # Install build dependencies for pgvector
            apt-get install -y build-essential git python3-dev libpq-dev

            # Install pgvector extension
            local pg_version
            pg_version=$(psql --version | awk '{print $3}' | awk -F. '{print $1"."$2}')

            if [[ ! -d "/usr/share/postgresql/$pg_version/extension/vector.control" ]]; then
                log_info "Compiling and installing pgvector extension"
                local pgvector_dir="/tmp/pgvector"
                git clone --depth 1 https://github.com/pgvector/pgvector.git "$pgvector_dir"
                cd "$pgvector_dir"
                make
                make install PG_CONFIG="/usr/lib/postgresql/$pg_version/bin/pg_config"
                rm -rf "$pgvector_dir"
                log_success "pgvector extension installed"
            else
                log_info "pgvector extension already installed"
            fi
            ;;
        centos|rhel|rocky|almalinux)
            # Install PostgreSQL
            dnf install -y postgresql-server postgresql-contrib python3-psycopg2
            dnf install -y gcc make git python3-devel postgresql-devel

            # Initialize database if needed
            if [[ ! -d /var/lib/pgsql/data ]]; then
                postgresql-setup --initdb
            fi

            # Install pgvector
            if [[ ! -d "/usr/share/pgsql/extension/vector.control" ]]; then
                log_info "Compiling and installing pgvector extension"
                local pgvector_dir="/tmp/pgvector"
                git clone --depth 1 https://github.com/pgvector/pgvector.git "$pgvector_dir"
                cd "$pgvector_dir"
                make
                make install
                rm -rf "$pgvector_dir"
                log_success "pgvector extension installed"
            fi
            ;;
        *)
            log_error "Unsupported OS for PostgreSQL installation: $OS"
            exit 1
            ;;
    esac

    # Enable and start PostgreSQL
    systemctl enable postgresql
    systemctl start postgresql

    log_success "PostgreSQL installed and started"
}

configure_postgresql() {
    log_info "Configuring PostgreSQL database"

    local db_name="${DB_NAME:-team1}"
    local db_user="${DB_USER:-team1}"
    local db_password="${DB_PASSWORD:-}"

    if [[ -z "$db_password" ]]; then
        log_error "DB_PASSWORD environment variable must be set"
        exit 1
    fi

    # Create database and user
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<-EOF
        -- Create database
        CREATE DATABASE $db_name;

        -- Create user with password
        CREATE USER $db_user WITH PASSWORD '$db_password';

        -- Grant privileges
        GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;

        -- Connect to database and enable extensions
        \c $db_name
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "vector";
        GRANT ALL ON SCHEMA public TO $db_user;
EOF

    log_success "PostgreSQL database configured"
}

# ============================================================================
# Python Backend Setup
# ============================================================================

install_python() {
    log_info "Installing Python dependencies"

    case "$OS" in
        ubuntu|debian)
            apt-get install -y python3 python3-pip python3-venv
            ;;
        centos|rhel|rocky|almalinux)
            dnf install -y python3 python3-pip
            ;;
    esac

    log_success "Python installed"
}

setup_backend() {
    log_info "Setting up backend application"

    # Copy backend files
    cp -r "$PROJECT_ROOT/backend" "$INSTALL_DIR/"

    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/backend/venv"
    source "$INSTALL_DIR/backend/venv/bin/activate"

    # Install dependencies
    pip install --upgrade pip
    pip install -r "$INSTALL_DIR/backend/requirements.txt"

    deactivate

    chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$INSTALL_DIR/backend"

    log_success "Backend configured"
}

# ============================================================================
# Frontend Setup
# ============================================================================

install_nodejs() {
    log_info "Installing Node.js"

    case "$OS" in
        ubuntu|debian)
            # Install Node.js from NodeSource
            if [[ ! -f "/etc/apt/sources.list.d/nodesource.list" ]]; then
                curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
                apt-get install -y nodejs
            else
                apt-get install -y nodejs
            fi
            ;;
        centos|rhel|rocky|almalinux)
            # Install Node.js from NodeSource
            if [[ ! -f "/etc/yum.repos.d/nodesource.repo" ]]; then
                curl -fsSL https://rpm.nodesource.com/setup_22.x | bash -
                dnf install -y nodejs
            else
                dnf install -y nodejs
            fi
            ;;
    esac

    log_success "Node.js $(node --version) and npm $(npm --version) installed"
}

build_frontend() {
    log_info "Building frontend application"

    # Copy frontend files
    cp -r "$PROJECT_ROOT/frontend" "$INSTALL_DIR/"

    cd "$INSTALL_DIR/frontend"

    # Install dependencies and build
    npm ci --production=false
    npm run build

    # Clean up source files, keep only dist
    rm -rf node_modules src tsconfig*.json vite.config.ts
    mv dist "$INSTALL_DIR/frontend/public"
    rm -rf "$INSTALL_DIR/frontend"/*.json "$INSTALL_DIR/frontend"/.*

    chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$INSTALL_DIR/frontend"

    log_success "Frontend built and configured"
}

# ============================================================================
# Nginx Installation
# ============================================================================

install_nginx() {
    log_info "Installing Nginx"

    case "$OS" in
        ubuntu|debian)
            apt-get install -y nginx
            ;;
        centos|rhel|rocky|almalinux)
            dnf install -y nginx
            ;;
    esac

    systemctl enable nginx

    log_success "Nginx installed"
}

configure_nginx() {
    log_info "Configuring Nginx"

    # Copy Nginx configuration
    cp "$SCRIPT_DIR/../config/nginx.conf" /etc/nginx/sites-available/team1
    ln -sf /etc/nginx/sites-available/team1 /etc/nginx/sites-enabled/

    # Test configuration
    nginx -t

    # Reload Nginx
    systemctl reload nginx

    log_success "Nginx configured"
}

# ============================================================================
# Systemd Service Setup
# ============================================================================

install_systemd_service() {
    log_info "Installing systemd service"

    # Copy service file
    cp "$SCRIPT_DIR/../config/team1-backend.service" /etc/systemd/system/

    # Reload systemd
    systemctl daemon-reload

    # Enable service
    systemctl enable team1-backend.service

    log_success "Systemd service installed"
}

# ============================================================================
# Environment Configuration
# ============================================================================

configure_environment() {
    log_info "Configuring environment variables"

    local env_file="$INSTALL_DIR/backend/.env"

    if [[ ! -f "$env_file" ]]; then
        cp "$PROJECT_ROOT/backend/.env.example" "$env_file"

        # Generate secure secret key
        local secret_key
        secret_key=$(openssl rand -base64 32)
        sed -i "s/change-this-secret-key-in-production-min-32-chars/$secret_key/" "$env_file"

        log_warning "Please edit $env_file with your actual configuration values"
        log_info "Especially update: DATABASE_URL, REDIS_URL, AI_API_KEY"
    else
        log_info "Environment file already exists"
    fi

    chown "$DEPLOY_USER:$DEPLOY_GROUP" "$env_file"
    chmod 600 "$env_file"
}

# ============================================================================
# Log Rotation Setup
# ============================================================================

install_logrotate() {
    log_info "Installing logrotate configuration"

    cp "$SCRIPT_DIR/../config/logrotate.conf" /etc/logrotate.d/team1

    log_success "Logrotate configured"
}

# ============================================================================
# Firewall Configuration
# ============================================================================

configure_firewall() {
    log_info "Configuring firewall"

    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian with UFW
        ufw allow 80/tcp
        ufw allow 443/tcp
        log_success "Firewall configured (UFW)"
    elif command -v firewall-cmd &> /dev/null; then
        # RHEL/CentOS with firewalld
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        log_success "Firewall configured (firewalld)"
    else
        log_warning "No firewall detected. Please configure manually."
    fi
}

# ============================================================================
# Installation Summary
# ============================================================================

print_summary() {
    cat <<EOF

${GREEN}=============================================================================
                    Team1 Fullstack Application Installation
                              Installation Complete
=============================================================================${NC}

${BLUE}Installation Directory:${NC}    $INSTALL_DIR
${BLUE}Backend Location:${NC}          $INSTALL_DIR/backend
${BLUE}Frontend Location:${NC}         $INSTALL_DIR/frontend/public
${BLUE}Logs Directory:${NC}            $LOG_DIR
${BLUE}Backup Directory:${NC}          $BACKUP_DIR

${BLUE}Environment:${NC}               $ENVIRONMENT
${BLUE}Deployment User:${NC}           $DEPLOY_USER

${YELLOW}Next Steps:${NC}
  1. Edit environment configuration:
     sudo nano $INSTALL_DIR/backend/.env

  2. Run database migrations:
     sudo -u $DEPLOY_USER $INSTALL_DIR/backend/venv/bin/alembic upgrade head

  3. Start the backend service:
     sudo systemctl start team1-backend.service
     sudo systemctl status team1-backend.service

  4. Check logs:
     sudo journalctl -u team1-backend.service -f
     tail -f $LOG_DIR/backend.log

${YELLOW}Service Management:${NC}
  Start:   sudo systemctl start team1-backend.service
  Stop:    sudo systemctl stop team1-backend.service
  Restart: sudo systemctl restart team1-backend.service
  Status:  sudo systemctl status team1-backend.service

${GREEN}=============================================================================
${NC}
EOF
}

# ============================================================================
# Main Installation Flow
# ============================================================================

main() {
    log_info "Starting Team1 fullstack application installation..."
    log_info "Environment: $ENVIRONMENT"

    check_root
    detect_os

    if ! prompt_confirm "Continue with installation?"; then
        log_info "Installation cancelled"
        exit 0
    fi

    # System preparation
    create_user
    create_directories

    # Database installation
    install_postgresql
    configure_postgresql

    # Application setup
    install_python
    setup_backend

    install_nodejs
    build_frontend

    # Web server
    install_nginx
    configure_nginx

    # Service and monitoring
    install_systemd_service
    install_logrotate

    # Configuration
    configure_environment
    configure_firewall

    print_summary

    log_success "Installation complete!"
}

# Run main function
main "$@"
