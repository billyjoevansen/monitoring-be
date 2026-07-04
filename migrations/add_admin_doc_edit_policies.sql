-- Allow admin/kabid/kasie to UPDATE any document in supporting_documents
CREATE POLICY admin_manage_all_docs ON public.supporting_documents
  FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid()
        AND users.role = ANY (ARRAY['admin'::text, 'kabid'::text, 'kasie'::text])
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid()
        AND users.role = ANY (ARRAY['admin'::text, 'kabid'::text, 'kasie'::text])
    )
  );

-- Allow admin/kabid/kasie to INSERT any file in storage documents bucket
CREATE POLICY admin_insert_all_storage ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'documents'
    AND EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
        AND users.role = ANY (ARRAY['admin'::text, 'kabid'::text, 'kasie'::text])
    )
  );

-- Allow admin/kabid/kasie to UPDATE any file in storage documents bucket
CREATE POLICY admin_update_all_storage ON storage.objects
  FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'documents'
    AND EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
        AND users.role = ANY (ARRAY['admin'::text, 'kabid'::text, 'kasie'::text])
    )
  );
