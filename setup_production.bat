@echo off
echo ========================================================
echo   CONFIGURACAO DE PRODUCAO - SETUP SSL & NGINX
echo ========================================================
cd /d "%~dp0"
echo.
echo ESTE SCRIPT PRECISA SER EXECUTADO COMO ADMINISTRADOR.
echo Se nao estiver como Admin, feche e clique com botao direito -> Executar como Administrador.
echo.
pause

echo.
echo [1/5] Parando servicos conflitantes (Porta 80)...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM nginx.exe >nul 2>&1
echo Concluido.

echo.
echo [2/5] Gerando Certificado SSL (Let's Encrypt)...
echo O Certbot vai solicitar o certificado para iaudit.alanturing.com
"C:\Program Files\Certbot\bin\certbot.exe" certonly --standalone --non-interactive --agree-tos -m iaudit@alanturing.com -d iaudit.alanturing.com

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao gerar certificado. Verifique conexao e se a porta 80 esta livre.
    echo Continuando para tentar iniciar o sistema mesmo assim (pode falhar o Nginx)...
    pause
)

echo.
echo [3/5] Iniciando API Backend (Porta 8000)...
cd backend
start /B "IAudit Backend" python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
cd ..

echo.
echo [4/5] Iniciando Frontend Streamlit (Porta 8501)...
set BACKEND_URL=https://iaudit.alanturing.com
start /B "IAudit Frontend" streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1

echo.
echo [5/5] Iniciando Nginx (Reverse Proxy 80/443 -> 8501)...
cd c:\nginx
start nginx.exe

echo.
echo ========================================================
echo   SISTEMA ONLINE AGORA EM HTTPS!
echo   Acesse: https://iaudit.alanturing.com
echo ========================================================
pause
