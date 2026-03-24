#!/bin/bash
# 惠东县区域公卫体检集中系统 - K8s 一键部署脚本
# 用法: chmod +x k8s/deploy-all.sh && ./k8s/deploy-all.sh [dev|prod]

set -e
ENV=${1:-prod}
echo "======================================================"
echo " K8s 部署: 惠东县区域公卫体检集中系统 (env=$ENV)"
echo "======================================================"

cd "$(dirname "$0")"

echo "[1/7] 创建命名空间..."
kubectl apply -f namespace/namespace.yaml

echo "[2/7] 应用 ConfigMap (env=$ENV)..."
kubectl apply -f configmap/configmap.yaml

echo "[3/7] 应用 Secret（确保已替换真实密码）..."
echo "  ⚠️  请确保 secret/secret.yaml 中的密码已修改为生产值！"
kubectl apply -f secret/secret.yaml

echo "[4/7] 部署基础设施（MySQL / Redis）..."
kubectl apply -f mysql/statefulset.yaml
kubectl apply -f redis/statefulset.yaml
echo "  等待MySQL就绪..."
kubectl rollout status statefulset/physical-mysql -n physical-health --timeout=120s

echo "[5/7] 部署微服务..."
for svc in auth dr core sync urine; do
  echo "  => 部署 physical-$svc ..."
  kubectl apply -f $svc/deployment.yaml
  kubectl apply -f $svc/service.yaml
  if [ -f "$svc/hpa.yaml" ]; then
    kubectl apply -f $svc/hpa.yaml
  fi
done

echo "[6/7] 部署网关和前端..."
kubectl apply -f gateway/deployment.yaml
kubectl apply -f gateway/service.yaml
kubectl apply -f web/deployment.yaml
kubectl apply -f web/service.yaml

echo "[7/7] 等待所有Pod就绪..."
kubectl rollout status deployment/physical-gateway -n physical-health --timeout=120s
kubectl rollout status deployment/physical-auth    -n physical-health --timeout=120s
kubectl rollout status deployment/physical-dr      -n physical-health --timeout=120s
kubectl rollout status deployment/physical-core    -n physical-health --timeout=120s

echo ""
echo "======================================================"
echo " 部署完成！Pod状态："
kubectl get pods -n physical-health
echo ""
echo " 访问地址："
echo "  网关 NodePort: http://NODE_IP:30888"
echo "  网页端: http://NODE_IP:30888/web"
echo "======================================================"
