@echo off
echo Starting Research Management System...

REM Kiểm tra xem file thực thi đã tồn tại chưa
if exist "dist\ResearchManagementSystem.exe" (
    echo Running from executable...
    start "" "dist\ResearchManagementSystem.exe"
) else (
    echo Building application...
    python build.py
    if exist "dist\ResearchManagementSystem.exe" (
        echo Running from executable...
        start "" "dist\ResearchManagementSystem.exe"
    ) else (
        echo Running from Python...
        python desktop_app.py
    )
)

echo Done! 