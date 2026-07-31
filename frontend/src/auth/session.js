import { getSupabaseClient, isAuthConfigured } from './supabase.js'

export async function getSession() {
  if (!isAuthConfigured()) return null
  const { data, error } = await getSupabaseClient().auth.getSession()
  if (error) throw error
  return data.session
}

export async function getAccessToken() {
  return (await getSession())?.access_token ?? null
}

export async function isAuthenticated() {
  return Boolean(await getSession())
}

export async function signInWithPassword(email, password) {
  const { data, error } = await getSupabaseClient().auth.signInWithPassword({
    email,
    password,
  })
  if (error) throw error
  return data
}

export async function signUp(email, password) {
  const emailRedirectTo = `${window.location.origin}${import.meta.env.BASE_URL}#/auth/callback`
  const { data, error } = await getSupabaseClient().auth.signUp({
    email,
    password,
    options: { emailRedirectTo },
  })
  if (error) throw error
  return data
}

export async function signOut() {
  if (!isAuthConfigured()) return
  const { error } = await getSupabaseClient().auth.signOut()
  if (error) throw error
}

export async function clearLocalSession() {
  if (!isAuthConfigured()) return
  const { error } = await getSupabaseClient().auth.signOut({ scope: 'local' })
  if (error) throw error
}

export function onAuthStateChange(callback) {
  if (!isAuthConfigured()) return () => {}
  const { data } = getSupabaseClient().auth.onAuthStateChange(callback)
  return () => data.subscription.unsubscribe()
}
