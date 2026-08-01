// Auth 会话的薄封装层：页面不直接调用 supabase.auth，便于统一测试和替换。
import { getSupabaseClient, isAuthConfigured } from './supabase.js'

export async function getSession() {
  // getSession 读取本地/刷新后的 Supabase 会话；未配置时安全返回 null。
  if (!isAuthConfigured()) return null
  const { data, error } = await getSupabaseClient().auth.getSession()
  if (error) throw error
  return data.session
}

export async function getAccessToken() {
  // FastAPI 只接收 access token，不接收前端 user_id 作为授权依据。
  return (await getSession())?.access_token ?? null
}

export async function isAuthenticated() {
  return Boolean(await getSession())
}

export async function signInWithPassword(email, password) {
  // 邮箱密码登录由 Supabase Auth 完成，业务资料仍需单独调用 FastAPI。
  const { data, error } = await getSupabaseClient().auth.signInWithPassword({
    email,
    password,
  })
  if (error) throw error
  return data
}

export async function signUp(email, password) {
  // 注册不附带 emailRedirectTo；是否立即返回 session 由 Supabase Auth 配置决定。
  const { data, error } = await getSupabaseClient().auth.signUp({
    email,
    password,
  })
  if (error) throw error
  return data
}

export async function signOut() {
  // 全局登出并清理 Supabase 会话。
  if (!isAuthConfigured()) return
  const { error } = await getSupabaseClient().auth.signOut()
  if (error) throw error
}

export async function clearLocalSession() {
  // 401 时只清理本地会话，避免失效 token 阻塞登录页跳转。
  if (!isAuthConfigured()) return
  const { error } = await getSupabaseClient().auth.signOut({ scope: 'local' })
  if (error) throw error
}

export function onAuthStateChange(callback) {
  // 返回取消订阅函数，组件卸载时可停止监听 Auth 状态变化。
  if (!isAuthConfigured()) return () => {}
  const { data } = getSupabaseClient().auth.onAuthStateChange(callback)
  return () => data.subscription.unsubscribe()
}
