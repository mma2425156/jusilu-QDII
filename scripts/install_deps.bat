@echo off
REM 自动安装依赖脚本(Windows版) - 支持虚拟环境

:: 优先使用虚拟环境中的Python
if exist "..\venv\Scripts\python.exe" (
    set PYTHON=..\venv\Scripts\python
) else (
    set PYTHON=python
    echo 警告: 未检测到虚拟环境，将使用系统Python
)

set MAX_RETRIES=3
set RETRY_DELAY=5

echo 正在安装Python依赖...
echo.

:retry_loop
set /a ATTEMPT+=1

%PYTHON% -m pip install -r requirements.txt
if %ERRORLEVEL% equ 0 (
    echo 依赖安装成功！
    goto success
) else (
    echo 第 %ATTEMPT% 次尝试失败
    if %ATTEMPT% lss %MAX_RETRIES% (
        echo %RETRY_DELAY%秒后重试...
        timeout /t %RETRY_DELAY% >nul
        goto retry_loop
    )
)

echo 依赖安装失败，请手动检查
pause
exit /b 1

:success
echo 正在生成更新的requirements.txt...
%PYTHON% -m pip freeze > requirements.txt
echo requirements.txt已更新

echo 安装完成！
pause
