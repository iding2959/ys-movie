"""
启动脚本
"""
import uvicorn
import sys
import argparse
from config import settings

def main():
  """主函数"""
  parser = argparse.ArgumentParser(description='ComfyUI API 中间件服务')
  parser.add_argument('--host', default=settings.api_host, help='服务器主机地址')
  parser.add_argument('--port', type=int, default=settings.api_port, help='服务器端口')
  parser.add_argument('--comfyui-server', default=settings.comfyui_server, help='ComfyUI服务器地址')
  parser.add_argument('--reload', action='store_true', default=True, help='开启自动重载（默认开启）')
  parser.add_argument('--no-reload', action='store_true', help='关闭自动重载')
  parser.add_argument('--workers', type=int, default=1, help='工作进程数')
  parser.add_argument('--access-log', action='store_true', help='显示HTTP访问日志（默认关闭）')
  
  args = parser.parse_args()
  
  # 更新配置
  if args.comfyui_server:
    settings.comfyui_server = args.comfyui_server
  
  # 处理reload选项
  enable_reload = args.reload and not args.no_reload
  
  log_tip = "💡 提示: HTTP访问日志已关闭" if not args.access_log else ""
  reload_tip = "🔄 热重载: 已启用" if enable_reload else ""
  
  print(f"""
╔═══════════════════════════════════════════════════════╗
║         ComfyUI API 中间件服务 v1.6.6                  ║
╚═══════════════════════════════════════════════════════╝

📡 ComfyUI服务器: {settings.comfyui_server}
🌐 API服务地址: http://{args.host}:{args.port}
📚 API文档地址: http://{args.host}:{args.port}/docs
🎨 调试界面地址: http://{args.host}:{args.port}

正在启动服务...
{reload_tip}
{log_tip}
  """)
  
  # 启动服务
  uvicorn_config = {
    "app": "main:app",
    "host": args.host,
    "port": args.port,
    "reload": enable_reload,
    "workers": args.workers if not enable_reload else 1,
    "log_level": settings.log_level.lower(),
    "access_log": args.access_log
  }
  
  # 如果启用热重载，添加监控目录
  if enable_reload:
    uvicorn_config["reload_dirs"] = [".", "core", "static"]
  
  uvicorn.run(**uvicorn_config)

if __name__ == "__main__":
  main()
