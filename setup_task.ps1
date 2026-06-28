$taskName = "AI日报推送"
$scriptPath = "D:\code空间\ai-news-daily\main.py"
$pythonPath = (Get-Command python).Source

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory "D:\code空间\ai-news-daily"

$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force

Write-Host "✅ 定时任务创建成功！"
Write-Host "任务名称: $taskName"
Write-Host "运行时间: 每天早上 9:00"
Write-Host "脚本路径: $scriptPath"

pause