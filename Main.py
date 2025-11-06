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
        print("✅ Database connected successfully!")
        return conn
    except Exception as e:
        print("❌ Database connection failed:", e)
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
            flash("❌ Passwords do not match.")
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
            flash("✅ Account created! You can now log in.")
            return redirect(url_for('login'))

        except errors.UniqueViolation:
            flash("⚠️ Email already exists.")
        except Exception as e:
            flash(f"❌ Error: {str(e)}")

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
                flash("⚠️ Account not found! Please sign up.")
                return redirect(url_for('signup'))

            if not check_password_hash(user[3], password):
                flash("❌ Incorrect password.")
                return redirect(url_for('login'))

            # ✅ Store user info in session
            session['user_email'] = email
            session['user_fullname'] = user[1]

            flash("✅ Login successful!")
            return redirect(url_for('homepage'))

        except Exception as e:
            flash(f"❌ Error: {str(e)}")

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
            flash("✅ Candidate added successfully!")
        except Exception as e:
            flash(f"❌ Error adding candidate: {str(e)}")

    return render_template('Admin2/AddCandidate.html')


@app.route('/scantracking')
def scantracking():
    return render_template('Admin2/Scantracking.html')


@app.route('/admin_settings', methods=['GET', 'POST'])
@app.route('/admin_settings', methods=['GET', 'POST'])
def admin_settings():
    if 'user_email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    email = session['user_email']
    conn = get_db_connection()
    cur = conn.cursor()

    # ✅ Fetch fullname, email, and password for verification
    cur.execute("SELECT fullname, email, password FROM users WHERE email = %s", (email,))
    admin = cur.fetchone()

    if request.method == 'POST':
        fullname = request.form.get('fullname', admin[0])
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        current_hashed_pw = admin[2]  # stored hashed password

        # ✅ If changing password
        if new_password:
            if not check_password_hash(current_hashed_pw, old_password):
                flash("❌ Old password is incorrect.")
            elif new_password != confirm_password:
                flash("❌ New passwords do not match.")
            else:
                hashed_pw = generate_password_hash(new_password)
                cur.execute(
                    "UPDATE users SET fullname = %s, password = %s WHERE email = %s",
                    (fullname, hashed_pw, email)
                )
                flash("✅ Name and password updated successfully!")
        else:
            # ✅ Only update name if no new password
            cur.execute("UPDATE users SET fullname = %s WHERE email = %s", (fullname, email))
            flash("✅ Name updated successfully!")

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
    flash("👋 Logged out successfully.")
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
        cur.close()
    except Exception as e:
        print(f"Error ensuring queue_entries table: {e}")
        raise

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

def generate_ticket_reference(queue_slug, entry_id):
    """Return a user-facing ticket reference that isn't sequentially ordered."""
    base = re.sub(r'[^A-Z0-9]', '', queue_slug.upper())
    if not base:
        base = "TICKET"
    token_src = f"{queue_slug}-{entry_id}"
    token = hashlib.sha1(token_src.encode("utf-8")).hexdigest()[:6].upper()
    return f"{base}-{token}"

def save_qr(queue_type, queue_purpose, queue_link, created_by, queue_number=None):
    """Save QR to database and return the inserted ID."""
    try:
        print(f"save_qr called with: type='{queue_type}', purpose='{queue_purpose}', link='{queue_link}', created_by='{created_by}'")
        conn = get_db_connection()
        if conn is None:
            print("ERROR: Database connection failed in save_qr")
            return None
        
        print("Database connection successful")
        cur = conn.cursor()
        
        # Try with RETURNING first (PostgreSQL)
        try:
            print("Attempting INSERT with RETURNING...")
            cur.execute(
                "INSERT INTO qr_history (queue_type, queue_purpose, queue_link, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
                (queue_type, queue_purpose, queue_link, created_by)
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
                    "INSERT INTO qr_history (queue_type, queue_purpose, queue_link, created_by) VALUES (%s, %s, %s, %s)",
                    (queue_type, queue_purpose, queue_link, created_by)
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
                "INSERT INTO temp_qr (queue_type, queue_purpose, queue_link, created_by) VALUES (%s, %s, %s, %s)",
                (queue_type, queue_purpose, queue_link, created_by)
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
        
        print(f"Queue Type: '{queue_type}', Purpose: '{queue_purpose}', Created By: '{created_by}'")
        
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
        
        # Save QR and get the ID
        print("Saving QR to database...")
        qr_id = save_qr(queue_type, queue_purpose, queue_link, created_by, queue_number)
        print(f"QR saved with ID: {qr_id}")
        
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
            if exists:
                conn.commit()
                cur.close()
                conn.close()
                print(f"Note: QR {qr_id} not in temp_qr (already deleted or never was), but exists in history")
                return jsonify({"status": "success", "message": "QR removed from active list (history preserved)"})
            else:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"status": "error", "message": "QR not found"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ QR {qr_id} deleted from temp_qr (history preserved)")
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
        cur.execute("""
            SELECT id, queue_type, queue_purpose, queue_link, created_by
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
                "created_by": row[4]
            })
        return jsonify(active_qrs)
    except Exception as e:
        print(f"Error fetching temp QR data: {e}")
        return jsonify([])

@app.route('/qr_history_data', methods=['GET'])
def qr_history_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Join qr_history with users table to get fullname
        cur.execute("""
            SELECT h.id, h.queue_type, h.queue_purpose, h.queue_link, u.fullname, h.created_at
            FROM qr_history h
            LEFT JOIN users u ON h.created_by = u.email
            ORDER BY h.created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "queue_type": row[1],
                "queue_purpose": row[2],
                "queue_link": row[3],
                "created_by": row[4] if row[4] else row[3],  # fallback if fullname not found
                "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S")
            })
        return jsonify(history)
    except Exception as e:
        print(f"Error fetching QR history: {e}")
        return jsonify([])



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
    """
    Return a JSON list of users who scanned a specific QR code.
    Expected columns: fullname, email, scanned_at
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Assuming you have a table like 'qr_scans' that stores scans
        # Example schema:
        # CREATE TABLE qr_scans (
        #   id SERIAL PRIMARY KEY,
        #   qr_id INT REFERENCES temp_qr(id),
        #   fullname VARCHAR(255),
        #   email VARCHAR(255),
        #   scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        # );
        cur.execute("""
            SELECT fullname, email, scanned_at
            FROM qr_scans
            WHERE qr_id = %s
            ORDER BY scanned_at DESC
        """, (qr_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        scans = []
        for row in rows:
            scans.append({
                "fullname": row[0],
                "email": row[1],
                "scanned_at": row[2].strftime("%Y-%m-%d %H:%M:%S")
            })
        return jsonify(scans)

    except Exception as e:
        print(f"Error fetching QR scans: {e}")
        return jsonify([])

@app.route('/add_candidate_modal', methods=['POST'])
def add_candidate_modal():
    data = request.get_json()
    fullname = data.get('fullname')
    phone = data.get('phone')
    timeslot = data.get('timeslot')
    qr_link = data.get('link')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Save candidate and link to QR
        cur.execute("INSERT INTO candidates (fullname, phone, timeslot, purpose, qr_link) VALUES (%s,%s,%s,%s,%s)",
                    (fullname, phone, timeslot, f"Linked to QR", qr_link))
        conn.commit()
        cur.execute("SELECT id FROM temp_qr WHERE queue_link=%s", (qr_link,))
        qr_id = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({"status": "success", "qr_id": qr_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
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

    if request.method == 'POST':
        fullname = (request.form.get('fullname') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        purpose = (request.form.get('purpose') or '').strip()

        if not fullname or not phone:
            flash("Please provide your full name and phone number to join the queue.", "error")
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





@app.route('/')
def home():
    return redirect(url_for('admin'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
