# Daily Fruit｜每日水果推荐

一个手机优先的 Vue 3 + FastAPI Web 原型：根据用户显式偏好、规则约束、历史与反馈，对候选水果组合评分，每天推荐两种水果并说明原因。

## 在线演示

- 前端：[GitHub Pages](https://dreamqwq114-del.github.io/daily-fruit/)
- 后端健康检查：[FastAPI Cloud](https://daily-fruit.fastapicloud.dev/health)

生产环境关闭 OpenAPI 文档；后端健康检查不会返回数据库地址或凭据。

## 当前状态

| 类别 | 当前事实 |
| --- | --- |
| 已实现 | 邮箱密码认证、用户资料与水果偏好、两种水果推荐、换一组、反馈、冻结后的历史记录、响应式 Web 页面 |
| 已参与推荐 | 地区、价格、甜/酸/质地、食用便利、尝鲜程度、喜欢/不喜欢/禁止、是否吃过、是否愿意尝试、季节与供应、历史和反馈 |
| 已保存但尚未参与推荐 | `consumption_horizon_days`、`market_access_level`、`accepts_online_purchase` |
| 兼容字段 | `city` 仍可用于城市级季节数据匹配，但当前页面不采集，演示季节数据也没有城市级记录 |
| 计划中 | 更细的本地可获得性、真实用户评估、购买与库存计划、PWA 或微信小程序 |
| 已知限制 | 24 种演示水果；部分属性为人工标注；价格和供应不是实时数据；当前不使用机器学习 |

## 核心功能

- Supabase Auth 邮箱密码注册、登录和会话恢复。
- 建立并更新地区、价格、口感、便利性、尝鲜和购买条件等资料。
- 标记特别喜欢、不喜欢或不能食用的水果，不强迫逐项填写全部水果。
- 水果态度只接受 `-1/0/1/2`（不喜欢/无所谓/喜欢/特别喜欢）或 `null`；
  特别喜欢会记录为已吃过，尝试意愿只描述明确没吃过的水果。
- 返回同一天稳定的两种水果推荐；主动换组会保存旧记录并尽量避开相同组合。
- 水果目录保留 24 个父水果；苹果、桃、葡萄、猕猴桃、石榴和火龙果的子类型只在父水果入选后解析，不会变成额外候选。
- 当前共有 13 个消费子类型；默认子类型的覆盖字段为空并继承父水果，非默认子类型只覆盖实际不同的字段。
- API 明确返回子类型的匹配模式与分数作用：苹果/桃/葡萄按质地匹配，猕猴桃按酸甜匹配；
  石榴只作过滤，火龙果的明确类型选择可覆盖父水果口感档案。
- 每种水果返回 2～4 条与实际评分贡献一致的理由。
- 记录吃过、喜欢、不喜欢、买不到、太贵、吃腻和换组等反馈。
- 查看 active 与 replaced 推荐历史；推荐项保存当时的水果详情、冷知识、解析类型、有效评分和模型/水果档案版本，不随当前目录编辑重算。

## 系统架构

```text
Vue 3 / GitHub Pages
  ├─ Supabase JS（仅 Auth）
  └─ HTTPS → FastAPI / FastAPI Cloud
                → Application Service（事务与流程编排）
                → 纯 Python 推荐核心
                → Repository / SQLAlchemy
                → Supabase PostgreSQL
```

GitHub Pages 只托管静态前端。浏览器不会直接读写业务表；业务数据统一经过 FastAPI。推荐核心接收普通数据对象，不持有数据库 `Session`，数据库加载和持久化由 Repository 与 Application Service 负责。

## 推荐算法

当前实现是白盒规则系统，不是机器学习。它先执行硬约束过滤，再枚举全部合法水果对，并从接近最高分的组合中进行可复现选择。

硬过滤包括：未启用水果、禁止食用、明确不愿尝试、明确不喜欢、供应状态为 unavailable，以及当前情境不允许的辅助型水果。保守尝鲜用户不会收到明确标记为没吃过的水果。非当季水果通常降分而不是直接删除；季节数据缺失也会使用保守的缺省分。

单水果个人匹配分为：

```text
U = 0.30 × explicit_preference
  + 0.25 × taste_match
  + 0.20 × availability_and_season
  + 0.10 × price_match
  + 0.10 × convenience_match
  + 0.05 × history_diversity
  + feedback_adjustment

availability_and_season = 0.45 × season_score
                        + 0.55 × availability_score
```

每一对合法水果的组合分为：

```text
Pair = 0.70 × mean(U1, U2)
     + 0.15 × nutrition_pair
     + 0.10 × sensory_category_diversity
     + 0.05 × pair_novelty
```

- `taste_match` 对已配置维度使用 `1 - abs(candidate - user)`；甜、酸、质地的内层权重为 `0.40`、`0.25`、`0.35`，未设置维度跳过并对剩余权重重新归一化，同时记录实际覆盖维度。
- `texture_score=0` 表示绵软，`1` 表示爽脆；旧 `soft_score`/`crisp_score` 与 `soft_preference`/`crisp_preference` 保留作兼容和回滚，不参与新的水果评分，旧用户冲突迁移不会被猜成 `0.50`。
- 资料页的甜度、酸味和质地滑块使用集中定义的五个水果语义锚点；锚点只帮助理解，不改变数值、seed 或推荐结果。未操作的滑块不会随其它资料保存，用户可清除为 `null`。
- `ripe_storage_score` 与 `typical_purchase_stage` 是水果资料和展示数据，不额外增加推荐外层权重；`ripening_note` 说明需要后熟或适食判断的水果。
- `nutrition_pair` 比较维生素 C、膳食纤维、钾、叶酸和类胡萝卜素的覆盖、多样性与数据置信度；能量不进入组合互补分。
- `sensory_category_diversity` 只比较甜、酸、质地的体验差异，不读取 `category` 或 `display_group`。
- `daily_recommendation_role` 只允许 `main` 与 `supporting`；默认普通推荐关闭 supporting。
- `display_group` 是消费者友好的展示分组，只用于目录、筛选和文案，不参与任何推荐评分；旧 `category` 仅作兼容字段并已标记 deprecated。
- 尝鲜是用户与水果之间的动态关系：明确 `has_tried=False` 且愿意尝试时才可标记为尝鲜状态。
- `discovery_level=0/1/2` 分别表示过滤明确未尝试、最多允许一个、最多允许两个明确未尝试水果；未知值不计入。
- `novelty_level` 表示普通用户第一次尝试该水果的接受门槛，目前仅作解释性元数据，不直接改变排序。
- `commonness_score` 是面向中国大陆普通商超和主流电商环境的演示性市场常见度，不是全球固定属性。
- 历史展示、吃过记录和反馈采用指数时间衰减；不同反馈有不同衰减周期。
- 所有合法组合都会被评分；算法在距离最佳分不超过既定阈值的组合中使用稳定 seed 选择。在候选数据、用户画像、历史和反馈等输入不变时，同一用户、日期和刷新序号可以复现结果。
- 推荐理由来自真实的加权贡献，不调用 LLM，也不生成医疗诊断或治疗承诺。

权重是人工设定的启发式参数。推荐分不是概率、准确率或医学评分，也尚未通过大规模真实用户实验验证。
固定画像审计会从 Git 中真实重放切换前版本，而不是只信任一份旧 JSON。当前 19 个
合成画像的结果仍高度集中，因而“测试通过”只证明规则合同成立，不代表推荐质量已被业务接受。

## 数据说明

| 数据文件 | 用途与语义 |
| --- | --- |
| `data/fruits_seed.json` | 24 种水果的身份、兼容口感字段、价格、便利性、角色和演示属性 |
| `data/fruit_profile_seed.json` | 24 种水果的人工校准甜度、酸度、质地、便利度、适食后常温保存档位和购买状态 |
| `data/fruit_selection_options_seed.json` | 13 个父水果内消费子类型；默认项覆盖字段为空 |
| `data/nutrition_demo.csv` | 六项 0～1 的无物理单位营养演示分数 |
| `data/seasons_demo.csv` | 地区、月份和季节分数；加载时补充演示供应状态与分数 |

`default_portion_grams` 是建议份量元数据，当前不参与营养计算。算法直接对
0～1 的无物理单位演示分数做 P05/P95 归一化；这些数值不代表真实的克或毫克，
也不构成每份营养计算。

项目中的季节、价格和部分营养数据用于软件功能演示，不构成医学或专业营养建议。营养字段是**归一化演示分数**，不表示每 100 克的真实克数或毫克数。

## 项目结构

```text
daily-fruit/
├─ backend/
│  ├─ app/
│  │  ├─ models/          # SQLAlchemy ORM
│  │  ├─ schemas/         # Pydantic 输入输出合同
│  │  ├─ routers/         # HTTP 路由
│  │  ├─ repositories/    # 数据查询与持久化
│  │  ├─ services/        # 业务编排、公开 Facade 与纯推荐核心
│  │  └─ seed/            # 演示数据校验与导入
│  ├─ alembic/            # 数据库 migration
│  ├─ tests/
│  └─ requirements.txt
├─ frontend/
│  ├─ src/                # Vue 页面、组件、路由与 API 客户端
│  ├─ tests/
│  └─ package.json
├─ data/                  # 水果、营养与季节演示数据
├─ docs/                  # 设计、审计与历史记录
└─ .github/workflows/     # GitHub Pages 部署
```

## 本地开发

需要 Python 3.11、Node.js 和 npm；仓库与部署运行时均固定 Python 3.11，其他 Python 版本需要自行验证。以下命令以仓库根目录为起点，PowerShell 示例不包含任何真实密钥。

### 后端

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

访问 `http://127.0.0.1:8000/health`。配置运行时数据库后，可用 `/health?check_database=true` 只检查连通性。

### 前端

```powershell
cd frontend
npm ci
npm run dev
```

访问 `http://localhost:5173`。开发服务器会把 `/api` 和 `/health` 代理到 `http://127.0.0.1:8000`。

### Migration 与 seed

只读查看当前 migration：

```powershell
cd backend
python -m alembic history
python -m alembic heads
python -m app.seed.seed_fruits --dry-run
```

执行 migration 前必须显式配置 `ALEMBIC_DATABASE_PURPOSE=migration` 与 `MIGRATION_DATABASE_URL`，并重新确认目标数据库；测试环境则使用 `ALEMBIC_DATABASE_PURPOSE=test` 与 `TEST_DATABASE_URL`。不要在不确定的数据库上执行 upgrade、downgrade 或 seed。

seed 写入器会同时读取 `fruits_seed.json`、`fruit_profile_seed.json`、冷知识和消费类型 seed；后者是甜、酸、质地、便利和适食后常温保存等人工标注的单一配置源。重复运行使用幂等 upsert，默认写入只允许本地可丢弃的 `daily_fruit_test`。向已确认的 Supabase 迁移库写入时，必须显式设置 `MIGRATION_DATABASE_URL`、`DAILY_FRUIT_ALLOW_MIGRATION_SEED=yes` 并传入 `--migration`。连接串只能来自本地环境或部署 Secret。

历史冻结采用两条路径：新推荐在应用层写入完整水果/冷知识 JSONB 快照；已有历史在结构迁移时冻结当时数据库中可重建的水果详情和按推荐日期选出的冷知识。已有记录的原始历史版本如果此前没有保存，无法被事后恢复，这一点不等同于重新计算旧推荐。

### 测试与构建

```powershell
cd backend
python -m pytest

cd ..\frontend
npm test
npm run build
```

数据库集成测试需要单独配置、可丢弃且名称包含 `daily_fruit_test` 的 PostgreSQL 数据库；测试配置会拒绝 Supabase 主机。

## 环境变量

真实值只放在被 Git 忽略的环境文件或部署平台 Secret 中。

后端变量见 `backend/.env.example`：

- `DATABASE_URL`：FastAPI 运行时 PostgreSQL 连接。
- `MIGRATION_DATABASE_URL`：Alembic migration 专用连接。
- `TEST_DATABASE_URL`：可丢弃测试库连接。
- `ALEMBIC_DATABASE_PURPOSE`：必须显式为 `migration` 或 `test`。
- `DATABASE_CONNECT_TIMEOUT_SECONDS`、`DATABASE_POOL_SIZE`、`DATABASE_MAX_OVERFLOW`：连接超时与池参数。
- `SUPABASE_URL`、`SUPABASE_JWT_AUDIENCE`：JWT issuer/JWKS 与 audience 校验。
- `FRONTEND_ORIGIN`：唯一允许的前端 CORS origin。
- `APP_TIMEZONE`、`APP_ENV`、`DEBUG`：时区和运行模式。

前端变量见 `frontend/.env.example`：

- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

所有 `VITE_` 变量都会进入公开构建产物，不能存放数据库密码、JWT secret、Supabase secret 或 service role key。

## API 与认证概览

| 类别 | 主要接口 |
| --- | --- |
| 健康检查 | `GET /health` |
| 当前用户 | `POST /api/me`、`GET /api/me`、`PUT /api/me` |
| 水果偏好 | `GET /api/me/fruit-preferences`、`PUT /api/me/fruit-preferences` |
| 水果目录 | `GET /api/fruits`、`GET /api/fruits/{fruit_id}` |
| 推荐 | `GET /api/recommendations/today`、`POST /api/recommendations/refresh` |
| 历史 | `GET /api/me/recommendations` |
| 推荐结果反馈 | `POST /api/recommendations/items/{item_id}/feedback` |
| 产品意见反馈 | `POST /api/product-feedback` |

除 `/health` 外，业务 API 要求有效 Supabase access token。FastAPI 校验签名、issuer、audience、有效期、角色和会话声明，并从 JWT `sub` 推导当前用户；客户端不能通过提交 `user_id` 冒充其他用户。开发环境可访问 `/docs`，生产环境关闭该入口。

## 部署

- `frontend` 由 `.github/workflows/deploy-pages.yml` 测试、构建并部署到 GitHub Pages。
- `backend` 以 Python 3.11 运行在 FastAPI Cloud，入口是 `backend/main.py` 暴露的 FastAPI 应用。
- 业务数据库与 Auth 使用 Supabase；前端 Supabase 客户端只负责 Auth。
- GitHub repository variables 只保存三个公开的 `VITE_` 值；数据库连接保存在 FastAPI Cloud Secret。
- 生产 CORS 由后端的 `FRONTEND_ORIGIN` 单一配置控制。

## 安全与隐私

- 禁止提交 `backend/.env`、数据库连接串、密码、高权限密钥或 token。
- Supabase service role 或数据库凭据只允许存在于后端安全环境，不能出现在浏览器。
- 当前业务表采用 RLS 且不向 `anon`、`authenticated` 或 `PUBLIC` 授予表权限；浏览器只能通过 FastAPI 访问业务数据。
- 后端拒绝匿名身份 token，并以 JWT 身份隔离用户资料、偏好、推荐和反馈。
- 当前内测部署预期关闭注册邮箱确认，使邮箱密码注册后立即获得 session。这是可变的 Auth 配置和已知身份验证限制，不是永久架构原则；仓库无法单独证明 Dashboard 当前开关状态，发布前应人工复核。关闭确认意味着系统不能证明注册者真正拥有该邮箱，也可能影响未来找回密码。
- 当前 Supabase 安全建议显示泄漏密码保护未启用，正式扩大用户范围前应评估并启用合适的密码保护策略。
- 不要在 Issue、日志、文档或截图中公开真实邮箱、UID、access token 或连接串。

## 测试范围

- 后端：配置安全、JWT、Schema、Repository、API、并发推荐、migration、seed 校验和推荐算法单元/回归测试。
- 前端：API 客户端、Auth、路由保护、页面状态、资料保存回显、推荐、历史和组件交互。
- 构建：GitHub Pages 工作流执行 `npm ci`、`npm test` 和 `npm run build`。

项目没有声明测试覆盖率百分比。部分数据库集成测试在未提供可丢弃测试库时会跳过。

## 每日冷知识数据

水果冷知识存放在 `data/fruit_facts_seed.json`，由 `public.fruit_facts` 表保存。当前为 24 种水果、每种 3 条、共 72 条演示文案；推荐接口以 `daily_fact` 返回当天稳定选择的一条，不参与过滤、评分或营养互补。

迁移和 seed 必须分开执行。先在后端目录运行 `python -m alembic upgrade head`，再运行 `python -m app.seed.seed_fruits --dry-run` 校验数据。默认 seed 只允许写入可丢弃的本地 `daily_fruit_test` 数据库；向已确认的 Supabase 迁移库写入时，必须在进程环境中显式设置 `MIGRATION_DATABASE_URL` 和 `DAILY_FRUIT_ALLOW_MIGRATION_SEED=yes`，并执行 `python -m app.seed.seed_fruits --migration`。连接串只放在本地环境或部署 Secret，不写入 Git。

文案中的季节、价格、营养和部分冷知识用于软件功能演示；涉及健康、药物、牙齿或过敏的内容需要来源审校，不构成医学或专业营养建议。

## 当前限制

- 仅有 24 种演示水果，水果口感、便利性、常见度、季节、供应和价格的部分值是人工标注。
- 营养值为 0～1 的无物理单位演示分数；`default_portion_grams` 当前不参与营养计算。
- 供应数据只有有限地区与月份粒度，价格不是实时市场数据。
- `market_access_level`、`accepts_online_purchase` 和 `consumption_horizon_days` 已保存但尚未进入推荐排序。
- 当前权重来自人工启发式设计，用户样本和线上评估指标有限，尚未经过真实用户实验验证。
- 注册邮箱确认属于当前内测配置；扩大公开使用前需要重新审查 Auth、密码保护和账号恢复策略。
- 本项目不构成医学、营养诊断或治疗建议。

## Roadmap

1. 将本地市场可获得性和网购条件接入规则，并明确数据来源与缺失值语义。
2. 建立真实用户反馈、推荐接受率、多样性和浪费减少等评估指标。
3. 在规则 V2 基线之外增加可解释的 Logistic Regression 对照实验，而不是直接引入复杂模型。
4. 支持库存、快过期水果和购买计划。
5. 评估 PWA 或微信小程序客户端，并复用现有 FastAPI 与推荐核心。
6. 抽离可复用推荐核心和公开评估工具。

## 贡献与许可证

提交改动前请阅读 [AGENTS.md](AGENTS.md)，保持分层、安全边界和测试合同。当前仓库尚未包含开源许可证。
