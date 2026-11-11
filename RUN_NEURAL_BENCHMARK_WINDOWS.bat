@echo off
setlocal
cd /d "%~dp0"
echo VERUNAI v0.5 - RESEARCH CPU MINING BENCHMARK
echo This is only for technical research. No real coins are issued.
py -3 -m verunai neural-mining-benchmark --attempts 150 --backend python
if errorlevel 1 python -m verunai neural-mining-benchmark --attempts 150 --backend python
echo.
echo Optional: from PowerShell, use --backend torch-cuda after installing CUDA PyTorch.
pause
