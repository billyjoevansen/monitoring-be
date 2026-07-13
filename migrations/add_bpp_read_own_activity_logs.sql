-- Izinkan BPP dan semua user membaca log aktivitas miliknya sendiri.
-- Admin/kabid/kasie tetap bisa baca semua log via policy "Admin Kabid Kasie can read logs".
DROP POLICY IF EXISTS "Users can read own activity logs" ON activity_logs;
CREATE POLICY "Users can read own activity logs"
  ON activity_logs FOR SELECT
  USING (auth.uid() = user_id);
