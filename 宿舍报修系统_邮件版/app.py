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
    # 邮件服务器配置（从环境变量读取，Replit中可在Secrets中配置）
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.qq.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')  # 
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')  # 
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '宿舍报修系统 <noreply@dormitory.com>')
    
    def send_email(to_email, subject, html_content):
        """
        发送邮件函数
        :param to_email: 收件人邮箱
        :param subject: 邮件主题
        :param html_content: HTML邮件内容
        :return: (success, message)
        """
        # 检查是否配置了邮件服务
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            return False, "邮件服务未配置，请在环境变量中设置MAIL_USERNAME和MAIL_PASSWORD"
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = app.config['MAIL_DEFAULT_SENDER']
            msg['To'] = to_email
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.sendmail(app.config['MAIL_USERNAME'], [to_email], msg.as_string())
            
            return True, "邮件发送成功"
        except smtplib.SMTPAuthenticationError:
            return False, "邮件认证失败，请检查邮箱用户名和SMTP授权码"
        except smtplib.SMTPException as e:
            return False, f"邮件发送失败：{str(e)}"
        except Exception as e:
            return False, f"邮件发送异常：{str(e)}"
    
    # 将发送邮件函数挂载到app上
    app.send_email = send_email
    
    # ========== 邮件模板函数 ==========
    
    def get_email_base_template(content):
        """邮件基础模板"""
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4a90d9 0%, #5b9bd5 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h2 {{ margin: 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; background: #4a90d9; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🏠 宿舍报修管理系统</h2>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>这是一封系统自动发送的邮件，请勿直接回复。</p>
                    <p>如有疑问，请联系宿舍管理员。</p>
                </div>
            </div>
        </body>
        </html>
        '''
    
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
