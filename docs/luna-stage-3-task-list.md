# Luna：阶段三小任务列表

## 执行总则

- 一次只执行一个任务，测试通过并提交后再进入下一个；
- 每次开始前读取 `AGENTS.md`、阶段三设计和验收标准；
- 所有测试默认离线运行，不连接 Supabase；
- 不提前实现 API、Repository、Router 或 Vue 页面；
- 发现需要修改数据库结构或 seed 数据时立即停止并汇报。

## S3-00：冻结算法合同

允许修改：

- `docs/stage-3-recommendation-design.md`
- `docs/stage-3-acceptance-criteria.md`
- `docs/luna-stage-3-task-list.md`
- `AGENTS.md`

运行：`git diff --check`

验收：范围、公式、失败方式和后续任务边界明确。

## S3-01：输入对象、季节和归一化基础

允许修改：

- `backend/app/services/__init__.py`
- `backend/app/services/recommendation_types.py`
- `backend/app/services/recommendation_service.py`
- `backend/tests/services/test_season.py`
- `backend/tests/services/test_normalization.py`

禁止：完整选对、理由、数据库访问。

运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/services/test_season.py tests/services/test_normalization.py -q
```

停止条件：输入需要 SQLAlchemy Session 或需要修改数据库字段。

## S3-02：过滤、基础评分、历史和反馈

允许修改：

- `backend/app/services/recommendation_service.py`
- `backend/tests/services/test_filtering_and_scoring.py`

禁止：营养互补、最终理由、API。

验收：过滤规则、六项子分数、固定权重和反馈上下限均有测试。

## S3-03：选对、营养互补和可复现随机性

允许修改：

- `backend/app/services/recommendation_service.py`
- `backend/tests/services/test_pair_selection.py`

禁止：数据库持久化、换一组事务、API。

验收：结果恰好两项、无重复、互补改变第二项、相同种子可复现。

## S3-04：结构化理由

允许修改：

- `backend/app/services/recommendation_service.py`
- `backend/tests/services/test_reasons.py`

验收：每项 2 到 4 条，代码与分数组件一致，无医疗承诺。

## S3-05：完整回归和阶段审查

允许修改：

- `README.md`
- `AGENTS.md`
- 本阶段三个文档中的状态段落
- 仅限审查发现的 S3 缺陷相关文件

运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git status --short
```

验收：阶段三标准全部通过，未访问 Supabase，未实现 S4 内容。

## 当前下一任务

- `S3-00` 已由提交 `f15a680` 完成：阶段合同与门禁已冻结；
- `S3-01` 已由提交 `02eeb6a` 完成：输入对象、季节和归一化基础已测试；
- `S3-02` 已由提交 `2d3a3f3` 完成：过滤、基础评分、历史和反馈已测试；
- `S3-03` 已由提交 `325610e` 完成：选对、营养互补和种子复现已测试；
- `S3-04` 已由提交 `b765283` 完成：结构化理由和正式结果已测试；
- `S3-05` 已完成：边界补强提交为 `0822cda`，最终文档已记录全量回归结果；
- S3 完成后没有自动开始的下一任务，必须等待用户明确授权 S4 后端 API 阶段。
