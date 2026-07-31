# 阶段五：Vue 正式前端设计

## 1. 范围

S5 把现有 FastAPI 接口接入手机优先的 Vue 3 页面。前端只通过 HTTP 访问
FastAPI，不引入 Supabase 客户端，不修改数据库结构、迁移、RLS 或 seed。

本阶段实现四个路由：

- `/onboarding`：创建演示用户并设置水果偏好；
- `/`：查看今日两种推荐、换一组和提交反馈；
- `/preferences`：修改用户资料、口味和水果偏好；
- `/history`：查看最近推荐、理由、反馈和 replaced 状态。

本地 Vite 开发使用普通 history 路径。Sites 托管层不会把未知深层路径交给应用
Worker，因此生产构建使用 hash history（例如 `/#/onboarding`），保证刷新和直接打开
不会返回托管层 404；页面内的逻辑路由名称和访问控制保持不变。

## 2. 前端分层

```text
View -> Component -> frontend/src/api -> FastAPI
                    -> frontend/src/utils/user-session.js
```

- View 负责页面级加载、空状态和交互编排；
- Component 负责可复用展示与局部交互；
- `api/http.js` 统一处理 base URL、超时、JSON、HTTP 错误和网络错误；
- `api/user.js`、`fruit.js`、`recommendation.js` 只描述对应接口；
- `user-session.js` 只保存和校验设备本地演示 `user_id`；
- Vue 不计算推荐分数，不改写后端返回的推荐理由。

第一版不用 Pinia。跨页面只共享一个整数 user ID，其余状态按页面重新从 API
读取，避免浏览器状态与数据库状态分叉。

## 3. 请求与错误

- 所有请求默认 10 秒超时，使用 `AbortController`；
- 非 2xx 响应统一抛出包含 `status` 和安全中文信息的 `ApiError`；
- `404` 用户不存在时清除本地 user ID，并引导重新设置；
- `409` 显示候选不足或当前状态冲突，不静默重试；
- `422` 显示输入校验失败，不展示后端内部对象；
- `503` 和网络错误保留 user ID，提供重试；
- 提交期间禁用触发按钮，避免快速重复请求；
- 不把数据库 URL、Supabase key 或内部异常放入前端。

本地开发使用 Vite proxy 把 `/api` 和 `/health` 转发到
`http://127.0.0.1:8000`。部署时可通过公开的 `VITE_API_BASE_URL` 指向 FastAPI；
该值只是服务地址，不是秘密。

## 4. 用户会话

localStorage 只保存 `dailyFruit.userId`：

- 缺失或不是正整数时视为未设置；
- 未设置用户访问业务页时跳转 `/onboarding`；
- 已设置用户访问 `/onboarding` 时仍允许修改或重新开始；
- 只有明确的用户 `404` 才清除 ID，临时网络/数据库错误不得清除。

第一版 user ID 机制不是认证。S5 和后续私有演示都不能把写接口公开为生产服务。

## 5. 页面数据流

### Onboarding

1. 获取 active 水果；
2. 校验用户资料与 0 到 1 的口味值；
3. `POST /api/users`；
4. 立即保存返回的 user ID；
5. `PUT /api/users/{id}/fruit-preferences`；
6. 成功后进入 `/`。

若第 5 步失败，保留已创建用户并允许重新保存，禁止重复创建用户。

### Today

并行读取用户和今日推荐。推荐项按 `rank` 排序，每项显示水果、建议份量、
营养演示标签、2 到 4 条后端理由及反馈按钮。普通页面刷新只读取现有 active
推荐；“换一组”只调用 refresh 接口一次并整体替换页面数据。

### Preferences

并行读取用户、水果和现有偏好。用户资料与偏好是两个 API 写操作；如果第二个
失败，保留已成功的用户资料并给出可重试提示，不假装整体事务成功。

### History

读取最近 30 组，按后端顺序显示日期、refresh number、active/replaced、两种
水果、理由和反馈。空数组显示明确空状态。

## 6. 偏好表示

每种水果只有一个最终状态：

| 界面状态 | preference_score | is_forbidden |
|---|---:|---|
| 非常喜欢 | 2 | false |
| 喜欢 | 1 | false |
| 无所谓 | 0 | false |
| 不喜欢 | -1 | false |
| 不能食用 | 0 | true |

PUT 请求发送完整 `preferences` 数组；无所谓且不禁止的水果可以省略，以减少无意义
记录。同一 fruit ID 绝不重复。

## 7. 视觉与可访问性

- 以 320px 宽度为最低基线；
- 主操作触控高度至少 44px；
- 底部导航在手机安全区上方；
- 颜色不是状态的唯一表达，文字同时说明 active、replaced 和反馈；
- 表单字段均有 label，错误与状态消息使用合适的 live region；
- 图片缺失时使用文字首字和 CSS 占位，不请求随机外部图片；
- 营养值明确标记为归一化演示分数，不显示虚假的 mg/g 单位。

## 8. S5 安全边界

- 不修改 Supabase；
- 不新增 Alembic migration；
- 不引入认证或 Supabase JS；
- 不把生产 API 暴露给公开匿名用户；
- Sites 可发布私有 UI 预览，但只有 FastAPI 获得安全公网地址后才做真实线上联调。
