"""
学生路由模块
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from models import db, User, Dormitory, StudentDormitory, RepairItem, RepairRequest, WorkOrder, Bill, Review, Complaint, Announcement
from datetime import datetime
from functools import wraps

student_bp = Blueprint('student', __name__, url_prefix='/student')


def student_required(f):
    """学生权限装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('您没有权限访问该页面', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@student_bp.before_request
def check_student():
    if not current_user.is_authenticated or current_user.role != 'student':
        if request.endpoint and 'auth' not in request.endpoint:
            flash('您没有权限访问该页面', 'danger')
            return redirect(url_for('auth.login'))


def get_student_dormitory():
    """获取学生所在的宿舍"""
    sd = StudentDormitory.query.filter_by(student_id=current_user.id).first()
    return sd.dormitory if sd else None


@student_bp.route('/')
def index():
    """学生首页"""
    dormitory = get_student_dormitory()
    
    # 我的报修统计
    my_requests = RepairRequest.query.filter_by(student_id=current_user.id).all()
    pending_count = sum(1 for r in my_requests if r.status == 'pending')
    processing_count = sum(1 for r in my_requests if r.status in ['assigned', 'processing'])
    completed_count = sum(1 for r in my_requests if r.status == 'completed')
    
    # 我的账单
    order_ids = [r.id for r in my_requests]
    my_orders = WorkOrder.query.filter(WorkOrder.request_id.in_(order_ids)).all() if order_ids else []
    order_ids = [o.id for o in my_orders]
    my_bills = Bill.query.filter(Bill.order_id.in_(order_ids)).all() if order_ids else []
    
    unpaid_count = sum(1 for b in my_bills if b.status == 'unpaid')
    unpaid_amount = sum(b.amount for b in my_bills if b.status == 'unpaid')
    
    # 最新公告
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
    
    return render_template('student/index.html',
                         dormitory=dormitory,
                         pending_count=pending_count,
                         processing_count=processing_count,
                         completed_count=completed_count,
                         unpaid_count=unpaid_count,
                         unpaid_amount=unpaid_amount,
                         announcements=announcements)


# ========== 报修申请 ==========

@student_bp.route('/repair-request/add', methods=['GET', 'POST'])
def repair_request_add():
    """提交报修申请"""
    dormitory = get_student_dormitory()
    if not dormitory:
        flash('您还没有分配宿舍，请联系管理员', 'warning')
        return redirect(url_for('student.index'))
    
    repair_items = RepairItem.query.all()
    
    if request.method == 'POST':
        repair_item_id = request.form.get('repair_item_id', type=int)
        description = request.form.get('description', '').strip()
        
        if not repair_item_id or not description:
            flash('请填写完整信息', 'danger')
            return redirect(url_for('student.repair_request_add'))
        
        repair_request = RepairRequest(
            student_id=current_user.id,
            dormitory_id=dormitory.id,
            repair_item_id=repair_item_id,
            description=description
        )
        db.session.add(repair_request)
        db.session.commit()
        
        # 发送邮件通知管理员
        admins = User.query.filter_by(role='admin').all()
        building = dormitory.building
        for admin in admins:
            if admin.email:
                subject = '新报修申请待处理'
                content = f'''<p style="margin:0 0 16px 0;">管理员，您好，</p>
<p style="margin:0 0 24px 0;">收到新的报修申请，请尽快安排处理。</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border-radius:8px;margin-bottom:24px;">
<tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;"><span style="color:#6b7280;">报修人</span></td>
<td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;text-align:right;">{current_user.name}</td></tr>
<tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;"><span style="color:#6b7280;">地点</span></td>
<td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;text-align:right;"><strong>{building.name} {dormitory.room_number}</strong></td></tr>
<tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;"><span style="color:#6b7280;">报修类型</span></td>
<td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;text-align:right;">{repair_request.repair_item.name}</td></tr>
<tr><td style="padding:16px 20px;"><span style="color:#6b7280;">问题描述</span></td>
<td style="padding:16px 20px;text-align:right;">{description or '无'}</td></tr>
</table>
<p style="margin:0;color:#6b7280;font-size:14px;">请登录系统进行工单分配。</p>'''
                html_content = current_app.get_email_base_template(content)
                current_app.send_email(admin.email, subject, html_content)
        
        flash('报修申请已提交，请等待管理员分配维修人员', 'success')
        return redirect(url_for('student.repair_requests'))
    
    return render_template('student/repair_request_form.html', repair_items=repair_items)


@student_bp.route('/repair-requests')
def repair_requests():
    """我的报修申请列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    query = RepairRequest.query.filter_by(student_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(RepairRequest.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('student/repair_requests.html', requests=pagination.items, pagination=pagination, status=status)


# ========== 工单管理 ==========

@student_bp.route('/work-orders')
def work_orders():
    """我的工单列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    my_requests = RepairRequest.query.filter_by(student_id=current_user.id).all()
    request_ids = [r.id for r in my_requests]
    
    query = WorkOrder.query.filter(WorkOrder.request_id.in_(request_ids)) if request_ids else WorkOrder.query.filter(db.false())
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(WorkOrder.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('student/work_orders.html', orders=pagination.items, pagination=pagination, status=status)


@student_bp.route('/work-orders/<int:id>/review', methods=['GET', 'POST'])
def add_review(id):
    """评价工单"""
    order = WorkOrder.query.get_or_404(id)
    
    # 验证是否是该学生的工单
    if order.repair_request.student_id != current_user.id:
        flash('您没有权限评价此工单', 'danger')
        return redirect(url_for('student.work_orders'))
    
    if order.status != 'completed':
        flash('只能在工单完成后才能评价', 'warning')
        return redirect(url_for('student.work_orders'))
    
    if order.review:
        flash('您已经评价过此工单', 'warning')
        return redirect(url_for('student.work_orders'))
    
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        
        if not rating or rating < 1 or rating > 5:
            flash('请选择1-5星的评分', 'danger')
            return redirect(url_for('student.add_review', id=id))
        
        review = Review(order_id=order.id, rating=rating, comment=comment)
        db.session.add(review)
        db.session.commit()
        flash('感谢您的评价', 'success')
        return redirect(url_for('student.work_orders'))
    
    return render_template('student/review_form.html', order=order)


# ========== 账单管理 ==========

@student_bp.route('/bills')
def bills():
    """我的账单列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    my_requests = RepairRequest.query.filter_by(student_id=current_user.id).all()
    request_ids = [r.id for r in my_requests]
    my_orders = WorkOrder.query.filter(WorkOrder.request_id.in_(request_ids)).all() if request_ids else []
    order_ids = [o.id for o in my_orders]
    
    query = Bill.query.filter(Bill.order_id.in_(order_ids)) if order_ids else Bill.query.filter(db.false())
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Bill.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    total_unpaid = sum(b.amount for b in query.filter_by(status='unpaid').all())
    total_paid = sum(b.amount for b in query.filter_by(status='paid').all())
    
    return render_template('student/bills.html', 
                         bills=pagination.items, 
                         pagination=pagination, 
                         status=status,
                         total_unpaid=total_unpaid,
                         total_paid=total_paid)


@student_bp.route('/bills/<int:id>/pay', methods=['POST'])
def pay_bill(id):
    """模拟缴费"""
    bill = Bill.query.get_or_404(id)
    
    # 验证是否是该学生的账单
    if bill.order.repair_request.student_id != current_user.id:
        flash('您没有权限操作此账单', 'danger')
        return redirect(url_for('student.bills'))
    
    if bill.status == 'paid':
        flash('该账单已支付', 'warning')
        return redirect(url_for('student.bills'))
    
    bill.status = 'paid'
    bill.paid_at = datetime.now()
    db.session.commit()
    flash(f'缴费成功，金额：{bill.amount}元', 'success')
    return redirect(url_for('student.bills'))


# ========== 投诉反馈 ==========

@student_bp.route('/complaints/add', methods=['GET', 'POST'])
def complaints_add():
    """提交投诉"""
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        
        if not content:
            flash('请填写投诉内容', 'danger')
            return redirect(url_for('student.complaints_add'))
        
        complaint = Complaint(student_id=current_user.id, content=content)
        db.session.add(complaint)
        db.session.commit()
        flash('投诉已提交，我们会尽快处理', 'success')
        return redirect(url_for('student.complaints'))
    
    return render_template('student/complaint_form.html')


@student_bp.route('/complaints')
def complaints():
    """我的投诉列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    query = Complaint.query.filter_by(student_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Complaint.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('student/complaints.html', complaints=pagination.items, pagination=pagination, status=status)


# ========== 公告 ==========

@student_bp.route('/announcements')
def announcements():
    """查看公告列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    pagination = Announcement.query.order_by(Announcement.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('student/announcements.html', announcements=pagination.items, pagination=pagination)
