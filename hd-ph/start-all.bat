@echo off
chcp 65001 >nul
title 惠东县公卫体检系统 - 启动脚本

echo ============================================
echo  惠东县区域公卫体检集中系统 - Windows启动
echo ============================================
echo.

:: 检查 Java
java -version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Java，请先安装 JDK 11 或以上版本
    pause
    exit /b 1
)

:: 检查 Maven
mvn -v >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Maven，请先安装 Maven 3.6+
    pause
    exit /b 1
)

:: 检查 Redis
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [警告] Redis未响应，正在尝试启动Redis...
    start /min redis-server
    timeout /t 2 >nul
)

echo [1/6] 编译整个项目...
call mvn clean package -DskipTests -q
if errorlevel 1 (
    echo [错误] 编译失败，请检查代码
    pause
    exit /b 1
)
echo      编译完成 ✓

echo.
echo [2/6] 启动 hd-auth  (端口 8001)...
start "hd-auth" cmd /k "java -jar hd-auth\target\hd-auth-1.0.0.jar --spring.profiles.active=dev & echo hd-auth started"
timeout /t 5 >nul

echo [3/6] 启动 hd-resident (端口 8002)...
start "hd-resident" cmd /k "java -jar hd-resident\target\hd-resident-1.0.0.jar"
timeout /t 3 >nul

echo [4/6] 启动 hd-device (端口 8003 / TCP:7100)...
start "hd-device" cmd /k "java -jar hd-device\target\hd-device-1.0.0.jar"
timeout /t 3 >nul

echo [5/6] 启动 hd-check (端口 8004)...
start "hd-check" cmd /k "java -jar hd-check\target\hd-check-1.0.0.jar"
timeout /t 3 >nul

echo [6/6] 启动 hd-dr (端口 8005)...
start "hd-dr" cmd /k "java -jar hd-dr\target\hd-dr-1.0.0.jar"
timeout /t 3 >nul

echo.
echo 等待所有服务就绪 (15秒)...
timeout /t 15 >nul

echo [7/7] 启动 hd-gateway (端口 9090)...
start "hd-gateway" cmd /k "java -jar hd-gateway\target\hd-gateway-1.0.0.jar"
timeout /t 5 >nul

echo.
echo ============================================
echo  所有服务已启动！
echo ============================================
echo.
echo  网关入口:   http://localhost:9090
echo  前端页面:   http://localhost:3000  (需单独启动)
echo  API文档:    http://localhost:8001/doc.html
echo.
echo  测试账号:
echo    管理员:  admin      / hd2024
echo    生化:    biochem01  / hd2024
echo    血常规:  blood01    / hd2024
echo    尿常规:  urine01    / hd2024
echo    糖化:    hba1c01    / hd2024
echo    DR放射:  dr01       / hd2024
echo    护士:    nurse01    / hd2024
echo.
echo  验证各服务健康:
echo    curl http://localhost:8001/api/auth/health
echo    curl http://localhost:9090/actuator/health
echo.
pause
