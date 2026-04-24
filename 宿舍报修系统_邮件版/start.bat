@echo off
chcp 65001 >nul
echo ========================================
echo      宿舍报修管理系统 - 启动脚本
echo ========================================
echo.

echo [1/3] 正在安装依赖...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo 安装依赖失败，请检查Python环境！
    pause
    exit /b 1
)

echo.
echo [2/3] 依赖安装完成
echo.

echo [3/3] 正在启动系统...
echo.
echo 系统启动后，请访问: http://localhost:5000
echo 默认管理员账号: admin / admin123
echo.
echo 按 Ctrl+C 停止服务器
echo.

python app.py

pause
