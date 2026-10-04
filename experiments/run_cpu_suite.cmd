@echo off
REM Full v2 suite on the CPU-only evaluation host (docs/14-optimizacion-cpu.md).
REM Detached runner: survives the terminal that launched it. Log: results\log_suite_cpu.txt
cd /d %~dp0
set GATEWAY_PORT=8080
set GATEWAY_URL=http://localhost:8080
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -u run_v2_suite.py --cpu-only --lanes 3 --threads 2 --phase %* --audio results\load_clip_real.wav --repeats 3 >> results\log_suite_cpu.txt 2>&1
echo SUITE_EXIT %ERRORLEVEL% >> results\log_suite_cpu.txt
