/**
 * Real Supabase client, created only when VITE_SUPABASE_URL and
 * VITE_SUPABASE_ANON_KEY are both configured. AuthProvider.tsx checks
 * `isSupabaseConfigured` to decide between real Supabase Auth and the
 * local dev-mode fallback (see AuthProvider.tsx's DEV_MODE_ACCOUNTS) --
 * no other file needs to change when real credentials are added later.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(supabaseUrl as string, supabaseAnonKey as string)
  : null;
