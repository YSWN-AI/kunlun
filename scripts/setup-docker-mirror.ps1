# 配置 Docker Desktop 镜像加速器
# 以管理员身份运行此脚本

$daemonJson = @"
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ],
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false
}
"@

$configPath = "$env:USERPROFILE\.docker\daemon.json"

# 备份原配置
if (Test-Path $configPath) {
    Copy-Item $configPath "$configPath.bak" -Force
    Write-Host "已备份原配置到 $configPath.bak"
}

# 写入新配置
$daemonJson | Out-File -FilePath $configPath -Encoding utf8 -Force
Write-Host "镜像加速器配置已写入 $configPath"
Write-Host ""
Write-Host "请在 Docker Desktop 中手动重启："
Write-Host "  右键系统托盘 Docker 图标 -> Restart Docker Desktop"
Write-Host ""
Write-Host "或者运行: & 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -Restart"
