// 浏览器端只初始化 Supabase Auth 客户端。
// 这里允许出现公开的 project URL 与 publishable key；数据库连接串、
// secret key 和 service_role key 永远不应放入 VITE_ 环境变量。
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = (import.meta.env?.VITE_SUPABASE_URL ?? '').trim().replace(/\/+$/, '')
const SUPABASE_PUBLISHABLE_KEY = (
  import.meta.env?.VITE_SUPABASE_PUBLISHABLE_KEY ?? ''
).trim()

let client

export class AuthConfigError extends Error {
  // 缺少公开 Auth 配置时，页面显示可理解的“未配置”，不发起无效请求。
  constructor() {
    super('在线登录服务尚未配置')
    this.name = 'AuthConfigError'
  }
}

export function isAuthConfigured() {
  // 只检查前端 Auth 所需的两个公开值，不代表后端数据库可用。
  return Boolean(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY)
}

export function getSupabaseClient() {
  // 延迟创建单例，避免在构建或未配置环境中初始化 Supabase。
  if (!isAuthConfigured()) throw new AuthConfigError()

  client ??= createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
    auth: {
      // 会话由 Supabase JS 持久化并自动刷新；业务表仍只能通过 FastAPI 访问。
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  })
  return client
}

export { SUPABASE_URL }
