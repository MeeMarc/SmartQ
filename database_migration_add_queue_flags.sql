-- Migration: add per-queue flag columns for configurable registration fields

ALTER TABLE IF EXISTS qr_history ADD COLUMN IF NOT EXISTS support_doc_enabled BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS qr_history ADD COLUMN IF NOT EXISTS valid_id_enabled BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS qr_history ADD COLUMN IF NOT EXISTS student_id_enabled BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS qr_history ADD COLUMN IF NOT EXISTS signature_enabled BOOLEAN DEFAULT false;

ALTER TABLE IF EXISTS temp_qr ADD COLUMN IF NOT EXISTS support_doc_enabled BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS temp_qr ADD COLUMN IF NOT EXISTS valid_id_enabled BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS temp_qr ADD COLUMN IF NOT EXISTS student_id_enabled BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS temp_qr ADD COLUMN IF NOT EXISTS signature_enabled BOOLEAN DEFAULT false;

-- Add signature_text column to store typed signature if not present
ALTER TABLE IF EXISTS queue_entries ADD COLUMN IF NOT EXISTS signature_text TEXT;

-- Ensure upload columns exist (if older schema)
ALTER TABLE IF EXISTS queue_entries ADD COLUMN IF NOT EXISTS id_doc_path VARCHAR(500);
ALTER TABLE IF EXISTS queue_entries ADD COLUMN IF NOT EXISTS req_doc_path VARCHAR(500);
ALTER TABLE IF EXISTS queue_entries ADD COLUMN IF NOT EXISTS signature_path VARCHAR(500);
ALTER TABLE IF EXISTS queue_entries ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE IF EXISTS queue_entries ADD COLUMN IF NOT EXISTS notification_message TEXT;
