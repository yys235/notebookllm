# NotebookLLM 运维手册 (Runbook)

## 1. 概述

本文档包含 NotebookLLM 后端服务的故障处理流程和常见问题解决方案。

**服务信息:**
- 服务名称: Team1 Backend API
- 版本: 0.1.0
- 技术栈: FastAPI + PostgreSQL + Redis + OpenAI/Ollama

**关键端点:**
- 健康检查: `/health`, `/health/ready`, `/health/live`
- Prometheus 指标: `/metrics`
- API 文档: `/docs` (仅开发环境)

---

## 2. 故障响应流程

### 2.1 告警级别定义

| 级别 | 响应时间 | 示例场景 |
|------|----------|----------|
| **P0 - Critical** | 15分钟 | 服务完全不可用、数据库连接失败 |
| **P1 - High** | 1小时 | 核心API故障、AI服务完全不可用 |
| **P2 - Medium** | 4小时 | 高延迟、部分功能异常 |
| **P3 - Low** | 1天 | 性能下降、缓存命中率低 |

### 2.2 故障处理步骤

```
1. [确认] 查看告警详情，评估影响范围
2. [定位] 检查日志和指标，确定根因
3. [止损] 实施临时修复或降级方案
4. [修复] 解决根本问题
5. [验证] 确认服务恢复正常
6. [复盘] 编写 Postmortem，更新 Runbook
```

---

## 3. 常见故障场景

### 3.1 服务不可用 (ServiceDown - P0)

**症状:**
- `/health` 端点返回 502/503
- Prometheus 显示 `up{job="team1-backend"} == 0`

**检查步骤:**
```bash
# 1. 检查服务状态
systemctl status team1-backend
# 或
docker ps | grep team1-backend

# 2. 查看最近的日志
journalctl -u team1-backend -n 100 --no-pager
# 或
docker logs team1-backend --tail 100

# 3. 检查端口占用
netstat -tlnp | grep 8000
```

**可能原因与解决方案:**

| 原因 | 解决方案 |
|------|----------|
| 服务崩溃 | 检查日志中的异常，重启服务 |
| 端口冲突 | 修改配置端口或终止占用进程 |
| 内存溢出 | 增加内存限制或优化内存使用 |
| 依赖服务失败 | 检查数据库/Redis 连接 |

**快速恢复:**
```bash
# 重启服务
systemctl restart team1-backend
# 或
docker-compose restart backend
```

---

### 3.2 高错误率 (HighErrorRate - P0/P1)

**症状:**
- 5xx 错误率 > 20% (Critical) 或 > 5% (Warning)
- 用户报告 API 失败

**检查步骤:**
```bash
# 查看最近的错误日志
grep -i "error\|exception\|critical" /var/log/team1-backend/app.log | tail -50

# 检查 Prometheus 错误率
curl http://prometheus:9090/api/v1/query?query='sum(rate(http_requests_total{status_code=~"5.."}[5m]))/sum(rate(http_requests_total[5m]))'
```

**常见原因:**

| 原因 | 检查 | 解决方案 |
|------|------|----------|
| 数据库连接失败 | 检查 `/health/ready` | 重启数据库，检查连接池配置 |
| Redis 不可用 | `redis-cli ping` | 重启 Redis，启用降级模式 |
| AI 服务超时 | 检查 AI 配置 | 增加超时时间，切换备用提供商 |
| 资源耗尽 | 检查内存/CPU | 扩容或优化资源使用 |
| 代码错误 | 查看堆栈跟踪 | 修复 Bug，部署热修复 |

---

### 3.3 高延迟 (HighLatency - P2)

**症状:**
- P95 延迟 > 5秒 (Critical) 或 > 2秒 (Warning)
- 响应头 `X-Process-Time` 显示高值

**检查步骤:**
```bash
# 检查慢查询日志
grep "Slow request" /var/log/team1-backend/app.log | tail -20

# 分析数据库查询延迟
curl http://prometheus:9090/api/v1/query?query='histogram_quantile(0.95,sum(rate(db_query_duration_seconds_bucket[5m]))by(le,operation))'

# 检查 AI 服务延迟
curl http://prometheus:9090/api/v1/query?query='histogram_quantile(0.95,sum(rate(ai_request_duration_seconds_bucket[5m]))by(le,model))'
```

**优化方案:**

| 组件 | 优化措施 |
|------|----------|
| 数据库 | 添加索引、优化查询、增加连接池 |
| Redis | 使用缓存减少 DB 负载 |
| AI 服务 | 启用流式响应、使用更快的模型 |
| 应用层 | 异步处理、批量操作 |

---

### 3.4 数据库问题 (DatabaseDown - P0)

**症状:**
- `/health/ready` 显示数据库 unhealthy
- 日志显示数据库连接错误

**检查步骤:**
```bash
# 检查 PostgreSQL 状态
systemctl status postgresql

# 测试连接
psql -h localhost -U team1 -d team1 -c "SELECT 1"

# 检查连接数
psql -h localhost -U team1 -d team1 -c "SELECT count(*) FROM pg_stat_activity;"
```

**解决方案:**

| 问题 | 解决方案 |
|------|----------|
| 服务停止 | `systemctl start postgresql` |
| 连接池耗尽 | 增加池大小: `DB_POOL_SIZE=40` |
| 慢查询 | 运行 `EXPLAIN ANALYZE`，添加索引 |
| 磁盘满 | 清理旧数据或扩容 |

---

### 3.5 AI 服务故障 (HighAIFailureRate - P1/P2)

**症状:**
- AI 搜索功能失败
- 告警显示 AI 服务错误率 > 30%

**检查步骤:**
```bash
# 测试 OpenAI API
curl -H "Authorization: Bearer $AI_API_KEY" https://api.openai.com/v1/models

# 检查 Ollama (如果使用)
curl http://localhost:11434/api/tags

# 查看日志中的 AI 错误
grep "ai_service\|openai\|ollama" /var/log/team1-backend/app.log | tail -20
```

**降级方案:**

```python
# 服务代码应包含降级逻辑
try:
    result = await ai_service.search(query)
except AIServiceError:
    # 返回基础搜索结果
    result = await basic_search(query)
    logger.warning("AI service unavailable, using fallback")
```

---

### 3.6 Redis 故障 (RedisDown - P1)

**症状:**
- `/health/ready` 显示 Redis unhealthy
- 缓存操作失败

**检查步骤:**
```bash
# 检查 Redis 状态
systemctl status redis
# 或
docker ps | grep redis

# 测试连接
redis-cli ping

# 检查内存使用
redis-cli INFO memory
```

**解决方案:**

| 问题 | 解决方案 |
|------|----------|
| 服务停止 | `systemctl start redis` |
| 内存满 | 清理过期键或增加 `maxmemory` |
| 连接数满 | 增加 `maxclients` |

---

## 4. 日常运维操作

### 4.1 部署新版本

```bash
# 1. 拉取新代码
git pull origin main

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行数据库迁移
alembic upgrade head

# 4. 重启服务
systemctl restart team1-backend

# 5. 验证健康
curl http://localhost:8000/health/ready
```

### 4.2 数据库备份

```bash
# 每日备份
pg_dump -h localhost -U team1 team1 | gzip > backup_$(date +%Y%m%d).sql.gz

# 恢复
gunzip < backup_20260302.sql.gz | psql -h localhost -U team1 team1
```

### 4.3 日志轮转

配置 `/etc/logrotate.d/team1-backend`:
```
/var/log/team1-backend/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 team1-backend team1-backend
    sharedscripts
    postrotate
        systemctl reload team1-backend >/dev/null 2>&1 || true
    endscript
}
```

---

## 5. 性能基准

### 5.1 目标指标

| 指标 | 目标 |
|------|------|
| P50 延迟 | < 100ms |
| P95 延迟 | < 500ms |
| P99 延迟 | < 2000ms |
| 错误率 | < 0.1% |
| QPS | > 100 (单实例) |

### 5.2 压力测试

```bash
# 使用 wrk 进行负载测试
wrk -t4 -c100 -d30s --latency http://localhost:8000/api/v1/notes

# 使用 locust
locust -f locustfile.py --host=http://localhost:8000
```

---

## 6. 联系信息

| 角色 | 联系方式 | 负责范围 |
|------|----------|----------|
| On-call 工程师 | oncall@team1.com | 24/7 响应 |
| 技术负责人 | tech-lead@team1.com | 技术决策 |
| DevOps 工程师 | devops@team1.com | 基础设施 |
| 安全团队 | security@team1.com | 安全事件 |

---

## 7. 变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-03-02 | 1.0 | 初始版本 | SRE Team |
