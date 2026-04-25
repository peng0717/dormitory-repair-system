"""
认证路由模块
处理用户登录、登出、注册等认证功能
"""
import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, PasswordReset

# 创建蓝图
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录页面"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'欢迎回来，{user.name}！', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            if user.role == 'admin':
                return redirect(url_for('admin.index'))
            elif user.role == 'worker':
                return redirect(url_for('worker.index'))
            else:
                return redirect(url_for('student.index'))
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册页面（仅限学生）"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        
        errors = []
        if not username or len(username) < 3:
            errors.append('用户名至少需要3个字符')
        if not password or len(password) < 6:
            errors.append('密码至少需要6个字符')
        if password != confirm_password:
            errors.append('两次输入的密码不一致')
        if not name:
            errors.append('请输入真实姓名')
        
        if User.query.filter_by(username=username).first():
            errors.append('该用户名已被注册')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            name=name,
            role='student',
            phone=phone,
            email=email
        )
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """个人信息页面"""
    if request.method == 'POST':
        current_user.name = request.form.get('name', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        current_user.email = request.form.get('email', '').strip()
        
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if current_password or new_password:
            if not check_password_hash(current_user.password_hash, current_password):
                flash('当前密码错误', 'danger')
                return render_template('auth/profile.html')
            
            if len(new_password) < 6:
                flash('新密码至少需要6个字符', 'danger')
                return render_template('auth/profile.html')
            
            if new_password != confirm_password:
                flash('两次输入的新密码不一致', 'danger')
                return render_template('auth/profile.html')
            
            current_user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        flash('个人信息已更新', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')


# ========== 忘记密码 ==========

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """忘记密码页面"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('请输入邮箱地址', 'danger')
            return render_template('auth/forgot_password.html')
        
        # 查找用户
        user = User.query.filter_by(email=email).first()
        if not user:
            # 为了安全，不提示用户邮箱不存在
            flash('如果该邮箱已注册，我们将发送验证码到该邮箱', 'info')
            return render_template('auth/forgot_password.html')
        
        # 生成6位验证码
        code = ''.join(random.choices(string.digits, k=6))
        
        # 删除该邮箱之前的未使用验证码
        PasswordReset.query.filter_by(email=email, used=False).delete()
        
        # 创建新的验证码记录
        reset_record = PasswordReset(
            email=email,
            code=code,
            expires_at=datetime.now() + timedelta(minutes=10)  # 10分钟有效期
        )
        db.session.add(reset_record)
        db.session.commit()
        
        # 发送邮件
        subject = '密码找回 - 验证码'
        content = f'''<p style="margin:0 0 16px 0;">您好，</p>
<p style="margin:0 0 24px 0;">您正在申请重置账户密码。请使用以下验证码完成身份确认：</p>
<div style="background:#f3f4f6;border-radius:8px;padding:20px;text-align:center;margin:0 0 24px 0;">
<span style="font-size:32px;font-weight:700;color:#1d4ed8;letter-spacing:8px;">{code}</span>
</div>
<p style="margin:0 0 8px 0;color:#6b7280;font-size:14px;">验证码10分钟内有效，请勿告知他人。</p>
<p style="margin:0;color:#9ca3af;font-size:14px;">如果这不是您本人的操作，请忽略此邮件。</p>'''
        html_content = current_app.get_email_base_template(content)
        success, message = current_app.send_email(email, subject, html_content)
        
        if success:
            flash(f'验证码已发送到您的邮箱 {email}，请查收', 'success')
        else:
            flash(f'验证码已生成，但邮件发送失败：{message}。您可以继续下一步。', 'warning')
            print(f"邮件发送失败: {message}")
        
        # 跳转到验证页面
        return redirect(url_for('auth.verify_reset_code', email=email))
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/verify-reset-code', methods=['GET', 'POST'])
def verify_reset_code():
    """验证重置码页面"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    email = request.args.get('email', '').strip()
    if not email:
        flash('请先输入邮箱获取验证码', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        if not code:
            flash('请输入验证码', 'danger')
            return render_template('auth/reset_password.html', email=email, step='verify')
        
        # 查找验证码记录
        reset_record = PasswordReset.query.filter_by(email=email, code=code, used=False).first()
        
        if not reset_record:
            flash('验证码错误或已过期', 'danger')
            return render_template('auth/reset_password.html', email=email, step='verify')
        
        if not reset_record.is_valid():
            flash('验证码已过期，请重新获取', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # 标记为已使用
        reset_record.used = True
        db.session.commit()
        
        flash('验证码验证成功，请设置新密码', 'success')
        return redirect(url_for('auth.reset_password', email=email, token='verified'))
    
    return render_template('auth/reset_password.html', email=email, step='verify')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """重置密码页面"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    email = request.args.get('email', '').strip()
    token = request.args.get('token', '').strip()
    
    if not email or token != 'verified':
        flash('链接无效，请重新获取验证码', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not new_password or len(new_password) < 6:
            flash('密码至少需要6个字符', 'danger')
            return render_template('auth/reset_password.html', email=email, step='reset')
        
        if new_password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('auth/reset_password.html', email=email, step='reset')
        
        # 查找用户并更新密码
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('用户不存在', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('密码重置成功，请使用新密码登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', email=email, step='reset')
