# 每日水果推荐系统

一个优先适配手机浏览器的 Vue 3 + FastAPI 教学项目。第一版计划使用条件过滤、加权评分、营养互补、历史去重和反馈调整，每天推荐两种水果，并给出可解释的推荐理由。

当前已完成阶段一、Supabase 审计、阶段二数据库基础结构和阶段三推荐算法：

- Vue 3 + Vite 单页占位界面；
- FastAPI `/health`；
- runtime、migration、test 三类数据库连接配置；
- 测试数据库防误连 Supabase 正式项目；
- 环境变量读取与可选数据库连通性检查；
- 阶段一架构、ER、API 与实施计划；
- SQLAlchemy Model、Pydantic Schema 和两版 Alembic migration；
- 目标 Supabase 已迁移到 `public.alembic_version=0002`；
- 八张业务表已启用 RLS，并对浏览器角色保持 deny-by-default；
- 目标 Supabase 已幂等写入 24 种水果、24 条营养和 48 条季节演示数据；
- 纯 Python 推荐算法已实现过滤、六项加权评分、历史和反馈调整、营养互补、
  可复现随机选择及结构化推荐理由。

阶段三算法不访问数据库或网络。正式 API、推荐持久化和 Vue 业务页面尚未实现，
将在后续阶段通过 Repository 和 FastAPI 接入。

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

### 推荐算法测试

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/services -q
.\.venv\Scripts\python.exe -m pytest -q
```

算法入口是 `app.services.recommend_fruits`。它接收内存中的用户、水果和上下文对象，
每次返回两种不同水果、归一化分数和每项 2 到 4 条理由。传入 `random_seed` 可复现结果。

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

## 演示数据口径

- `data/fruits_seed.json` 提供水果属性、价格等级和食用便利度演示值；
- `data/nutrition_demo.csv` 的六项营养字段统一使用 0 到 1 的
  **归一化演示分数**，仅用于比较营养特点和测试互补算法，不表示每
  100 克的真实克数或毫克数；
- `data/seasons_demo.csv` 的月份、地区和季节分数用于验证跨年季节和
  地区匹配逻辑；
- 不得把这些演示值用于医疗判断、营养诊断或治疗建议。

### Seed 校验与本地测试

`--dry-run` 和 `--emit-sql` 都不会连接数据库：

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.seed.seed_fruits --dry-run
.\.venv\Scripts\python.exe -m app.seed.seed_fruits --emit-sql
```

本地写入只允许精确名为 `daily_fruit_test` 的 localhost 数据库，并要求
同时设置 `TEST_DATABASE_URL` 和
`DAILY_FRUIT_ALLOW_TEST_DATABASE_WRITE=yes`。正式 Supabase seed 必须先
核对 project ref 和 schema 版本，再使用经过审查的 SQL/连接流程；不要
把数据库密码写入命令、README 或 Git。

详细设计见 [docs/stage-1-plan.md](docs/stage-1-plan.md)。
