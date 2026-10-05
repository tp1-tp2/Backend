@echo off
REM Remaining CPU runs after the edge-admission and job-backlog fixes (docs/16).
cd /d %~dp0
set GATEWAY_PORT=8080
set GATEWAY_URL=http://localhost:8080
set PYTHONIOENCODING=utf-8
set S=.venv\Scripts\python.exe -u run_v2_suite.py --cpu-only --lanes 3 --threads 2 --audio results\load_clip_real.wav --repeats 3
echo ### CHAIN3 START %DATE% %TIME% >> results\log_suite_cpu.txt
%S% --phase e4 --e4-only S2c-v2-cpu-sync-edge >> results\log_suite_cpu.txt 2>&1
%S% --phase e6 --e6-only D7-monolith-crash --e6-users 10 >> results\log_suite_cpu.txt 2>&1
%S% --phase e3 >> results\log_suite_cpu.txt 2>&1
echo CHAIN3_EXIT %ERRORLEVEL% >> results\log_suite_cpu.txt
