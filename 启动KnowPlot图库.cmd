@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m streamlit run personal_studio.py --server.showEmailPrompt false --browser.gatherUsageStats false --server.headless false
pause
