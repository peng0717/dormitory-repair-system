"""
管理员路由模块
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, Building, Dormitory, StudentDormitory, Worker, WorkerBuilding, RepairItem, RepairRequest, WorkOrder, Bill, Review, Complaint, Announcement
from datetime import datetime
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('您没有权限访问该页面', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# 管理员权限检查（仅针对该蓝图）
@admin_bp.before_request
def check_admin():
    if not current_user.is_authenticated or current_user.role != 'admin':
        if request.endpoint and 'auth' not in request.endpoint:
            flash('您没有权限访问该页面', 'danger')
            return redirect(url_for('auth.login'))


@admin_bp.route('/')
def index():
    """管理员首页"""
    total_students = User.query.filter_by(role='student').count()
    total_workers = User.query.filter_by(role='worker').count()
    total_buildings = Building.query.count()
    total_requests = RepairRequest.query.count()
    
    pending_orders = WorkOrder.query.filter_by(status='assigned').count()
    processing_orders = WorkOrder.query.filter_by(status='processing').count()
    completed_orders = WorkOrder.query.filter_by(status='completed').count()
    
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_bills = Bill.query.filter(Bill.created_at >= month_start).all()
    monthly_income = sum(b.amount for b in monthly_bills if b.status == 'paid')
    monthly_unpaid = sum(b.amount for b in monthly_bills if b.status == 'unpaid')
    
    reviews = Review.query.all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
    pending_complaints = Complaint.query.filter_by(status='pending').count()
    
    recent_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).limit(10).all()
    
    return render_template('admin/index.html',
                         total_students=total_students,
                         total_workers=total_workers,
                         total_buildings=total_buildings,
                         total_requests=total_requests,
                         pending_orders=pending_orders,
                         processing_orders=processing_orders,
                         completed_orders=completed_orders,
                         monthly_income=monthly_income,
                         monthly_unpaid=monthly_unpaid,
                         avg_rating=round(avg_rating, 1),
                         pending_complaints=pending_complaints,
                         recent_orders=recent_orders)


# ========== 楼栋管理 ==========

@admin_bp.route('/buildings')
def buildings():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    pagination = Building.query.order_by(Building.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/buildings.html', buildings=pagination.items, pagination=pagination)


@admin_bp.route('/buildings/add', methods=['GET', 'POST'])
def buildings_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        floors = request.form.get('floors', type=int)
        rooms_per_floor = request.form.get('rooms_per_floor', type=int)
        
        if not name or not floors or not rooms_per_floor:
            flash('请填写完整信息', 'danger')
            return redirect(url_for('admin.buildings_add'))
        
        building = Building(name=name, floors=floors, rooms_per_floor=rooms_per_floor)
        db.session.add(building)
        db.session.commit()
        flash('楼栋添加成功', 'success')
        return redirect(url_for('admin.buildings'))
    
    return render_template('admin/building_form.html', building=None)


@admin_bp.route('/buildings/<int:id>/edit', methods=['GET', 'POST'])
def buildings_edit(id):
    building = Building.query.get_or_404(id)
    if request.method == 'POST':
        building.name = request.form.get('name', '').strip()
        building.floors = request.form.get('floors', type=int)
        building.rooms_per_floor = request.form.get('rooms_per_floor', type=int)
        db.session.commit()
        flash('楼栋信息已更新', 'success')
        return redirect(url_for('admin.buildings'))
    return render_template('admin/building_form.html', building=building)


@admin_bp.route('/buildings/<int:id>/delete', methods=['POST'])
def buildings_delete(id):
    building = Building.query.get_or_404(id)
    if building.dormitories:
        flash('该楼栋下有宿舍，无法删除', 'danger')
        return redirect(url_for('admin.buildings'))
    db.session.delete(building)
    db.session.commit()
    flash('楼栋已删除', 'success')
    return redirect(url_for('admin.buildings'))


# ========== 宿舍管理 ==========

@admin_bp.route('/dormitories')
def dormitories():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    building_id = request.args.get('building_id', type=int)
    
    query = Dormitory.query
    if building_id:
        query = query.filter_by(building_id=building_id)
    
    pagination = query.order_by(Dormitory.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    buildings = Building.query.all()
    return render_template('admin/dormitories.html', dormitories=pagination.items, pagination=pagination, buildings=buildings, selected_building=building_id)


@admin_bp.route('/dormitories/add', methods=['GET', 'POST'])
def dormitories_add():
    buildings = Building.query.all()
    if request.method == 'POST':
        building_id = request.form.get('building_id', type=int)
        room_number = request.form.get('room_number', '').strip()
        capacity = request.form.get('capacity', type=int, default=4)
        
        if not building_id or not room_number:
            flash('请填写完整信息', 'danger')
            return redirect(url_for('admin.dormitories_add'))
        
        existing = Dormitory.query.filter_by(building_id=building_id, room_number=room_number).first()
        if existing:
            flash('该宿舍已存在', 'danger')
            return redirect(url_for('admin.dormitories_add'))
        
        dormitory = Dormitory(building_id=building_id, room_number=room_number, capacity=capacity)
        db.session.add(dormitory)
        db.session.commit()
        flash('宿舍添加成功', 'success')
        return redirect(url_for('admin.dormitories'))
    return render_template('admin/dormitory_form.html', dormitory=None, buildings=buildings)


@admin_bp.route('/dormitories/<int:id>/edit', methods=['GET', 'POST'])
def dormitories_edit(id):
    dormitory = Dormitory.query.get_or_404(id)
    buildings = Building.query.all()
    if request.method == 'POST':
        dormitory.building_id = request.form.get('building_id', type=int)
        dormitory.room_number = request.form.get('room_number', '').strip()
        dormitory.capacity = request.form.get('capacity', type=int, default=4)
        dormitory.current_count = request.form.get('current_count', type=int, default=0)
        db.session.commit()
        flash('宿舍信息已更新', 'success')
        return redirect(url_for('admin.dormitories'))
    return render_template('admin/dormitory_form.html', dormitory=dormitory, buildings=buildings)


@admin_bp.route('/dormitories/<int:id>/delete', methods=['POST'])
def dormitories_delete(id):
    dormitory = Dormitory.query.get_or_404(id)
    if dormitory.students or dormitory.repair_requests:
        flash('该宿舍有关联数据，无法删除', 'danger')
        return redirect(url_for('admin.dormitories'))
    db.session.delete(dormitory)
    db.session.commit()
    flash('宿舍已删除', 'success')
    return redirect(url_for('admin.dormitories'))


# ========== 学生管理 ==========

@admin_bp.route('/students')
def students():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    pagination = User.query.filter_by(role='student').order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/students.html', students=pagination.items, pagination=pagination)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
def students_add():
    dormitories = Dormitory.query.filter(Dormitory.current_count < Dormitory.capacity).all()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '123456')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        dormitory_id = request.form.get('dormitory_id', type=int)
        
        if not username or not name:
            flash('请填写用户名和姓名', 'danger')
            return redirect(url_for('admin.students_add'))
        
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('admin.students_add'))
        
        user = User(username=username, password_hash=generate_password_hash(password), name=name, role='student', phone=phone, email=email)
        db.session.add(user)
        db.session.flush()
        
        if dormitory_id:
            student_dorm = StudentDormitory(student_id=user.id, dormitory_id=dormitory_id)
            db.session.add(student_dorm)
            dormitory = Dormitory.query.get(dormitory_id)
            dormitory.current_count += 1
        
        db.session.commit()
        flash('学生添加成功，默认密码：123456', 'success')
        return redirect(url_for('admin.students'))
    return render_template('admin/student_form.html', student=None, dormitories=dormitories)


@admin_bp.route('/students/<int:id>/edit', methods=['GET', 'POST'])
def students_edit(id):
    student = User.query.get_or_404(id)
    dormitories = Dormitory.query.all()
    if request.method == 'POST':
        student.name = request.form.get('name', '').strip()
        student.phone = request.form.get('phone', '').strip()
        student.email = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()
        if new_password:
            student.password_hash = generate_password_hash(new_password)
            flash('密码已更新', 'info')
        db.session.commit()
        flash('学生信息已更新', 'success')
        return redirect(url_for('admin.students'))
    return render_template('admin/student_form.html', student=student, dormitories=dormitories)


@admin_bp.route('/students/<int:id>/delete', methods=['POST'])
def students_delete(id):
    student = User.query.get_or_404(id)
    if student.repair_requests:
        flash('该学生有报修记录，无法删除', 'danger')
        return redirect(url_for('admin.students'))
    db.session.delete(student)
    db.session.commit()
    flash('学生已删除', 'success')
    return redirect(url_for('admin.students'))


# ========== 维修工管理 ==========

@admin_bp.route('/workers')
def workers():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    pagination = User.query.filter_by(role='worker').order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/workers.html', workers=pagination.items, pagination=pagination)


@admin_bp.route('/workers/add', methods=['GET', 'POST'])
def workers_add():
    buildings = Building.query.all()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '123456')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        specialty = request.form.get('specialty', '').strip()
        building_ids = request.form.getlist('building_ids')
        
        if not username or not name:
            flash('请填写用户名和姓名', 'danger')
            return redirect(url_for('admin.workers_add'))
        
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('admin.workers_add'))
        
        user = User(username=username, password_hash=generate_password_hash(password), name=name, role='worker', phone=phone, email=email)
        db.session.add(user)
        db.session.flush()
        
        worker = Worker(user_id=user.id, specialty=specialty)
        db.session.add(worker)
        db.session.flush()
        
        for bid in building_ids:
            wb = WorkerBuilding(worker_id=worker.id, building_id=int(bid))
            db.session.add(wb)
        
        db.session.commit()
        flash('维修工添加成功，默认密码：123456', 'success')
        return redirect(url_for('admin.workers'))
    return render_template('admin/worker_form.html', worker=None, buildings=buildings)


@admin_bp.route('/workers/<int:id>/edit', methods=['GET', 'POST'])
def workers_edit(id):
    user = User.query.get_or_404(id)
    worker = Worker.query.filter_by(user_id=id).first()
    buildings = Building.query.all()
    if request.method == 'POST':
        user.name = request.form.get('name', '').strip()
        user.phone = request.form.get('phone', '').strip()
        user.email = request.form.get('email', '').strip()
        if worker:
            worker.specialty = request.form.get('specialty', '').strip()
            WorkerBuilding.query.filter_by(worker_id=worker.id).delete()
            for bid in request.form.getlist('building_ids'):
                wb = WorkerBuilding(worker_id=worker.id, building_id=int(bid))
                db.session.add(wb)
        new_password = request.form.get('password', '').strip()
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            flash('密码已更新', 'info')
        db.session.commit()
        flash('维修工信息已更新', 'success')
        return redirect(url_for('admin.workers'))
    return render_template('admin/worker_form.html', worker=user, buildings=buildings, worker_obj=worker)


@admin_bp.route('/workers/<int:id>/delete', methods=['POST'])
def workers_delete(id):
    user = User.query.get_or_404(id)
    worker = Worker.query.filter_by(user_id=id).first()
    if worker:
        WorkerBuilding.query.filter_by(worker_id=worker.id).delete()
        db.session.delete(worker)
    db.session.delete(user)
    db.session.commit()
    flash('维修工已删除', 'success')
    return redirect(url_for('admin.workers'))


# ========== 维修项目管理 ==========

@admin_bp.route('/repair-items')
def repair_items():
    items = RepairItem.query.order_by(RepairItem.id.desc()).all()
    return render_template('admin/repair_items.html', items=items)


@admin_bp.route('/repair-items/add', methods=['GET', 'POST'])
def repair_items_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', type=float)
        description = request.form.get('description', '').strip()
        
        if not name or price is None:
            flash('请填写完整信息', 'danger')
            return redirect(url_for('admin.repair_items_add'))
        
        item = RepairItem(name=name, price=price, description=description)
        db.session.add(item)
        db.session.commit()
        flash('维修项目添加成功', 'success')
        return redirect(url_for('admin.repair_items'))
    return render_template('admin/repair_item_form.html', item=None)


@admin_bp.route('/repair-items/<int:id>/edit', methods=['GET', 'POST'])
def repair_items_edit(id):
    item = RepairItem.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form.get('name', '').strip()
        item.price = request.form.get('price', type=float)
        item.description = request.form.get('description', '').strip()
        db.session.commit()
        flash('维修项目已更新', 'success')
        return redirect(url_for('admin.repair_items'))
    return render_template('admin/repair_item_form.html', item=item)


@admin_bp.route('/repair-items/<int:id>/delete', methods=['POST'])
def repair_items_delete(id):
    item = RepairItem.query.get_or_404(id)
    if item.repair_requests:
        flash('该维修项目已被使用，无法删除', 'danger')
        return redirect(url_for('admin.repair_items'))
    db.session.delete(item)
    db.session.commit()
    flash('维修项目已删除', 'success')
    return redirect(url_for('admin.repair_items'))


# ========== 报修申请管理 ==========

@admin_bp.route('/repair-requests')
def repair_requests():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    query = RepairRequest.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(RepairRequest.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/repair_requests.html', requests=pagination.items, pagination=pagination, status=status)


@admin_bp.route('/repair-requests/<int:id>/assign', methods=['GET', 'POST'])
def assign_worker(id):
    repair_request = RepairRequest.query.get_or_404(id)
    workers = Worker.query.all()
    if request.method == 'POST':
        worker_id = request.form.get('worker_id', type=int)
        note = request.form.get('note', '').strip()
        
        if not worker_id:
            flash('请选择维修工', 'danger')
            return redirect(url_for('admin.assign_worker', id=id))
        
        work_order = WorkOrder(request_id=id, worker_id=worker_id, status='assigned', admin_note=note)
        repair_request.status = 'assigned'
        db.session.add(work_order)
        db.session.commit()
        
        # 发送邮件通知维修工
        worker = Worker.query.get(worker_id)
        if worker and worker.user.email:
            dormitory = repair_request.dormitory
            building = dormitory.building
            subject = '【宿舍报修系统】您有新的维修任务'
            content = f'''
            <p>尊敬的{worker.user.name}：</p>
            <p>您有新的维修任务待处理。</p>
            <ul>
                <li><strong>楼栋宿舍：</strong>{building.name} - {dormitory.room_number}</li>
                <li><strong>报修类型：</strong>{repair_request.repair_item.name}</li>
                <li><strong>问题描述：</strong>{repair_request.description}</li>
            </ul>
            <p>请及时登录系统查看详情并处理。</p>
            '''
            html_content = current_app.get_email_base_template(content)
            success, message = current_app.send_email(worker.user.email, subject, html_content)
            if success:
                flash(f'工单已分配，已发送邮件通知维修工', 'success')
            else:
                flash(f'工单已分配，但邮件通知发送失败：{message}', 'warning')
        else:
            flash('工单已分配', 'success')
        
        return redirect(url_for('admin.work_orders'))
    return render_template('admin/assign_worker.html', repair_request=repair_request, workers=workers)


# ========== 工单管理 ==========

@admin_bp.route('/work-orders')
def work_orders():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    query = WorkOrder.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(WorkOrder.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/work_orders.html', orders=pagination.items, pagination=pagination, status=status)


@admin_bp.route('/work-orders/<int:id>/cancel', methods=['POST'])
def cancel_order(id):
    order = WorkOrder.query.get_or_404(id)
    order.status = 'cancelled'
    order.repair_request.status = 'cancelled'
    db.session.commit()
    flash('工单已取消', 'success')
    return redirect(url_for('admin.work_orders'))


# ========== 账单管理 ==========

@admin_bp.route('/bills')
def bills():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    query = Bill.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Bill.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    total_paid = sum(b.amount for b in Bill.query.filter_by(status='paid').all())
    total_unpaid = sum(b.amount for b in Bill.query.filter_by(status='unpaid').all())
    
    return render_template('admin/bills.html', bills=pagination.items, pagination=pagination, status=status, total_paid=total_paid, total_unpaid=total_unpaid)


# ========== 投诉管理 ==========

@admin_bp.route('/complaints')
def complaints():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    query = Complaint.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Complaint.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/complaints.html', complaints=pagination.items, pagination=pagination, status=status)


@admin_bp.route('/complaints/<int:id>/reply', methods=['POST'])
def complaints_reply(id):
    complaint = Complaint.query.get_or_404(id)
    reply = request.form.get('reply', '').strip()
    
    if not reply:
        flash('请输入回复内容', 'danger')
        return redirect(url_for('admin.complaints'))
    
    complaint.reply = reply
    complaint.status = 'replied'
    db.session.commit()
    
    # 发送邮件通知学生
    student = complaint.student
    if student and student.email:
        subject = '【宿舍报修系统】您的投诉已处理'
        content = f'''
        <p>尊敬的同学：</p>
        <p>您的投诉已得到处理回复。</p>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <p><strong>您的投诉：</strong></p>
            <p>{complaint.content}</p>
            <hr>
            <p><strong>管理员回复：</strong></p>
            <p>{reply}</p>
        </div>
        <p>如需进一步帮助，请联系宿舍管理员。</p>
        '''
        html_content = current_app.get_email_base_template(content)
        success, message = current_app.send_email(student.email, subject, html_content)
        if success:
            flash(f'已回复投诉，已发送邮件通知学生', 'success')
        else:
            flash(f'已回复投诉，但邮件通知发送失败：{message}', 'warning')
    else:
        flash('已回复投诉', 'success')
    
    return redirect(url_for('admin.complaints'))


@admin_bp.route('/complaints/<int:id>/close', methods=['POST'])
def complaints_close(id):
    complaint = Complaint.query.get_or_404(id)
    complaint.status = 'closed'
    db.session.commit()
    flash('投诉已关闭', 'success')
    return redirect(url_for('admin.complaints'))


# ========== 公告管理 ==========

@admin_bp.route('/announcements')
def announcements():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    pagination = Announcement.query.order_by(Announcement.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/announcements.html', announcements=pagination.items, pagination=pagination)


@admin_bp.route('/announcements/add', methods=['GET', 'POST'])
def announcements_add():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title or not content:
            flash('请填写完整信息', 'danger')
            return redirect(url_for('admin.announcements_add'))
        
        announcement = Announcement(title=title, content=content)
        db.session.add(announcement)
        db.session.commit()
        
        # 发送邮件通知所有学生
        students = User.query.filter_by(role='student').all()
        sent_count = 0
        failed_count = 0
        
        for student in students:
            if student.email:
                subject = f'【宿舍报修系统】新公告：{title}'
                email_content = f'''
                <p>尊敬的同学：</p>
                <p>系统发布了新公告，请登录查看详情。</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <h4 style="margin-top: 0;">{title}</h4>
                    <p>{content.replace(chr(10), '<br>')}</p>
                    <p style="color: #666; font-size: 12px;">发布时间：{announcement.created_at.strftime("%Y-%m-%d %H:%M")}</p>
                </div>
                '''
                html_content = current_app.get_email_base_template(email_content)
                success, message = current_app.send_email(student.email, subject, html_content)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
        
        if students:
            flash(f'公告发布成功，已发送邮件通知{sent_count}位学生（{failed_count}封发送失败）', 'success')
        else:
            flash('公告发布成功', 'success')
        
        return redirect(url_for('admin.announcements'))
    return render_template('admin/announcement_form.html', announcement=None)


@admin_bp.route('/announcements/<int:id>/edit', methods=['GET', 'POST'])
def announcements_edit(id):
    announcement = Announcement.query.get_or_404(id)
    if request.method == 'POST':
        announcement.title = request.form.get('title', '').strip()
        announcement.content = request.form.get('content', '').strip()
        db.session.commit()
        flash('公告已更新', 'success')
        return redirect(url_for('admin.announcements'))
    return render_template('admin/announcement_form.html', announcement=announcement)


@admin_bp.route('/announcements/<int:id>/delete', methods=['POST'])
def announcements_delete(id):
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    flash('公告已删除', 'success')
    return redirect(url_for('admin.announcements'))
