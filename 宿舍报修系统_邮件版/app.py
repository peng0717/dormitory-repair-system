"""
宿舍报修管理系统 - 主应用入口
支持本地开发和云端部署（Render/PythonAnywhere）
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

# 导入数据库和模型
from models import db, User, Building, Dormitory, Worker, WorkerBuilding, RepairItem, Announcement


def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    
    # 安全密钥 - 云端部署时使用环境变量
    app.secret_key = os.environ.get('SECRET_KEY', 'dormitory-repair-system-secret-key-2024')
    
    # 数据库配置 - 使用相对路径确保云端可写
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'dormitory.db')
    
    # 确保instance目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化扩展
    db.init_app(app)
    
    # ========== 邮件配置 ==========
    # 邮件服务器配置
    app.config['MAIL_SERVER'] = 'smtp.qq.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '2790885462@qq.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'fncwiptujvaydhba')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', '2790885462@qq.com')
    
    def send_email(to_email, subject, html_content, retries=3):
        """
        发送邮件函数（带重试机制）
        """
        import time
        from email.utils import formataddr, formatdate
        
        for attempt in range(retries):
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = formataddr(('宿舍报修系统', app.config['MAIL_USERNAME']))
                msg['To'] = to_email
                msg['Date'] = formatdate(localtime=True)
                
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
                
                with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=30) as server:
                    server.set_debuglevel(0)
                    server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                    server.sendmail(app.config['MAIL_USERNAME'], [to_email], msg.as_string())
                
                return True, "邮件发送成功"
                
            except smtplib.SMTPAuthenticationError:
                return False, "认证失败：请确认授权码是否正确"
            except smtplib.SMTPException as e:
                error_msg = str(e)
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return False, f"邮件发送失败：{error_msg}"
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return False, f"网络连接异常，请稍后重试"
        
        return False, "发送超时，请检查网络"
    
    app.send_email = send_email
    
    # ========== 专业邮件模板 ==========
    
    def get_email_base_template(content, title="宿舍报修系统"):
        """专业邮件基础模板"""
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;padding:40px 20px;">
<tr>
<td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<!-- 顶部色块 -->
<tr>
<td style="background:linear-gradient(135deg,#3b82f6 0%,#1d4ed8 100%);padding:32px 40px;text-align:center;">
<div style="display:inline-block;width:48px;height:48px;background:rgba(255,255,255,0.2);border-radius:10px;line-height:48px;font-size:24px;">🏠</div>
<h1 style="margin:12px 0 0 0;color:#ffffff;font-size:22px;font-weight:600;letter-spacing:0.5px;">宿舍报修管理系统</h1>
</td>
</tr>
<!-- 主体内容 -->
<tr>
<td style="padding:36px 40px;color:#1f2937;font-size:15px;line-height:1.7;">
{content}
</td>
</tr>
<!-- 分割线 -->
<tr>
<td style="padding:0 40px;">
<div style="height:1px;background:#e5e7eb;"></div>
</td>
</tr>
<!-- 底部信息 -->
<tr>
<td style="padding:24px 40px;text-align:center;">
<p style="margin:0 0 8px 0;color:#6b7280;font-size:13px;">此邮件由系统自动发送，请勿直接回复</p>
<p style="margin:0;color:#9ca3af;font-size:12px;">© 2024 宿舍报修管理系统 · 保障宿舍生活品质</p>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>'''
    
    app.get_email_base_template = get_email_base_template
    
    # 配置Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 注册蓝图
    from routes import auth_bp, admin_bp, worker_bp, student_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(student_bp)
    
    # 根路径跳转
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.index'))
            elif current_user.role == 'worker':
                return redirect(url_for('worker.index'))
            else:
                return redirect(url_for('student.index'))
        return redirect(url_for('auth.login'))
    
    # 初始化数据库
    with app.app_context():
        db.create_all()
        init_data()
    
    return app


def init_data():
    """初始化默认数据"""
    # 检查是否已有管理员
    if User.query.filter_by(username='admin').first():
        return
    
    print("正在初始化系统数据...")
    
    # 创建管理员
    admin = User(
        username='admin',
        password_hash=generate_password_hash('admin123'),
        name='系统管理员',
        role='admin'
    )
    db.session.add(admin)
    
    # 创建示例楼栋
    buildings_data = [
        {'name': '1号楼', 'floors': 6, 'rooms_per_floor': 10},
        {'name': '2号楼', 'floors': 6, 'rooms_per_floor': 10},
        {'name': '3号楼', 'floors': 5, 'rooms_per_floor': 8},
        {'name': '4号楼', 'floors': 5, 'rooms_per_floor': 8},
    ]
    
    buildings = []
    for data in buildings_data:
        building = Building(**data)
        db.session.add(building)
        buildings.append(building)
    
    db.session.flush()
    
    # 创建示例宿舍
    for building in buildings:
        for floor in range(1, building.floors + 1):
            for room in range(1, building.rooms_per_floor + 1):
                room_number = f"{floor}0{room}" if room < 10 else f"{floor}{room}"
                dormitory = Dormitory(
                    building_id=building.id,
                    room_number=room_number,
                    capacity=4,
                    current_count=0
                )
                db.session.add(dormitory)
    
    # 创建维修项目
    repair_items_data = [
        {'name': '水管维修', 'price': 30.0, 'description': '水龙头、水管漏水维修'},
        {'name': '电路维修', 'price': 50.0, 'description': '插座、开关、灯具维修'},
        {'name': '门锁维修', 'price': 40.0, 'description': '门锁更换、钥匙配制'},
        {'name': '家具维修', 'price': 35.0, 'description': '桌椅、床柜维修'},
        {'name': '窗户维修', 'price': 25.0, 'description': '玻璃、窗框维修'},
        {'name': '空调维修', 'price': 60.0, 'description': '空调清洗、故障维修'},
        {'name': '热水器维修', 'price': 55.0, 'description': '热水器清洗、维修'},
        {'name': '网络维修', 'price': 20.0, 'description': '网络故障排查'},
    ]
    
    for item in repair_items_data:
        repair_item = RepairItem(**item)
        db.session.add(repair_item)
    
    # 创建示例公告
    announcements_data = [
        {
            'title': '欢迎使用宿舍报修系统',
            'content': '欢迎大家使用宿舍报修系统！如有任何问题，请联系宿舍管理员。\n\n系统使用说明：\n1. 学生可以在线提交报修申请\n2. 管理员分配维修人员后，会发送通知\n3. 维修完成后请及时评价\n4. 如有投诉建议，请通过投诉反馈功能提交'
        },
        {
            'title': '维修服务时间安排',
            'content': '日常维修服务时间为：周一至周五 8:00-18:00\n紧急维修可联系宿舍管理员。\n\n请同学们提前预约，合理安排报修时间。'
        },
        {
            'title': '系统使用注意事项',
            'content': '1. 请准确描述故障情况\n2. 上传清晰的故障图片有助于快速维修\n3. 维修完成后请及时确认和评价\n4. 如需取消报修，请提前通知'
        },
    ]
    
    for ann in announcements_data:
        announcement = Announcement(**ann)
        db.session.add(announcement)
    
    db.session.commit()
    print("数据初始化完成！")
    print("默认管理员账号: admin / admin123")


# 云端部署时使用gunicorn
# 本地开发时使用Flask内置服务器
app = create_app()

if __name__ == '__main__':
    # 本地开发模式
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
