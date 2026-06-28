-- Buat tabel kecamatan_desa untuk mapping kode desa BPS → kecamatan
CREATE TABLE IF NOT EXISTS kecamatan_desa (
  id SERIAL PRIMARY KEY,
  kode_desa TEXT NOT NULL UNIQUE,
  nama_desa TEXT NOT NULL,
  kecamatan TEXT NOT NULL
);

-- RLS: semua user bisa baca, hanya admin yang bisa ubah
ALTER TABLE kecamatan_desa ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Semua user bisa baca kecamatan_desa"
  ON kecamatan_desa FOR SELECT USING (true);

CREATE POLICY "Admin bisa kelola kecamatan_desa"
  ON kecamatan_desa FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'admin')
  );

-- Tambah kolom kecamatan ke supporting_documents
ALTER TABLE supporting_documents
  ADD COLUMN IF NOT EXISTS kecamatan TEXT;
