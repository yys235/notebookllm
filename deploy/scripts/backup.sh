#!/bin/bash
# ============================================================================
# Team1 Fullstack Application - Backup Script
# ============================================================================
# This script creates backups of the database and uploaded files.
#
# Usage:
#   ./backup.sh [type]
#
# Arguments:
#   type - Backup type: full|database|files (default: full)
#
# Schedule with cron:
#   0 2 * * * /opt/team1/scripts/backup.sh full
# ============================================================================

set -euo pipefail

# Colors for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly INSTALL_DIR="/opt/team1"
readonly BACKUP_DIR="/var/backups/team1"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)
readonly BACKUP_TYPE="${1:-full}"

# Retention settings
readonly RETENTION_DAYS=30
readonly RETENTION_COUNT=10

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
    echo >&2 -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# ============================================================================
# Utility Functions
# ============================================================================

send_notification() {
    local status="$1"
    local message="$2"

    # Send webhook notification if configured
    if [[ -n "${BACKUP_WEBHOOK_URL:-}" ]]; then
        curl -s -X POST "$BACKUP_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -Iseconds)\"}" \
            >/dev/null 2>&1 || true
    fi
}

ensure_backup_dir() {
    mkdir -p "$BACKUP_DIR"/{database,files,deployments}
}

# ============================================================================
# Database Backup
# ============================================================================

backup_database() {
    log_info "Creating database backup..."

    local backup_file="$BACKUP_DIR/database/team1_${TIMESTAMP}.dump"
    local backup_log="$BACKUP_DIR/database/team1_${TIMESTAMP}.log"

    # Load environment variables
    if [[ -f "$INSTALL_DIR/backend/.env" ]]; then
        source "$INSTALL_DIR/backend/.env"
    else
        log_error "Environment file not found: $INSTALL_DIR/backend/.env"
        return 1
    fi

    # Parse DATABASE_URL
    # Format: postgresql+asyncpg://user:password@host:port/database
    local db_name db_user db_host db_port db_password
    db_url="${DATABASE_URL#postgresql+asyncpg://}"
    db_url="${db_url#postgresql://}"

    db_user=$(echo "$db_url" | cut -d: -f1)
    db_password=$(echo "$db_url" | cut -d: -f2 | cut -d@ -f1)
    db_host_port=$(echo "$db_url" | cut -d@ -f2)
    db_host=$(echo "$db_host_port" | cut -d: -f1)
    db_port=$(echo "$db_host_port" | cut -d: -f2 | cut -d/ -f1)
    db_name=$(echo "$db_host_port" | cut -d/ -f2 | cut -d? -f1)

    # Set PGPASSWORD for pg_dump
    export PGPASSWORD="$db_password"

    # Create database dump
    if pg_dump -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" \
            -F c -f "$backup_file" -f "$backup_log" 2>&1; then
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log_success "Database backup created: $backup_file ($size)"

        # Create checksum
        sha256sum "$backup_file" > "$backup_file.sha256"

        # Cleanup old backups
        cleanup_old_backups "$BACKUP_DIR/database" "$RETENTION_DAYS"

        unset PGPASSWORD
        return 0
    else
        log_error "Database backup failed"
        unset PGPASSWORD
        return 1
    fi
}

# ============================================================================
# Files Backup
# ============================================================================

backup_files() {
    log_info "Creating files backup..."

    local backup_file="$BACKUP_DIR/files/uploads_${TIMESTAMP}.tar.gz"

    # Create compressed archive of uploads directory
    if tar -czf "$backup_file" -C "$INSTALL_DIR" uploads 2>/dev/null; then
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log_success "Files backup created: $backup_file ($size)"

        # Create checksum
        sha256sum "$backup_file" > "$backup_file.sha256"

        # Cleanup old backups
        cleanup_old_backups "$BACKUP_DIR/files" "$RETENTION_DAYS"

        return 0
    else
        log_error "Files backup failed"
        return 1
    fi
}

# ============================================================================
# Full Backup
# ============================================================================

backup_full() {
    log_info "Creating full backup..."

    local backup_dir="$BACKUP_DIR/deployments/full_${TIMESTAMP}"
    mkdir -p "$backup_dir"

    local errors=0

    # Backup database
    if ! backup_database; then
        ((errors++))
    fi

    # Backup files
    if ! backup_files; then
        ((errors++))
    fi

    # Create backup manifest
    cat > "$backup_dir/manifest.json" <<EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date -Iseconds)",
    "type": "full",
    "hostname": "$(hostname)",
    "database": "$BACKUP_DIR/database/team1_${TIMESTAMP}.dump",
    "files": "$BACKUP_DIR/files/uploads_${TIMESTAMP}.tar.gz"
}
EOF

    if [[ $errors -eq 0 ]]; then
        log_success "Full backup completed successfully"
        return 0
    else
        log_error "Full backup completed with $errors errors"
        return 1
    fi
}

# ============================================================================
# Cleanup Functions
# ============================================================================

cleanup_old_backups() {
    local backup_dir="$1"
    local retention_days="$2"

    log_info "Cleaning up old backups in $backup_dir (older than $retention_days days)..."

    # Remove backups older than retention period
    find "$backup_dir" -name "*.dump" -mtime +$retention_days -delete
    find "$backup_dir" -name "*.tar.gz" -mtime +$retention_days -delete
    find "$backup_dir" -name "*.sha256" -mtime +$retention_days -delete

    # Also keep only the last N backups regardless of age
    find "$backup_dir" -name "*.dump" -type f | sort -r | tail -n +$RETENTION_COUNT | xargs -r rm -f
    find "$backup_dir" -name "*.tar.gz" -type f | sort -r | tail -n +$RETENTION_COUNT | xargs -r rm -f
    find "$backup_dir" -name "*.sha256" -type f | sort -r | tail -n +$RETENTION_COUNT | xargs -r rm -f

    log_success "Cleanup completed"
}

# ============================================================================
# Backup Verification
# ============================================================================

verify_backup() {
    local backup_file="$1"

    log_info "Verifying backup: $backup_file"

    # Check if file exists
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    # Verify checksum if exists
    if [[ -f "$backup_file.sha256" ]]; then
        if sha256sum -c "$backup_file.sha256" >/dev/null 2>&1; then
            log_success "Checksum verification passed"
        else
            log_error "Checksum verification failed"
            return 1
        fi
    fi

    # For database dumps, verify it's a valid PostgreSQL custom format
    if [[ "$backup_file" == *.dump ]]; then
        if pg_restore -l "$backup_file" >/dev/null 2>&1; then
            log_success "Database backup is valid"
        else
            log_error "Database backup is invalid"
            return 1
        fi
    fi

    # For file archives, verify tar integrity
    if [[ "$backup_file" == *.tar.gz ]]; then
        if tar -tzf "$backup_file" >/dev/null 2>&1; then
            log_success "File archive is valid"
        else
            log_error "File archive is invalid"
            return 1
        fi
    fi

    return 0
}

# ============================================================================
# Restore Functions
# ============================================================================

restore_database() {
    local backup_file="$1"

    log_info "Restoring database from: $backup_file"

    # Load environment variables
    if [[ -f "$INSTALL_DIR/backend/.env" ]]; then
        source "$INSTALL_DIR/backend/.env"
    else
        log_error "Environment file not found"
        return 1
    fi

    # Parse DATABASE_URL
    local db_url="${DATABASE_URL#postgresql+asyncpg://}"
    db_url="${db_url#postgresql://}"

    local db_user=$(echo "$db_url" | cut -d: -f1)
    local db_password=$(echo "$db_url" | cut -d: -f2 | cut -d@ -f1)
    local db_host_port=$(echo "$db_url" | cut -d@ -f2)
    local db_host=$(echo "$db_host_port" | cut -d: -f1)
    local db_port=$(echo "$db_host_port" | cut -d: -f2 | cut -d/ -f1)
    local db_name=$(echo "$db_host_port" | cut -d/ -f2 | cut -d? -f1)

    export PGPASSWORD="$db_password"

    # Drop existing database and recreate
    psql -h "$db_host" -p "$db_port" -U "$db_user" postgres <<-EOF
        SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db_name' AND pid != pg_backend_pid();
        DROP DATABASE IF EXISTS $db_name;
        CREATE DATABASE $db_name;
EOF

    # Restore database
    if pg_restore -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -j 4 "$backup_file"; then
        log_success "Database restore completed"
        unset PGPASSWORD
        return 0
    else
        log_error "Database restore failed"
        unset PGPASSWORD
        return 1
    fi
}

restore_files() {
    local backup_file="$1"

    log_info "Restoring files from: $backup_file"

    # Stop backend service
    systemctl stop team1-backend.service

    # Remove existing uploads
    rm -rf "$INSTALL_DIR/uploads"

    # Extract backup
    if tar -xzf "$backup_file" -C "$INSTALL_DIR"; then
        log_success "Files restore completed"
    else
        log_error "Files restore failed"
    fi

    # Start backend service
    systemctl start team1-backend.service
}

# ============================================================================
# Main
# ============================================================================

main() {
    local start_time=$(date +%s)
    local exit_code=0

    log_info "Starting backup process..."
    log_info "Backup type: $BACKUP_TYPE"

    ensure_backup_dir

    case "$BACKUP_TYPE" in
        database)
            if ! backup_database; then
                exit_code=1
            fi
            ;;
        files)
            if ! backup_files; then
                exit_code=1
            fi
            ;;
        full)
            if ! backup_full; then
                exit_code=1
            fi
            ;;
        restore)
            if [[ -z "${2:-}" ]]; then
                log_error "Restore requires backup file path"
                exit_code=1
            else
                if [[ "$2" == *.dump ]]; then
                    restore_database "$2"
                elif [[ "$2" == *.tar.gz ]]; then
                    restore_files "$2"
                else
                    log_error "Unknown backup file type"
                    exit_code=1
                fi
            fi
            ;;
        *)
            log_error "Unknown backup type: $BACKUP_TYPE"
            log_info "Valid types: full, database, files, restore"
            exit_code=1
            ;;
    esac

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [[ $exit_code -eq 0 ]]; then
        log_success "Backup completed in ${duration}s"
        send_notification "success" "Backup completed successfully"
    else
        log_error "Backup failed after ${duration}s"
        send_notification "failure" "Backup failed"
    fi

    exit $exit_code
}

# Run main function
main "$@"
