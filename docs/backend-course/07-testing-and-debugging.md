# 测试与调试

## 学习目标

知道不同测试保护哪一层，能使用固定画像和 random seed 做 characterization，
并能定位 monkeypatch 的真实 lookup 位置。

## 测试分层

- `backend/tests/services/`：季节、营养、过滤、评分、配对、理由和固定画像；
- `backend/tests/test_recommendation_mapper.py`：ORM 图到领域对象的转换；
- `backend/tests/test_recommendation_application_invariants.py`：应用层不重试旧组合、
  不变量和失败回滚相关合同；
- `backend/tests/api/`：认证用户资料、水果、推荐、反馈和归属检查；
- `backend/tests/integration/`：安全迁移、migration round trip、seed 幂等等，只有
  配置安全本地测试数据库时才可执行；
- `backend/tests/test_model_metadata.py`、`test_schemas.py`、`test_database_config.py`：
  ORM 元数据、Pydantic 约束和连接配置的静态/单元保护。

## 真实测试案例

`test_pair_selection.py` 的 `test_same_random_seed_reproduces_pair` 保护 seeded
near-top 选择的确定性；`test_excluded_pair_is_never_restored_during_relaxation`
保护换组硬约束。`test_recommendation_application_invariants.py` 中的
`test_application_service_does_not_retry_with_modified_fruit_library` 防止应用层
删候选库后二次补丁计算。

`test_normalization.py` 验证 0～1 演示营养指数、P05/P95、缺失值和相同值 0.5；
`test_reasons.py` 验证理由数量、文本条件、贡献与结果一致。

`test_texture_profile_report.py` 还会调用 `texture_baseline_replay.py`：它使用
`git archive` 解包固定 revision，在临时目录中执行旧推荐模块，再与规范化 JSON 基线
逐字比较。19 个画像的日期、月份和 seed 固定；检查键也固定，避免删除反例后空集通过。
分布集中度只报告，不由测试自行宣称业务质量合格。

## monkeypatch 与 lookup 位置

测试必须 patch “被测试模块查找的名字”，不是定义函数的原始模块。例如应用层
测试 patch `app.services.recommendation_application_service.recommend_fruits`，
因为 `_calculate_recommendation` 从自己的模块命名空间读取它；如果 patch
`recommendation_service.recommend_fruits`，已导入的本地名称可能不会改变。

这条是通用 Python 测试知识；当前测试文件展示了真实 lookup 位置。

## 调试路径

```text
先复现最小失败测试
→ 判断是输入语义、mapper、算法、事务还是数据库环境
→ 查看完整异常和调用方
→ 不修改期望值掩盖失败
→ 修复后先跑定向测试，再跑完整套件
```

若失败来自未配置安全数据库，应记录跳过原因，不把“没有运行”写成“通过”。
测试配置将测试数据库限制为可丢弃本地库，并拒绝 Supabase 主机，这是当前安全边界。

## characterization 思路

在重构算法前，固定用户画像、日期、历史、反馈和 `random_seed`，记录水果 ID、分数、
理由和 contribution；重构后逐字段比较。这保护行为，而不是保护某种代码布局。

## 常见错误修改

- 看到失败就改测试期望，而不检查当前数据语义；
- 只测单函数，不测应用层 rollback 和资源归属；
- 用真实 Supabase 作为测试库；
- 把“没有异常”误认为事务已提交；
- patch 了定义处，却没有 patch 被测模块实际读取的名称。
- 只在 JSON 写入 `source_revision`，却没有实际执行那个 revision。

## 小练习

选择一个 `test_filtering_and_scoring.py` 测试，写出它保护的业务不变量；再选择一个
API 测试，说明它为什么不能只用纯算法 fixture 替代。

## 本章事实来源

| 教学结论 | 源文件 | 测试 | 事实类型 |
| --- | --- | --- | --- |
| 配对确定性 | `backend/tests/services/test_pair_selection.py` | `test_same_random_seed_reproduces_pair` | 测试事实 |
| excluded_pair 硬约束 | 同上 | `test_excluded_pair_is_never_restored_during_relaxation` | 测试事实 |
| 应用层不重试 | `backend/tests/test_recommendation_application_invariants.py` | named test | 测试事实 |
| mapper 合同 | `backend/tests/test_recommendation_mapper.py` | mapper tests | 测试事实 |
| 数据库隔离 | `backend/tests/test_database_config.py` | URL validation tests | 测试事实 |
| V1 真实重放 | `backend/tests/services/test_texture_profile_report.py` | baseline replay test | 测试事实 |

## 本章总结

测试是分层合同：服务测试保护规则，mapper 测试保护对象转换，应用测试保护事务，
API 测试保护身份和资源边界，集成测试才验证真实数据库行为。调试时先判断失败属于哪一层。
