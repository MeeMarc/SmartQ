import os
import re
import random
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import psycopg2
from psycopg2 import errors
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import io
import base64

load_dotenv()  # Load variables from .env if present (local dev)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-insecure-secret")  # for flash messages

# Make Flask respect X-Forwarded-* headers on Render so url_for(..., _external=True)
# uses the correct scheme/host (https and your subdomain)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

def get_public_base_url():
    """Return a public base URL suitable for QR links in production.

    Priority:
    1) PUBLIC_BASE_URL (user-defined)
    2) RENDER_EXTERNAL_URL (provided by Render)
    3) request.host_url as fallback
    """
    env_base = os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if env_base:
        return env_base.rstrip('/')
    # Fallback to current request host
    return request.host_url.rstrip('/')

def get_db_connection():
    try:
        # Get the DATABASE_URL and remove any hidden newline or space
        db_url = os.getenv("DATABASE_URL", "").strip()
        conn = psycopg2.connect(db_url)
        print("Database connected successfully!")
        return conn
    except Exception as e:
        print("Database connection failed:", e)
        return None



# ==============================================================  
# AUTH ROUTES
# ==============================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)",
                (fullname, email, hashed_password)
            )
            conn.commit()
            cur.close()
            conn.close()
            flash("Account created! You can now log in.")
            return redirect(url_for('login'))

        except errors.UniqueViolation:
            flash("Email already exists.")
        except Exception as e:
            flash(f"Error: {str(e)}")

    return render_template('Admin/SignUp.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if not user:
                flash("Account not found! Please sign up.")
                return redirect(url_for('signup'))

            if not check_password_hash(user[3], password):
                flash("Incorrect password.")
                return redirect(url_for('login'))

            # Store user info in session
            session['user_email'] = email
            session['user_fullname'] = user[1]

            flash("Login successful!", "login")
            return redirect(url_for('homepage'))

        except Exception as e:
            flash(f"Error: {str(e)}")

    return render_template('Admin/login.html')


# ==============================================================  
# ADMIN ROUTES
# ==============================================================

@app.route('/homepage')
def homepage():
    if 'user_email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))
    return render_template('Admin2/Homepage.html', user=session.get('user_fullname'))


@app.route('/admin')
def admin():
    return render_template('Admin/admin.html')


@app.route('/createq')
def createq():
    return render_template('Admin2/CreateQ.html')


@app.route('/addcandidate', methods=['GET', 'POST'])
def addcandidate():
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        timeslot = request.form['timeslot']
        purpose = request.form['purpose']

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO candidates (fullname, phone, timeslot, purpose) VALUES (%s, %s, %s, %s)",
                (fullname, phone, timeslot, purpose)
            )
            conn.commit()
            cur.close()
            conn.close()
            flash("Candidate added successfully!")
        except Exception as e:
            flash(f"Error adding candidate: {str(e)}")

    return render_template('Admin2/AddCandidate.html')


@app.route('/scantracking')
def scantracking():
    return render_template('Admin2/Scantracking.html')


@app.route('/admin_settings', methods=['GET', 'POST'])
def admin_settings():
    if 'user_email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    email = session['user_email']
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch fullname, email, and password for verification
    cur.execute("SELECT fullname, email, password FROM users WHERE email = %s", (email,))
    admin = cur.fetchone()

    if request.method == 'POST':
        fullname = request.form.get('fullname', admin[0])
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        current_hashed_pw = admin[2]  # stored hashed password

        # If changing password
        if new_password:
            if not check_password_hash(current_hashed_pw, old_password):
                flash("Old password is incorrect.")
            elif new_password != confirm_password:
                flash("New passwords do not match.")
            else:
                hashed_pw = generate_password_hash(new_password)
                cur.execute(
                    "UPDATE users SET fullname = %s, password = %s WHERE email = %s",
                    (fullname, hashed_pw, email)
                )
                flash("Name and password updated successfully!")
        else:
            # Only update name if no new password
            cur.execute("UPDATE users SET fullname = %s WHERE email = %s", (fullname, email))
            flash("Name updated successfully!")

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_settings'))

    cur.close()
    conn.close()
    return render_template('Admin2/AdminSettings.html', admin=admin)



@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "logout")
    return redirect(url_for('login'))


# ==============================================================  
# QR CODE GENERATION
# ==============================================================

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    purpose = request.form.get('purpose', 'General')
    candidate = request.form.get('candidate', 'Anonymous')

    qr_data = f"{candidate} - Purpose: {purpose}"
    qr_img = qrcode.make(qr_data)

    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return jsonify({"qr_image": qr_base64})


# ==============================================================  
# QR DATABASE HANDLING (NEW)
# ==============================================================

def create_slug(text):
    """Convert text to URL-friendly slug."""
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def get_next_queue_number(queue_type):
    """Get the next queue number for a given queue type (exact match)."""
    try:
        conn = get_db_connection()
        if conn is None:
            print("Database connection failed in get_next_queue_number")
            return 1
        cur = conn.cursor()
        # Count existing queues of this exact type
        cur.execute(
            "SELECT COUNT(*) FROM qr_history WHERE queue_type = %s",
            (queue_type,)
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count + 1  # Next number
    except Exception as e:
        print(f"Error getting queue number: {e}")
        import traceback
        traceback.print_exc()
        return 1  # Default to 1 if error

def ensure_queue_entries_table(conn):
    """Create queue_entries table if it doesn't exist."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS queue_entries (
                id SERIAL PRIMARY KEY,
                queue_slug VARCHAR(255) NOT NULL,
                queue_number INTEGER NOT NULL,
                queue_type VARCHAR(255),
                queue_purpose VARCHAR(255),
                fullname VARCHAR(255) NOT NULL,
                phone VARCHAR(50) NOT NULL,
                purpose TEXT,
                status VARCHAR(50) DEFAULT 'waiting',
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

        # Ensure required columns exist (handles older schemas)
        column_statements = [
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_slug VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_number INTEGER",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_type VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_purpose VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS fullname VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS phone VARCHAR(50)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS purpose TEXT",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'waiting'",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS reschedule_status VARCHAR(50)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS rescheduled_to_queue_number INTEGER",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS last_rescheduled_at TIMESTAMP WITHOUT TIME ZONE"
        ]

        for stmt in column_statements:
            try:
                cur.execute(stmt)
            except Exception as column_error:
                # Log and continue; column may already exist with different definition
                print(f"Warning: ensure_queue_entries_table column migration issue: {column_error}")
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error ensuring queue_entries table: {e}")
        raise

def ensure_queue_limit_column(conn):
    """Ensure queue_limit column exists in qr_history and temp_qr tables."""
    try:
        cur = conn.cursor()
        
        # Add queue_limit column to qr_history if it doesn't exist
        try:
            cur.execute("ALTER TABLE qr_history ADD COLUMN IF NOT EXISTS queue_limit INTEGER")
            conn.commit()
            print("queue_limit column added to qr_history (or already exists)")
        except Exception as e:
            print(f"Note: Could not add queue_limit to qr_history: {e}")
            conn.rollback()
        
        # Add queue_limit column to temp_qr if it doesn't exist
        try:
            cur.execute("ALTER TABLE temp_qr ADD COLUMN IF NOT EXISTS queue_limit INTEGER")
            conn.commit()
            print("queue_limit column added to temp_qr (or already exists)")
        except Exception as e:
            print(f"Note: Could not add queue_limit to temp_qr: {e}")
            conn.rollback()
        
        cur.close()
    except Exception as e:
        print(f"Error ensuring queue_limit column: {e}")
        # Don't raise - this is not critical

def resolve_queue_metadata(queue_slug, queue_number):
    """Resolve queue type and purpose based on slug and sequence number."""
    default_type = queue_slug.replace('-', ' ').title()
    default_purpose = "Queue Registration"

    conn = get_db_connection()
    if conn is None:
        return default_type, default_purpose

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT queue_type, queue_purpose FROM qr_history ORDER BY id"
        )
        all_queues = cur.fetchall()
        cur.close()
        conn.close()

        matching_queues = [
            (q_type, q_purpose)
            for q_type, q_purpose in all_queues
            if create_slug(q_type) == queue_slug
        ]

        if matching_queues and 0 < queue_number <= len(matching_queues):
            return matching_queues[queue_number - 1]

        return default_type, default_purpose
    except Exception as e:
        print(f"Error resolving queue metadata: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return default_type, default_purpose

def get_queue_limit(queue_slug, queue_number):
    """Get the queue limit for a specific queue from qr_history."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cur = conn.cursor()
        # Get all queues that match the slug
        cur.execute(
            """
            SELECT queue_limit FROM qr_history 
            WHERE queue_type IN (
                SELECT queue_type FROM qr_history ORDER BY id
            )
            ORDER BY id
            """
        )
        all_queues = cur.fetchall()
        
        # Also need to get queue types to match slug
        cur.execute("SELECT queue_type, queue_limit FROM qr_history ORDER BY id")
        all_queue_data = cur.fetchall()
        cur.close()
        conn.close()
        
        # Find matching queues by slug
        matching_indices = [
            idx for idx, (q_type, q_limit) in enumerate(all_queue_data, 1)
            if create_slug(q_type) == queue_slug
        ]
        
        # If queue_number matches one of the indices, return its limit
        if queue_number in matching_indices:
            # Get the actual data for this queue number
            actual_index = matching_indices.index(queue_number)
            return all_queue_data[queue_number - 1][1]  # Return queue_limit
        
        return None
    except Exception as e:
        print(f"Error getting queue limit: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_queue_entry_count(queue_slug, queue_number):
    """Count the number of entries that consume a slot in a queue.
    
    Counts:
    - 'waiting' entries (active, not yet served)
    - 'completed' entries (already served, time slot consumed)
    
    Excludes:
    - 'cancelled' entries (slot freed up)
    - 'rescheduled' entries (slot freed up, moved to another queue)
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return 0
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        # Count entries with status = 'waiting' OR 'completed' (exclude cancelled and rescheduled)
        cur.execute(
            "SELECT COUNT(*) FROM queue_entries WHERE queue_slug = %s AND queue_number = %s AND status IN ('waiting', 'completed')",
            (queue_slug, queue_number)
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        print(f"Error counting queue entries: {e}")
        return 0

def check_existing_entry(queue_slug, queue_number, phone):
    """Check if a user with this phone number already has an entry in this queue."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM queue_entries 
            WHERE queue_slug = %s AND queue_number = %s AND phone = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (queue_slug, queue_number, phone)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        return result[0] if result else None
    except Exception as e:
        print(f"Error checking existing entry: {e}")
        return None

def generate_ticket_reference(queue_slug, entry_id):
    """Return a user-facing ticket reference that isn't sequentially ordered."""
    base = re.sub(r'[^A-Z0-9]', '', queue_slug.upper())
    if not base:
        base = "TICKET"
    token_src = f"{queue_slug}-{entry_id}"
    token = hashlib.sha1(token_src.encode("utf-8")).hexdigest()[:6].upper()
    return f"{base}-{token}"

def save_qr(queue_type, queue_purpose, queue_link, created_by, queue_number=None, 
             avg_service_time=None, morning_start=None, morning_end=None, 
             afternoon_start=None, afternoon_end=None, staff_count=None, queue_limit=None):
    """Save QR to database and return the inserted ID."""
    try:
        print(f"save_qr called with: type='{queue_type}', purpose='{queue_purpose}', link='{queue_link}', created_by='{created_by}', queue_limit={queue_limit}")
        conn = get_db_connection()
        if conn is None:
            print("ERROR: Database connection failed in save_qr")
            return None
        
        print("Database connection successful")
        
        # Ensure queue_limit column exists
        ensure_queue_limit_column(conn)
        
        cur = conn.cursor()
        
        # Try with RETURNING first (PostgreSQL)
        try:
            print("Attempting INSERT with RETURNING...")
            cur.execute(
                """INSERT INTO qr_history 
                (queue_type, queue_purpose, queue_link, created_by, 
                 avg_service_time, morning_start, morning_end, 
                 afternoon_start, afternoon_end, staff_count, queue_limit) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (queue_type, queue_purpose, queue_link, created_by,
                 avg_service_time, morning_start, morning_end,
                 afternoon_start, afternoon_end, staff_count, queue_limit)
            )
            qr_id = cur.fetchone()[0]
            print(f"INSERT successful with RETURNING, got ID: {qr_id}")
        except Exception as ret_error:
            # If RETURNING doesn't work, try alternative approach
            print(f"RETURNING failed, trying alternative: {ret_error}")
            import traceback
            traceback.print_exc()
            try:
                cur.execute(
                    """INSERT INTO qr_history 
                    (queue_type, queue_purpose, queue_link, created_by,
                     avg_service_time, morning_start, morning_end,
                     afternoon_start, afternoon_end, staff_count, queue_limit) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (queue_type, queue_purpose, queue_link, created_by,
                     avg_service_time, morning_start, morning_end,
                     afternoon_start, afternoon_end, staff_count, queue_limit)
                )
                # Get the last inserted ID
                cur.execute("SELECT LASTVAL()")
                qr_id = cur.fetchone()[0]
                print(f"INSERT successful with LASTVAL(), got ID: {qr_id}")
            except Exception as alt_error:
                print(f"Alternative insert also failed: {alt_error}")
                import traceback
                traceback.print_exc()
                conn.rollback()
                cur.close()
                conn.close()
                return None
        
        # Also insert into temp_qr (if table exists, ignore if it doesn't)
        try:
            print("Inserting into temp_qr...")
            cur.execute(
                """INSERT INTO temp_qr 
                (queue_type, queue_purpose, queue_link, created_by,
                 avg_service_time, morning_start, morning_end,
                 afternoon_start, afternoon_end, staff_count, queue_limit) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (queue_type, queue_purpose, queue_link, created_by,
                 avg_service_time, morning_start, morning_end,
                 afternoon_start, afternoon_end, staff_count, queue_limit)
            )
            print("temp_qr insert successful")
        except Exception as temp_error:
            print(f"Note: temp_qr insert failed (this is okay): {temp_error}")
            # Continue anyway, qr_history is the important one
        
        print("Committing transaction...")
        conn.commit()
        cur.close()
        conn.close()
        print(f"save_qr completed successfully, returning ID: {qr_id}")
        return qr_id
    except Exception as e:
        print(f"ERROR in save_qr: {e}")
        import traceback
        traceback.print_exc()
        return None


@app.route('/generate_qr_db', methods=['POST'])
def generate_qr_db():
    try:
        print("=== QR Generation Started ===")
        print(f"Form data: {dict(request.form)}")
        print(f"Session: {dict(session)}")
        
        queue_type = request.form.get('type', '').strip()
        queue_purpose = request.form.get('purpose', '').strip()
        created_by = session.get('user_email', 'Unknown')
        
        # Get the new parameters
        avg_service_time = request.form.get('avgServiceTime', '').strip()
        morning_start = request.form.get('morningStart', '').strip()
        morning_end = request.form.get('morningEnd', '').strip()
        afternoon_start = request.form.get('afternoonStart', '').strip()
        afternoon_end = request.form.get('afternoonEnd', '').strip()
        staff_count = request.form.get('staffCount', '').strip()
        queue_limit = request.form.get('queueLimit', '').strip()
        
        print(f"Queue Type: '{queue_type}', Purpose: '{queue_purpose}', Created By: '{created_by}'")
        print(f"Avg Service Time: {avg_service_time}, Staff Count: {staff_count}, Queue Limit: {queue_limit}")
        print(f"Morning: {morning_start} - {morning_end}, Afternoon: {afternoon_start} - {afternoon_end}")
        
        if not queue_type or not queue_purpose:
            error_msg = "Queue Type and Purpose are required"
            print(f"Validation failed: {error_msg}")
            return jsonify({
                "error": error_msg,
                "qr_image": None
            }), 400
        
        # Auto-generate URL based on Queue Type and unique number
        print("Getting queue number...")
        queue_number = get_next_queue_number(queue_type)
        print(f"Queue number: {queue_number}")
        
        queue_slug = create_slug(queue_type)
        print(f"Queue slug: {queue_slug}")
        
        # Generate the URL: /queue/<slug>/<number>
        try:
            base = get_public_base_url()
            print(f"Base URL from get_public_base_url: {base}")
        except Exception as e:
            print(f"Error getting base URL: {e}")
            # Fallback to environment variable or default
            base = os.getenv("PUBLIC_BASE_URL", "https://smartq-vd9k.onrender.com")
            if not base.startswith('http'):
                base = f"https://{base}"
            print(f"Using fallback base URL: {base}")
        
        queue_link = f"{base}/queue/{queue_slug}/{queue_number}"
        print(f"Generated queue link: {queue_link}")
        
        # Convert numeric fields to int or None
        try:
            avg_service_time = float(avg_service_time) if avg_service_time else None
            staff_count = int(staff_count) if staff_count else None
            queue_limit = int(queue_limit) if queue_limit else None
        except ValueError:
            avg_service_time = None
            staff_count = None
            queue_limit = None
        
        # Save QR and get the ID
        print("Saving QR to database...")
        qr_id = save_qr(queue_type, queue_purpose, queue_link, created_by, queue_number,
                       avg_service_time, morning_start or None, morning_end or None,
                       afternoon_start or None, afternoon_end or None, staff_count, queue_limit)
        print(f"QR saved with ID: {qr_id}")
        
        # Auto-enroll pending reschedules for this queue type
        auto_enroll_pending_reschedules(queue_slug, queue_number, queue_type)
        
        if qr_id is None:
            error_msg = "Failed to save QR to database. Check server logs for details."
            print(f"ERROR: {error_msg}")
            return jsonify({
                "error": error_msg,
                "qr_image": None
            }), 500
        
        # Generate QR code with the auto-generated URL
        print("Generating QR image...")
        qr_img = qrcode.make(queue_link)

        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        print("QR image generated successfully")

        print("=== QR Generation Completed Successfully ===")
        return jsonify({
            "qr_image": qr_base64,
            "queue_link": queue_link,
            "queue_number": queue_number,
            "qr_id": qr_id
        })
    except Exception as e:
        print(f"ERROR in generate_qr_db: {e}")
        import traceback
        error_trace = traceback.format_exc()
        print(error_trace)
        return jsonify({
            "error": f"Server error: {str(e)}",
            "qr_image": None,
            "details": error_trace if os.getenv("FLASK_ENV") == "development" else None
        }), 500


# Simple endpoint to auto-generate a QR for the site URL without providing a link
@app.route('/generate_site_qr', methods=['GET'])
def generate_site_qr():
    base = get_public_base_url()
    target_url = f"{base}{url_for('user_page')}"

    qr_img = qrcode.make(target_url)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return jsonify({
        "qr_image": qr_base64,
        "target_url": target_url
    })


@app.route('/delete_qr', methods=['POST'])
def delete_qr():
    """Delete a QR from temp_qr only. qr_history is kept for permanent history."""
    data = request.get_json() if request.is_json else request.form
    qr_id = data.get('id') or data.get('qr_id')
    force = str(data.get('force', '')).lower() == 'true'

    if not qr_id:
        return jsonify({"status": "error", "message": "QR ID is required"}), 400
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        cur = conn.cursor()
        
        # Only delete from temp_qr (active/temporary QRs)
        # Keep qr_history intact for permanent history
        cur.execute("DELETE FROM temp_qr WHERE id = %s", (qr_id,))
        deleted_count = cur.rowcount
        
        if deleted_count == 0:
            # Check if QR exists in qr_history (for reference)
            cur.execute("SELECT id FROM qr_history WHERE id = %s", (qr_id,))
            exists = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            if exists:
                print(f"Note: QR {qr_id} not in temp_qr (already deleted or never was), but exists in history")
                return jsonify({"status": "success", "message": "QR removed from active list (history preserved)"})

            if force:
                print(f"Force deleting QR {qr_id} succeeded (no server records found)")
            else:
                print(f"QR {qr_id} already removed (nothing to delete)")

            return jsonify({"status": "success", "message": "QR removed."})
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"QR {qr_id} deleted from temp_qr (history preserved)")
        return jsonify({"status": "success", "message": "QR removed from active list. History preserved."})
    except Exception as e:
        print(f"Error deleting QR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete_temp_qr', methods=['POST'])
def delete_temp_qr():
    """Legacy endpoint - redirects to delete_qr."""
    qr_id = request.form.get('id')
    if qr_id:
        return delete_qr()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM temp_qr")  # Clear all if no ID
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error deleting temp QR: {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route('/temp_qr_data', methods=['GET'])
def temp_qr_data():
    """Get all active QRs from temp_qr table."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if temp_qr table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'temp_qr'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            cur.close()
            conn.close()
            return jsonify([])
        
        cur.execute("""
            SELECT id, queue_type, queue_purpose, queue_link, created_by, created_at
            FROM temp_qr
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        active_qrs = []
        for row in rows:
            active_qrs.append({
                "id": row[0],
                "queue_type": row[1],
                "queue_purpose": row[2],
                "queue_link": row[3],
                "created_by": row[4],
                "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "N/A"
            })
        return jsonify(active_qrs)
    except Exception as e:
        print(f"Error fetching temp QR data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/qr_history_data', methods=['GET'])
def qr_history_data():
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: Database connection failed")
            return jsonify({"error": "Database connection failed"}), 500
            
        cur = conn.cursor()
        
        # Simple query - get ALL columns from qr_history
        # Don't join with users yet to avoid issues
        cur.execute("""
            SELECT id, queue_type, queue_purpose, queue_link, created_by, created_at,
                   avg_service_time, morning_start, morning_end, 
                   afternoon_start, afternoon_end, staff_count
            FROM qr_history
            ORDER BY created_at DESC
        """)
        
        rows = cur.fetchall()
        print(f"Found {len(rows)} QR codes in history")
        cur.close()
        conn.close()

        history = []
        for row in rows:
            try:
                history_item = {
                    "id": row[0],
                    "queue_type": row[1] or "Unknown",
                    "queue_purpose": row[2] or "N/A",
                    "queue_link": row[3] or "#",
                    "created_by": row[4] or "Unknown",
                    "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "N/A",
                    "avg_service_time": row[6],
                    "morning_start": str(row[7]) if row[7] else None,
                    "morning_end": str(row[8]) if row[8] else None,
                    "afternoon_start": str(row[9]) if row[9] else None,
                    "afternoon_end": str(row[10]) if row[10] else None,
                    "staff_count": row[11],
                    "queue_limit": None  # Will be added later if column exists
                }
                history.append(history_item)
            except Exception as row_error:
                print(f"Error processing row {row[0]}: {row_error}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"Returning {len(history)} QR codes")
        return jsonify(history)
    except Exception as e:
        print(f"Error fetching QR history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route('/clear_temp_qr', methods=['POST'])
def clear_temp_qr():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM temp_qr")  # empty the table
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
# ==============================================================  
# GET SCANS FOR A SPECIFIC QR
# ==============================================================

@app.route('/get_qr_scans/<int:qr_id>', methods=['GET'])
def get_qr_scans(qr_id):
    """Return a JSON list of users linked to a specific QR code."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify([])

        cur = conn.cursor()

        # Resolve the queue link using qr_history first, then fallback to temp_qr
        queue_link = None
        cur.execute("SELECT queue_link FROM qr_history WHERE id = %s", (qr_id,))
        row = cur.fetchone()
        if row:
            queue_link = row[0]
        else:
            cur.execute("SELECT queue_link FROM temp_qr WHERE id = %s", (qr_id,))
            row = cur.fetchone()
            if row:
                queue_link = row[0]

        if not queue_link:
            cur.close()
            conn.close()
            return jsonify([])

        # Extract queue_slug and queue_number from the queue_link
        # Format: https://domain.com/queue/<slug>/<number>
        match = re.search(r'/queue/([^/]+)/(\d+)', queue_link)
        if not match:
            cur.close()
            conn.close()
            return jsonify([])
        
        queue_slug = match.group(1)
        queue_number = int(match.group(2))

        # Ensure queue_entries table exists
        ensure_queue_entries_table(conn)

        # Fetch queue entries (users who filled the form / scanned the QR)
        # Order by status (waiting first) then by created_at
        cur.execute(
            """
            SELECT id, fullname, phone, purpose, status, created_at
            FROM queue_entries
            WHERE queue_slug = %s AND queue_number = %s
            ORDER BY 
                CASE 
                    WHEN status = 'waiting' THEN 1
                    WHEN status = 'completed' THEN 2
                    ELSE 3
                END,
                created_at DESC
            """,
            (queue_slug, queue_number)
        )
        rows = cur.fetchall()

        scans = []
        for row in rows:
            scans.append({
                "id": row[0],
                "fullname": row[1] or "Unknown",
                "phone": row[2] or "",
                "purpose": row[3] or "",
                "status": row[4] or "waiting",
                "scanned_at": row[5].strftime('%Y-%m-%d %I:%M %p') if row[5] else ""
            })

        cur.close()
        conn.close()

        return jsonify(scans)

    except Exception as e:
        print(f"Error fetching QR scans: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/update_queue_status', methods=['POST'])
def update_queue_status():
    """Update the status of a queue entry."""
    try:
        data = request.get_json()
        entry_id = data.get('entry_id')
        new_status = data.get('status', 'completed')
        
        if not entry_id:
            return jsonify({"status": "error", "message": "Entry ID is required"}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE queue_entries SET status = %s WHERE id = %s",
            (new_status, entry_id)
        )
        
        if cur.rowcount == 0:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "Entry not found"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "message": f"Status updated to {new_status}"})
    except Exception as e:
        print(f"Error updating queue status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/cancel_queue_entry/<int:entry_id>', methods=['POST'])
def cancel_queue_entry(entry_id):
    """Cancel a queue entry by setting its status to 'cancelled'."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        # Check if entry exists and is not already cancelled/completed
        cur.execute(
            "SELECT status FROM queue_entries WHERE id = %s",
            (entry_id,)
        )
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "Entry not found"}), 404
        
        current_status = row[0] or "waiting"
        if current_status in ['cancelled', 'completed']:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": f"Entry is already {current_status}"}), 400
        
        # Update status to cancelled
        cur.execute(
            "UPDATE queue_entries SET status = 'cancelled' WHERE id = %s",
            (entry_id,)
        )
        
        if cur.rowcount == 0:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "Failed to cancel entry"}), 500
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Registration cancelled successfully"})
    except Exception as e:
        print(f"Error cancelling queue entry: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

def find_next_available_queue(queue_type, current_queue_number):
    """Find the next available queue of the same type."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cur = conn.cursor()
        
        # Find the next queue number of the same type (greater than current)
        # Check both qr_history and temp_qr
        cur.execute(
            """
            SELECT queue_number, queue_slug
            FROM (
                SELECT queue_number, queue_slug FROM qr_history 
                WHERE queue_type = %s AND queue_number > %s
                UNION
                SELECT queue_number, queue_slug FROM temp_qr 
                WHERE queue_type = %s AND queue_number > %s
            ) AS combined
            ORDER BY queue_number ASC
            LIMIT 1
            """,
            (queue_type, current_queue_number, queue_type, current_queue_number)
        )
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return {"queue_number": result[0], "queue_slug": result[1]}
        return None
    except Exception as e:
        print(f"Error finding next queue: {e}")
        return None

def can_reschedule(entry_id, queue_type):
    """Check if user can reschedule (24-hour cooldown check per queue type)."""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        
        cur = conn.cursor()
        
        # Get user's phone number from this entry
        cur.execute(
            """
            SELECT phone
            FROM queue_entries
            WHERE id = %s
            """,
            (entry_id,)
        )
        
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return False, "Entry not found"
        
        phone = row[0]
        
        # Check last reschedule time for this queue type across all user's entries
        cur.execute(
            """
            SELECT MAX(last_rescheduled_at) as last_reschedule
            FROM queue_entries
            WHERE phone = %s 
            AND queue_type = %s
            AND last_rescheduled_at IS NOT NULL
            """,
            (phone, queue_type)
        )
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        last_rescheduled_at = row[0] if row else None
        
        # If never rescheduled for this queue type, allow it
        if not last_rescheduled_at:
            return True, None
        
        # Check if 24 hours have passed
        from datetime import datetime, timedelta
        now = datetime.now()
        time_diff = now - last_rescheduled_at
        
        if time_diff < timedelta(hours=24):
            hours_remaining = 24 - (time_diff.total_seconds() / 3600)
            return False, f"You can reschedule {queue_type} queues again in {int(hours_remaining)} hours"
        
        return True, None
    except Exception as e:
        print(f"Error checking reschedule eligibility: {e}")
        return False, str(e)

def auto_enroll_pending_reschedules(queue_slug, queue_number, queue_type):
    """Auto-enroll users with pending reschedules for this queue type."""
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        # Find all pending reschedules for this queue type
        cur.execute(
            """
            SELECT id, fullname, phone, purpose, queue_purpose
            FROM queue_entries
            WHERE reschedule_status = 'pending' 
            AND queue_type = %s
            AND status = 'rescheduled'
            """,
            (queue_type,)
        )
        
        pending_entries = cur.fetchall()
        
        for entry in pending_entries:
            entry_id, fullname, phone, purpose, old_queue_purpose = entry
            
            # Create new entry in the new queue
            cur.execute(
                """
                INSERT INTO queue_entries (
                    queue_slug, queue_number, queue_type, queue_purpose,
                    fullname, phone, purpose, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting')
                RETURNING id
                """,
                (
                    queue_slug,
                    queue_number,
                    queue_type,
                    old_queue_purpose,  # Keep original purpose
                    fullname,
                    phone,
                    purpose,
                )
            )
            
            new_entry_id = cur.fetchone()[0]
            
            # Update old entry to mark as rescheduled with new queue info
            # Don't update last_rescheduled_at here - it was already set when user initiated reschedule
            cur.execute(
                """
                UPDATE queue_entries
                SET reschedule_status = 'completed',
                    rescheduled_to_queue_number = %s
                WHERE id = %s
                """,
                (queue_number, entry_id)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        if pending_entries:
            print(f"Auto-enrolled {len(pending_entries)} pending reschedules to queue {queue_number}")
    except Exception as e:
        print(f"Error auto-enrolling pending reschedules: {e}")
        import traceback
        traceback.print_exc()

@app.route('/reschedule_queue_entry/<int:entry_id>', methods=['POST'])
def reschedule_queue_entry(entry_id):
    """Reschedule a queue entry to the next available queue of the same type."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        # Get entry details
        cur.execute(
            """
            SELECT id, queue_slug, queue_number, queue_type, queue_purpose,
                   fullname, phone, purpose, status
            FROM queue_entries
            WHERE id = %s
            """,
            (entry_id,)
        )
        
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "Entry not found"}), 404
        
        entry_id_db, queue_slug, queue_number, queue_type, queue_purpose, fullname, phone, purpose, status = row
        
        # Check if entry can be rescheduled
        if status not in ['waiting']:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": f"Cannot reschedule entry with status: {status}"}), 400
        
        # Check 24-hour cooldown
        can_resched, cooldown_msg = can_reschedule(entry_id, queue_type)
        if not can_resched:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": cooldown_msg}), 400
        
        # Find next available queue of same type
        next_queue = find_next_available_queue(queue_type, queue_number)
        
        if next_queue:
            # Next queue exists - move user there
            new_queue_slug = next_queue["queue_slug"]
            new_queue_number = next_queue["queue_number"]
            
            # Create new entry in next queue
            cur.execute(
                """
                INSERT INTO queue_entries (
                    queue_slug, queue_number, queue_type, queue_purpose,
                    fullname, phone, purpose, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting')
                RETURNING id
                """,
                (
                    new_queue_slug,
                    new_queue_number,
                    queue_type,
                    queue_purpose,
                    fullname,
                    phone,
                    purpose if purpose else None,
                )
            )
            
            new_entry_id = cur.fetchone()[0]
            
            # Mark old entry as rescheduled
            cur.execute(
                """
                UPDATE queue_entries
                SET status = 'rescheduled',
                    reschedule_status = 'completed',
                    rescheduled_to_queue_number = %s,
                    last_rescheduled_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (new_queue_number, entry_id)
            )
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                "status": "success",
                "message": f"Rescheduled successfully! You've been moved to {queue_type} Queue #{new_queue_number}.",
                "new_queue_slug": new_queue_slug,
                "new_queue_number": new_queue_number,
                "new_entry_id": new_entry_id
            })
        else:
            # No next queue exists - mark as pending
            cur.execute(
                """
                UPDATE queue_entries
                SET status = 'rescheduled',
                    reschedule_status = 'pending',
                    last_rescheduled_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (entry_id,)
            )
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                "status": "pending",
                "message": f"Reschedule request received! You'll be automatically enrolled in the next {queue_type} queue when it's created. Your slot in the current queue has been freed."
            })
            
    except Exception as e:
        print(f"Error rescheduling queue entry: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_candidate_modal', methods=['POST'])
def add_candidate_modal():
    """Add a candidate directly to queue_entries from the admin modal."""
    data = request.get_json()
    fullname = data.get('fullname', '').strip()
    phone = data.get('phone', '').strip()
    qr_link = data.get('link', '').strip()

    if not fullname or not phone or not qr_link:
        return jsonify({"status": "error", "message": "Full name, phone, and queue link are required"}), 400

    try:
        # Parse queue_link to get queue_slug and queue_number
        # Format: https://domain.com/queue/<slug>/<number>
        match = re.search(r'/queue/([^/]+)/(\d+)', qr_link)
        if not match:
            return jsonify({"status": "error", "message": "Invalid queue link format"}), 400
        
        queue_slug = match.group(1)
        queue_number = int(match.group(2))
        
        # Get queue metadata
        queue_type, queue_purpose = resolve_queue_metadata(queue_slug, queue_number)
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        # Check queue limit
        queue_limit = get_queue_limit(queue_slug, queue_number)
        current_count = get_queue_entry_count(queue_slug, queue_number)
        
        if queue_limit is not None and queue_limit > 0 and current_count >= queue_limit:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "Queue is full. Cannot add more candidates."}), 400
        
        # Check if user already has an entry
        existing_entry = check_existing_entry(queue_slug, queue_number, phone)
        if existing_entry:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "A user with this phone number already exists in this queue."}), 400
        
        # Insert into queue_entries
        cur.execute(
            """
            INSERT INTO queue_entries (
                queue_slug, queue_number, queue_type, queue_purpose,
                fullname, phone, purpose, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting')
            RETURNING id
            """,
            (
                queue_slug,
                queue_number,
                queue_type,
                queue_purpose,
                fullname,
                phone,
                "Added via Admin Panel",  # Purpose field
            )
        )
        
        entry_id = cur.fetchone()[0]
        conn.commit()
        
        # Get QR ID for response
        cur.execute("SELECT id FROM temp_qr WHERE queue_link=%s", (qr_link,))
        qr_row = cur.fetchone()
        qr_id = qr_row[0] if qr_row else None
        
        # Also check qr_history
        if not qr_id:
            cur.execute("SELECT id FROM qr_history WHERE queue_link=%s", (qr_link,))
            qr_row = cur.fetchone()
            qr_id = qr_row[0] if qr_row else None
        
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "qr_id": qr_id, "entry_id": entry_id})
    except Exception as e:
        print(f"Error adding candidate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/migrate_db')
def migrate_db():
    """Run database migrations to add queue_limit column."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed", "status": "error"}), 500
        
        # Ensure queue_limit column exists
        ensure_queue_limit_column(conn)
        
        # Ensure queue_entries table exists
        ensure_queue_entries_table(conn)
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Database migration completed successfully. queue_limit column added to qr_history and temp_qr tables."
        })
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "status": "error",
            "traceback": traceback.format_exc()
        }), 500

@app.route('/test_db')
def test_db():
    """Test endpoint to check database connectivity and table structure."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed", "status": "error"}), 500
        
        cur = conn.cursor()
        
        # Check if qr_history table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'qr_history'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            cur.close()
            conn.close()
            return jsonify({
                "error": "qr_history table does not exist",
                "status": "error",
                "suggestion": "Please create the table with: CREATE TABLE qr_history (id SERIAL PRIMARY KEY, queue_type VARCHAR(255), queue_purpose VARCHAR(255), queue_link VARCHAR(500), created_by VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
            }), 500
        
        # Check table structure
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'qr_history'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        # Test insert (will rollback)
        cur.execute("BEGIN")
        try:
            cur.execute(
                "INSERT INTO qr_history (queue_type, queue_purpose, queue_link, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
                ("TEST", "TEST", "TEST", "TEST")
            )
            test_id = cur.fetchone()[0]
            cur.execute("ROLLBACK")
        except Exception as insert_error:
            cur.execute("ROLLBACK")
            cur.close()
            conn.close()
            return jsonify({
                "error": f"Insert test failed: {str(insert_error)}",
                "status": "error",
                "columns": [{"name": col[0], "type": col[1]} for col in columns]
            }), 500
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Database connection successful",
            "table_exists": True,
            "columns": [{"name": col[0], "type": col[1]} for col in columns],
            "test_insert": "passed"
        })
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "status": "error",
            "traceback": traceback.format_exc()
        }), 500

@app.route('/user')
def user_page():
    return render_template("User/User.html")

@app.route('/queue/<queue_slug>/<int:queue_number>', methods=['GET', 'POST'])
def queue_page(queue_slug, queue_number):
    """Dynamic route for auto-generated queue pages."""
    queue_type, queue_purpose = resolve_queue_metadata(queue_slug, queue_number)
    
    # Get queue limit and current count
    queue_limit = get_queue_limit(queue_slug, queue_number)
    current_count = get_queue_entry_count(queue_slug, queue_number)
    queue_full = False
    
    if queue_limit is not None and queue_limit > 0:
        queue_full = current_count >= queue_limit

    if request.method == 'POST':
        phone = (request.form.get('phone') or '').strip()
        
        # Check if user already has an entry (trying to retrieve ticket)
        existing_entry_id = check_existing_entry(queue_slug, queue_number, phone)
        
        if existing_entry_id:
            # User already has a ticket, redirect to their waiting page
            flash("Welcome back! Here's your existing queue ticket.", "success")
            return redirect(url_for('queue_waiting', queue_slug=queue_slug, queue_number=queue_number, entry_id=existing_entry_id))
        
        # If queue is full and user doesn't have existing entry, deny registration
        if queue_full:
            flash("Sorry, this queue is currently full. The maximum capacity has been reached.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
        
        # Get individual name fields
        lastname = (request.form.get('lastname') or '').strip()
        firstname = (request.form.get('firstname') or '').strip()
        middleinitial = (request.form.get('middleinitial') or '').strip()
        suffix = (request.form.get('suffix') or '').strip()
        
        # Construct fullname from separate fields
        # Format: "Lastname, Firstname M.I. Suffix"
        name_parts = [lastname, firstname]
        if middleinitial:
            name_parts.append(middleinitial)
        if suffix:
            name_parts.append(suffix)
        
        fullname = ', '.join(name_parts[:2]) if len(name_parts) >= 2 else ' '.join(name_parts)
        if len(name_parts) > 2:
            fullname += ' ' + ' '.join(name_parts[2:])
        
        purpose = (request.form.get('purpose') or '').strip()

        if not lastname or not firstname or not phone:
            flash("Please provide your last name, first name, and phone number to join the queue.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        conn = None
        cur = None
        entry_id = None
        try:
            conn = get_db_connection()
            if conn is None:
                raise RuntimeError("Database connection failed")

            ensure_queue_entries_table(conn)
            cur = conn.cursor()
            
            # Double-check queue limit right before insertion (race condition protection)
            current_count = get_queue_entry_count(queue_slug, queue_number)
            if queue_limit is not None and queue_limit > 0 and current_count >= queue_limit:
                flash("Sorry, this queue just became full. Please try again later.", "error")
                return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
            
            cur.execute(
                """
                INSERT INTO queue_entries (
                    queue_slug, queue_number, queue_type, queue_purpose,
                    fullname, phone, purpose
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    queue_slug,
                    queue_number,
                    queue_type,
                    queue_purpose,
                    fullname,
                    phone,
                    purpose if purpose else None,
                )
            )
            entry_id = cur.fetchone()[0]
            conn.commit()
        except Exception as e:
            print(f"Error saving queue entry: {e}")
            if conn:
                conn.rollback()
            flash("Something went wrong while saving your registration. Please try again.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        return redirect(url_for('queue_waiting', queue_slug=queue_slug, queue_number=queue_number, entry_id=entry_id))

    return render_template(
        "User/User.html",
        queue_type=queue_type,
        queue_purpose=queue_purpose,
        queue_number=queue_number,
        queue_slug=queue_slug,
        queue_full=queue_full,
        queue_limit=queue_limit,
        current_count=current_count,
    )


@app.route('/queue/<queue_slug>', methods=['GET', 'POST'])
@app.route('/queue/<queue_slug>/', methods=['GET', 'POST'])
def queue_page_default(queue_slug):
    """Fallback route when queue number isn't provided in the URL."""
    return queue_page(queue_slug, 1)


@app.route('/queue/<queue_slug>/<int:queue_number>/waiting/<int:entry_id>')
def queue_waiting(queue_slug, queue_number, entry_id):
    queue_type, queue_purpose = resolve_queue_metadata(queue_slug, queue_number)

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise RuntimeError("Database connection failed")

        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, queue_slug, queue_number, queue_type, queue_purpose,
                   fullname, phone, purpose, status, created_at
            FROM queue_entries
            WHERE id = %s AND queue_slug = %s AND queue_number = %s
            """,
            (entry_id, queue_slug, queue_number)
        )
        row = cur.fetchone()

        if not row:
            flash("We couldn't find your queue registration. Please submit the form again.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        entry = {
            "id": row[0],
            "queue_slug": row[1],
            "queue_number": row[2],
            "queue_type": row[3] or queue_type,
            "queue_purpose": row[4] or queue_purpose,
            "fullname": row[5],
            "phone": row[6],
            "purpose": row[7],
            "status": row[8] or "waiting",
            "created_at": row[9],
        }

        queue_type = entry["queue_type"] or queue_type
        queue_purpose = entry["queue_purpose"] or queue_purpose
        ticket_reference = generate_ticket_reference(queue_slug, entry["id"])

        cur.execute(
            """
            SELECT id, fullname, purpose, status, created_at
            FROM queue_entries
            WHERE queue_slug = %s AND queue_number = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 10
            """,
            (queue_slug, queue_number)
        )
        history_rows = cur.fetchall()
        recent_entries = [
            {
                "id": r[0],
                "fullname": r[1],
                "purpose": r[2],
                "status": r[3] or "waiting",
                "created_at": r[4],
            }
            for r in history_rows
        ]

        return render_template(
            "User/Waiting.html",
            queue_type=queue_type,
            queue_purpose=queue_purpose,
            queue_number=queue_number,
            queue_slug=queue_slug,
            entry=entry,
            ticket_reference=ticket_reference,
            recent_entries=recent_entries,
        )
    except Exception as e:
        print(f"Error loading waiting page: {e}")
        flash("Unable to load your queue status. Please try again.", "error")
        return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()





@app.route('/download_ticket/<queue_slug>/<int:queue_number>/<int:entry_id>')
def download_ticket(queue_slug, queue_number, entry_id):
    """Generate a downloadable text ticket for a queue entry."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "Error: Could not connect to database", 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT fullname, phone, purpose, created_at, queue_type, queue_purpose
            FROM queue_entries
            WHERE id = %s AND queue_slug = %s AND queue_number = %s
            """,
            (entry_id, queue_slug, queue_number)
        )
        entry = cur.fetchone()
        cur.close()
        conn.close()
        
        if not entry:
            return "Ticket not found", 404
        
        fullname, phone, purpose, created_at, queue_type, queue_purpose = entry
        ticket_ref = generate_ticket_reference(queue_slug, entry_id)
        
        ticket_content = f"""
========================================
          SMARTQ QUEUE TICKET
========================================

Ticket Reference: {ticket_ref}
Queue Type: {queue_type or 'N/A'}
Queue Purpose: {queue_purpose or 'N/A'}

----------------------------------------
CUSTOMER INFORMATION
----------------------------------------
Name: {fullname}
Phone: {phone}
Purpose: {purpose or 'N/A'}
Registered: {created_at.strftime('%Y-%m-%d %I:%M %p') if created_at else 'N/A'}

----------------------------------------
IMPORTANT NOTES
----------------------------------------
• Please keep this ticket for your records
• Show this ticket at the service counter

========================================
        Thank you for using SmartQ!
========================================
"""
        
        from flask import Response
        return Response(
            ticket_content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename=SmartQ_Ticket_{ticket_ref}.txt'
            }
        )
    except Exception as e:
        print(f"Error generating ticket: {e}")
        return "Error generating ticket", 500


@app.route('/')
def home():
    return redirect(url_for('admin'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
