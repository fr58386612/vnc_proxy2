@echo off
chcp 65001 >nul
echo VNC代理服务器 - 一键打包工具
echo ================================

echo.
echo 正在检查uv是否已安装...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到uv工具
    echo 请先安装uv：pip install uv
    pause
    exit /b 1
)

echo.
echo 正在使用uv运行打包脚本...
uv run build.py

echo.
echo 打包完成！按任意键退出...
pause >nul