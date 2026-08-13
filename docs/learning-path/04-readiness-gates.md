# 学习就绪门槛

## Gate 1：Python

在 IOM103 根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/python/test_python_practice.py
```

通过条件：个人 practice 不再出现 XFAIL；能独立解释一个函数、一个异常路径和一个基础
class。当前实测是 `36 passed, 36 xfailed`，尚未通过个人门槛。

## Gate 2：SQL

通过条件：

- setup verify 为 PASS；
- 两个 checkpoint 独立完成；
- 第 11 章至少 80/100；
- 第 6 题安全门槛通过；
- 能解释 NULL、LEFT JOIN 重复、WHERE/HAVING 与 ROLLBACK。

当前进度表为空，MariaDB 服务也未监听；尚未通过。旧审计的答案实跑结果不能替代个人
空白作答。

## Gate 3：工程与 PostgreSQL 桥

通过条件：P1～P4、S1～S4 都有自己的无答案笔记；随机抽一题时能不看文档解释；能指出
MySQL、PostgreSQL、ORM、migration 四层之间的区别。

## Gate 4：Daily Fruit 只读理解

通过条件：

- 能画完整请求调用链；
- 能说明 `None` 与 `False`、硬约束与软评分、base 与 pair score；
- 能解释 `0014` 为什么先 precheck；
- 能解释类型 matching mode 与 score effect；
- 能指出测试通过不代表真实用户质量通过。

## Gate 5：本地验证

只在本仓库与确认过的可丢弃本地环境运行。最低命令：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests/services
.\.venv\Scripts\python.exe -m app.services.texture_baseline_replay --verify

cd ..\frontend
npm test
npm run build
```

数据库集成测试只有在目标明确、名称受保护、迁移 head 已核对后才运行。任何 skip 都要
单独报告，不能写成 pass。完成 Gate 5 仍只代表工程练习就绪，不代表可以操作远程环境。
