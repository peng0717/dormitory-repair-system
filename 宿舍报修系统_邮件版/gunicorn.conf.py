"""
Gunicorn 配置文件
用于生产环境部署
"""
import os

# 绑定地址 - Render 会通过 PORT 环境变量提供端口
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")

# 工作进程数
workers = 2

# 工作模式
worker_class = "sync"

# 超时设置
timeout = 120

# 访问日志
accesslog = "-"

# 错误日志
errorlog = "-"

# 日志级别
loglevel = "info"
