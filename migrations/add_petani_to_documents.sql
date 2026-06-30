-- =====================================================
-- Migration: Tambah kolom total_petani ke supporting_documents
-- =====================================================

-- 1. Tambah kolom total_petani (default 0 untuk data lama)
ALTER TABLE supporting_documents
  ADD COLUMN IF NOT EXISTS total_petani INTEGER DEFAULT 0;

-- 2. Index untuk query cepat
CREATE INDEX IF NOT EXISTS idx_supporting_documents_type_petani
  ON supporting_documents(document_type, total_petani);
