# 产品意见反馈运维说明

第一版没有管理员页面或管理员 API。维护者在已确认目标环境的 Supabase SQL Editor 中，以只读查询为主查看留言，并按明确的数字 ID 手动更新处理状态。

产品意见反馈与推荐卡片上的 `liked`、`disliked`、`expensive` 等推荐结果反馈是两套独立数据。这里的留言只作为产品建议或问题记录，不会自动修改用户的水果偏好、推荐历史或推荐算法。

## 查看最新留言

```sql
SELECT
    pf.id,
    pf.category,
    pf.content,
    pf.page_key,
    pf.status,
    pf.created_at,
    pf.resolved_at,
    u.username
FROM public.product_feedback AS pf
LEFT JOIN public.users AS u
    ON u.id = pf.user_id
ORDER BY pf.created_at DESC
LIMIT 100;
```

必须使用 `LEFT JOIN`：删除业务用户后，反馈记录会保留但 `user_id` 可能变为 `NULL`。

## 查看未处理留言

```sql
SELECT
    pf.id,
    pf.category,
    pf.content,
    pf.page_key,
    pf.created_at,
    u.username
FROM public.product_feedback AS pf
LEFT JOIN public.users AS u
    ON u.id = pf.user_id
WHERE pf.status = 'new'
ORDER BY pf.created_at ASC
LIMIT 100;
```

## 标记为已处理

先通过查询确认要处理的留言，再把示例中的 `123` 替换成实际的数字主键。Supabase SQL Editor 直接执行时不要使用 `:feedback_id` 这类未绑定参数。

```sql
BEGIN;

UPDATE public.product_feedback
SET
    status = 'resolved',
    resolved_at = now()
WHERE id = 123
  AND status = 'new';

COMMIT;
```

提交前检查 UPDATE 的受影响行数；如果为 0，应先确认 ID 或当前状态，不要重复执行无条件更新。

## 重新打开留言

```sql
BEGIN;

UPDATE public.product_feedback
SET
    status = 'new',
    resolved_at = NULL
WHERE id = 123
  AND status = 'resolved';

COMMIT;
```

不要直接修改 `content`、`user_id` 或 `created_at`。第一版不提供自动通知、回复、删除、管理员 API 或防刷限流；如果后续需要这些能力，应单独设计权限、审计和数据保留策略。
