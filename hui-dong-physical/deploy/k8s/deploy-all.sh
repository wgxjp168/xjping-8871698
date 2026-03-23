#!/bin/bash
# ============================================================
# 惠东县区域公卫体检集中系统 - K8s一键部署脚本
# ============================================================
set -e

NAMESPACE=physical

echo "==> 创建命名空间"
kubectl apply -f namespace.yaml

echo "==> 创建配置项"
kubectl apply -f configmap.yaml

echo "==> 创建密钥（生产环境请先修改secret.yaml）"
kubectl apply -f secret.yaml

echo "==> 部署核心业务服务"
kubectl apply -f core-deployment.yaml

echo "==> 部署协议适配服务"
kubectl apply -f protocol-deployment.yaml

echo "==> 部署下乡尿机专用服务"
kubectl apply -f urine-deployment.yaml

echo "==> 部署数据同步服务"
kubectl apply -f sync-deployment.yaml

echo "==> 部署统一网关"
kubectl apply -f gateway-deployment.yaml

echo "==> 等待所有Pod就绪..."
kubectl rollout status deployment/physical-core -n $NAMESPACE
kubectl rollout status deployment/physical-protocol -n $NAMESPACE
kubectl rollout status deployment/physical-urine -n $NAMESPACE
kubectl rollout status deployment/physical-sync -n $NAMESPACE
kubectl rollout status deployment/gateway -n $NAMESPACE

echo ""
echo "========================================="
echo "  部署完成！"
echo "  统一网关: http://NODE_IP:30888"
echo "  API文档:  http://NODE_IP:30888/doc.html"
echo "========================================="
