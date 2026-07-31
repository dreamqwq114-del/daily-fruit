# 每日水果推荐系统

一个优先适配手机浏览器的 Vue 3 + FastAPI 教学项目。第一版计划使用条件过滤、加权评分、营养互补、历史去重和反馈调整，每天推荐两种水果，并给出可解释的推荐理由。

当前已完成阶段一、Supabase 只读审计和阶段二的数据库配置合同：

- Vue 3 + Vite 单页占位界面；
- FastAPI `/health`；
- runtime、migration、test 三类数据库连接配置；
- 测试数据库防误连 Supabase 正式项目；
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

访问 `http://127.0.0.1:8000/health`。只有在 `backend/.env`
正确填写 `DATABASE_URL` 后，才能使用
`http://127.0.0.1:8000/health?check_database=true`
检查运行时数据库连接。响应不会返回连接字符串。

## 数据库配置

真实配置只写入已被 Git 忽略的 `backend/.env`：

```dotenv
DATABASE_URL=
MIGRATION_DATABASE_URL=
TEST_DATABASE_URL=
DATABASE_CONNECT_TIMEOUT_SECONDS=5
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
FRONTEND_ORIGIN=http://localhost:5173
APP_ENV=development
DEBUG=true
```

- `DATABASE_URL`：FastAPI 运行时连接；
- `MIGRATION_DATABASE_URL`：未来只供 Alembic 使用，不自动回退到运行时连接；
- `TEST_DATABASE_URL`：只供数据库集成测试使用，数据库名必须包含
  `daily_fruit_test`，并拒绝 `*.supabase.co` 和
  `*.pooler.supabase.com`；
- 三类 URL 均必须使用 `postgresql+psycopg://`；
- Supabase 连接必须显式启用 `sslmode=require`、`verify-ca` 或
  `verify-full`；
- `APP_ENV=production` 时必须设置 `DEBUG=false`。

当前 FastAPI 是持久运行的后端：网络支持 IPv6 时优先使用 Supabase
Direct Connection；IPv4 环境优先使用 Supavisor Session Pooler
（端口 `5432`）。本项目不使用端口 `6543` 的 Transaction Pooler
作为 FastAPI 或 Alembic 连接。具体地址从 Supabase Dashboard 的
Connect 面板复制，再将驱动前缀转换为 `postgresql+psycopg://`。

参考：[Supabase 数据库连接方式](https://supabase.com/docs/guides/database/connecting-to-postgres)。

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
