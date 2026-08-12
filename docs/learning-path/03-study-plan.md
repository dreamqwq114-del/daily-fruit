# 分阶段学习计划

本计划按“通过门槛再前进”，不按日历日期假设进度。每次 45～60 分钟；SQL 普通章节
本身约需 65～90 分钟，可拆成两次。

## 阶段 A：Python 基础，9～12 次

按 IOM103 Python 1～9 顺序完成 lesson → example → practice → test。每次优先完成一个
小节，不先看 answer。阶段末重新运行 Python 专项；36 个个人练习都应从 XFAIL 变成
PASSED。

## 阶段 B：SQL 主线，14～22 次

1. setup 与 diagnostic；
2. 第 1～4 章后完成 checkpoint 1；
3. 第 5～8 章后完成 checkpoint 2；
4. 第 9 章只在练习库事务中修改并默认 ROLLBACK；
5. 第 10 章综合练习；
6. 第 11 章 90 分钟独立测评。

MariaDB 服务当前未运行，因此先恢复本地练习环境并让 `verify_database.sql` 返回 PASS。
不要把启动数据库、完成教材和通过独立测评合并成一个结论。

## 阶段 C：两座桥，6～8 次

- Python 工程桥 P1～P4；
- PostgreSQL 桥 S1～S4；
- 每次只做一题并保留自己的解释；
- 不打开 Daily Fruit 的实现注释当作可复制答案，先预测再核对。

## 阶段 D：Daily Fruit 源码课，8～12 次

按 `docs/backend-course/README.md` 的 00→10 顺序。建议把以下四个节点作为阶段复盘：

1. 画出 Router → Service → Repository/Mapper → Core；
2. 解释 preference、has_tried、willingness 与 option policy；
3. 手算单水果分和 pair 分，并指出硬约束；
4. 读 migration/seed 测试，说明哪些证据只来自本地可丢弃数据库。

## 可并行的数据分析分支

Pandas、Matplotlib、sklearn 与综合项目继续按 IOM103 原顺序学习。它们帮助数据审计、
可视化和未来评估，但不是理解当前 Daily Fruit 白盒推荐核心的前置。不要因为还没学
完 KMeans 或逻辑回归就停止后端主线，也不要把当前规则系统称为机器学习。
