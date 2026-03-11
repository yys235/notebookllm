# ============================================================================
# Team1 Fullstack Application - Makefile
# ============================================================================
# Convenient shortcuts for common deployment operations.
#
# Usage:
#   make help          - Show all available commands
#   make install       - Run installation
#   make deploy        - Deploy application
#   make status        - Show service status
# ============================================================================

.PHONY: help install deploy status logs health backup clean test

# Default target
.DEFAULT_GOAL := help

# Variables
SCRIPTS_DIR := $(CURDIR)/scripts
INSTALL_DIR := /opt/team1
SERVICE_NAME := team1-backend.service

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

##@ Help

help: ## Display this help message
	@echo "$(BLUE)Team1 Fullstack Application - Deployment Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation

install: ## Run full installation (requires sudo)
	sudo $(SCRIPTS_DIR)/install.sh production

install-dev: ## Install for development environment
	sudo $(SCRIPTS_DIR)/install.sh development

##@ Deployment

deploy: ## Deploy application (staging)
	$(SCRIPTS_DIR)/deploy.sh staging

deploy-prod: ## Deploy to production
	$(SCRIPTS_DIR)/deploy.sh production

deploy-dev: ## Deploy to development
	$(SCRIPTS_DIR)/deploy.sh development

rollback: ## Rollback to previous deployment
	$(SCRIPTS_DIR)/deploy.sh rollback

##@ Service Management

start: ## Start all services
	$(SCRIPTS_DIR)/control.sh start

stop: ## Stop all services
	$(SCRIPTS_DIR)/control.sh stop

restart: ## Restart all services
	$(SCRIPTS_DIR)/control.sh restart

status: ## Show service status
	$(SCRIPTS_DIR)/control.sh status

##@ Monitoring

logs: ## Show recent logs (backend)
	$(SCRIPTS_DIR)/control.sh logs backend

logs-nginx: ## Show Nginx logs
	$(SCRIPTS_DIR)/control.sh logs nginx

logs-app: ## Show application logs
	$(SCRIPTS_DIR)/control.sh logs app

logs-follow: ## Follow logs in real-time
	$(SCRIPTS_DIR)/control.sh logs-follow backend

health: ## Check application health
	$(SCRIPTS_DIR)/control.sh health

##@ Database

migrate: ## Run database migrations
	$(SCRIPTS_DIR)/control.sh migrate

migrate-rollback: ## Rollback last migration
	$(SCRIPTS_DIR)/control.sh migrate-rollback 1

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	$(SCRIPTS_DIR)/control.sh migrate-create "$(MSG)"

##@ Backup

backup: ## Create full backup
	$(SCRIPTS_DIR)/backup.sh full

backup-db: ## Backup database only
	$(SCRIPTS_DIR)/backup.sh database

backup-files: ## Backup uploaded files
	$(SCRIPTS_DIR)/backup.sh files

##@ Development

shell: ## Open Python shell with app context
	$(SCRIPTS_DIR)/control.sh shell

test: ## Run backend tests
	cd ../backend && source venv/bin/activate && pytest -v

test-coverage: ## Run tests with coverage
	cd ../backend && source venv/bin/activate && pytest --cov=app --cov-report=html

##@ Maintenance

clean: ## Clean temporary files and cache
	$(SCRIPTS_DIR)/control.sh clean

clean-cache: ## Clean Nginx cache
	sudo rm -rf /var/cache/nginx/team1/*

clean-logs: ## Clean old log files
	sudo find /var/log/team1 -name "*.log.*" -mtime +30 -delete

update: ## Update system packages
	sudo apt update && sudo apt upgrade -y

##@ SSL

ssl-cert: ## Obtain SSL certificate with Let's Encrypt
	sudo certbot --nginx -d $(DOMAIN)

ssl-renew: ## Renew SSL certificates manually
	sudo certbot renew

##@ Utilities

check-config: ## Validate Nginx configuration
	sudo nginx -t

reload-nginx: ## Reload Nginx configuration
	sudo systemctl reload nginx

restart-nginx: ## Restart Nginx
	sudo systemctl restart nginx

##@ Actions

setup-postgres: ## Setup PostgreSQL database and extensions
	@echo "Creating database and user..."
	sudo -u postgres psql -c "CREATE DATABASE team1;" || true
	sudo -u postgres psql -c "CREATE USER team1 WITH PASSWORD 'changeme';" || true
	sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE team1 TO team1;" || true
	sudo -u postgres psql -d team1 -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
	sudo -u postgres psql -d team1 -c "CREATE EXTENSION IF NOT EXISTS \"vector\";"
	@echo "$(GREEN)Database setup complete$(NC)"
	@echo "$(YELLOW)Remember to change the default password!$(NC)"

init-env: ## Initialize environment file
	@if [ ! -f $(INSTALL_DIR)/backend/.env ]; then \
		cp ../backend/.env.example $(INSTALL_DIR)/backend/.env; \
		echo "$(GREEN)Environment file created$(NC)"; \
		echo "$(YELLOW)Please edit $(INSTALL_DIR)/backend/.env with your configuration$(NC)"; \
	else \
		echo "$(YELLOW)Environment file already exists$(NC)"; \
	fi

generate-secret: ## Generate a new SECRET_KEY
	@openssl rand -base64 32

##@ Monitoring

metrics: ## Show current metrics (requires curl)
	@curl -s http://localhost:8000/metrics | head -50

prometheus-restart: ## Restart Prometheus (if installed)
	sudo systemctl restart prometheus

grafana-restart: ## Restart Grafana (if installed)
	sudo systemctl restart grafana-server

##@ Docker (alternative deployment)

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f
