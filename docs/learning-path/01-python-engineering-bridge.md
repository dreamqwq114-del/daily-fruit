# Python 数据分析到后端工程桥

## 已经能复用的基础

IOM103 Python 1～9 已覆盖变量、容器、字典、条件循环、函数、模块、路径、异常和基础类。
这些内容可直接用于理解 Daily Fruit 的纯函数、dataclass、Repository 调用和测试。
IOM103 的模块运行方式与 pytest 也能迁移到当前仓库。

## 仍需补齐的概念

| 缺口 | Daily Fruit 中的入口 | 学到什么程度 |
| --- | --- | --- |
| 类型标注与可空值 | `recommendation_types.py` | 能解释 `T | None`、`Mapping`、`tuple`，不把 `None` 当 `False` |
| dataclass | 同上 | 能区分 frozen 领域对象与可变 ORM 对象 |
| Pydantic | `schemas/user.py`、`schemas/fruit.py` | 能解释请求校验、`exclude_unset` 与 API 合同 |
| 分层与依赖方向 | `routers/`、`services/`、`repositories/` | 能说出每层能做和不能做什么 |
| pytest 工程测试 | `backend/tests/` | 能读 fixture、monkeypatch、参数化与 xfail/skip 差别 |
| 配置与秘密 | `config.py`、`.env.example` | 能区分公开前端变量与后端 Secret |
| HTTP 与依赖注入 | `routers/`、`auth/` | 能解释状态码、认证主体和 Session 生命周期 |

## 四个桥接实验

所有实验只新增个人草稿或笔记，不修改生产代码。

### P1：可空状态表

- TODO：从 `FruitPreference` 抄出字段名，不抄实现注释；
- TODO：列出 `has_tried=None/False/True` 与 `willing_to_try` 的合法组合；
- TODO：解释为什么“未选择”不能写成 `preference_score=0`；
- 验收：能用自己的例子解释 unknown、neutral、untried、refusal、forbidden。

### P2：三种对象同名字段

- TODO：比较 ORM `UserFruitPreference`、Pydantic 偏好 Schema、领域
  `FruitPreference`；
- TODO：分别写出它们的创建者、生命周期和验证责任；
- 验收：不能说 Pydantic 会自动创建数据库列，也不能把 ORM 直接传入纯算法。

### P3：追踪一次部分更新

- TODO：从资料 API 追踪到 Schema、Service、Repository 和 commit；
- TODO：标出 `exclude_unset`、合并更新和 rollback 所在位置；
- 验收：能解释为什么省略字段与显式提交 `null` 不相同。

### P4：读一个失败测试

- TODO：选择一个偏好 Schema 测试，先预测输入和预期异常；
- TODO：运行单个测试，再定位被测模块实际查找的名字；
- TODO：写出若错误 patch 定义处而非 lookup 处会发生什么；
- 验收：能区分 FAILED、XFAIL、SKIPPED 与“没有运行”。

## 进入数据库桥之前

至少满足：IOM103 Python practice 不再有 xfailed；能独立写函数、异常与基础类；能读懂
上述四个实验涉及的类型标注。Pandas 和 sklearn 不作为这一步的硬前置。
