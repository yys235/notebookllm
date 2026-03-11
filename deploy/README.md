# Team1 Fullstack Application - Deployment Guide

This guide covers the deployment of the Team1 fullstack application on bare metal servers.

## Table of Contents

- [Overview](#overview)
- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Service Management](#service-management)
- [Monitoring](#monitoring)
- [Backup and Restore](#backup-and-restore)
- [Troubleshooting](#troubleshooting)

---

## Overview

The application consists of:

- **Backend**: FastAPI application with PostgreSQL database and Redis cache
- **Frontend**: Vue.js SPA built with Vite
- **Web Server**: Nginx as reverse proxy and static file server
- **Services**: Systemd-managed services for auto-restart

---

## System Requirements

### Minimum Requirements

- **OS**: Ubuntu 20.04+ / Debian 11+ / RHEL 8+
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 20 GB

### Recommended Requirements

- **OS**: Ubuntu 22.04 LTS
- **CPU**: 4+ cores
- **RAM**: 8 GB
- **Storage**: 50 GB SSD

### Software Dependencies

- PostgreSQL 14+ with pgvector extension
- Python 3.10+
- Node.js 22+
- Nginx 1.18+
- Redis 6+

---

## Quick Start

### Automated Installation

```bash
# Clone the repository
git clone https://github.com/team1/fullstack-team1.git
cd fullstack-team1

# Run the installation script
sudo ./deploy/scripts/install.sh production
```

### Manual Installation

See the [Installation](#installation) section for detailed steps.

---

## Installation

### Step 1: System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install basic dependencies
sudo apt install -y curl wget git build-essential
```

### Step 2: PostgreSQL with pgvector

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install build dependencies
sudo apt install -y build-essential git python3-dev libpq-dev

# Clone and compile pgvector
cd /tmp
git clone --depth 1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 3: Create Database

```bash
# Create database and user
sudo -u postgres psql
```

```sql
-- In PostgreSQL prompt
CREATE DATABASE team1;
CREATE USER team1 WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE team1 TO team1;
\c team1
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
GRANT ALL ON SCHEMA public TO team1;
\q
```

### Step 4: Backend Installation

```bash
# Create application directory
sudo mkdir -p /opt/team1
sudo useradd -r -m -s /bin/bash -d /opt/team1 team1

# Copy backend files
sudo cp -r backend /opt/team1/

# Create virtual environment
python3 -m venv /opt/team1/backend/venv
source /opt/team1/backend/venv/bin/activate
pip install --upgrade pip
pip install -r /opt/team1/backend/requirements.txt
deactivate

# Set permissions
sudo chown -R team1:team1 /opt/team1
```

### Step 5: Frontend Build

```bash
# Install Node.js (if not installed)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Copy and build frontend
sudo cp -r frontend /opt/team1/
cd /opt/team1/frontend
npm ci
npm run build

# Deploy built files
sudo rm -rf /opt/team1/frontend/src
sudo mv dist /opt/team1/frontend/public
sudo chown -R team1:team1 /opt/team1/frontend
```

### Step 6: Configuration

```bash
# Create environment file
sudo cp /opt/team1/backend/.env.example /opt/team1/backend/.env
sudo nano /opt/team1/backend/.env

# Edit the following variables:
# - DATABASE_URL
# - SECRET_KEY
# - REDIS_URL
# - AI_API_KEY
```

### Step 7: Systemd Service

```bash
# Install service file
sudo cp deploy/config/team1-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable team1-backend.service
```

### Step 8: Nginx Configuration

```bash
# Install Nginx
sudo apt install -y nginx

# Copy configuration
sudo cp deploy/config/nginx.conf /etc/nginx/sites-available/team1
sudo ln -s /etc/nginx/sites-available/team1 /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 9: Database Migration

```bash
# Run migrations
sudo -u team1 /opt/team1/backend/venv/bin/alembic upgrade head
```

### Step 10: Start Services

```bash
# Start backend service
sudo systemctl start team1-backend.service

# Check status
sudo systemctl status team1-backend.service
```

---

## Configuration

### Environment Variables

Key variables in `/opt/team1/backend/.env`:

```bash
# Application
APP_NAME="Team1 Backend API"
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database
DATABASE_URL=postgresql+asyncpg://team1:password@localhost:5432/team1

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=generate-with-openssl-rand-base64-32
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Services
AI_SERVICE_URL=https://api.openai.com/v1
AI_API_KEY=your-api-key-here
```

### Nginx Configuration

Edit `/etc/nginx/sites-available/team1`:

- Update `server_name` with your domain
- Configure SSL certificates (see HTTPS setup)
- Adjust rate limits as needed

---

## Service Management

### Using the control script

```bash
# Show status
./deploy/scripts/control.sh status

# Start/stop/restart
./deploy/scripts/control.sh start
./deploy/scripts/control.sh stop
./deploy/scripts/control.sh restart

# View logs
./deploy/scripts/control.sh logs
./deploy/scripts/control.sh logs-follow

# Health check
./deploy/scripts/control.sh health
```

### Using systemctl directly

```bash
# Start service
sudo systemctl start team1-backend.service

# Stop service
sudo systemctl stop team1-backend.service

# Restart service
sudo systemctl restart team1-backend.service

# View status
sudo systemctl status team1-backend.service

# View logs
sudo journalctl -u team1-backend.service -f
```

---

## Monitoring

### Application Logs

```bash
# Systemd journal
sudo journalctl -u team1-backend.service -f

# Application logs
tail -f /var/log/team1/backend.log

# Nginx logs
tail -f /var/log/nginx/team1-access.log
tail -f /var/log/nginx/team1-error.log
```

### Health Endpoints

- `http://your-server/health` - Application health
- `http://your-server/metrics` - Prometheus metrics

### Monitoring with Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'team1-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

## Backup and Restore

### Automated Backups

Set up cron job:

```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/team1/deploy/scripts/backup.sh full
```

### Manual Backup

```bash
# Full backup
./deploy/scripts/backup.sh full

# Database only
./deploy/scripts/backup.sh database

# Files only
./deploy/scripts/backup.sh files
```

### Restore

```bash
# Restore database
./deploy/scripts/backup.sh restore /var/backups/team1/database/team1_20240101.dump

# Restore files
./deploy/scripts/backup.sh restore /var/backups/team1/files/uploads_20240101.tar.gz
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check journal for errors
sudo journalctl -u team1-backend.service -n 100

# Check configuration
sudo -u team1 /opt/team1/backend/venv/bin/python -c "from main import app; print('OK')"

# Check port availability
sudo ss -tlnp | grep 8000
```

### Database Connection Issues

```bash
# Test connection
psql -h localhost -U team1 -d team1

# Check PostgreSQL status
sudo systemctl status postgresql

# Check pg_hba.conf for authentication settings
sudo cat /etc/postgresql/*/main/pg_hba.conf
```

### Nginx Issues

```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Reload after changes
sudo systemctl reload nginx
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R team1:team1 /opt/team1
sudo chown -R team1:adm /var/log/team1

# Fix permissions
sudo chmod 755 /opt/team1/backend
sudo chmod 600 /opt/team1/backend/.env
```

---

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Set strong database password
- [ ] Configure HTTPS with SSL certificates
- [ ] Set up firewall rules
- [ ] Disable debug mode in production
- [ ] Configure CORS properly
- [ ] Set up log rotation
- [ ] Configure automated backups
- [ ] Monitor system logs
- [ ] Keep system packages updated

---

## SSL/TLS Configuration

### Using Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

### Manual Certificate

Update Nginx configuration:

```nginx
listen 443 ssl http2;
ssl_certificate /path/to/certificate.crt;
ssl_certificate_key /path/to/private.key;
ssl_protocols TLSv1.2 TLSv1.3;
```

---

## Performance Tuning

### PostgreSQL

Edit `/etc/postgresql/*/main/postgresql.conf`:

```ini
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 16MB

# Connection settings
max_connections = 100
```

### Nginx

Edit `/etc/nginx/nginx.conf`:

```ini
worker_processes auto;
worker_connections 2048;
keepalive_timeout 65;
```

### FastAPI

Adjust workers in systemd service:

```ini
ExecStart=... uvicorn ... --workers 4
```

Use formula: `workers = (2 x CPU cores) + 1`

---

## Support

For issues and questions:

- GitHub Issues: https://github.com/team1/fullstack-team1/issues
- Documentation: https://docs.team1.example.com
- Email: ops@team1.example.com
