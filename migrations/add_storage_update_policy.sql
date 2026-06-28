-- =====================================================
-- Migration: Tambah policy UPDATE untuk storage documents
-- =====================================================

-- Policy UPDATE: user bisa overwrite file sendiri (dibutuhkan untuk upsert)
DROP POLICY IF EXISTS "user_update_own_docs" ON storage.objects;
CREATE POLICY "user_update_own_docs" ON storage.objects
  FOR UPDATE USING (
    bucket_id = 'documents'
    AND auth.uid()::text = (string_to_array(name, '/'))[1]
  );
