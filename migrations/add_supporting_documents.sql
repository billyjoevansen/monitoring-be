-- =====================================================
-- Migration: Tambah tabel supporting_documents + bucket
-- =====================================================

-- 1. Buat bucket Supabase Storage
INSERT INTO storage.buckets (id, name, public)
VALUES ('documents', 'documents', false)
ON CONFLICT (id) DO NOTHING;

-- 2. Tabel metadata dokumen pendukung
CREATE TABLE IF NOT EXISTS supporting_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  document_type TEXT NOT NULL CHECK (document_type IN ('rdkk', 'siverval')),
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Index untuk query cepat
CREATE INDEX IF NOT EXISTS idx_supporting_documents_user_id ON supporting_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_supporting_documents_type ON supporting_documents(document_type);

-- 4. Enable RLS
ALTER TABLE supporting_documents ENABLE ROW LEVEL SECURITY;

-- 5. Policy: user bisa CRUD file sendiri
DROP POLICY IF EXISTS "user_manage_own_docs" ON supporting_documents;
CREATE POLICY "user_manage_own_docs" ON supporting_documents
  FOR ALL USING (auth.uid() = user_id);

-- 6. Storage policies
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
