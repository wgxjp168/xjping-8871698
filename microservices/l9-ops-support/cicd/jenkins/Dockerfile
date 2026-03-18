FROM jenkins/jenkins:2.460-lts-jdk21

# 以 root 安装系统依赖
USER root

# 安装工具依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    jq \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 Docker CLI（用于构建镜像）
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list && \
    apt-get update && apt-get install -y --no-install-recommends docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# 安装 kubectl 1.29
RUN curl -LO "https://dl.k8s.io/release/v1.29.4/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# 安装 Helm 3.14
RUN curl -fsSL https://get.helm.sh/helm-v3.14.4-linux-amd64.tar.gz | tar -xz && \
    mv linux-amd64/helm /usr/local/bin/helm && \
    rm -rf linux-amd64

# 安装 SonarQube Scanner
ARG SONAR_SCANNER_VERSION=5.0.1.3006
RUN curl -fsSL "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux.zip" \
    -o /tmp/sonar-scanner.zip && \
    unzip -q /tmp/sonar-scanner.zip -d /opt && \
    mv /opt/sonar-scanner-${SONAR_SCANNER_VERSION}-linux /opt/sonar-scanner && \
    ln -s /opt/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    rm /tmp/sonar-scanner.zip

# 安装 Trivy（镜像安全扫描）
RUN curl -fsSL https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" \
    > /etc/apt/sources.list.d/trivy.list && \
    apt-get update && apt-get install -y --no-install-recommends trivy && \
    rm -rf /var/lib/apt/lists/*

# 安装 Jenkins 插件
USER jenkins
COPY --chown=jenkins:jenkins jenkins-plugins.txt /usr/share/jenkins/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/plugins.txt

# 跳过初始向导
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs

# 复制 JCasC 配置
COPY --chown=jenkins:jenkins jenkins.yaml /var/jenkins_home/casc_configs/jenkins.yaml

EXPOSE 8080 50000
