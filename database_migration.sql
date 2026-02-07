-- Migration script to add new queue configuration fields
-- Run this script on your PostgreSQL database to add the new columns

-- Add columns to qr_history table
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS avg_service_time INTEGER;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS morning_start TIME;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS morning_end TIME;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS afternoon_start TIME;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS afternoon_end TIME;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS staff_count INTEGER;

-- Add columns to temp_qr table
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS avg_service_time INTEGER;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS morning_start TIME;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS morning_end TIME;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS afternoon_start TIME;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS afternoon_end TIME;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS staff_count INTEGER;

-- Optional: Remove old columns that are no longer used (comment out if you want to keep historical data)
-- ALTER TABLE qr_history DROP COLUMN IF EXISTS daily_capacity;
-- ALTER TABLE qr_history DROP COLUMN IF EXISTS morning_count;
-- ALTER TABLE qr_history DROP COLUMN IF EXISTS afternoon_count;
-- ALTER TABLE temp_qr DROP COLUMN IF EXISTS daily_capacity;
-- ALTER TABLE temp_qr DROP COLUMN IF EXISTS morning_count;
-- ALTER TABLE temp_qr DROP COLUMN IF EXISTS afternoon_count;

-- Verify the changes
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'qr_history' 
ORDER BY ordinal_position;

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'temp_qr' 
ORDER BY ordinal_position;

-- Queue form config: admin can enable/disable fields in registration form
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS require_supporting_doc BOOLEAN DEFAULT TRUE;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS require_valid_id BOOLEAN DEFAULT TRUE;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS require_student_id BOOLEAN DEFAULT TRUE;
ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS esign_required BOOLEAN DEFAULT TRUE;

ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS require_supporting_doc BOOLEAN DEFAULT TRUE;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS require_valid_id BOOLEAN DEFAULT TRUE;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS require_student_id BOOLEAN DEFAULT TRUE;
ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS esign_required BOOLEAN DEFAULT TRUE;

