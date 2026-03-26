@echo off
chcp 65001 >nul
title 惠东县公卫体检系统 - 启动脚本

:: =============================================
:: 项目路径（根据实际位置修改）
set PROJECT_ROOT=F:\Claude Git Hdtj\hdtj\hd-ph
:: =============================================

echo ============================================
echo  惠东县区域公卫体检集中系统 - Windows启动
echo ============================================
echo.

:: 进入项目目录
cd /d "%PROJECT_ROOT%"
if errorlevel 1 (
    echo [错误] 找不到项目目录: %PROJECT_ROOT%
    echo 请修改脚本第6行的 PROJECT_ROOT 路径
    pause
    exit /b 1
)
echo [OK] 项目目录: %cd%
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
call mvn clean install -DskipTests -q
if errorlevel 1 (
    echo [错误] 编译失败，请检查代码
    pause
    exit /b 1
)
echo      编译完成 ✓

echo.
echo [2/6] 启动 hd-auth  (端口 8001)...
start "hd-auth-8001" cmd /k "cd /d "%PROJECT_ROOT%" && java -jar hd-auth\target\hd-auth-1.0.0.jar"
timeout /t 5 >nul

echo [3/6] 启动 hd-resident (端口 8002)...
start "hd-resident-8002" cmd /k "cd /d "%PROJECT_ROOT%" && java -jar hd-resident\target\hd-resident-1.0.0.jar"
timeout /t 3 >nul

echo [4/6] 启动 hd-device (端口 8003)...
start "hd-device-8003" cmd /k "cd /d "%PROJECT_ROOT%" && java -jar hd-device\target\hd-device-1.0.0.jar"
timeout /t 3 >nul

echo [5/6] 启动 hd-check (端口 8004)...
start "hd-check-8004" cmd /k "cd /d "%PROJECT_ROOT%" && java -jar hd-check\target\hd-check-1.0.0.jar"
timeout /t 3 >nul

echo [6/6] 启动 hd-dr (端口 8005)...
start "hd-dr-8005" cmd /k "cd /d "%PROJECT_ROOT%" && java -jar hd-dr\target\hd-dr-1.0.0.jar"
timeout /t 3 >nul

echo.
echo 等待所有服务就绪 (15秒)...
timeout /t 15 >nul

echo [7/7] 启动 hd-gateway (端口 9090)...
start "hd-gateway-9090" cmd /k "cd /d "%PROJECT_ROOT%" && java -jar hd-gateway\target\hd-gateway-1.0.0.jar"
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
echo  测试账号: admin / hd2024
echo.
echo  启动前端请另开 cmd 窗口执行:
echo    cd "F:\Claude Git Hdtj\hdtj\hd-ph\hd-frontend"
echo    npm run dev
echo.
pause
