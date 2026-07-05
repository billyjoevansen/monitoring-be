-- =====================================================
-- Simpubes Serang — Seed User Admin/Kabid Pertama
-- Untuk deployment baru (fresh database)
-- Tidak ada fitur register, user pertama dibuat via SQL
-- =====================================================

-- =========================
-- PANDUAN PENGGUNAAN
-- =========================
-- 1. Ganti nilai di bawah sesuai kebutuhan:
--    - USER_UUID   : UUID unik (generate di https://www.uuidgenerator.net/)
--    - USER_EMAIL  : Email untuk login
--    - USER_PASS   : Password (minimal 8 karakter)
--    - USER_NAMA   : Nama lengkap
--    - USER_ROLE   : admin | kabid | kasie | bpp
-- 2. Jalankan file ini via Supabase SQL Editor
-- 3. Login ke aplikasi dengan email + password tersebut
-- 4. **Ubah password** setelah login pertama
-- =========================

-- GANTI SEMUA nilai placeholder di bawah!
-- =========================

-- 1. Insert ke auth.users (Supabase Auth — kredensial)
INSERT INTO auth.users (
  id,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  raw_app_meta_data,
  raw_user_meta_data,
  role,
  aud
) VALUES (
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'::uuid,  -- GANTI: UUID unik
  'admin@serang.go.id',                           -- GANTI: email login
  crypt('ganti_password_ini', gen_salt('bf')),     -- GANTI: password (minimal 8 karakter)
  now(),
  now(),
  now(),
  '{"provider":"email","providers":["email"]}'::jsonb,
  '{"nama":"Administrator"}'::jsonb,               -- GANTI: nama lengkap
  'authenticated',
  'authenticated'
);

-- 2. Insert ke public.users (profil)
INSERT INTO users (id, email, nama, role, is_active)
VALUES (
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'::uuid,   -- GANTI: UUID yang SAMA dengan di atas
  'admin@serang.go.id',                            -- GANTI: email yang SAMA
  'Administrator',                                 -- GANTI: nama yang SAMA
  'admin',                                         -- GANTI: admin | kabid | kasie | bpp
  true
);
