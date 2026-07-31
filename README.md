# 每日水果推荐系统

一个优先适配手机浏览器的 Vue 3 + FastAPI 教学项目。第一版计划使用条件过滤、加权评分、营养互补、历史去重和反馈调整，每天推荐两种水果，并给出可解释的推荐理由。

当前已完成阶段一、Supabase 审计、阶段二数据库基础结构、阶段三推荐算法、
阶段四后端 API 和阶段五 Vue 正式前端：

- Vue 3 + Vite 手机优先界面，包含初始设置、今日推荐、偏好和历史四个路由；
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
  可复现随机选择及结构化推荐理由；
- FastAPI 已实现用户、偏好、水果、今日推荐、换一组、历史和反馈接口；
- 今日推荐支持同日幂等和并发保护，换一组会替换旧组并记录 change_requested；
- Repository 批量预加载关联数据，数据库错误统一返回不泄漏内部信息的响应；
- Vue 通过统一 fetch 客户端调用 FastAPI，包含超时、错误、空状态和防重复提交；
- 第一版演示 user ID 只保存在 localStorage，不保存用户资料或任何数据库密钥。

阶段三算法仍不访问数据库或网络。阶段五没有修改数据库或 Supabase。当前 Sites
部署可以用于私有前端预览；在 FastAPI 获得安全的公网运行地址前，线上页面不会连接
本机后端，也不应对公网开放第一版无认证写接口。

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

### 后端业务接口

启动 FastAPI 后可以在 `http://127.0.0.1:8000/docs` 查看交互式接口文档。当前接口包括：

- `POST /api/users`、`GET/PUT /api/users/{user_id}`；
- `GET/PUT /api/users/{user_id}/fruit-preferences`；
- `GET /api/fruits`、`GET /api/fruits/{fruit_id}`；
- `GET /api/recommendations/today?user_id=1`；
- `POST /api/recommendations/refresh`；
- `GET /api/users/{user_id}/recommendations`；
- `POST /api/recommendations/items/{item_id}/feedback`。

第一版通过普通 `user_id` 演示流程，没有正式登录与授权，不应把写接口直接开放到公网。
Vue 只调用 FastAPI，不能直接操作 Supabase 业务表。

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

访问 `http://localhost:5173`。本地开发服务器会把 `/api` 和 `/health` 转发到
`http://127.0.0.1:8000`，因此需要同时启动 FastAPI。

前端路由：

- `/onboarding`：创建或恢复演示用户设置；
- `/`：今日两种水果、换一组和反馈；
- `/preferences`：修改用户与水果偏好；
- `/history`：查看 active/replaced 推荐、理由与反馈。

运行前端工具测试和生产构建：

```powershell
npm test
npm run build
```

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
