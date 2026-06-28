-- Admin/Kabid/Kasie bisa baca semua dokumen (SELECT saja)
CREATE POLICY "admin_read_all_docs" ON supporting_documents
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );

-- Admin/Kabid/Kasie bisa baca semua file di storage
CREATE POLICY "admin_read_all_storage" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'documents'
    AND EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role IN ('admin', 'kabid', 'kasie'))
  );
