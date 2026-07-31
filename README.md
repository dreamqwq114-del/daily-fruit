# 每日水果推荐系统

一个优先适配手机浏览器的 Vue 3 + FastAPI 教学项目。第一版计划使用条件过滤、加权评分、营养互补、历史去重和反馈调整，每天推荐两种水果，并给出可解释的推荐理由。

当前仅完成阶段一与最小可启动骨架：

- Vue 3 + Vite 单页占位界面；
- FastAPI `/health`；
- 环境变量读取与可选数据库连通性检查；
- 阶段一架构、ER、API 与实施计划；
- 尚未创建或修改任何 Supabase 数据表。

## 本地运行

### 后端

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

访问 `http://127.0.0.1:8000/health`。只有在 `backend/.env` 正确填写 `DATABASE_URL` 后，才能使用 `http://127.0.0.1:8000/health?check_database=true` 检查数据库连接。响应不会返回连接字符串。

### 前端

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

## 安全边界

- `backend/.env` 已被 Git 忽略，禁止提交；
- 浏览器端不保存数据库密码、Supabase secret key 或 service role key；
- 第一版由 FastAPI 连接 PostgreSQL，Vue 不直连业务表；
- 当前简化用户机制不属于生产级认证方案；
- 项目中的季节、价格和部分营养数据用于软件功能演示，不构成医学或专业营养建议。

详细设计见 [docs/stage-1-plan.md](docs/stage-1-plan.md)。

