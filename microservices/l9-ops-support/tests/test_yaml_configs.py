"""
L9 运维支撑层 — 配置文件验收测试
验证所有 YAML / 告警规则 / K8s 配置的完整性和正确性
"""
import glob
import os
import re
import pytest
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════════════════════
# Fixture：加载所有文件
# ═══════════════════════════════════════════════════════════════════════════

def all_yaml_files():
    return sorted(glob.glob(os.path.join(BASE_DIR, "**/*.yaml"), recursive=True) +
                  glob.glob(os.path.join(BASE_DIR, "**/*.yml"), recursive=True))


def load_all_k8s_docs():
    """返回所有 K8s 资源 (kind, name, doc, path)"""
    results = []
    for path in all_yaml_files():
        try:
            with open(path) as f:
                for doc in yaml.safe_load_all(f):
                    if isinstance(doc, dict) and doc.get("kind"):
                        meta = doc.get("metadata", {}) or {}
                        results.append((doc["kind"], meta.get("name", "?"), doc, path))
        except Exception:
            pass
    return results


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: 所有 YAML 文件语法正确
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("path", all_yaml_files())
def test_yaml_syntax_valid(path):
    """每个 YAML 文件都应能正常解析"""
    with open(path) as f:
        docs = list(yaml.safe_load_all(f))
    assert docs is not None, f"YAML 解析返回 None: {path}"


# ═══════════════════════════════════════════════════════════════════════════
# Test 2: 所有 Deployment/StatefulSet/DaemonSet 必须有 resources + 探针
# ═══════════════════════════════════════════════════════════════════════════

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


def iter_workload_containers():
    """生成 (kind, svc_name, container_name, container_dict, path)"""
    for kind, name, doc, path in load_all_k8s_docs():
        if kind not in WORKLOAD_KINDS:
            continue
        spec = doc.get("spec", {}) or {}
        tmpl_spec = (spec.get("template", {}) or {}).get("spec", {}) or {}
        for c in (tmpl_spec.get("containers") or []):
            yield kind, name, c.get("name", "?"), c, path


@pytest.mark.parametrize("kind,svc,cname,container,path",
                         iter_workload_containers(),
                         ids=[f"{k}/{s}/{c}" for k, s, c, _, _ in iter_workload_containers()])
def test_container_has_resource_limits(kind, svc, cname, container, path):
    resources = container.get("resources", {}) or {}
    assert resources.get("limits"), \
        f"{kind}/{svc}/{cname} 缺少 resources.limits  ({path})"


@pytest.mark.parametrize("kind,svc,cname,container,path",
                         iter_workload_containers(),
                         ids=[f"{k}/{s}/{c}" for k, s, c, _, _ in iter_workload_containers()])
def test_container_has_resource_requests(kind, svc, cname, container, path):
    resources = container.get("resources", {}) or {}
    assert resources.get("requests"), \
        f"{kind}/{svc}/{cname} 缺少 resources.requests  ({path})"


@pytest.mark.parametrize("kind,svc,cname,container,path",
                         iter_workload_containers(),
                         ids=[f"{k}/{s}/{c}" for k, s, c, _, _ in iter_workload_containers()])
def test_container_has_liveness_probe(kind, svc, cname, container, path):
    assert container.get("livenessProbe"), \
        f"{kind}/{svc}/{cname} 缺少 livenessProbe  ({path})"


@pytest.mark.parametrize("kind,svc,cname,container,path",
                         iter_workload_containers(),
                         ids=[f"{k}/{s}/{c}" for k, s, c, _, _ in iter_workload_containers()])
def test_container_has_readiness_probe(kind, svc, cname, container, path):
    assert container.get("readinessProbe"), \
        f"{kind}/{svc}/{cname} 缺少 readinessProbe  ({path})"


# ═══════════════════════════════════════════════════════════════════════════
# Test 3: 所有 HPA 必须配置 minReplicas / maxReplicas / metrics
# ═══════════════════════════════════════════════════════════════════════════

def iter_hpa_docs():
    for kind, name, doc, path in load_all_k8s_docs():
        if kind == "HorizontalPodAutoscaler":
            yield name, doc, path


@pytest.mark.parametrize("name,doc,path",
                         iter_hpa_docs(),
                         ids=[n for n, _, _ in iter_hpa_docs()])
def test_hpa_has_min_replicas(name, doc, path):
    spec = doc.get("spec", {}) or {}
    assert spec.get("minReplicas") is not None, f"HPA {name} 缺少 minReplicas ({path})"


@pytest.mark.parametrize("name,doc,path",
                         iter_hpa_docs(),
                         ids=[n for n, _, _ in iter_hpa_docs()])
def test_hpa_has_max_replicas(name, doc, path):
    spec = doc.get("spec", {}) or {}
    assert spec.get("maxReplicas", 0) > 0, f"HPA {name} 缺少有效 maxReplicas ({path})"


@pytest.mark.parametrize("name,doc,path",
                         iter_hpa_docs(),
                         ids=[n for n, _, _ in iter_hpa_docs()])
def test_hpa_has_metrics(name, doc, path):
    spec = doc.get("spec", {}) or {}
    assert spec.get("metrics"), f"HPA {name} 缺少 metrics ({path})"


@pytest.mark.parametrize("name,doc,path",
                         iter_hpa_docs(),
                         ids=[n for n, _, _ in iter_hpa_docs()])
def test_hpa_max_greater_than_min(name, doc, path):
    spec = doc.get("spec", {}) or {}
    min_r = spec.get("minReplicas", 1)
    max_r = spec.get("maxReplicas", 0)
    assert max_r >= min_r, f"HPA {name}: maxReplicas({max_r}) < minReplicas({min_r}) ({path})"


# ═══════════════════════════════════════════════════════════════════════════
# Test 4: Prometheus 告警规则完整性
# ═══════════════════════════════════════════════════════════════════════════

ALERT_RULE_FILE = os.path.join(BASE_DIR, "observability/prometheus/rules/ilbuy-alerts.yml")
RECORDING_RULE_FILE = os.path.join(BASE_DIR, "observability/prometheus/rules/ilbuy-recording.yml")


def load_alerts():
    with open(ALERT_RULE_FILE) as f:
        doc = yaml.safe_load(f)
    alerts = []
    for group in (doc.get("groups") or []):
        for rule in (group.get("rules") or []):
            if rule.get("alert"):
                alerts.append((rule["alert"], rule, group["name"]))
    return alerts


@pytest.mark.parametrize("alert_name,rule,group",
                         load_alerts(),
                         ids=[a for a, _, _ in load_alerts()])
def test_alert_has_expr(alert_name, rule, group):
    assert rule.get("expr"), f"告警 {alert_name} 缺少 expr"


@pytest.mark.parametrize("alert_name,rule,group",
                         load_alerts(),
                         ids=[a for a, _, _ in load_alerts()])
def test_alert_has_severity_label(alert_name, rule, group):
    labels = rule.get("labels", {}) or {}
    assert labels.get("severity") in ("critical", "warning", "info"), \
        f"告警 {alert_name} 缺少有效 severity label (当前: {labels.get('severity')})"


@pytest.mark.parametrize("alert_name,rule,group",
                         load_alerts(),
                         ids=[a for a, _, _ in load_alerts()])
def test_alert_has_summary_annotation(alert_name, rule, group):
    annotations = rule.get("annotations", {}) or {}
    assert annotations.get("summary"), f"告警 {alert_name} 缺少 summary annotation"


@pytest.mark.parametrize("alert_name,rule,group",
                         load_alerts(),
                         ids=[a for a, _, _ in load_alerts()])
def test_alert_has_description_annotation(alert_name, rule, group):
    annotations = rule.get("annotations", {}) or {}
    assert annotations.get("description"), f"告警 {alert_name} 缺少 description annotation"


# ═══════════════════════════════════════════════════════════════════════════
# Test 5: Recording Rules 完整性
# ═══════════════════════════════════════════════════════════════════════════

def load_recording_rules():
    with open(RECORDING_RULE_FILE) as f:
        doc = yaml.safe_load(f)
    rules = []
    for group in (doc.get("groups") or []):
        for rule in (group.get("rules") or []):
            if rule.get("record"):
                rules.append((rule["record"], rule, group["name"]))
    return rules


@pytest.mark.parametrize("record_name,rule,group",
                         load_recording_rules(),
                         ids=[r for r, _, _ in load_recording_rules()])
def test_recording_rule_has_expr(record_name, rule, group):
    assert rule.get("expr"), f"Recording rule {record_name} 缺少 expr"


@pytest.mark.parametrize("record_name,rule,group",
                         load_recording_rules(),
                         ids=[r for r, _, _ in load_recording_rules()])
def test_recording_rule_name_format(record_name, rule, group):
    """Recording rule 名称必须包含冒号（Prometheus 命名规范）"""
    assert ":" in record_name, \
        f"Recording rule 名称 '{record_name}' 不符合 Prometheus 规范（应含 ':'）"


# ═══════════════════════════════════════════════════════════════════════════
# Test 6: AlertManager 路由配置完整性
# ═══════════════════════════════════════════════════════════════════════════

ALERTMANAGER_CONFIG = os.path.join(BASE_DIR, "observability/alertmanager/alertmanager.yml")


def test_alertmanager_has_receivers():
    with open(ALERTMANAGER_CONFIG) as f:
        config = yaml.safe_load(f)
    assert config.get("receivers"), "AlertManager 配置缺少 receivers"
    receiver_names = [r["name"] for r in config["receivers"]]
    assert len(receiver_names) >= 3, f"receivers 数量不足(当前 {len(receiver_names)}，期望 ≥ 3)"


def test_alertmanager_has_route():
    with open(ALERTMANAGER_CONFIG) as f:
        config = yaml.safe_load(f)
    route = config.get("route", {}) or {}
    assert route.get("receiver"), "AlertManager route 缺少默认 receiver"
    assert route.get("group_by"), "AlertManager route 缺少 group_by"


def test_alertmanager_has_inhibit_rules():
    with open(ALERTMANAGER_CONFIG) as f:
        config = yaml.safe_load(f)
    assert config.get("inhibit_rules"), "AlertManager 缺少 inhibit_rules（防止告警风暴）"


def test_alertmanager_route_has_sub_routes():
    with open(ALERTMANAGER_CONFIG) as f:
        config = yaml.safe_load(f)
    routes = (config.get("route", {}) or {}).get("routes", [])
    assert len(routes) >= 3, f"AlertManager 子路由不足(当前 {len(routes)}，期望 ≥ 3)"


# ═══════════════════════════════════════════════════════════════════════════
# Test 7: Prometheus scrape_configs 覆盖 L1-L8
# ═══════════════════════════════════════════════════════════════════════════

PROMETHEUS_CONFIG = os.path.join(BASE_DIR, "observability/prometheus/prometheus.yml")


def test_prometheus_scrapes_all_layers():
    with open(PROMETHEUS_CONFIG) as f:
        config = yaml.safe_load(f)
    scrape_jobs = [sc["job_name"] for sc in (config.get("scrape_configs") or [])]
    for layer in range(1, 9):
        layer_jobs = [j for j in scrape_jobs if f"l{layer}-" in j]
        assert layer_jobs, f"Prometheus 缺少 L{layer} 层的 scrape job"


def test_prometheus_scrapes_infrastructure():
    with open(PROMETHEUS_CONFIG) as f:
        config = yaml.safe_load(f)
    scrape_jobs = [sc["job_name"] for sc in (config.get("scrape_configs") or [])]
    for infra in ("postgresql", "redis", "rabbitmq"):
        assert infra in scrape_jobs, f"Prometheus 缺少 {infra} 基础设施监控"


def test_prometheus_has_alertmanager_config():
    with open(PROMETHEUS_CONFIG) as f:
        config = yaml.safe_load(f)
    alerting = config.get("alerting", {}) or {}
    ams = alerting.get("alertmanagers", [])
    assert ams, "Prometheus 未配置 alertmanagers"


def test_prometheus_rule_files_configured():
    with open(PROMETHEUS_CONFIG) as f:
        config = yaml.safe_load(f)
    rule_files = config.get("rule_files", [])
    assert len(rule_files) >= 2, f"Prometheus 规则文件配置不足(当前 {len(rule_files)})"


# ═══════════════════════════════════════════════════════════════════════════
# Test 8: Nacos 初始化脚本覆盖 L1-L8 配置
# ═══════════════════════════════════════════════════════════════════════════

NACOS_INIT_SCRIPT = os.path.join(BASE_DIR, "config-management/nacos/scripts/init-configs.sh")


def test_nacos_init_covers_all_layers():
    with open(NACOS_INIT_SCRIPT) as f:
        content = f.read()
    for layer in ("L1", "L2", "L5", "L6", "L7", "L8"):
        assert layer in content, f"Nacos 初始化脚本未包含 {layer} 层配置"


def test_nacos_init_publishes_common_config():
    with open(NACOS_INIT_SCRIPT) as f:
        content = f.read()
    assert "COMMON" in content, "Nacos 初始化脚本缺少公共配置发布"


def test_nacos_init_has_health_check():
    with open(NACOS_INIT_SCRIPT) as f:
        content = f.read()
    assert "health" in content.lower() or "ready" in content.lower(), \
        "Nacos 初始化脚本缺少 Nacos 就绪等待逻辑"


# ═══════════════════════════════════════════════════════════════════════════
# Test 9: Fluent Bit 配置完整性
# ═══════════════════════════════════════════════════════════════════════════

FLUENTBIT_CONFIG = os.path.join(BASE_DIR, "observability/elk/fluentbit/fluent-bit.conf")


def test_fluentbit_has_input():
    with open(FLUENTBIT_CONFIG) as f:
        content = f.read()
    assert "[INPUT]" in content, "Fluent Bit 配置缺少 [INPUT] 块"


def test_fluentbit_has_filter_kubernetes():
    with open(FLUENTBIT_CONFIG) as f:
        content = f.read()
    assert "kubernetes" in content.lower(), "Fluent Bit 未启用 Kubernetes 元数据过滤"


def test_fluentbit_has_output_es():
    with open(FLUENTBIT_CONFIG) as f:
        content = f.read()
    assert "elasticsearch" in content.lower() or "Name            es" in content, \
        "Fluent Bit 缺少 Elasticsearch 输出"


def test_fluentbit_filters_ilbuy_namespace():
    with open(FLUENTBIT_CONFIG) as f:
        content = f.read()
    assert "ilbuy-" in content, "Fluent Bit 未过滤 ilbuy-* 命名空间"


def test_fluentbit_lua_has_layer_map():
    lua_file = os.path.join(BASE_DIR, "observability/elk/fluentbit/add_layer.lua")
    with open(lua_file) as f:
        content = f.read()
    for i in range(1, 9):
        assert f"ilbuy-l{i}" in content, f"Fluent Bit Lua 脚本缺少 L{i} 层映射"


# ═══════════════════════════════════════════════════════════════════════════
# Test 10: Vault Policy 覆盖 L1-L8
# ═══════════════════════════════════════════════════════════════════════════

VAULT_POLICY = os.path.join(BASE_DIR, "config-management/vault/scripts/policies/ilbuy-policy.hcl")


def test_vault_policy_covers_all_layers():
    with open(VAULT_POLICY) as f:
        content = f.read()
    for i in range(1, 9):
        assert f"secret/data/ilbuy/l{i}/" in content, \
            f"Vault Policy 未授权 L{i} 层 Secret 访问"


def test_vault_policy_has_database_creds():
    with open(VAULT_POLICY) as f:
        content = f.read()
    assert "database/creds/" in content, "Vault Policy 缺少动态数据库凭据访问权限"


def test_vault_policy_has_transit():
    with open(VAULT_POLICY) as f:
        content = f.read()
    assert "transit/" in content, "Vault Policy 缺少 Transit 加密权限"


# ═══════════════════════════════════════════════════════════════════════════
# Test 11: K8s Namespace 覆盖完整性
# ═══════════════════════════════════════════════════════════════════════════

NAMESPACES_FILE = os.path.join(BASE_DIR, "k8s/namespaces.yaml")


def test_namespaces_cover_all_layers():
    with open(NAMESPACES_FILE) as f:
        docs = list(yaml.safe_load_all(f))
    ns_names = [
        (d.get("metadata", {}) or {}).get("name", "")
        for d in docs
        if isinstance(d, dict) and d.get("kind") == "Namespace"
    ]
    for i in range(1, 9):
        assert f"ilbuy-l{i}" in ns_names, f"缺少命名空间 ilbuy-l{i}"
    assert "ilbuy-ops" in ns_names, "缺少命名空间 ilbuy-ops"
    assert "ilbuy-infra" in ns_names, "缺少命名空间 ilbuy-infra"


def test_namespaces_have_resource_quota():
    with open(NAMESPACES_FILE) as f:
        docs = list(yaml.safe_load_all(f))
    quota_ns = set()
    for d in docs:
        if isinstance(d, dict) and d.get("kind") == "ResourceQuota":
            meta = d.get("metadata", {}) or {}
            quota_ns.add(meta.get("namespace", ""))
    for i in range(1, 9):
        assert f"ilbuy-l{i}" in quota_ns, f"命名空间 ilbuy-l{i} 缺少 ResourceQuota"
