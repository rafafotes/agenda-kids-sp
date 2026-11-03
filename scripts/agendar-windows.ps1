# Cria (ou atualiza) a tarefa "Agenda Kids SP - coleta" no Agendador de Tarefas do Windows.
# Roda scripts/coletar.sh dentro do WSL às 6h e às 18h. Se o computador estiver desligado no
# horário, a coleta roda assim que ele voltar (StartWhenAvailable).
#
# Uso (no PowerShell do Windows, sem precisar de administrador):
#   powershell -ExecutionPolicy Bypass -File agendar-windows.ps1 -Distro Ubuntu-26.04 -Script /caminho/coletar.sh

param(
    [Parameter(Mandatory = $true)][string]$Distro,
    [Parameter(Mandatory = $true)][string]$Script
)

$nome = "Agenda Kids SP - coleta"
$acao = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d $Distro -- bash $Script"
$gatilhos = @(
    New-ScheduledTaskTrigger -Daily -At "06:00"
    New-ScheduledTaskTrigger -Daily -At "18:00"
)
$opcoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $nome -Action $acao -Trigger $gatilhos -Settings $opcoes `
    -Description "Coleta atividades infantis (shoppings e Sesc) e publica em rafafotes.github.io/agenda-kids-sp" `
    -Force | Out-Null

Get-ScheduledTask -TaskName $nome | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
