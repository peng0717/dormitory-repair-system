"""
维修工路由模块
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from models import db, Worker, WorkOrder, Bill, RepairItem, Building, WorkerBuilding
from datetime import datetime
from functools import wraps

worker_bp = Blueprint('worker', __name__, url_prefix='/worker')


def worker_required(f):
    """维修工权限装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'worker':
            flash('您没有权限访问该页面', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@worker_bp.before_request
def check_worker():
    if not current_user.is_authenticated or current_user.role != 'worker':
        if request.endpoint and 'auth' not in request.endpoint:
            flash('您没有权限访问该页面', 'danger')
            return redirect(url_for('auth.login'))


@worker_bp.route('/')
def index():
    """维修工首页"""
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    if not worker:
        flash('维修工信息不存在', 'danger')
        return redirect(url_for('auth.login'))
    
    # 负责的楼栋
    building_ids = [wb.building_id for wb in worker.buildings]
    buildings = Building.query.filter(Building.id.in_(building_ids)).all() if building_ids else []
    
    # 工单统计
    assigned_count = WorkOrder.query.filter_by(worker_id=worker.id, status='assigned').count()
    processing_count = WorkOrder.query.filter_by(worker_id=worker.id, status='processing').count()
    completed_count = WorkOrder.query.filter_by(worker_id=worker.id, status='completed').count()
    
    # 最近工单
    recent_orders = WorkOrder.query.filter_by(worker_id=worker.id).order_by(WorkOrder.created_at.desc()).limit(5).all()
    
    return render_template('worker/index.html',
                         buildings=buildings,
                         assigned_count=assigned_count,
                         processing_count=processing_count,
                         completed_count=completed_count,
                         recent_orders=recent_orders)


@worker_bp.route('/work-orders')
def work_orders():
    """工单列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', '')
    
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    if not worker:
        flash('维修工信息不存在', 'danger')
        return redirect(url_for('auth.login'))
    
    query = WorkOrder.query.filter_by(worker_id=worker.id)
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(WorkOrder.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('worker/work_orders.html', orders=pagination.items, pagination=pagination, status=status)


@worker_bp.route('/work-orders/<int:id>/start', methods=['POST'])
def start_work(id):
    """开始维修"""
    order = WorkOrder.query.get_or_404(id)
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    if order.worker_id != worker.id:
        flash('您没有权限操作此工单', 'danger')
        return redirect(url_for('worker.work_orders'))
    
    order.status = 'processing'
    order.start_time = datetime.now()
    order.worker_note = request.form.get('note', '').strip()
    db.session.commit()
    flash('工单已开始维修', 'success')
    return redirect(url_for('worker.work_orders'))


@worker_bp.route('/work-orders/<int:id>/complete', methods=['POST'])
def complete_work(id):
    """完成维修"""
    order = WorkOrder.query.get_or_404(id)
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    if order.worker_id != worker.id:
        flash('您没有权限操作此工单', 'danger')
        return redirect(url_for('worker.work_orders'))
    
    order.status = 'completed'
    order.end_time = datetime.now()
    order.worker_note = request.form.get('note', '').strip()
    
    # 自动生成账单
    repair_item = order.repair_request.repair_item
    bill = None
    if not order.bill:
        bill = Bill(order_id=order.id, amount=repair_item.price)
        db.session.add(bill)
    
    db.session.commit()
    
    # 获取刚创建的账单
    if not bill:
        bill = order.bill
    
    # 发送邮件通知学生
    student = order.repair_request.student
    dormitory = order.repair_request.dormitory
    building = dormitory.building
    
    if student and student.email:
        subject = '您的报修已完成'
        content = f'''<p style="margin:0 0 16px 0;">{student.name}，您好，</p>
<p style="margin:0 0 24px 0;">您的报修申请已完成维修，请确认验收。</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border-radius:8px;margin-bottom:24px;">
<tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;"><span style="color:#6b7280;">维修地点</span></td>
<td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;text-align:right;">{building.name} {dormitory.room_number}</td></tr>
<tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;"><span style="color:#6b7280;">维修项目</span></td>
<td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;text-align:right;">{repair_item.name}</td></tr>
<tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;"><span style="color:#6b7280;">维修师傅</span></td>
<td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;text-align:right;">{current_user.name}</td></tr>
<tr><td style="padding:16px 20px;"><span style="color:#6b7280;">完成时间</span></td>
<td style="padding:16px 20px;text-align:right;">{order.end_time.strftime("%Y-%m-%d %H:%M")}</td></tr>
</table>
<div style="background:#ecfdf5;border:1px solid #10b981;border-radius:8px;padding:20px;text-align:center;margin-bottom:24px;">
<p style="margin:0 0 8px 0;color:#047857;font-size:14px;">本次维修费用</p>
<p style="margin:0;font-size:28px;font-weight:700;color:#059669;">¥{bill.amount}</p>
</div>
<p style="margin:0;color:#6b7280;font-size:14px;">请登录系统确认验收并完成缴费。</p>'''
        html_content = current_app.get_email_base_template(content)
        success, message = current_app.send_email(student.email, subject, html_content)
        if success:
            flash(f'工单已完成，已发送邮件通知学生', 'success')
        else:
            flash(f'工单已完成，但邮件通知发送失败', 'warning')
    else:
        flash('工单已完成', 'success')
    
    return redirect(url_for('worker.work_orders'))


@worker_bp.route('/work-orders/<int:id>/cancel', methods=['POST'])
def cancel_work(id):
    """取消工单"""
    order = WorkOrder.query.get_or_404(id)
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    if order.worker_id != worker.id:
        flash('您没有权限操作此工单', 'danger')
        return redirect(url_for('worker.work_orders'))
    
    order.status = 'cancelled'
    order.repair_request.status = 'cancelled'
    db.session.commit()
    flash('工单已取消', 'success')
    return redirect(url_for('worker.work_orders'))


@worker_bp.route('/bills')
def bills():
    """账单列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    if not worker:
        flash('维修工信息不存在', 'danger')
        return redirect(url_for('auth.login'))
    
    # 获取该维修工完成的工单对应的账单
    order_ids = [o.id for o in WorkOrder.query.filter_by(worker_id=worker.id, status='completed').all()]
    query = Bill.query.filter(Bill.order_id.in_(order_ids)) if order_ids else Bill.query.filter(db.false())
    
    pagination = query.order_by(Bill.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    total_amount = sum(b.amount for b in query.all())
    
    return render_template('worker/bills.html', bills=pagination.items, pagination=pagination, total_amount=total_amount)


@worker_bp.route('/repair-items')
def repair_items():
    """维修价格表"""
    items = RepairItem.query.order_by(RepairItem.id.desc()).all()
    return render_template('worker/repair_items.html', items=items)
