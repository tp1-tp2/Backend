@echo off
REM Remaining CPU runs after the edge-admission and job-backlog fixes (docs/16).
cd /d %~dp0
set GATEWAY_PORT=8080
set GATEWAY_URL=http://127.0.0.1:8080
set PYTHONIOENCODING=utf-8
set S=.venv\Scripts\python.exe -u run_v2_suite.py --cpu-only --lanes 3 --threads 2 --audio results\load_clip_real.wav --repeats 3
echo ### CHAIN5 START %DATE% %TIME% >> results\log_suite_cpu.txt
%S% --phase e4 --e4-only S2c-v2-cpu-sync-edge --rep-from 3 >> results\log_suite_cpu.txt 2>&1
%S% --phase e3 >> results\log_suite_cpu.txt 2>&1
echo CHAIN5_EXIT %ERRORLEVEL% >> results\log_suite_cpu.txt
