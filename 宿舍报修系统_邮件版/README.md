# 宿舍报修管理系统

一个基于 Flask 的宿舍报修管理系统，支持学生提交报修、管理员分配维修任务、维修工接单处理、账单管理和投诉反馈等功能。

## 功能特性

- **用户角色**：管理员、维修工、学生三种角色
- **报修管理**：学生在线提交报修，管理员分配维修人员
- **工单流转**：维修工接单、维修、完成、评价全流程
- **账单管理**：自动生成账单，支持模拟缴费
- **投诉反馈**：学生提交投诉，管理员回复处理
- **公告通知**：管理员发布公告，学生查看
- **响应式设计**：支持手机、平板、电脑访问

## 技术栈

- **后端**：Python Flask
- **数据库**：SQLite（无需额外安装）
- **前端**：Bootstrap 5 + Jinja2
- **认证**：Flask-Login

## 快速开始

### 本地运行

1. **Windows 用户**
   - 双击运行 `start.bat`
   - 或在命令行执行：`start.bat`

2. **Mac/Linux 用户**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

3. **手动启动**
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

### 访问系统

启动后访问：http://localhost:5000

**默认管理员账号**：
- 用户名：`admin`
- 密码：`admin123`

## 部署到云端

### Render 部署

1. 创建 GitHub 仓库并上传代码
2. 登录 [Render](https://render.com/)
3. 点击 "New" → "Web Service"
4. 连接 GitHub 仓库
5. 设置构建命令：`pip install -r requirements.txt`
6. 设置启动命令：`gunicorn app:app`
7. 点击 "Create Web Service"

### PythonAnywhere 部署

1. 登录 [PythonAnywhere](https://www.pythonanywhere.com/)
2. 打开 Bash 控制台
3. 克隆代码：`git clone <your-repo-url>`
4. 安装依赖：`pip install -r requirements.txt`
5. 创建 Web 应用并配置

## 项目结构

```
宿舍报修系统/
├── app.py              # 主应用入口
├── models.py           # 数据模型
├── routes/              # 路由模块
│   ├── auth.py         # 认证路由
│   ├── admin.py        # 管理员路由
│   ├── worker.py       # 维修工路由
│   └── student.py      # 学生路由
├── templates/          # HTML模板
│   ├── base.html
│   ├── auth/
│   ├── admin/
│   ├── worker/
│   └── student/
├── instance/           # 数据库文件
├── requirements.txt    # 依赖列表
├── gunicorn.conf.py    # Gunicorn配置
├── runtime.txt         # Python版本
├── start.bat           # Windows启动
└── start.sh            # Mac/Linux启动
```

## 角色功能

### 管理员
- 首页统计
- 学生管理
- 维修人员管理
- 楼栋管理
- 宿舍管理
- 报修申请审核与分配
- 工单管理
- 账单管理
- 维修价格设置
- 投诉反馈处理
- 公告发布

### 维修工
- 查看负责楼栋
- 工单接收与处理
- 维修完成操作
- 账单查看

### 学生
- 提交报修申请
- 查看工单进度
- 账单缴费
- 服务评价
- 投诉反馈
- 查看公告

## 注意事项

1. 首次运行会自动创建数据库和示例数据
2. 请及时修改管理员默认密码
3. SQLite 数据库文件位于 `instance/dormitory.db`
4. 云端部署时请设置 `SECRET_KEY` 环境变量

## 许可证

MIT License
