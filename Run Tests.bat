@echo off
if not exist "reports" mkdir reports
for /f %%i in ('powershell -command "Get-Date -Format \"yyyy-MM-dd_HH-mm-ss\""') do set timestamp=%%i
python -m pytest test_main.py -v --html=reports/report_%timestamp%.html --self-contained-html
pause
