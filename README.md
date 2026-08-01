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
- SQLAlchemy Model、Pydantic Schema 和五版 Alembic migration；
- 目标 Supabase 已迁移到 `public.alembic_version=0006`，并完成推荐 V2 数据字段升级；
- 八张业务表已启用 RLS，并对浏览器角色保持 deny-by-default；
- 目标 Supabase 已幂等写入 24 种水果、24 条营养和 48 条季节演示数据；
- 纯 Python 推荐算法已实现过滤、六项加权评分、历史和反馈调整、营养互补、
  可复现随机选择及结构化推荐理由；
- FastAPI 已实现用户、偏好、水果、今日推荐、换一组、历史和反馈接口；
- 今日推荐支持同日幂等和并发保护，换一组会替换旧组并记录 change_requested；
- Repository 批量预加载关联数据，数据库错误统一返回不泄漏内部信息的响应；
- Vue 通过统一 fetch 客户端调用 FastAPI，包含超时、错误、空状态和防重复提交；
- 阶段六已接入 Supabase Auth；业务 API 从已验证 JWT 推导当前用户，不再信任浏览器
  提交的 BIGINT user ID。

阶段三算法仍不访问数据库或网络。阶段六已把 Supabase Auth、受保护的 FastAPI Cloud
业务接口和 GitHub Pages 连成公网链路；浏览器仍不能直接访问业务表。

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

### 后端业务接口与认证

启动 FastAPI 后可以在 `http://127.0.0.1:8000/docs` 查看交互式接口文档。当前接口包括：

- `POST/GET/PUT /api/me`；
- `GET/PUT /api/me/fruit-preferences`；
- `GET /api/fruits`、`GET /api/fruits/{fruit_id}`；
- `GET /api/recommendations/today`；
- `POST /api/recommendations/refresh`；
- `GET /api/me/recommendations`；
- `POST /api/recommendations/items/{item_id}/feedback`。

除 `/health` 外，业务接口要求 Supabase Auth access token。Vue 只调用 FastAPI 处理业务
数据，Supabase 客户端只负责登录，不直接操作业务表。

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
SUPABASE_URL=
SUPABASE_JWT_AUDIENCE=authenticated
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

- `/login`：邮箱密码注册和登录；
- `/auth/callback`：保留给未来的密码找回等邮件回调，普通注册不使用此路由；
- `/onboarding`：创建或更新当前登录账号的水果档案；
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
- Vue 只使用公开 Supabase URL 和 publishable key 完成 Auth；
- FastAPI 校验 JWT 后连接 PostgreSQL，Vue 不直连业务表；
- 项目中的季节、价格和部分营养数据用于软件功能演示，不构成医学或专业营养建议。

### 邮箱密码注册

- 注册只提交邮箱和至少 8 位密码，不发送注册验证码或确认链接；
- 注册成功必须立即返回会话，然后进入建档页；
- 关闭注册邮箱确认意味着系统不能证明用户真正拥有该邮箱，填错邮箱可能影响未来找回密码；
- 忘记密码仍可以独立使用邮件，并仍受 Supabase 邮件限流影响；
- 匿名登录保持关闭，FastAPI 仍校验 JWT 并拒绝匿名身份。

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

## FastAPI Cloud 后端

后端地址为 `https://daily-fruit.fastapicloud.dev`。部署运行时固定为 Python 3.11。
云端入口 `backend/main.py` 运行完整且必须登录的 `app.main:app`，依赖继续由
`backend/requirements.txt` 管理。2026-07-31 的已上线版本验证结果是：

- `GET /health` 返回 HTTP 200，环境为 `production`；
- `GET /health?check_database=true` 返回 HTTP 200，数据库状态为 `ok`；
- 匿名访问 `/api/fruits` 和 `/api/me` 返回 401；
- `/docs` 和 `/openapi.json` 在 production 返回 404；
- `DATABASE_URL` 只保存在 FastAPI Cloud Secret 和本机被 Git 忽略的
  `backend/.env` 中；
- Supabase 已迁移到 `0006`，并在幂等 seed 后保持 24/24/48 演示数据不变；
- 线上 E2E 已验证登录、建档、两卡、刷新幂等、反馈、换组和历史数据，临时账号及
  行为数据随后已清理。

所有业务接口都要求有效 Supabase access token，不能以请求参数冒充其他用户。

## GitHub Pages 部署

GitHub Pages 只托管 `frontend` 生成的 Vue 静态文件。FastAPI 已独立部署，并继续由
FastAPI 连接 Supabase PostgreSQL；浏览器不能直接访问业务表，也不能持有数据库密码、
Supabase secret key 或 service role key。

项目站点地址为：

`https://dreamqwq114-del.github.io/daily-fruit/`

本地开发仍使用根路径和 Vite proxy：

```powershell
cd frontend
npm ci
npm run dev
```

验证普通 Sites 构建：

```powershell
npm test
npm run build
```

在 PowerShell 中验证 GitHub Pages 静态构建：

```powershell
$env:DEPLOY_TARGET = "github-pages"
$env:GITHUB_REPOSITORY = "dreamqwq114-del/daily-fruit"
$env:GITHUB_REPOSITORY_OWNER = "dreamqwq114-del"
$env:VITE_API_BASE_URL = "https://daily-fruit.fastapicloud.dev"
$env:VITE_SUPABASE_URL = "https://frzbbpocyzlqxljsrsiw.supabase.co"
$env:VITE_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_your_public_key"
npm run build
npm run preview -- --host 127.0.0.1
```

预览地址为 `http://127.0.0.1:4173/daily-fruit/`。结束预览后，如果继续在同一
PowerShell 中开发，可以清理本次构建变量：

```powershell
Remove-Item Env:DEPLOY_TARGET,Env:GITHUB_REPOSITORY,Env:GITHUB_REPOSITORY_OWNER, `
  Env:VITE_API_BASE_URL,Env:VITE_SUPABASE_URL,Env:VITE_SUPABASE_PUBLISHABLE_KEY `
  -ErrorAction SilentlyContinue
```

仓库的 `Settings → Pages → Source` 使用 **GitHub Actions**。推送 `frontend/**`
或部署工作流到 `main` 会自动部署，也可以在 Actions 页面手动运行
`Deploy frontend to GitHub Pages`（`workflow_dispatch`）。

公开配置通过仓库 variables 设置：`VITE_API_BASE_URL`、`VITE_SUPABASE_URL` 和
`VITE_SUPABASE_PUBLISHABLE_KEY`。它们分别是公开 FastAPI 地址、Supabase 项目 URL 和
浏览器可用 publishable key。FastAPI 地址必须是 HTTPS，例如
`https://api.example.com`；不得把 `DATABASE_URL`、数据库密码、secret key 或
service role key 放入 `VITE_` 变量。变量未设置时，生产页面不会请求访问者的
localhost；普通本地/Sites 构建会显示“在线服务尚未配置”，GitHub Pages 构建则会直接失败，
避免发布一个无法登录的版本。当前三个公开变量已配置，GitHub Pages 可以
完成登录、推荐和反馈；publishable key 不是高权限密钥。

FastAPI Cloud 已把 `https://dreamqwq114-del.github.io` 配置为允许的 CORS 来源；
Supabase Auth Site URL 和回调 allow list 已配置为 GitHub Pages 项目地址。该部署没有
修改或重新发布现有 ChatGPT Site。
## Recommendation V2 data contract

The V2 recommender keeps fruit identity, availability, familiarity, and data
quality as explicit columns. `data/fruits_seed.json` is the source for the
24 demonstration fruits; Alembic migrations `0005` and `0006` add the
corresponding database fields. `discovery_level`, `has_tried`,
`willing_to_try`, and `consumption_horizon_days` are
optional familiarity signals. A null signal means that the user has not
provided an answer and is not treated as a hard preference.

```text
U = .30 explicit + .25 taste + .20 availability_and_season
    + .10 price + .10 convenience + .05 history + feedback_adjustment
Pair = .70 mean(U) + .15 nutrition_pair + .10 sensory_category_diversity
       + .05 pair_novelty
```

Only inactive, forbidden, explicitly unwilling, unavailable, and
ordinary-context supporting fruits are filtered. An out-of-season fruit stays
eligible with a lower score. Nutrition is normalized over the complete active
library after portion conversion; missing values stay missing and lower
confidence. Recommendation reasons store the actual weighted contribution.

水果口味、便利性、常见度、尝鲜门槛及部分市场数据为推荐系统演示性结构化标注，不构成医学、营养或市场价格建议。
## V2 acceptance status

The repaired implementation and seven-profile acceptance run are recorded in
`docs/recommendation-v2-comparison.md`. The remote Daily Fruit project is at
Alembic version `0006`; the V2 seed was executed twice with counts remaining
24 fruits, 24 nutrition rows and 48 season rows. The seed updates only the
fruit, nutrition and season demonstration records and does not touch users or
recommendation history.

## Preferences settings data contract

The current settings page does not collect city; the legacy `users.city` value
is retained on partial updates and new API-created users use `UNKNOWN`. Region
selection uses the seven supported areas plus an internal unknown value. The
consumption horizon accepts only 2, 4, or 7 days and is stored for future
features; it is not part of recommendation ranking yet.

Fruit selections are explicit favorite, dislike, or forbidden states. Favorites
are limited to five. Unselected fruits clear only the managed score/forbidden
fields while preserving familiarity (`has_tried`, `willing_to_try`) and the
preference row itself. See
[`docs/preferences-ui-v1-audit.md`](docs/preferences-ui-v1-audit.md).
