import { createServerClient as createSupabaseServerClient } from '@supabase/ssr'
import type { CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

export function createServerClient() {
  const cookieStore = cookies()
  
  return createSupabaseServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      get(name: string) {
        return cookieStore.get(name)?.value ?? null
      },
      set(name: string, value: string, options?: CookieOptions) {
        cookieStore.set({
          name,
          value,
          ...(options ?? {}),
        })
      },
      remove(name: string, options?: CookieOptions) {
        cookieStore.delete({
          name,
          ...(options ?? {}),
        })
      },
    },
  })
}

