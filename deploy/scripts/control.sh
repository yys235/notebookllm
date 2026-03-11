#!/bin/bash
# ============================================================================
# Team1 Fullstack Application - Service Control Script
# ============================================================================
# This script provides convenient commands for managing the application.
#
# Usage:
#   ./control.sh [command] [options]
#
# Commands:
#   start       - Start all services
#   stop        - Stop all services
#   restart     - Restart all services
#   status      - Show service status
#   logs        - Show service logs
#   health      - Check application health
#   migrate     - Run database migrations
#   shell       - Open Python shell with app context
#   clean       - Clean temporary files and logs
# ============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly INSTALL_DIR="/opt/team1"
readonly LOG_DIR="/var/log/team1"
readonly SERVICE_NAME="team1-backend.service"

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
# Service Management
# ============================================================================

start_services() {
    log_info "Starting Team1 services..."

    systemctl start "$SERVICE_NAME"

    # Wait for service to be active
    local count=0
    while [[ $count -lt 30 ]]; do
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_success "Services started successfully"
            return 0
        fi
        sleep 1
        ((count++))
    done

    log_error "Failed to start services"
    return 1
}

stop_services() {
    log_info "Stopping Team1 services..."

    systemctl stop "$SERVICE_NAME"

    # Wait for service to stop
    local count=0
    while [[ $count -lt 30 ]]; do
        if ! systemctl is-active --quiet "$SERVICE_NAME"; then
            log_success "Services stopped successfully"
            return 0
        fi
        sleep 1
        ((count++))
    done

    log_warning "Services did not stop gracefully"
    return 1
}

restart_services() {
    log_info "Restarting Team1 services..."

    systemctl restart "$SERVICE_NAME"

    # Wait for service to be active
    local count=0
    while [[ $count -lt 30 ]]; do
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_success "Services restarted successfully"
            return 0
        fi
        sleep 1
        ((count++))
    done

    log_error "Failed to restart services"
    return 1
}

show_status() {
    echo ""
    log_info "Team1 Application Status"
    echo "================================"

    # Backend service status
    echo ""
    echo "Backend Service:"
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "  Status: ${GREEN}Running${NC}"
    else
        echo -e "  Status: ${RED}Stopped${NC}"
    fi
    echo "  Enabled: $(systemctl is-enabled "$SERVICE_NAME" || echo "disabled")"

    # Show PID and memory if running
    local pid
    pid=$(systemctl show -p MainPID --value "$SERVICE_NAME")
    if [[ -n "$pid" ]] && [[ "$pid" != "0" ]]; then
        echo "  PID: $pid"
        local mem
        mem=$(ps -o rss= -p "$pid" | awk '{printf "%.2f MB", $1/1024}')
        echo "  Memory: $mem"
    fi

    # Nginx status
    echo ""
    echo "Nginx Service:"
    if systemctl is-active --quiet nginx; then
        echo -e "  Status: ${GREEN}Running${NC}"
    else
        echo -e "  Status: ${RED}Stopped${NC}"
    fi

    # PostgreSQL status
    echo ""
    echo "PostgreSQL Service:"
    if systemctl is-active --quiet postgresql; then
        echo -e "  Status: ${GREEN}Running${NC}"
    elif systemctl is-active --quiet "postgresql@*"; then
        echo -e "  Status: ${GREEN}Running${NC}"
    else
        echo -e "  Status: ${RED}Stopped${NC}"
    fi

    # Redis status
    echo ""
    echo "Redis Service:"
    if systemctl is-active --quiet redis-server; then
        echo -e "  Status: ${GREEN}Running${NC}"
    elif systemctl is-active --quiet redis; then
        echo -e "  Status: ${GREEN}Running${NC}"
    else
        echo -e "  Status: ${YELLOW}Not Running${NC}"
    fi

    # Health check
    echo ""
    if check_health silent; then
        echo -e "Health Check: ${GREEN}Healthy${NC}"
    else
        echo -e "Health Check: ${RED}Unhealthy${NC}"
    fi

    echo ""
    echo "================================"
}

# ============================================================================
# Logs Management
# ============================================================================

show_logs() {
    local service="${1:-backend}"
    local lines="${2:-50}"
    local follow="${3:-false}"

    case "$service" in
        backend)
            if [[ "$follow" == "true" ]]; then
                journalctl -u "$SERVICE_NAME" -f
            else
                journalctl -u "$SERVICE_NAME" -n "$lines" --no-pager
            fi
            ;;
        nginx)
            if [[ "$follow" == "true" ]]; then
                tail -f /var/log/nginx/access.log /var/log/nginx/error.log
            else
                tail -n "$lines" /var/log/nginx/access.log /var/log/nginx/error.log
            fi
            ;;
        app)
            if [[ -f "$LOG_DIR/backend.log" ]]; then
                if [[ "$follow" == "true" ]]; then
                    tail -f "$LOG_DIR/backend.log"
                else
                    tail -n "$lines" "$LOG_DIR/backend.log"
                fi
            else
                log_warning "Application log not found: $LOG_DIR/backend.log"
            fi
            ;;
        all)
            echo "=== Backend Service Logs ==="
            journalctl -u "$SERVICE_NAME" -n "$lines" --no-pager
            echo ""
            echo "=== Nginx Access Logs ==="
            tail -n "$lines" /var/log/nginx/access.log
            echo ""
            echo "=== Nginx Error Logs ==="
            tail -n "$lines" /var/log/nginx/error.log
            ;;
        *)
            log_error "Unknown log source: $service"
            echo "Valid sources: backend, nginx, app, all"
            exit 1
            ;;
    esac
}

# ============================================================================
# Health Check
# ============================================================================

check_health() {
    local silent="${1:-false}"
    local healthy=true

    if [[ "$silent" != "true" ]]; then
        log_info "Checking application health..."
    fi

    # Check backend service
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        if [[ "$silent" != "true" ]]; then
            log_error "Backend service is not running"
        fi
        healthy=false
    fi

    # Check HTTP endpoint
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        if [[ "$silent" != "true" ]]; then
            log_success "Backend HTTP endpoint is responding"
        fi
    else
        if [[ "$silent" != "true" ]]; then
            log_error "Backend HTTP endpoint is not responding"
        fi
        healthy=false
    fi

    # Check Nginx
    if systemctl is-active --quiet nginx; then
        if [[ "$silent" != "true" ]]; then
            log_success "Nginx is running"
        fi
    else
        if [[ "$silent" != "true" ]]; then
            log_warning "Nginx is not running"
        fi
        healthy=false
    fi

    if [[ "$silent" != "true" ]]; then
        if [[ "$healthy" == "true" ]]; then
            log_success "All health checks passed"
        else
            log_error "Some health checks failed"
        fi
    fi

    [[ "$healthy" == "true" ]]
}

# ============================================================================
# Database Operations
# ============================================================================

run_migrations() {
    log_info "Running database migrations..."

    source "$INSTALL_DIR/backend/venv/bin/activate"
    cd "$INSTALL_DIR/backend"

    if alembic upgrade head; then
        log_success "Migrations completed successfully"
    else
        log_error "Migration failed"
        return 1
    fi

    deactivate
}

rollback_migration() {
    local steps="${1:-1}"

    log_info "Rolling back $steps migration(s)..."

    source "$INSTALL_DIR/backend/venv/bin/activate"
    cd "$INSTALL_DIR/backend"

    if alembic downgrade "-$steps"; then
        log_success "Rollback completed successfully"
    else
        log_error "Rollback failed"
        return 1
    fi

    deactivate
}

create_migration() {
    local message="${1:-migration}"

    log_info "Creating new migration: $message"

    source "$INSTALL_DIR/backend/venv/bin/activate"
    cd "$INSTALL_DIR/backend"

    if alembic revision -m "$message"; then
        log_success "Migration created successfully"
    else
        log_error "Migration creation failed"
        return 1
    fi

    deactivate
}

# ============================================================================
# Shell Access
# ============================================================================

open_shell() {
    log_info "Opening Python shell with application context..."

    source "$INSTALL_DIR/backend/venv/bin/activate"
    cd "$INSTALL_DIR/backend"

    cat <<'EOF' | python
import sys
sys.path.insert(0, '/opt/team1/backend')

from app.core.database import async_session
from app.models import *

print("Team1 Application Shell")
print("========================")
print("\nAvailable models:")
import app.models
models = [name for name in dir(app.models) if name[0].isupper()]
print(", ".join(models))

print("\nDatabase session: async_session")
print("\nExample usage:")
print("  import asyncio")
print("  async def get_notes():")
print("      async with async_session() as session:")
print("          result = await session.execute(select(Note))")
print("          return result.scalars().all()")

import asyncio
EOF

    deactivate
}

# ============================================================================
# Cleanup Operations
# ============================================================================

clean_temp() {
    log_info "Cleaning temporary files..."

    # Clean Python cache
    find "$INSTALL_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$INSTALL_DIR/backend" -type f -name "*.pyc" -delete 2>/dev/null || true

    # Clean old logs
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true

    # Clean pytest cache
    rm -rf "$INSTALL_DIR/backend/.pytest_cache" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/backend/.ruff_cache" 2>/dev/null || true

    log_success "Cleanup completed"
}

# ============================================================================
# Help
# ============================================================================

show_help() {
    cat <<EOF
Team1 Application Control Script

Usage: ./control.sh [command] [options]

Commands:
  start               Start all services
  stop                Stop all services
  restart             Restart all services
  status              Show service status
  health              Check application health

  logs [source] [n]   Show logs
                      source: backend|nginx|app|all (default: backend)
                      n: number of lines (default: 50)
  logs-follow [src]   Follow logs in real-time

  migrate             Run database migrations
  migrate-rollback [n] Rollback n migrations (default: 1)
  migrate-create [msg] Create new migration

  shell               Open Python shell with app context

  clean               Clean temporary files and cache

  help                Show this help message

Examples:
  ./control.sh start
  ./control.sh logs backend 100
  ./control.sh logs-follow app
  ./control.sh migrate-create add_user_settings
  ./control.sh health

Service Locations:
  Backend:  $INSTALL_DIR/backend
  Logs:     $LOG_DIR
  Config:   $INSTALL_DIR/backend/.env

EOF
}

# ============================================================================
# Main
# ============================================================================

main() {
    local command="${1:-help}"
    shift || true

    case "$command" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        health)
            check_health
            ;;
        logs)
            show_logs "${1:-backend}" "${2:-50}"
            ;;
        logs-follow)
            show_logs "${1:-backend}" 50 true
            ;;
        migrate)
            run_migrations
            ;;
        migrate-rollback)
            rollback_migration "${1:-1}"
            ;;
        migrate-create)
            create_migration "${1:-migration}"
            ;;
        shell)
            open_shell
            ;;
        clean)
            clean_temp
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
