@echo off
python -m pytest test_main.py -v --html=report.html --self-contained-html
pause
