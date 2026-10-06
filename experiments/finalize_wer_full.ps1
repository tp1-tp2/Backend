# Waits for the three full-corpus parity containers (engine_parity.py on the
# 2111 clips), then runs wer_full_control.py, which writes the report, a
# ready-to-paste chapter text (results\e2_parity_full_chapter_text.md) and the
# docs/17 section. It never edits cap-5-extracted.md (edited by hand).
# Log: results\log_wer_full.txt. Launch detached:
#   Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File <ruta>\finalize_wer_full.ps1' -WindowStyle Hidden
$ErrorActionPreference = "Continue"
$d = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $d "results\log_wer_full.txt"
$names = @("parity_transformers_fp32", "parity_ctranslate2_fp32", "parity_ctranslate2_int8")
"[$(Get-Date)] waiting for: $($names -join ', ')" | Out-File $log -Append -Encoding utf8
$codes = docker wait @names
"[$(Get-Date)] exit codes: $($codes -join ', ')" | Out-File $log -Append -Encoding utf8
$ok = $true
foreach ($n in $names) {
    $csv = Join-Path $d ("results\e2_parity_full_" + $n.Substring(7) + ".csv")
    if (-not (Test-Path $csv)) { "MISSING $csv" | Out-File $log -Append -Encoding utf8; $ok = $false }
}
if (($codes | Where-Object { $_ -ne "0" }).Count -gt 0) { $ok = $false }
if (-not $ok) {
    "[$(Get-Date)] NOT finalizing: a container failed or a CSV is missing (see docker logs <name>)" | Out-File $log -Append -Encoding utf8
    exit 1
}
$env:PYTHONIOENCODING = "utf-8"
& (Join-Path $d ".venv\Scripts\python.exe") (Join-Path $d "e8_inference_throughput\wer_full_control.py") *>> $log
"[$(Get-Date)] FINALIZE_EXIT $LASTEXITCODE" | Out-File $log -Append -Encoding utf8
