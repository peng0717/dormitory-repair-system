# 路由模块初始化文件
from .auth import auth_bp
from .admin import admin_bp
from .worker import worker_bp
from .student import student_bp

__all__ = ['auth_bp', 'admin_bp', 'worker_bp', 'student_bp']
