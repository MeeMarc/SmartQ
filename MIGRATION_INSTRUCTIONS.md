# Queue Creation Form Update - Migration Instructions

## Summary of Changes

The Create Queue form has been updated to replace the "Total Users Per Day" and "Split Between" fields with more flexible queue management options:

### Removed Fields:
- ❌ Total Users Per Day
- ❌ Split Between (Morning/Afternoon counts)

### New Fields:
- ✅ **Average Service Time per Customer** (in minutes)
- ✅ **Total Available Service Time** with customizable time slots:
  - Morning Start time
  - Morning End time (Lunch Break)
  - Afternoon Start time  
  - Afternoon End time (Time Out)
- ✅ **Number of Staff/Windows**

## Files Modified

### Frontend Files:
1. **templates/Admin2/CreateQ.html**
   - Updated form fields
   - Modified JavaScript to handle new parameters
   - Updated display logic for QR cards and history

2. **static/Admin2/CreateQ.css**
   - Added styles for time slots container
   - Responsive design for time input fields

### Backend Files:
3. **Main.py**
   - Updated `save_qr()` function to accept new parameters
   - Modified `/generate_qr_db` endpoint to process new fields
   - Updated `/qr_history_data` endpoint to return new fields

## Database Migration Required

⚠️ **IMPORTANT**: You must run the database migration to add the new columns to your PostgreSQL database.

### Steps to Migrate:

1. **Connect to your PostgreSQL database**
   - Use pgAdmin, psql command line, or your database management tool
   - Connect to the database used by SmartQ

2. **Run the migration script**
   ```bash
   psql -h your-host -U your-user -d your-database -f database_migration.sql
   ```
   
   Or copy and paste the contents of `database_migration.sql` into your SQL client.

3. **Verify the migration**
   - The script will display the columns in both tables at the end
   - Confirm that the new columns are present:
     - `avg_service_time`
     - `morning_start`
     - `morning_end`
     - `afternoon_start`
     - `afternoon_end`
     - `staff_count`

### What the Migration Does:

- Adds 6 new columns to the `qr_history` table
- Adds 6 new columns to the `temp_qr` table
- Uses `IF NOT EXISTS` to safely run multiple times
- Preserves all existing data

### Optional: Remove Old Columns

The migration script includes commented-out commands to remove the old columns (`daily_capacity`, `morning_count`, `afternoon_count`). If you want to clean up the old columns, uncomment those lines in the SQL file.

**Note**: Only remove old columns if you don't need historical data in the old format.

## Testing the Changes

After migration:

1. **Test Queue Creation**
   - Go to Create Queue page
   - Fill in all new fields
   - Generate a QR code
   - Verify it saves successfully

2. **Test QR History**
   - Click "View QR History" button
   - Verify old queues display (with "N/A" for new fields)
   - Verify new queues display all information correctly

3. **Test Time Validation**
   - Try creating a queue with invalid times (e.g., end time before start time)
   - Verify validation messages appear

## Default Values

The form now includes default time values:
- Morning Start: 8:00 AM
- Morning End: 12:00 PM (Lunch Break)
- Afternoon Start: 1:00 PM
- Afternoon End: 5:00 PM

Admin users can freely adjust these times based on their queue requirements.

## Troubleshooting

### Issue: Database columns don't exist error
**Solution**: Run the migration script (`database_migration.sql`)

### Issue: Old QR codes showing "N/A" for new fields
**Solution**: This is expected behavior. Old queue records don't have the new data. New queues will display properly.

### Issue: Form not submitting
**Solution**: Check browser console (F12) for JavaScript errors. Ensure all required fields are filled.

## Support

If you encounter any issues after migration, check:
1. Database connection is working
2. All migration steps completed successfully
3. Browser cache is cleared
4. Server has been restarted after code changes

