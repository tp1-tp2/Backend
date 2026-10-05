@echo off
REM v2 suite on the host WITH an NVIDIA GPU (docs/15-pendientes-gpu.md).
REM Detached-friendly runner. Usage: run_gpu_suite.cmd <phases and extra args>
REM   e.g.  run_gpu_suite.cmd e8 --manifest e1_dataset_characterization\manifest_e5_sample.csv
REM Log: results\log_suite_gpu.txt
cd /d %~dp0
set GATEWAY_PORT=8080
set GATEWAY_URL=http://127.0.0.1:8080
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -u run_v2_suite.py --phase %* --audio results\load_clip_real.wav >> results\log_suite_gpu.txt 2>&1
echo SUITE_EXIT %ERRORLEVEL% >> results\log_suite_gpu.txt
