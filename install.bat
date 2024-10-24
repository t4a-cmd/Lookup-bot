@echo off
echo Installing dependencies for the Python Discord bot...

:: Vérifier si Python est installé
where python >nul 2>nul
if errorlevel 1 (
    echo Python n'est pas installé. Veuillez installer Python à partir de https://www.python.org/
    pause
    exit /b
)

:: Installer les dépendances nécessaires
pip install discord.py
pip install asyncio
pip install json
pip install regex
pip install random2

echo Installation complete!
pause
