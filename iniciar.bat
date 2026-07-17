@echo off
setlocal
title Dashboard de Cobrancas

echo ============================================
echo   Dashboard de Cobrancas
echo ============================================
echo.

cd /d "%~dp0"

python -c "import streamlit, pandas, plotly, pygwalker" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias (primeira vez, pode demorar um pouco)...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERRO ao instalar dependencias. Verifique se o Python esta instalado e no PATH.
        pause
        exit /b 1
    )
)

echo Subindo o dashboard...
echo O navegador vai abrir automaticamente em http://localhost:8501
echo.
echo Para PARAR o sistema, feche esta janela ou pressione Ctrl+C.
echo ============================================
echo.

python -m streamlit run app.py
pause
