# 邮件服务配置说明

本文档说明如何在宿舍报修系统中配置邮件发送功能，支持 QQ 邮箱和 163 邮箱。

## 功能概述

配置完成后，系统将在以下场景自动发送邮件通知：

1. **学生提交报修** → 通知管理员
2. **工单分配维修工** → 通知维修工
3. **维修完成** → 通知学生并附带账单信息
4. **投诉被回复** → 通知学生
5. **发布新公告** → 通知所有已设置邮箱的学生
6. **用户找回密码** → 发送验证码

---

## QQ 邮箱配置步骤

### 1. 开启 SMTP 服务

1. 登录 [QQ 邮箱](https://mail.qq.com/)
2. 点击右上角 **设置** → **账户**
3. 找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务**
4. 开启 **SMTP 服务**
5. 按照提示发送短信验证
6. 系统会生成一个 **16 位授权码**（格式如：`abcdefghijklmnop`）

### 2. 复制授权码

生成的授权码请妥善保存，这是配置邮件服务的密码。

---

## 163 邮箱配置步骤

### 1. 开启 SMTP 服务

1. 登录 [163 邮箱](https://mail.163.com/)
2. 点击右上角 **设置** → **POP3/SMTP/IMAP**
3. 找到 **SMTP 服务**，点击 **开启**
4. 按照提示发送短信验证
5. 系统会生成一个 **授权码**

### 2. 注意事项

163 邮箱的 SMTP 配置与 QQ 邮箱略有不同，请注意端口设置。

---

## 在 Replit 中配置环境变量

### 方式一：使用 Replit Secrets（推荐）

1. 打开你的 Replit 项目
2. 点击左侧 **Secrets (Environment variables)**
3. 添加以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `MAIL_SERVER` | SMTP 服务器地址 | `smtp.qq.com` 或 `smtp.163.com` |
| `MAIL_PORT` | SMTP 端口 | `587`（TLS）或 `465`（SSL） |
| `MAIL_USE_TLS` | 是否使用 TLS | `True` 或 `False` |
| `MAIL_USERNAME` | 发送邮箱地址 | `your_email@qq.com` |
| `MAIL_PASSWORD` | SMTP 授权码（非邮箱密码） | `abcdefghijklmnop` |
| `MAIL_DEFAULT_SENDER` | 发件人显示名称 | `宿舍报修系统 <your_email@qq.com>` |

### 方式二：在代码中配置

如果你不想使用环境变量，也可以直接修改 `app.py` 中的配置：

```python
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@qq.com'
app.config['MAIL_PASSWORD'] = 'your_auth_code'
app.config['MAIL_DEFAULT_SENDER'] = '宿舍报修系统 <your_email@qq.com>'
```

---

## 常用 SMTP 配置

### QQ 邮箱
```
MAIL_SERVER = smtp.qq.com
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = your_email@qq.com
MAIL_PASSWORD = 授权码（16位）
```

### 163 邮箱
```
MAIL_SERVER = smtp.163.com
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = your_email@163.com
MAIL_PASSWORD = 授权码
```

### Gmail（备选，需要科学上网）
```
MAIL_SERVER = smtp.gmail.com
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = your_email@gmail.com
MAIL_PASSWORD = 应用专用密码
```

---

## 安装依赖

确保已安装邮件相关的 Python 包：

```bash
pip install Flask-Mail==0.9.1
```

或在 Replit 的 `requirements.txt` 中添加：
```
Flask-Mail==0.9.1
```

---

## 测试邮件发送

### 方法一：通过忘记密码功能测试

1. 登录系统
2. 点击"忘记密码"
3. 输入已配置邮箱
4. 检查邮箱是否收到验证码

### 方法二：手动测试

在 Python 控制台中执行：

```python
from app import app
with app.app_context():
    success, message = app.send_email(
        'test@example.com',
        '测试邮件',
        '<h1>这是一封测试邮件</h1><p>如果收到此邮件，说明配置成功！</p>'
    )
    print(message)
```

---

## 常见问题

### 1. 邮件发送失败：认证失败

**原因**：授权码错误
**解决**：重新获取 QQ 邮箱的授权码，确保使用的是 16 位授权码而非邮箱密码

### 2. 邮件发送失败：连接超时

**原因**：网络问题或 SMTP 端口被阻止
**解决**：
- 检查网络连接
- 尝试更换端口（587 → 465）
- 如果在企业网络，可能需要联系网管开放 SMTP 端口

### 3. 收件箱没有收到邮件

**可能原因**：
- 邮件被误判为垃圾邮件
- 邮箱地址错误
- 邮件服务未正确配置

**解决**：
- 检查垃圾邮件文件夹
- 确认邮箱地址正确
- 验证环境变量配置

### 4. 如何设置管理员邮箱？

管理员邮箱可以在用户管理中设置：
1. 以管理员身份登录
2. 进入"学生管理"或"维修工管理"
3. 编辑用户信息，填写邮箱

### 5. 学生没有收到通知？

**可能原因**：
- 学生没有在个人信息中填写邮箱
- 学生填写的邮箱地址错误
- 邮件发送失败

**解决**：提醒学生在"个人信息"页面填写正确的邮箱地址

---

## 安全建议

1. **不要将授权码提交到 GitHub**：将包含敏感信息的文件添加到 `.gitignore`
2. **定期更换授权码**：建议每 3-6 个月更换一次
3. **使用专用邮箱**：建议创建一个专门用于发送系统邮件的邮箱
4. **监控邮件发送**：如果发现异常发送记录，立即更换授权码

---

## 邮件模板说明

系统使用统一的邮件模板，包括：
- 统一的页眉（系统名称和图标）
- 专业的内容布局
- 响应式设计，适配各种设备

邮件内容已针对中文优化，包含必要的操作引导和联系信息。

---

如有问题，请联系系统管理员或查看代码 `app.py` 中的 `send_email` 函数实现。
