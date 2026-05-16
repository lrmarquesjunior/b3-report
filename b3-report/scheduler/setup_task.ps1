# setup_task.ps1
# Cria uma tarefa agendada no Windows Task Scheduler para rodar o b3-report a cada 3 dias.
# Execute como Administrador.

# --- Configurações — ajuste conforme seu ambiente ---
$TaskName    = "B3-Report-Auto"
$PythonPath  = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python312\python.exe"
$ScriptPath  = "C:\Jr\git\b3-report\src\main.py"
$WorkingDir  = "C:\Jr\git\b3-report\src"
$StartTime   = "07:00"   # horário de execução

# --- Verifica se o Python existe ---
if (-not (Test-Path $PythonPath)) {
    Write-Warning "Python não encontrado em: $PythonPath"
    Write-Warning "Ajuste a variável `$PythonPath no script."
    exit 1
}

# --- Remove tarefa anterior se existir ---
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Tarefa anterior removida."
}

# --- Cria a ação ---
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

# --- Cria o gatilho: diário, mas com repetição a cada 3 dias ---
# O Task Scheduler não tem "a cada N dias" nativo de forma simples,
# então usamos um gatilho diário com intervalo de 3 dias.
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -DaysInterval 3 `
    -At $StartTime

# --- Configurações da tarefa ---
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -WakeToRun:$false

# --- Registra a tarefa ---
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Coleta posição B3, gera relatório HTML e envia para o Google Drive." `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "✅ Tarefa '$TaskName' criada com sucesso!"
Write-Host "   Executa a cada 3 dias às $StartTime"
Write-Host "   Script: $ScriptPath"
Write-Host ""
Write-Host "Para executar agora manualmente:"
Write-Host "   Start-ScheduledTask -TaskName '$TaskName'"
