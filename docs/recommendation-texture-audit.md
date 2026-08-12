# 质地 V2 固定画像审计

## 结论

本审计验证“代码合同是否保持”，不宣称推荐质量、准确率或真实用户满意度合格。
V1 不再来自一份自报来源的 JSON：工具从固定 Git revision 解包旧源码，在临时目录
运行旧推荐核心，再把规范化结果与仓库基线比较。

统一输入为华东、2026-07-31、月份 7、固定 seed `20260731`。19 个合成画像覆盖原有
口感画像，以及低预算、重便利、明确不喜欢、禁止、没吃过且拒绝尝试、买不到、近期
重复和负反馈。当前硬过滤和软惩罚方向检查全部通过。

## 当前观察

- V1/V2 有序推荐组合变化：1/19，5.2632%；
- V2 的第一名共有 4 种，有序组合共有 4 种；
- `peach + papaya` 出现在 16/19 个画像中；
- 生产单水果权重、组合权重和近优阈值 `0.03` 未在本阶段修改。

机器可核对摘要：

- `ordered_recommendation_change_count=1`
- `ordered_recommendation_change_rate=0.052632`
- `v2_unique_top1_count=4`
- `v2_unique_ordered_pair_count=4`
- `v2_largest_ordered_pair_share=0.842105`

16/19 的集中度是业务审阅项。它可能表示 seed 数据和公式形成全局冠军，也可能反映
画像差异不足；仅凭单元测试无法作出业务接受决定。未取得验收标准前，不应为了让
输出“看起来更多样”而随手调权或改阈值。

## 运行方式

在 `backend/` 目录：

```powershell
.\.venv\Scripts\python.exe -m app.services.texture_baseline_replay --verify
.\.venv\Scripts\python.exe -m app.services.texture_profile_report
.\.venv\Scripts\python.exe -m pytest -q tests/services/test_texture_profile_report.py
```

这些命令只运行 Git/临时文件与纯算法，不连接数据库或远程 Supabase。基线需要更新时
使用 `--write`，随后必须审阅 revision、画像合同、公式和完整 diff，不能把重写 JSON
本身当作验收通过。
