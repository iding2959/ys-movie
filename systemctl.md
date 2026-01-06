# ComfyUI 开机自启动配置指南

本文档说明如何配置 `startup.sh` 脚本在系统启动时自动运行。

## 方法一：使用 systemd 服务（推荐）

这是最推荐的方法，适合服务器和桌面环境。

### 1. 创建 systemd 服务文件

```bash
sudo nano /etc/systemd/system/comfyui-startup.service
```

### 2. 添加以下内容

```ini
[Unit]
Description=ComfyUI and ComfyUIAPI Startup Service
After=network.target

[Service]
Type=forking
User=yian
WorkingDirectory=/home/yian/safone/comfyuiapi
ExecStart=/bin/bash /home/yian/safone/comfyuiapi/startup.sh
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 3. 启用并启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启动
sudo systemctl enable comfyui-startup.service

# 立即启动服务（测试用）
sudo systemctl start comfyui-startup.service

# 查看服务状态
sudo systemctl status comfyui-startup.service

# 查看日志
journalctl -u comfyui-startup.service -f
```

### 4. 管理命令

```bash
# 停止服务
sudo systemctl stop comfyui-startup.service

# 重启服务
sudo systemctl restart comfyui-startup.service

# 禁用开机自启动
sudo systemctl disable comfyui-startup.service
```

## 方法二：使用 crontab @reboot

这是一个较简单的方法，适合个人用户。

```bash
# 编辑当前用户的 crontab
crontab -e

# 添加以下行
@reboot /bin/bash /home/yian/safone/comfyuiapi/startup.sh

# 保存并退出
```

查看已设置的 crontab：

```bash
crontab -l
```

**强烈推荐使用方法一（systemd）**，因为它提供：

- ✅ 完善的日志管理
- ✅ 自动重启失败的服务
- ✅ 依赖管理（等待网络启动后再执行）
- ✅ 易于管理和调试
- ✅ 标准化的服务管理方式

## 注意事项

### 1. 确保脚本有执行权限

```bash
chmod +x /home/yian/safone/comfyuiapi/startup.sh
```

### 2. 测试脚本

在设置自启动前，先手动运行确保脚本正常工作：

```bash
/home/yian/safone/comfyuiapi/startup.sh
```

### 3. 检查日志目录

确保 `$HOME/safone/logs` 目录存在且有写入权限。

### 4. 环境变量

systemd 服务运行时的环境变量可能与用户登录时不同，如果遇到问题，可以在服务文件中添加：

```ini
[Service]
Environment="HOME=/home/yian"
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
```

## 故障排查

### 查看服务日志

```bash
# 查看最新日志
journalctl -u comfyui-startup.service -n 100

# 实时查看日志
journalctl -u comfyui-startup.service -f

# 查看所有日志（包括启动失败）
journalctl -u comfyui-startup.service --no-pager
```

### 检查服务状态

```bash
systemctl status comfyui-startup.service
```

### 常见问题

1. **服务启动失败**：检查 `startup.sh` 脚本路径是否正确
2. **权限问题**：确保 User 字段设置正确，且该用户有执行权限
3. **Conda 环境问题**：确保 conda 路径在 systemd 环境中可访问
4. **网络依赖**：如果服务需要网络，确保 `After=network.target` 已设置

## 验证开机自启动

重启系统后，检查服务是否自动启动：

```bash
# 重启系统
sudo reboot

# 重启后检查服务状态
systemctl status comfyui-startup.service

# 检查进程
ps aux | grep -E "(ComfyUI|comfyuiapi)"

# 检查日志
ls -lh ~/safone/logs/
```

