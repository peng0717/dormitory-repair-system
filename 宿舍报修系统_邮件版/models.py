"""
数据模型模块
定义所有数据库表结构
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# 创建数据库实例
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户表 - 存储所有系统用户"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin/worker/student
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    student_dormitory = db.relationship('StudentDormitory', backref='student', lazy=True)
    worker_info = db.relationship('Worker', backref='user', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Building(db.Model):
    """楼栋表"""
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    floors = db.Column(db.Integer, nullable=False)
    rooms_per_floor = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    dormitories = db.relationship('Dormitory', backref='building', lazy=True)
    workers = db.relationship('WorkerBuilding', backref='building', lazy=True)
    
    def __repr__(self):
        return f'<Building {self.name}>'


class Dormitory(db.Model):
    """宿舍表"""
    __tablename__ = 'dormitories'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, default=4)
    current_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    students = db.relationship('StudentDormitory', backref='dormitory', lazy=True)
    repair_requests = db.relationship('RepairRequest', backref='dormitory', lazy=True)
    
    def __repr__(self):
        return f'<Dormitory {self.building.name}-{self.room_number}>'


class StudentDormitory(db.Model):
    """学生宿舍关联表"""
    __tablename__ = 'student_dormitory'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dormitory_id = db.Column(db.Integer, db.ForeignKey('dormitories.id'), nullable=False)


class Worker(db.Model):
    """维修工信息表"""
    __tablename__ = 'workers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    specialty = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    buildings = db.relationship('WorkerBuilding', backref='worker', lazy=True)
    work_orders = db.relationship('WorkOrder', backref='worker', lazy=True)
    
    def __repr__(self):
        return f'<Worker {self.user.name}>'


class WorkerBuilding(db.Model):
    """维修工负责楼栋关联表"""
    __tablename__ = 'worker_building'
    
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)


class RepairItem(db.Model):
    """维修项目价格表"""
    __tablename__ = 'repair_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    
    # 关系
    repair_requests = db.relationship('RepairRequest', backref='repair_item', lazy=True)
    
    def __repr__(self):
        return f'<RepairItem {self.name}>'


class RepairRequest(db.Model):
    """报修申请表"""
    __tablename__ = 'repair_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dormitory_id = db.Column(db.Integer, db.ForeignKey('dormitories.id'), nullable=False)
    repair_item_id = db.Column(db.Integer, db.ForeignKey('repair_items.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)  # 图片路径，多个用逗号分隔
    status = db.Column(db.String(20), default='pending')  # pending/assigned/processing/completed/cancelled
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    student = db.relationship('User', foreign_keys=[student_id], backref='repair_requests')
    work_orders = db.relationship('WorkOrder', backref='repair_request', lazy=True)
    
    def __repr__(self):
        return f'<RepairRequest {self.id}>'


class WorkOrder(db.Model):
    """工单表"""
    __tablename__ = 'work_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('repair_requests.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'))
    status = db.Column(db.String(20), default='assigned')  # assigned/processing/completed/cancelled
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    admin_note = db.Column(db.Text)
    worker_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    bill = db.relationship('Bill', backref='order', uselist=False, lazy=True)
    review = db.relationship('Review', backref='order', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<WorkOrder {self.id}>'


class Bill(db.Model):
    """账单表"""
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='unpaid')  # paid/unpaid
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Bill {self.id}>'


class Review(db.Model):
    """评价表"""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Review {self.id}>'


class Complaint(db.Model):
    """投诉表"""
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/replied/closed
    reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    student = db.relationship('User', backref='complaints')
    
    def __repr__(self):
        return f'<Complaint {self.id}>'


class Announcement(db.Model):
    """公告表"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Announcement {self.title}>'


class PasswordReset(db.Model):
    """密码重置验证码表"""
    __tablename__ = 'password_resets'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def is_valid(self):
        """检查验证码是否有效"""
        return not self.used and datetime.now() < self.expires_at
    
    def __repr__(self):
        return f'<PasswordReset {self.email}>'
