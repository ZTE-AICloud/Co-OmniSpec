@echo off
setlocal enabledelayedexpansion

:: Graphify 一键安装脚本 (Windows)
:: 使用方法: install_graphify.bat [platform]
::   - 不带参数: 默认安装 Claude Code 平台
::   - 带参数:   安装指定平台 (codebuddy/codex/opencode/claw/droid/trae/trae-cn)

set "PLATFORM=%~1"

echo ==========================================
echo   Graphify 安装脚本
echo ==========================================

:: 1. 检查 Python 版本
echo.
echo [1/3] 检查 Python 版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 python 命令，请确保 Python 已安装
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%v"
echo   Python 版本: %PYTHON_VERSION%

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "PYTHON_MAJOR=%%a"
    set "PYTHON_MINOR=%%b"
)

:: 检查 Python 3.10+
if %PYTHON_MAJOR% LSS 3 (
    echo 错误: 需要 Python 3.10 或更高版本，当前版本: %PYTHON_VERSION%
    exit /b 1
)
if %PYTHON_MAJOR% EQU 3 (
    if %PYTHON_MINOR% LSS 10 (
        echo 错误: 需要 Python 3.10 或更高版本，当前版本: %PYTHON_VERSION%
        exit /b 1
    )
)
echo   Python 版本检查通过

:: 2. 安装 graphify
echo.
echo [2/3] 安装 graphify (公共源)...
python -m pip install --user ^
    graphify

if not !errorlevel!==0 (
    echo 错误: graphify 安装失败
    exit /b 1
)
echo   graphify 安装成功

:: 3. 注册 Skill
echo.
echo [3/3] 注册 Graphify Skill...

:: 查找 graphify 命令
set "GRAPHIFY_CMD="
where graphify >nul 2>&1
if not errorlevel 1 (
    set "GRAPHIFY_CMD=graphify"
) else (
    :: 尝试在用户本地路径查找
    set "USER_BASE="
    for /f "tokens=*" %%i in ('python -m site --user_base 2^>^&1') do set "USER_BASE=%%i"
    if not "!USER_BASE!"=="" (
        if exist "!USER_BASE!\Scripts\graphify.exe" (
            set "GRAPHIFY_CMD=!USER_BASE!\Scripts\graphify.exe"
        )
    )
)

if "!GRAPHIFY_CMD!"=="" (
    echo 错误: 未找到 graphify 命令，请确保 pip 安装成功
    exit /b 1
)

echo   找到 graphify: !GRAPHIFY_CMD!

:: 执行注册
if not "%PLATFORM%"=="" (
    echo   指定平台: %PLATFORM%
    call !GRAPHIFY_CMD! install --platform %PLATFORM%
    set "REGISTERED_PLATFORM=%PLATFORM%"
) else (
    call !GRAPHIFY_CMD! install
    set "REGISTERED_PLATFORM=claude-code"
)

if not !errorlevel!==0 (
    echo 错误: Skill 注册失败
    exit /b 1
)

echo.
echo ==========================================
echo   安装完成!
echo ==========================================
echo.
echo 使用 graphify 命令开始知识图谱构建:
echo   graphify
echo.
echo 已注册平台: !REGISTERED_PLATFORM!
exit /b 0
