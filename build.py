import PyInstaller.__main__
import os

# Đường dẫn đến thư mục hiện tại
current_dir = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    'desktop_app.py',
    '--name=ResearchManagementSystem',
    '--onefile',
    '--windowed',
    '--icon=static/logo.png',
    '--add-data=main.py;.',
    '--add-data=routes;routes',
    '--add-data=models;models',
    '--add-data=services;services',
    '--add-data=database;database',
    '--add-data=static;static',
    '--add-data=templates;templates',
    '--hidden-import=uvicorn.logging',
    '--hidden-import=uvicorn.loops',
    '--hidden-import=uvicorn.loops.auto',
    '--hidden-import=uvicorn.protocols',
    '--hidden-import=uvicorn.protocols.http',
    '--hidden-import=uvicorn.protocols.http.auto',
    '--hidden-import=uvicorn.protocols.websockets',
    '--hidden-import=uvicorn.protocols.websockets.auto',
    '--hidden-import=uvicorn.lifespan',
    '--hidden-import=uvicorn.lifespan.on',
    '--hidden-import=jinja2',
    '--hidden-import=starlette',
    '--hidden-import=starlette.middleware',
    '--hidden-import=starlette.middleware.sessions',
    '--hidden-import=starlette.middleware.base',
    '--hidden-import=starlette.responses',
    '--hidden-import=starlette.staticfiles',
    '--hidden-import=starlette.templating',
]) 