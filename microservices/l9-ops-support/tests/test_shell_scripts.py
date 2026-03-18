"""
L9 运维支撑层 — Shell 脚本验收测试
验证 deploy/rollback/health-check/backup 脚本的语法、帮助输出、参数校验
"""
import os
import subprocess
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")


def run_bash(script_path, args=None, env=None):
    """执行 bash 脚本，返回 (returncode, stdout, stderr)"""
    cmd = ["bash"] + (["-n"] if args is None else []) + [script_path]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env,
                            timeout=10)
    return result.returncode, result.stdout, result.stderr


# ═══════════════════════════════════════════════════════════════════════════
# 语法检查
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("script", [
    "deploy.sh", "rollback.sh", "health-check.sh", "backup.sh"
])
def test_script_syntax_valid(script):
    """bash -n 语法检查"""
    path = os.path.join(SCRIPTS_DIR, script)
    rc, _, stderr = run_bash(path)
    assert rc == 0, f"{script} 语法错误:\n{stderr}"


@pytest.mark.parametrize("script", [
    os.path.join(BASE_DIR, "config-management/nacos/scripts/init-configs.sh"),
    os.path.join(BASE_DIR, "config-management/vault/scripts/init-vault.sh"),
    os.path.join(BASE_DIR, "cicd/harbor/harbor-projects-init.sh"),
])
def test_infra_script_syntax_valid(script):
    rc, _, stderr = run_bash(script)
    assert rc == 0, f"{os.path.basename(script)} 语法错误:\n{stderr}"


# ═══════════════════════════════════════════════════════════════════════════
# deploy.sh 参数校验
# ═══════════════════════════════════════════════════════════════════════════

def test_deploy_exits_without_service():
    """缺少 -s 参数应以非0退出"""
    path = os.path.join(SCRIPTS_DIR, "deploy.sh")
    result = subprocess.run(
        ["bash", path, "-t", "v1.0.0", "-n", "ilbuy-l8"],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode != 0, "deploy.sh 缺少 -s 参数应报错退出"
    assert "必须指定" in result.stderr or "must" in result.stderr.lower() or \
           "ERR" in result.stderr or result.returncode != 0


def test_deploy_exits_without_tag():
    """缺少 -t 参数应以非0退出"""
    path = os.path.join(SCRIPTS_DIR, "deploy.sh")
    result = subprocess.run(
        ["bash", path, "-s", "feedback-svc", "-n", "ilbuy-l8"],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode != 0, "deploy.sh 缺少 -t 参数应报错退出"


def test_deploy_exits_without_namespace():
    """缺少 -n 参数应以非0退出"""
    path = os.path.join(SCRIPTS_DIR, "deploy.sh")
    result = subprocess.run(
        ["bash", path, "-s", "feedback-svc", "-t", "v1.0.0"],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode != 0, "deploy.sh 缺少 -n 参数应报错退出"


def test_deploy_help_option():
    """deploy.sh -h 应显示帮助信息"""
    path = os.path.join(SCRIPTS_DIR, "deploy.sh")
    result = subprocess.run(
        ["bash", path, "-h"],
        capture_output=True, text=True, timeout=5
    )
    output = result.stdout + result.stderr
    assert "用法" in output or "Usage" in output or "-s" in output, \
        "deploy.sh -h 未输出帮助信息"


def test_deploy_dryrun_no_kubectl():
    """dry-run 模式不应调用 kubectl（无 kubectl 也能运行）"""
    path = os.path.join(SCRIPTS_DIR, "deploy.sh")
    result = subprocess.run(
        ["bash", path, "-s", "feedback-svc", "-t", "abc123", "-n", "ilbuy-l8", "-d"],
        capture_output=True, text=True, timeout=10,
        env={**os.environ, "PATH": "/usr/bin:/bin"}  # 限制 PATH 确保没有 kubectl
    )
    # dry-run 应显示将要执行的命令，不实际执行
    output = result.stdout + result.stderr
    assert "DRY" in output or "dry" in output.lower(), \
        "deploy.sh -d 未进入 dry-run 模式"


# ═══════════════════════════════════════════════════════════════════════════
# rollback.sh 参数校验
# ═══════════════════════════════════════════════════════════════════════════

def test_rollback_exits_without_service():
    path = os.path.join(SCRIPTS_DIR, "rollback.sh")
    result = subprocess.run(
        ["bash", path, "-n", "ilbuy-l8"],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode != 0, "rollback.sh 缺少 -s 应报错"


def test_rollback_exits_without_namespace():
    path = os.path.join(SCRIPTS_DIR, "rollback.sh")
    result = subprocess.run(
        ["bash", path, "-s", "feedback-svc"],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode != 0, "rollback.sh 缺少 -n 应报错"


def test_rollback_help_option():
    path = os.path.join(SCRIPTS_DIR, "rollback.sh")
    result = subprocess.run(
        ["bash", path, "-h"],
        capture_output=True, text=True, timeout=5
    )
    output = result.stdout + result.stderr
    assert "-s" in output or "用法" in output, "rollback.sh -h 无有效输出"


# ═══════════════════════════════════════════════════════════════════════════
# backup.sh 功能验证
# ═══════════════════════════════════════════════════════════════════════════

def test_backup_dryrun_runs_without_error():
    """DRY_RUN=true 模式下 backup.sh 应正常结束"""
    path = os.path.join(SCRIPTS_DIR, "backup.sh")
    result = subprocess.run(
        ["bash", path, "--dry-run"],
        capture_output=True, text=True, timeout=15,
        env={**os.environ, "DRY_RUN": "true",
             "BACKUP_ROOT": "/tmp/ilbuy-backup-test"}
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"backup.sh --dry-run 失败:\n{output}"
    assert "DRY-RUN" in output or "干运行" in output.lower() or \
           "dry" in output.lower(), "backup.sh 未进入 DRY_RUN 模式"


def test_backup_has_retention_logic():
    """backup.sh 应包含清理旧备份的逻辑"""
    path = os.path.join(SCRIPTS_DIR, "backup.sh")
    with open(path) as f:
        content = f.read()
    assert "RETENTION_DAYS" in content or "mtime" in content, \
        "backup.sh 缺少数据保留/清理逻辑"


# ═══════════════════════════════════════════════════════════════════════════
# health-check.sh 验证
# ═══════════════════════════════════════════════════════════════════════════

def test_healthcheck_has_service_list():
    """health-check.sh 应包含 L1-L8 服务清单"""
    path = os.path.join(SCRIPTS_DIR, "health-check.sh")
    with open(path) as f:
        content = f.read()
    for layer in range(1, 9):
        assert f"ilbuy-l{layer}" in content, \
            f"health-check.sh 未包含 L{layer} 层服务"


def test_healthcheck_checks_infrastructure():
    """health-check.sh 应检查基础设施"""
    path = os.path.join(SCRIPTS_DIR, "health-check.sh")
    with open(path) as f:
        content = f.read()
    for infra in ("PostgreSQL", "Redis", "Nacos"):
        assert infra in content or infra.lower() in content, \
            f"health-check.sh 未包含 {infra} 基础设施检查"


def test_healthcheck_has_exit_code_on_failure():
    """health-check.sh 发现故障时应非0退出"""
    path = os.path.join(SCRIPTS_DIR, "health-check.sh")
    with open(path) as f:
        content = f.read()
    assert "exit 1" in content, "health-check.sh 缺少失败时 exit 1"


# ═══════════════════════════════════════════════════════════════════════════
# Dockerfile 验证
# ═══════════════════════════════════════════════════════════════════════════

JENKINS_DOCKERFILE = os.path.join(BASE_DIR, "cicd/jenkins/Dockerfile")


def test_dockerfile_has_from():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert content.startswith("FROM"), "Dockerfile 必须以 FROM 开头"


def test_dockerfile_installs_kubectl():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "kubectl" in content, "Jenkins Dockerfile 未安装 kubectl"


def test_dockerfile_installs_helm():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "helm" in content.lower(), "Jenkins Dockerfile 未安装 helm"


def test_dockerfile_installs_sonar_scanner():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "sonar-scanner" in content, "Jenkins Dockerfile 未安装 sonar-scanner"


def test_dockerfile_installs_trivy():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "trivy" in content.lower(), "Jenkins Dockerfile 未安装 trivy (安全扫描)"


def test_dockerfile_exposes_ports():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "EXPOSE 8080" in content, "Dockerfile 未声明 EXPOSE 8080"
    assert "50000" in content, "Dockerfile 未声明 Agent Port 50000"


def test_dockerfile_copies_plugins():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "jenkins-plugins.txt" in content, \
        "Dockerfile 未 COPY jenkins-plugins.txt"
    plugins_file = os.path.join(BASE_DIR, "cicd/jenkins/jenkins-plugins.txt")
    assert os.path.exists(plugins_file), \
        f"jenkins-plugins.txt 文件不存在: {plugins_file}"


def test_dockerfile_switches_to_jenkins_user():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "USER jenkins" in content, \
        "Dockerfile 最终未切换回 jenkins 用户（安全隐患）"


def test_dockerfile_cleanup_apt_cache():
    with open(JENKINS_DOCKERFILE) as f:
        content = f.read()
    assert "rm -rf /var/lib/apt/lists" in content, \
        "Dockerfile 未清理 apt 缓存（镜像体积优化）"


# ═══════════════════════════════════════════════════════════════════════════
# docker-compose.yml 验证
# ═══════════════════════════════════════════════════════════════════════════

DC_FILE = os.path.join(BASE_DIR, "docker-compose.yml")


def test_compose_file_exists():
    assert os.path.exists(DC_FILE), "docker-compose.yml 不存在（本地启动验证需要）"


def test_compose_services_have_healthcheck():
    import yaml
    with open(DC_FILE) as f:
        config = yaml.safe_load(f)
    services = config.get("services", {})
    for svc_name, svc in services.items():
        assert svc.get("healthcheck"), \
            f"docker-compose 服务 {svc_name} 缺少 healthcheck"


def test_compose_services_have_no_port_conflicts():
    import yaml
    with open(DC_FILE) as f:
        config = yaml.safe_load(f)
    host_ports = {}
    for svc_name, svc in config.get("services", {}).items():
        for port_mapping in (svc.get("ports") or []):
            host_port = str(port_mapping).split(":")[0]
            assert host_port not in host_ports, \
                f"端口 {host_port} 冲突: {svc_name} vs {host_ports[host_port]}"
            host_ports[host_port] = svc_name


def test_compose_has_monitoring_services():
    import yaml
    with open(DC_FILE) as f:
        config = yaml.safe_load(f)
    services = list(config.get("services", {}).keys())
    for expected in ("prometheus", "grafana", "elasticsearch", "kibana", "jaeger"):
        assert expected in services, f"docker-compose 缺少 {expected} 服务"
