#!/bin/bash
# ============================================================================
# Team1 Fullstack Application - Deployment Script
# ============================================================================
# This script handles deployment of the application including building,
# migrating database, and restarting services.
#
# Usage:
#   ./deploy.sh [environment]
#
# Arguments:
#   environment - Environment to deploy (production|staging|development)
#                 Default: staging
# ============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly ENVIRONMENT="${1:-staging}"
readonly INSTALL_DIR="/opt/team1"
readonly BACKUP_DIR="/var/backups/team1"
readonly LOG_DIR="/var/log/team1"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Service names
readonly BACKEND_SERVICE="team1-backend.service"

# ============================================================================
# Logging Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# ============================================================================
# Pre-deployment Checks
# ============================================================================

check_prerequisites() {
    log_info "Checking deployment prerequisites..."

    local errors=0

    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        log_warning "Not running as root. Some operations may fail."
    fi

    # Check if project directory exists
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log_error "Project root not found: $PROJECT_ROOT"
        ((errors++))
    fi

    # Check if backend directory exists
    if [[ ! -d "$PROJECT_ROOT/backend" ]]; then
        log_error "Backend directory not found"
        ((errors++))
    fi

    # Check if frontend directory exists
    if [[ ! -d "$PROJECT_ROOT/frontend" ]]; then
        log_error "Frontend directory not found"
        ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        log_error "Prerequisites check failed with $errors errors"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

check_running_processes() {
    log_info "Checking running processes..."

    if systemctl is-active --quiet "$BACKEND_SERVICE"; then
        log_info "Backend service is running"
        return 0
    else
        log_warning "Backend service is not running"
        return 1
    fi
}

# ============================================================================
# Backup Functions
# ============================================================================

create_backup() {
    log_info "Creating backup..."

    local backup_path="$BACKUP_DIR/deployments/$TIMESTAMP"
    mkdir -p "$backup_path"

    # Backup current installation
    if [[ -d "$INSTALL_DIR/backend" ]]; then
        tar -czf "$backup_path/backend.tar.gz" -C "$INSTALL_DIR" backend 2>/dev/null || true
        log_info "Backend backed up"
    fi

    if [[ -d "$INSTALL_DIR/frontend" ]]; then
        tar -czf "$backup_path/frontend.tar.gz" -C "$INSTALL_DIR" frontend 2>/dev/null || true
        log_info "Frontend backed up"
    fi

    # Backup database if configured
    if [[ -n "${DB_BACKUP:-}" ]] && [[ "$DB_BACKUP" == "true" ]]; then
        backup_database "$backup_path"
    fi

    log_success "Backup created at $backup_path"

    # Keep only last 10 backups
    find "$BACKUP_DIR/deployments" -mindepth 1 -maxdepth 1 -type d | sort -r | tail -n +11 | xargs rm -rf
}

backup_database() {
    local backup_path="$1"

    log_info "Backing up database..."

    # Source environment variables
    if [[ -f "$INSTALL_DIR/backend/.env" ]]; then
        source "$INSTALL_DIR/backend/.env"
    fi

    # Extract database connection from DATABASE_URL
    local db_name db_user db_host db_port
    db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    db_user=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    if pg_isready -h "$db_host" -p "$db_port" -U "$db_user" &>/dev/null; then
        pg_dump -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -F c -f "$backup_path/database.dump"
        log_success "Database backup created"
    else
        log_warning "Database is not accessible, skipping backup"
    fi
}

# ============================================================================
# Deployment Functions
# ============================================================================

deploy_backend() {
    log_info "Deploying backend application..."

    # Stop service
    if systemctl is-active --quiet "$BACKEND_SERVICE"; then
        systemctl stop "$BACKEND_SERVICE"
        log_info "Backend service stopped"
    fi

    # Copy new code
    rsync -av --delete \
        --exclude='venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache/' \
        --exclude='*.log' \
        --exclude='.env' \
        "$PROJECT_ROOT/backend/" "$INSTALL_DIR/backend/"

    # Activate virtual environment and update dependencies
    if [[ ! -d "$INSTALL_DIR/backend/venv" ]]; then
        python3 -m venv "$INSTALL_DIR/backend/venv"
    fi

    source "$INSTALL_DIR/backend/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$INSTALL_DIR/backend/requirements.txt"
    deactivate

    # Ensure correct permissions
    chown -R team1:team1 "$INSTALL_DIR/backend"

    log_success "Backend deployed"
}

deploy_frontend() {
    log_info "Building and deploying frontend application..."

    local temp_build_dir="/tmp/team1-frontend-build-$TIMESTAMP"

    # Copy frontend to temp directory
    cp -r "$PROJECT_ROOT/frontend" "$temp_build_dir"

    # Install dependencies and build
    cd "$temp_build_dir"
    npm ci
    npm run build

    # Deploy built files
    rm -rf "$INSTALL_DIR/frontend/public"
    mkdir -p "$INSTALL_DIR/frontend/public"
    cp -r dist/* "$INSTALL_DIR/frontend/public/"

    # Cleanup
    rm -rf "$temp_build_dir"

    # Ensure correct permissions
    chown -R team1:team1 "$INSTALL_DIR/frontend"

    log_success "Frontend deployed"
}

run_migrations() {
    log_info "Running database migrations..."

    source "$INSTALL_DIR/backend/venv/bin/activate"
    cd "$INSTALL_DIR/backend"

    # Run Alembic migrations
    alembic upgrade head

    deactivate

    log_success "Database migrations completed"
}

# ============================================================================
# Health Check Functions
# ============================================================================

health_check() {
    local max_attempts=30
    local attempt=1
    local wait_time=2

    log_info "Performing health check..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log_success "Health check passed"
            return 0
        fi

        log_info "Health check attempt $attempt/$max_attempts failed, retrying in ${wait_time}s..."
        sleep $wait_time
        ((attempt++))
    done

    log_error "Health check failed after $max_attempts attempts"

    # Rollback on failure
    if [[ "${ROLLBACK_ON_FAILURE:-true}" == "true" ]]; then
        log_warning "Initiating rollback..."
        rollback
    fi

    return 1
}

# ============================================================================
# Rollback Functions
# ============================================================================

rollback() {
    local backup_path="${1:-$BACKUP_DIR/deployments/$(ls -t "$BACKUP_DIR/deployments" | head -1)}"

    if [[ -z "$backup_path" ]] || [[ ! -d "$backup_path" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi

    log_warning "Rolling back to backup: $backup_path"

    # Stop service
    systemctl stop "$BACKEND_SERVICE"

    # Restore backend
    if [[ -f "$backup_path/backend.tar.gz" ]]; then
        rm -rf "$INSTALL_DIR/backend"
        tar -xzf "$backup_path/backend.tar.gz" -C "$INSTALL_DIR"
        log_info "Backend restored"
    fi

    # Restore frontend
    if [[ -f "$backup_path/frontend.tar.gz" ]]; then
        rm -rf "$INSTALL_DIR/frontend"
        tar -xzf "$backup_path/frontend.tar.gz" -C "$INSTALL_DIR"
        log_info "Frontend restored"
    fi

    # Start service
    systemctl start "$BACKEND_SERVICE"

    log_success "Rollback completed"
}

# ============================================================================
# Service Management
# ============================================================================

start_services() {
    log_info "Starting services..."

    systemctl start "$BACKEND_SERVICE"

    # Wait for service to be active
    local count=0
    while [[ $count -lt 30 ]]; do
        if systemctl is-active --quiet "$BACKEND_SERVICE"; then
            log_success "Backend service started"
            return 0
        fi
        sleep 1
        ((count++))
    done

    log_error "Failed to start backend service"
    return 1
}

restart_services() {
    log_info "Restarting services..."

    systemctl restart "$BACKEND_SERVICE"

    # Wait for service to be active
    local count=0
    while [[ $count -lt 30 ]]; do
        if systemctl is-active --quiet "$BACKEND_SERVICE"; then
            log_success "Backend service restarted"
            return 0
        fi
        sleep 1
        ((count++))
    done

    log_error "Failed to restart backend service"
    return 1
}

# ============================================================================
# Post-deployment Tasks
# ============================================================================

post_deploy_tasks() {
    log_info "Running post-deployment tasks..."

    # Clean old log files
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true

    # Clean old backups
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true

    # Rotate application logs
    if command -v logrotate &>/dev/null; then
        logrotate -f /etc/logrotate.d/team1
    fi

    log_success "Post-deployment tasks completed"
}

# ============================================================================
# Deployment Summary
# ============================================================================

print_summary() {
    local duration=$1
    local status=$2

    cat <<EOF

${BLUE}=============================================================================
                        Team1 Deployment Summary
=============================================================================${NC}

${BLUE}Environment:${NC}       $ENVIRONMENT
${BLUE}Deployment Time:${NC}   $duration seconds
${BLUE}Status:${NC}            $status
${BLUE}Timestamp:${NC}         $TIMESTAMP

${BLUE}Service Status:${NC}
    Backend:     $(systemctl is-active "$BACKEND_SERVICE" || echo "inactive")
    Nginx:       $(systemctl is-active nginx || echo "inactive")

${BLUE}Recent Logs:${NC}
    Backend:     journalctl -u "$BACKEND_SERVICE" -n 50
    Application: tail -f $LOG_DIR/backend.log

${BLUE}Management:${NC}
    Restart:     sudo systemctl restart "$BACKEND_SERVICE"
    Stop:        sudo systemctl stop "$BACKEND_SERVICE"
    Status:      sudo systemctl status "$BACKEND_SERVICE"

${GREEN}=============================================================================
${NC}
EOF
}

# ============================================================================
# Signal Handlers
# ============================================================================

trap cleanup EXIT INT TERM

cleanup() {
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log_error "Deployment failed with exit code $exit_code"

        if [[ "${ROLLBACK_ON_FAILURE:-true}" == "true" ]]; then
            rollback
        fi
    fi

    exit $exit_code
}

# ============================================================================
# Main Deployment Flow
# ============================================================================

main() {
    local start_time=$(date +%s)

    log_info "Starting Team1 application deployment..."
    log_info "Environment: $ENVIRONMENT"

    # Pre-deployment
    check_prerequisites
    check_running_processes || true
    create_backup

    # Deployment
    deploy_backend
    deploy_frontend
    run_migrations

    # Start services
    start_services

    # Health check
    if ! health_check; then
        log_error "Deployment failed health check"
        exit 1
    fi

    # Post-deployment
    post_deploy_tasks

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    print_summary "$duration" "SUCCESS"

    log_success "Deployment completed successfully!"
}

# Allow rollback command
if [[ "${1:-}" == "rollback" ]]; then
    rollback "${2:-}"
    exit 0
fi

# Run main function
main "$@"
