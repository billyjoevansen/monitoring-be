-- =====================================================
-- Simpubes Serang — Database Schema
-- Full snapshot: semua tabel, RLS, indexes, triggers
-- Jalankan sekali saat setup awal database
-- =====================================================

-- =========================
-- 1. TABLES
-- =========================

-- 1.1 users (profil, FK ke auth.users)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE,
  nama TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'kabid', 'kasie', 'bpp')),
  kecamatan TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.2 activity_logs
CREATE TABLE IF NOT EXISTS activity_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  user_email TEXT,
  user_nama TEXT,
  user_role TEXT,
  action TEXT NOT NULL,
  detail TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 1.3 reconciliation_archives
CREATE TABLE IF NOT EXISTS reconciliation_archives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  user_nama TEXT NOT NULL,
  nama_arsip TEXT NOT NULL,
  summary JSONB DEFAULT '{}'::jsonb,
  detail JSONB DEFAULT '[]'::jsonb,
  kecamatan TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 1.4 classification_archives
CREATE TABLE IF NOT EXISTS classification_archives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  user_nama TEXT NOT NULL,
  reconciliation_id UUID REFERENCES reconciliation_archives(id) ON DELETE SET NULL,
  nama_arsip TEXT NOT NULL,
  summary JSONB DEFAULT '{}'::jsonb,
  detail JSONB DEFAULT '[]'::jsonb,
  model_info JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 1.5 supporting_documents
CREATE TABLE IF NOT EXISTS supporting_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  document_type TEXT NOT NULL CHECK (document_type IN ('rdkk', 'siverval')),
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size INTEGER,
  kecamatan TEXT[],
  total_petani INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 1.6 kecamatan_desa
CREATE TABLE IF NOT EXISTS kecamatan_desa (
  id SERIAL PRIMARY KEY,
  kode_desa TEXT NOT NULL UNIQUE,
  nama_desa TEXT NOT NULL,
  kecamatan TEXT NOT NULL
);

-- =========================
-- 2. FUNCTIONS & TRIGGERS
-- =========================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =========================
-- 3. ROW LEVEL SECURITY
-- =========================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_archives ENABLE ROW LEVEL SECURITY;
ALTER TABLE classification_archives ENABLE ROW LEVEL SECURITY;
ALTER TABLE supporting_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE kecamatan_desa ENABLE ROW LEVEL SECURITY;

-- -------------------------
-- 3.1 users policies
-- -------------------------
DROP POLICY IF EXISTS "Authenticated can read all users" ON users;
CREATE POLICY "Authenticated can read all users"
  ON users FOR SELECT USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Users can read own profile" ON users;
CREATE POLICY "Users can read own profile"
  ON users FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Authenticated can insert users" ON users;
CREATE POLICY "Authenticated can insert users"
  ON users FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can update users" ON users;
CREATE POLICY "Authenticated can update users"
  ON users FOR UPDATE USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can delete users" ON users;
CREATE POLICY "Authenticated can delete users"
  ON users FOR DELETE USING (auth.uid() IS NOT NULL);

-- -------------------------
-- 3.2 activity_logs policies
-- -------------------------
DROP POLICY IF EXISTS "Admin Kabid Kasie can read logs" ON activity_logs;
CREATE POLICY "Admin Kabid Kasie can read logs"
  ON activity_logs FOR SELECT USING (
    EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.role IN ('admin', 'kabid', 'kasie'))
  );

DROP POLICY IF EXISTS "Authenticated users can insert logs" ON activity_logs;
CREATE POLICY "Authenticated users can insert logs"
  ON activity_logs FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Enable delete for users based on user_role" ON activity_logs;
CREATE POLICY "Enable delete for users based on user_role"
  ON activity_logs FOR DELETE USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );

-- -------------------------
-- 3.3 reconciliation_archives policies
-- -------------------------
DROP POLICY IF EXISTS "Authenticated can read reconciliation archives" ON reconciliation_archives;
CREATE POLICY "Authenticated can read reconciliation archives"
  ON reconciliation_archives FOR SELECT USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can insert reconciliation archives" ON reconciliation_archives;
CREATE POLICY "Authenticated can insert reconciliation archives"
  ON reconciliation_archives FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can update reconciliation archives" ON reconciliation_archives;
CREATE POLICY "Authenticated can update reconciliation archives"
  ON reconciliation_archives FOR UPDATE USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can delete reconciliation archives" ON reconciliation_archives;
CREATE POLICY "Authenticated can delete reconciliation archives"
  ON reconciliation_archives FOR DELETE USING (auth.uid() IS NOT NULL);

-- -------------------------
-- 3.4 classification_archives policies
-- -------------------------
DROP POLICY IF EXISTS "Authenticated can read classification archives" ON classification_archives;
CREATE POLICY "Authenticated can read classification archives"
  ON classification_archives FOR SELECT USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can insert classification archives" ON classification_archives;
CREATE POLICY "Authenticated can insert classification archives"
  ON classification_archives FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can update classification archives" ON classification_archives;
CREATE POLICY "Authenticated can update classification archives"
  ON classification_archives FOR UPDATE USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Authenticated can delete classification archives" ON classification_archives;
CREATE POLICY "Authenticated can delete classification archives"
  ON classification_archives FOR DELETE USING (auth.uid() IS NOT NULL);

-- -------------------------
-- 3.5 supporting_documents policies
-- -------------------------
DROP POLICY IF EXISTS "select_all_docs" ON supporting_documents;
CREATE POLICY "select_all_docs"
  ON supporting_documents FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "admin_read_all_docs" ON supporting_documents;
CREATE POLICY "admin_read_all_docs"
  ON supporting_documents FOR SELECT USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );

DROP POLICY IF EXISTS "admin_manage_all_docs" ON supporting_documents;
CREATE POLICY "admin_manage_all_docs"
  ON supporting_documents FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );

DROP POLICY IF EXISTS "manage_own_docs" ON supporting_documents;
CREATE POLICY "manage_own_docs"
  ON supporting_documents FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "any_user_delete_docs" ON supporting_documents;
CREATE POLICY "any_user_delete_docs"
  ON supporting_documents FOR DELETE USING (auth.uid() IS NOT NULL);

-- -------------------------
-- 3.6 kecamatan_desa policies
-- -------------------------
DROP POLICY IF EXISTS "Semua user bisa baca kecamatan_desa" ON kecamatan_desa;
CREATE POLICY "Semua user bisa baca kecamatan_desa"
  ON kecamatan_desa FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admin bisa kelola kecamatan_desa" ON kecamatan_desa;
CREATE POLICY "Admin bisa kelola kecamatan_desa"
  ON kecamatan_desa FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'admin')
  );

-- =========================
-- 4. INDEXES
-- =========================

-- users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_kecamatan ON users(kecamatan);

-- activity_logs
CREATE INDEX IF NOT EXISTS idx_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_action ON activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_logs_created ON activity_logs(created_at DESC);

-- supporting_documents
CREATE INDEX IF NOT EXISTS idx_supporting_documents_user_id ON supporting_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_supporting_documents_type ON supporting_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_supporting_documents_type_petani ON supporting_documents(document_type, total_petani);

-- =========================
-- 5. STORAGE
-- =========================

-- Bucket (private)
INSERT INTO storage.buckets (id, name, public)
VALUES ('documents', 'documents', false)
ON CONFLICT (id) DO NOTHING;

-- User policies
DROP POLICY IF EXISTS "user_upload_own_docs" ON storage.objects;
CREATE POLICY "user_upload_own_docs" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'documents'
    AND auth.uid()::text = (string_to_array(name, '/'))[1]
  );

DROP POLICY IF EXISTS "user_read_own_docs" ON storage.objects;
CREATE POLICY "user_read_own_docs" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'documents'
    AND auth.uid()::text = (string_to_array(name, '/'))[1]
  );

DROP POLICY IF EXISTS "user_delete_own_docs" ON storage.objects;
CREATE POLICY "user_delete_own_docs" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'documents'
    AND auth.uid()::text = (string_to_array(name, '/'))[1]
  );

DROP POLICY IF EXISTS "user_update_own_docs" ON storage.objects;
CREATE POLICY "user_update_own_docs" ON storage.objects
  FOR UPDATE USING (
    bucket_id = 'documents'
    AND auth.uid()::text = (string_to_array(name, '/'))[1]
  );

-- Admin/Kabid/Kasie policies
DROP POLICY IF EXISTS "admin_read_all_storage" ON storage.objects;
CREATE POLICY "admin_read_all_storage" ON storage.objects
  FOR SELECT TO authenticated USING (
    bucket_id = 'documents'
    AND EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );

DROP POLICY IF EXISTS "admin_insert_all_storage" ON storage.objects;
CREATE POLICY "admin_insert_all_storage" ON storage.objects
  FOR INSERT TO authenticated WITH CHECK (
    bucket_id = 'documents'
    AND EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );

DROP POLICY IF EXISTS "admin_update_all_storage" ON storage.objects;
CREATE POLICY "admin_update_all_storage" ON storage.objects
  FOR UPDATE TO authenticated USING (
    bucket_id = 'documents'
    AND EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );
