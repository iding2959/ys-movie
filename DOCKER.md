# Docker 部署指南

本项目使用 `uv` 作为 Python 包管理器，Docker 镜像构建时会自动使用 `uv` 安装依赖。

## 快速开始

### 方式一：使用 Docker Compose（推荐）

1. **配置环境变量（可选）**

   创建 `.env` 文件（可选，如果不创建会使用默认值）：
   ```env
   COMFYUI_SERVER=192.168.48.123:8188
   COMFYUI_PROTOCOL=http
   COMFYUI_WS_PROTOCOL=ws
   LOG_LEVEL=INFO
   ```

2. **构建并启动服务**

   ```bash
   docker-compose up -d
   ```

3. **查看日志**

   ```bash
   docker-compose logs -f
   ```

4. **停止服务**

   ```bash
   docker-compose down
   ```

### 方式二：使用 Docker 命令

1. **构建镜像**

   ```bash
   docker build -t comfyui-api:latest .
   ```

2. **运行容器**

   ```bash
   docker run -d \
     --name comfyui-api \
     -p 12321:12321 \
     -e COMFYUI_COMFYUI_SERVER=192.168.48.123:8188 \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/outputs:/app/outputs \
     -v $(pwd)/workflows:/app/workflows \
     --restart unless-stopped \
     comfyui-api:latest
   ```

3. **查看日志**

   ```bash
   docker logs -f comfyui-api
   ```

4. **停止容器**

   ```bash
   docker stop comfyui-api
   docker rm comfyui-api
   ```

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `COMFYUI_COMFYUI_SERVER` | ComfyUI 服务器地址 | `192.168.48.123:8188` |
| `COMFYUI_COMFYUI_PROTOCOL` | ComfyUI HTTP 协议 | `http` |
| `COMFYUI_COMFYUI_WS_PROTOCOL` | ComfyUI WebSocket 协议 | `ws` |
| `COMFYUI_API_HOST` | API 服务监听地址 | `0.0.0.0` |
| `COMFYUI_API_PORT` | API 服务端口 | `12321` |
| `COMFYUI_LOG_LEVEL` | 日志级别 | `INFO` |

## 数据持久化

以下目录会被挂载到宿主机，确保数据持久化：

- `./uploads` - 上传的文件
- `./outputs` - 生成的输出文件
- `./workflows` - 工作流文件
- `./static` - 静态文件（前端界面）

## 访问服务

启动成功后，可以通过以下地址访问：

- **调试界面**: http://localhost:12321
- **API 文档**: http://localhost:12321/docs
- **健康检查**: http://localhost:12321/api/health

## 注意事项

1. **网络连接**：确保容器可以访问 ComfyUI 服务器地址
   - 如果 ComfyUI 在同一台机器上，使用 `host.docker.internal` 或宿主机 IP
   - 如果在 Docker 网络中，使用服务名或容器 IP

2. **端口映射**：默认映射端口为 `12321`，如需修改请修改 `docker-compose.yml` 中的端口映射

3. **数据备份**：定期备份 `uploads`、`outputs` 和 `workflows` 目录

4. **资源限制**：根据实际情况调整容器的 CPU 和内存限制

## 故障排查

### 查看容器状态

```bash
docker-compose ps
```

### 查看详细日志

```bash
docker-compose logs --tail=100 comfyui-api
```

### 进入容器调试

```bash
docker-compose exec comfyui-api bash
```

### 重启服务

```bash
docker-compose restart
```

