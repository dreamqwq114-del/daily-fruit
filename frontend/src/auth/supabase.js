import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = (import.meta.env?.VITE_SUPABASE_URL ?? '').trim().replace(/\/+$/, '')
const SUPABASE_PUBLISHABLE_KEY = (
  import.meta.env?.VITE_SUPABASE_PUBLISHABLE_KEY ?? ''
).trim()

let client

export class AuthConfigError extends Error {
  constructor() {
    super('在线登录服务尚未配置')
    this.name = 'AuthConfigError'
  }
}

export function isAuthConfigured() {
  return Boolean(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY)
}

export function getSupabaseClient() {
  if (!isAuthConfigured()) throw new AuthConfigError()

  client ??= createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  })
  return client
}

export { SUPABASE_URL }
