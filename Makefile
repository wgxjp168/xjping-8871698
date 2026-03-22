# ILbuy 我来购平台 - Makefile
# 用法: make <target>

.PHONY: help start stop health e2e test docker-build k8s-deploy clean

help:
	@echo "ILbuy 平台操作命令:"
	@echo "  make start       - 本地进程模式启动所有服务"
	@echo "  make stop        - 停止所有本地服务"
	@echo "  make health      - 检查所有服务健康状态"
	@echo "  make e2e         - 运行 E2E 全链路业务场景测试"
	@echo "  make test        - 运行所有测试（接口+限流+E2E）"
	@echo "  make docker-up   - Docker Compose 启动（需要 Docker）"
	@echo "  make docker-down - Docker Compose 停止"
	@echo "  make k8s-deploy  - 部署到 K8s（需要 kubectl）"
	@echo "  make clean       - 清理本地 SQLite 数据库"

start:
	@bash scripts/start-local.sh

stop:
	@bash scripts/stop-local.sh

health:
	@bash scripts/health-check.sh

e2e:
	@bash scripts/e2e-scenario-test.sh http://localhost:8080

test: e2e
	@echo ""
	@echo "运行接口功能测试..."
	@bash validation/run_api_tests.sh
	@echo ""
	@echo "运行限流性能测试..."
	@python3 validation/run_ratelimit_perf_tests.py

docker-up:
	@docker-compose up -d --build
	@echo "等待服务启动..."
	@sleep 30
	@bash scripts/health-check.sh

docker-down:
	@docker-compose down

k8s-deploy:
	@kubectl apply -f k8s/namespace-and-rbac.yaml
	@kubectl apply -f k8s/configmap-and-secrets.yaml
	@kubectl apply -f k8s/services-deployment.yaml
	@kubectl apply -f k8s/api-gateway-deployment.yaml
	@kubectl apply -f k8s/hpa-and-pdb.yaml
	@echo "部署完成，检查状态..."
	@kubectl get pods -n ilbuy-prod

k8s-status:
	@kubectl get pods,svc,hpa,pdb -n ilbuy-prod

clean:
	@rm -f /tmp/ilbuy_*.db
	@echo "数据库已清理"
