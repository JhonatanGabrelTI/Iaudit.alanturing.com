@echo off
echo ========================================================
echo   CONFIGURACAO DE FALLBACK - SSL AUTO-ASSINADO
echo ========================================================
cd /d "%~dp0"
echo.
echo [1/4] Gerando Certificado Auto-Assinado...
python generate_cert.py

echo.
echo [2/4] Configurando Nginx...
copy /Y "c:\nginx\conf\nginx_fallback.conf" "c:\nginx\conf\nginx.conf"

echo.
echo [3/4] Parando servicos antigos...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM nginx.exe >nul 2>&1

echo.
echo [4/4] Iniciando Servicos (HTTPS)...
set BACKEND_URL=http://127.0.0.1:8000
cd backend
start /B "IAudit Backend" python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
cd ..
start /B "IAudit Frontend" streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1

cd c:\nginx
start nginx.exe

echo.
echo ========================================================
echo   SISTEMA ONLINE (HTTPS AUTO-ASSINADO)
echo   Acesse: https://iaudit.alanturing.com
echo   NOTA: O navegador vai mostrar "Nao seguro".
echo   Clique em "Avancado -> Ir para iaudit..." para acessar.
echo ========================================================
pause
