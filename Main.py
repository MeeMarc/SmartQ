import os
import re
import random
import smtplib
import hashlib
import glob
from collections import OrderedDict
from threading import Lock
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response, send_from_directory
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import psycopg2
from psycopg2 import errors
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import io
import base64
import time
from werkzeug.utils import secure_filename

load_dotenv()  # Load variables from .env if present (local dev)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-insecure-secret")  # for flash messages
app.permanent_session_lifetime = timedelta(days=30)  # 30 days for "Remember Me"
QUEUE_ENTRIES_SCHEMA_MIGRATED = False

# Make Flask respect X-Forwarded-* headers on Render so url_for(..., _external=True)
# uses the correct scheme/host (https and your subdomain)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

import re
def normalize_processing_time(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    # Accept "3", "3.7", "3 days", "5 business days"
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return ""

    num = float(m.group(1))
    if num <= 0:
        return ""

    return str(int(num))  # ✅ whole number only


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'images'),
        'logo.png',
        mimetype='image/png'
    )

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


def extract_first_name(fullname):
    """Extract a best-effort first name from stored fullname formats."""
    name = (fullname or "").strip()
    if not name:
        return "Applicant"

    # Stored format is commonly "Lastname, Firstname M.I. Suffix".
    if "," in name:
        given_part = name.split(",", 1)[1].strip()
        if given_part:
            return given_part.split()[0]

    return name.split()[0]


def is_valid_email(value):
    """Return True when value looks like a valid email address."""
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (value or "").strip()))


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


def ensure_uploaded_documents_table(conn):
    """Create the uploaded_documents table if it doesn't exist (stores files in DB)."""
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_documents (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                data BYTEA NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error creating uploaded_documents table: {e}")
        conn.rollback()


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
        terms_accepted = request.form.get('terms') == 'on'

        # Validate terms and conditions acceptance
        if not terms_accepted:
            flash("You must agree to the Terms and Conditions to create an account.", "error")
            return redirect(url_for('signup'))

        if password != confirm:
            flash("Passwords do not match.", "error")
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
            flash("Account created! You can now log in.", "success")
            return redirect(url_for('login'))

        except errors.UniqueViolation:
            flash("Email already exists.", "error")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template('Admin/SignUp.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = request.form.get('remember') == 'on'  # Check if "Remember Me" is checked

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if not user:
                flash("Account not found! Please sign up.", "error")
                return redirect(url_for('signup'))

            if not check_password_hash(user[3], password):
                flash("Incorrect password.", "error")
                return redirect(url_for('login'))

            # Store user info in session
            session['user_email'] = email
            session['user_fullname'] = user[1]
            
            # If "Remember Me" is checked, make session permanent (30 days)
            if remember_me:
                session.permanent = True
            else:
                session.permanent = False  # Session expires when browser closes

            flash("Login successful!", "success")
            return redirect(url_for('homepage'))

        except Exception as e:
            flash(f"Error: {str(e)}", "error")

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


# Allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'jpg', 'png', 'zip'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Content type mapping
CONTENT_TYPE_MAP = {
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'txt': 'text/plain',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'zip': 'application/zip',
}

def get_content_type(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')

# Hot in-process cache to reduce repeat DB fetches for uploaded files.
DOCUMENT_CACHE_MAX_ITEMS = max(1, int(os.getenv("DOCUMENT_CACHE_MAX_ITEMS", "200")))
DOCUMENT_CACHE_TTL_SECONDS = max(0, int(os.getenv("DOCUMENT_CACHE_TTL_SECONDS", "900")))
_document_cache = OrderedDict()
_document_cache_lock = Lock()

def _cache_document(filename, data_bytes, content_type):
    if not filename:
        return
    expires_at = (time.time() + DOCUMENT_CACHE_TTL_SECONDS) if DOCUMENT_CACHE_TTL_SECONDS > 0 else 0
    with _document_cache_lock:
        _document_cache[filename] = (data_bytes, content_type, expires_at)
        _document_cache.move_to_end(filename)
        while len(_document_cache) > DOCUMENT_CACHE_MAX_ITEMS:
            _document_cache.popitem(last=False)

def _get_cached_document(filename):
    if not filename:
        return None
    now = time.time()
    with _document_cache_lock:
        cached = _document_cache.get(filename)
        if not cached:
            return None
        data_bytes, content_type, expires_at = cached
        if expires_at and expires_at <= now:
            _document_cache.pop(filename, None)
            return None
        _document_cache.move_to_end(filename)
        return data_bytes, content_type

def save_file_to_db(filename, file_data, content_type=None):
    """Save a file to the uploaded_documents table in the database."""
    if content_type is None:
        content_type = get_content_type(filename)
    data_bytes = file_data if isinstance(file_data, bytes) else bytes(file_data)
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return False
        ensure_uploaded_documents_table(conn)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO uploaded_documents (filename, content_type, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (filename) DO UPDATE SET data = EXCLUDED.data, content_type = EXCLUDED.content_type, created_at = NOW()
        """, (filename, content_type, psycopg2.Binary(data_bytes)))
        conn.commit()
        _cache_document(filename, data_bytes, content_type)
        return True
    except Exception as e:
        print(f"Error saving file to DB: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# Upload document endpoint (entry_id-based + accepted-only)
@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'document' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['document']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    # ✅ Use entry_id (matches your JS: formData.append("entry_id", entryId))
    entry_id_raw = (request.form.get('entry_id') or '').strip()
    if not entry_id_raw.isdigit():
        return jsonify({"error": "Missing or invalid entry_id"}), 400
    entry_id = int(entry_id_raw)

    conn = None
    cur = None
    recipient_email = ""
    applicant_id = ""

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        ensure_queue_entries_table(conn)
        cur = conn.cursor()

        # ✅ Fetch admin_status + email for this specific entry
        cur.execute("""
            SELECT applicant_id, email, admin_status, phone
            FROM queue_entries
            WHERE id = %s
            LIMIT 1
        """, (entry_id,))
        row = cur.fetchone()

        if not row:
            return jsonify({"error": "Entry not found"}), 404

        applicant_id, recipient_email, admin_status, phone = row
        admin_status = (admin_status or "pending").strip().lower()
        recipient_email = resolve_entry_email(
            cur,
            current_email=recipient_email,
            applicant_id=applicant_id,
            phone=phone
        )
        applicant_id = (applicant_id or "").strip()

        # ✅ Block if not accepted
        if admin_status != "accepted":
            return jsonify({
                "error": "Documents can only be sent for ACCEPTED applications.",
                "admin_status": admin_status
            }), 403

        # ✅ Email required
        if not is_valid_email(recipient_email):
            return jsonify({"error": "Recipient email is missing or invalid for this entry"}), 400

    except Exception as e:
        return jsonify({"error": f"Failed to validate entry: {str(e)}"}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    # ✅ Save file to database (persistent across Render redeploys)
    timestamp = int(time.time())
    filename = f"entry{entry_id}_{timestamp}_{secure_filename(file.filename)}"
    file_data = file.read()
    content_type = get_content_type(file.filename)

    if not save_file_to_db(filename, file_data, content_type):
        return jsonify({"error": "Failed to save document"}), 500

    download_path = url_for('uploaded_file', filename=filename)
    download_url = f"{get_public_base_url()}{download_path}"

    return jsonify({
        "download_url": download_url,
        "download_link": download_url,
        "document_link": download_url,
        "file_url": download_url,
        "entry_id": entry_id,
        "applicant_id": applicant_id,
        "email": recipient_email,
        "admin_status": "accepted"
    })

# Serve uploaded files from database
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    filename = (filename or "").strip().strip("/")
    if not filename:
        return "File not found", 404

    cached = _get_cached_document(filename)
    if cached:
        data_bytes, content_type = cached
        response = make_response(data_bytes)
        response.headers['Content-Type'] = content_type
        response.headers['Content-Length'] = len(data_bytes)
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed", 500
        ensure_uploaded_documents_table(conn)
        cur = conn.cursor()
        cur.execute("SELECT data, content_type FROM uploaded_documents WHERE filename = %s", (filename,))
        row = cur.fetchone()
        if not row:
            return "File not found", 404
        file_data, content_type = row
        data_bytes = bytes(file_data)
        _cache_document(filename, data_bytes, content_type)
        response = make_response(data_bytes)
        response.headers['Content-Type'] = content_type
        response.headers['Content-Length'] = len(data_bytes)
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
    except Exception as e:
        print(f"Error serving file: {e}")
        return "Error retrieving file", 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

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

def ensure_queue_entries_table(conn, include_column_migrations=True):
    """Create queue_entries table if it doesn't exist.

    `include_column_migrations=False` keeps read-heavy endpoints fast by
    skipping ALTER TABLE checks.
    """
    global QUEUE_ENTRIES_SCHEMA_MIGRATED
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
                applicant_id VARCHAR(100),
                email VARCHAR(255),
                purpose TEXT,
                status VARCHAR(50) DEFAULT 'waiting',
                admin_status VARCHAR(50) DEFAULT 'pending',
                reference_number VARCHAR(100),
                id_doc_path VARCHAR(500),
                req_doc_path VARCHAR(500),
                signature_path VARCHAR(500),
                notification_sent BOOLEAN DEFAULT FALSE,
                notification_message TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

        if not include_column_migrations or QUEUE_ENTRIES_SCHEMA_MIGRATED:
            cur.close()
            return

        # Ensure required columns exist (handles older schemas)
        column_statements = [
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_slug VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_number INTEGER",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_type VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS queue_purpose VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS fullname VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS phone VARCHAR(50)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS applicant_id VARCHAR(100)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS purpose TEXT",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'waiting'",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS reference_number VARCHAR(100)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS id_doc_path VARCHAR(500)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS req_doc_path VARCHAR(500)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS signature_path VARCHAR(500)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS reschedule_status VARCHAR(50)",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS rescheduled_to_queue_number INTEGER",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS last_rescheduled_at TIMESTAMP WITHOUT TIME ZONE",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS admin_status VARCHAR(50) DEFAULT 'pending'",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE",
            "ALTER TABLE queue_entries ADD COLUMN IF NOT EXISTS notification_message TEXT"
        ]

        migration_failed = False
        for stmt in column_statements:
            try:
                cur.execute(stmt)
                conn.commit()
            except Exception as column_error:
                # Log and continue; column may already exist with different definition
                print(f"Warning: ensure_queue_entries_table column migration issue: {column_error}")
                conn.rollback()
                migration_failed = True

        if not migration_failed:
            QUEUE_ENTRIES_SCHEMA_MIGRATED = True
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

def ensure_queue_form_config_columns(conn):
    """Ensure queue form config columns exist in qr_history and temp_qr (enable/disable registration fields)."""
    columns = [
        "require_supporting_doc BOOLEAN DEFAULT TRUE",
        "require_valid_id BOOLEAN DEFAULT TRUE",
        "require_student_id BOOLEAN DEFAULT TRUE",
        "esign_required BOOLEAN DEFAULT TRUE",
    ]
    try:
        cur = conn.cursor()
        for col in columns:
            for table in ("qr_history", "temp_qr"):
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col}")
                    conn.commit()
                except Exception as e:
                    print(f"Note: Could not add {col} to {table}: {e}")
                    conn.rollback()
        cur.close()
    except Exception as e:
        print(f"Error ensuring queue form config columns: {e}")

def ensure_queue_mode_columns(conn):
    """Ensure queue mode columns exist in qr_history and temp_qr."""
    columns = [
        "processing_method VARCHAR(100)",
        "release_type VARCHAR(100)",
    ]
    try:
        cur = conn.cursor()
        for col in columns:
            for table in ("qr_history", "temp_qr"):
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col}")
                    conn.commit()
                except Exception as e:
                    print(f"Note: Could not add {col} to {table}: {e}")
                    conn.rollback()
        cur.close()
    except Exception as e:
        print(f"Error ensuring queue mode columns: {e}")

def normalize_processing_method(value):
    raw = (value or "").strip()
    v = raw.lower()
    if v in ("walk-in", "walk in", "walkin", "in-person", "in person", "onsite", "on-site"):
        return "Walk-in"
    if v in ("online", "digital", "remote"):
        return "Online"
    return raw

def normalize_release_type(value):
    raw = (value or "").strip()
    v = raw.lower()
    if v in ("physical claim", "physical", "physical release", "pickup", "claim"):
        return "Physical Claim"
    if v in ("digital copy", "digital", "digital release", "online copy", "email"):
        return "Digital Copy"
    return raw

def get_queue_mode_hints(processing_method, release_type):
    """Return normalized mode values and user-facing flow hints."""
    mode = normalize_processing_method(processing_method) or "Online"
    release = normalize_release_type(release_type) or "Digital Copy"

    matrix = {
        ("Online", "Digital Copy"): {
            "registration_hint": "Complete registration online. Approved documents are released digitally.",
            "waiting_hint": "Monitor your email for approval updates and digital document release."
        },
        ("Online", "Physical Claim"): {
            "registration_hint": "Submit online, then wait for a pickup notice before claiming the document onsite.",
            "waiting_hint": "Wait for approval, then present your ticket at the office for physical claiming."
        },
        ("Walk-in", "Digital Copy"): {
            "registration_hint": "Queue may be processed onsite, but approved documents are sent digitally.",
            "waiting_hint": "After review, your document will be sent digitally to your provided contact."
        },
        ("Walk-in", "Physical Claim"): {
            "registration_hint": "This queue is handled onsite, and document release is through physical claiming.",
            "waiting_hint": "Bring your ticket and required documents when called for onsite physical claiming."
        },
    }
    hints = matrix.get((mode, release), {
        "registration_hint": "Follow queue instructions and complete the required steps for this queue.",
        "waiting_hint": "Wait for status updates and follow the release instructions provided by the office."
    })
    return {
        "processing_method": mode,
        "release_type": release,
        "registration_hint": hints["registration_hint"],
        "waiting_hint": hints["waiting_hint"],
    }

def get_queue_mode(queue_slug, queue_number, cur=None, ensure_columns=True):
    """Get queue processing/release mode for a queue."""
    default = {"processing_method": "Online", "release_type": "Digital Copy"}
    queue_path = f"/queue/{queue_slug}/{queue_number}"
    queue_links = []
    try:
        queue_links.append(f"{get_public_base_url()}{queue_path}")
    except Exception:
        pass
    queue_links.append(queue_path)
    queue_suffix = f"%{queue_path}"

    own_connection = cur is None
    conn = None
    if own_connection:
        conn = get_db_connection()
        if conn is None:
            return default

    row = None
    try:
        if own_connection:
            if ensure_columns:
                ensure_queue_mode_columns(conn)
            cur = conn.cursor()

        for table_name in ("qr_history", "temp_qr"):
            if row:
                break
            for queue_link in queue_links:
                try:
                    cur.execute(
                        f"""SELECT processing_method, release_type
                            FROM {table_name}
                            WHERE queue_link = %s
                            ORDER BY created_at DESC, id DESC
                            LIMIT 1""",
                        (queue_link,),
                    )
                    row = cur.fetchone()
                except Exception as query_error:
                    print(f"Warning get_queue_mode exact match query failed on {table_name}: {query_error}")
                    try:
                        cur.connection.rollback()
                    except Exception:
                        pass
                    row = None
                if row:
                    break

        if not row:
            for table_name in ("qr_history", "temp_qr"):
                try:
                    cur.execute(
                        f"""SELECT processing_method, release_type
                            FROM {table_name}
                            WHERE queue_link LIKE %s
                            ORDER BY created_at DESC, id DESC
                            LIMIT 1""",
                        (queue_suffix,),
                    )
                    row = cur.fetchone()
                except Exception as query_error:
                    print(f"Warning get_queue_mode fallback query failed on {table_name}: {query_error}")
                    try:
                        cur.connection.rollback()
                    except Exception:
                        pass
                    row = None
                if row:
                    break
    except Exception as e:
        print(f"Error get_queue_mode: {e}")
    finally:
        try:
            if own_connection and cur:
                cur.close()
        except Exception:
            pass
        try:
            if own_connection and conn:
                conn.close()
        except Exception:
            pass

    if row:
        mode = normalize_processing_method(row[0]) or default["processing_method"]
        release = normalize_release_type(row[1]) or default["release_type"]
        return {"processing_method": mode, "release_type": release}
    return default


def get_queue_processing_days(queue_slug, queue_number, cur=None):
    """Get estimated processing time (in days) for a queue."""
    if not queue_slug or queue_number is None:
        return None

    queue_path = f"/queue/{queue_slug}/{queue_number}"
    queue_links = []
    try:
        queue_links.append(f"{get_public_base_url()}{queue_path}")
    except Exception:
        pass
    queue_links.append(queue_path)
    queue_suffix = f"%{queue_path}"

    own_connection = cur is None
    conn = None
    if own_connection:
        conn = get_db_connection()
        if conn is None:
            return None

    row = None
    try:
        if own_connection:
            cur = conn.cursor()

        for table_name in ("qr_history", "temp_qr"):
            if row:
                break

            for queue_link in queue_links:
                try:
                    cur.execute(
                        f"""SELECT avg_service_time
                            FROM {table_name}
                            WHERE queue_link = %s
                              AND avg_service_time IS NOT NULL
                            ORDER BY created_at DESC, id DESC
                            LIMIT 1""",
                        (queue_link,),
                    )
                    row = cur.fetchone()
                except Exception as query_error:
                    print(f"Warning get_queue_processing_days exact match query failed on {table_name}: {query_error}")
                    try:
                        cur.connection.rollback()
                    except Exception:
                        pass
                    row = None

                if row and row[0] is not None:
                    break

            if row and row[0] is not None:
                break

            try:
                cur.execute(
                    f"""SELECT avg_service_time
                        FROM {table_name}
                        WHERE queue_link LIKE %s
                          AND avg_service_time IS NOT NULL
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1""",
                    (queue_suffix,),
                )
                row = cur.fetchone()
            except Exception as query_error:
                print(f"Warning get_queue_processing_days fallback query failed on {table_name}: {query_error}")
                try:
                    cur.connection.rollback()
                except Exception:
                    pass
                row = None

            if row and row[0] is not None:
                break
    except Exception as e:
        print(f"Error get_queue_processing_days: {e}")
    finally:
        try:
            if own_connection and cur:
                cur.close()
        except Exception:
            pass
        try:
            if own_connection and conn:
                conn.close()
        except Exception:
            pass

    if row and row[0] is not None:
        try:
            return float(row[0])
        except (TypeError, ValueError):
            return None
    return None


def format_processing_time_label(days_value):
    """Format processing days for user-facing text (e.g., '3 days')."""
    if days_value is None:
        return ""
    try:
        numeric = float(days_value)
    except (TypeError, ValueError):
        return str(days_value).strip()
    if numeric <= 0:
        return ""
    if numeric.is_integer():
        whole = int(numeric)
        return f"{whole} day" if whole == 1 else f"{whole} days"
    return f"{numeric:g} days"

def get_queue_config(queue_slug, queue_number):
    """Get registration form config for a queue (which fields are enabled). Returns dict with require_* booleans."""
    default = {
        "require_supporting_doc": True,
        "require_valid_id": True,
        "require_student_id": True,
        "esign_required": True,
    }
    queue_path = f"/queue/{queue_slug}/{queue_number}"
    queue_links = []
    try:
        queue_links.append(f"{get_public_base_url()}{queue_path}")
    except Exception:
        pass
    # Keep a relative fallback in case queue links were saved without host.
    queue_links.append(queue_path)
    queue_suffix = f"%{queue_path}"

    conn = get_db_connection()
    if conn is None:
        return default
    row = None
    try:
        ensure_queue_form_config_columns(conn)
        cur = conn.cursor()

        for table_name in ("qr_history", "temp_qr"):
            if row:
                break
            for queue_link in queue_links:
                cur.execute(
                    f"""SELECT require_supporting_doc, require_valid_id, require_student_id, esign_required
                        FROM {table_name}
                        WHERE queue_link = %s
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1""",
                    (queue_link,),
                )
                row = cur.fetchone()
                if row:
                    break

        # Fallback: match by queue path suffix so config still resolves across base URL changes.
        if not row:
            for table_name in ("qr_history", "temp_qr"):
                cur.execute(
                    f"""SELECT require_supporting_doc, require_valid_id, require_student_id, esign_required
                        FROM {table_name}
                        WHERE queue_link LIKE %s
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1""",
                    (queue_suffix,),
                )
                row = cur.fetchone()
                if row:
                    break

        cur.close()
    except Exception as e:
        print(f"Error get_queue_config: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if row:
        return {
            "require_supporting_doc": bool(row[0]) if row[0] is not None else True,
            "require_valid_id": bool(row[1]) if row[1] is not None else True,
            "require_student_id": bool(row[2]) if row[2] is not None else True,
            "esign_required": bool(row[3]) if row[3] is not None else True,
        }
    return default

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
             afternoon_start=None, afternoon_end=None, staff_count=None, queue_limit=None,
             require_supporting_doc=True, require_valid_id=True, require_student_id=True, esign_required=True,
             processing_method=None, release_type=None):
    """Save QR to database and return the inserted ID."""
    try:
        print(f"save_qr called with: type='{queue_type}', purpose='{queue_purpose}', link='{queue_link}', created_by='{created_by}', queue_limit={queue_limit}")
        conn = get_db_connection()
        if conn is None:
            print("ERROR: Database connection failed in save_qr")
            return None

        print("Database connection successful")

        ensure_queue_limit_column(conn)
        ensure_queue_form_config_columns(conn)
        ensure_queue_mode_columns(conn)

        processing_method = normalize_processing_method(processing_method) or "Online"
        release_type = normalize_release_type(release_type) or "Digital Copy"

        cur = conn.cursor()

        # Try with RETURNING first (PostgreSQL)
        try:
            print("Attempting INSERT with RETURNING...")
            cur.execute(
                """INSERT INTO qr_history 
                (queue_type, queue_purpose, queue_link, created_by, 
                 avg_service_time, morning_start, morning_end, 
                 afternoon_start, afternoon_end, staff_count, queue_limit,
                 require_supporting_doc, require_valid_id, require_student_id, esign_required,
                 processing_method, release_type) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (queue_type, queue_purpose, queue_link, created_by,
                 avg_service_time, morning_start, morning_end,
                 afternoon_start, afternoon_end, staff_count, queue_limit,
                 require_supporting_doc, require_valid_id, require_student_id, esign_required,
                 processing_method, release_type)
            )
            qr_id = cur.fetchone()[0]
            print(f"INSERT successful with RETURNING, got ID: {qr_id}")
        except Exception as ret_error:
            print(f"RETURNING failed, trying alternative: {ret_error}")
            import traceback
            traceback.print_exc()
            try:
                cur.execute(
                    """INSERT INTO qr_history 
                    (queue_type, queue_purpose, queue_link, created_by,
                     avg_service_time, morning_start, morning_end,
                     afternoon_start, afternoon_end, staff_count, queue_limit,
                     require_supporting_doc, require_valid_id, require_student_id, esign_required,
                     processing_method, release_type) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (queue_type, queue_purpose, queue_link, created_by,
                     avg_service_time, morning_start, morning_end,
                     afternoon_start, afternoon_end, staff_count, queue_limit,
                     require_supporting_doc, require_valid_id, require_student_id, esign_required,
                     processing_method, release_type)
                )
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
                 afternoon_start, afternoon_end, staff_count, queue_limit,
                 require_supporting_doc, require_valid_id, require_student_id, esign_required,
                 processing_method, release_type) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (queue_type, queue_purpose, queue_link, created_by,
                 avg_service_time, morning_start, morning_end,
                 afternoon_start, afternoon_end, staff_count, queue_limit,
                 require_supporting_doc, require_valid_id, require_student_id, esign_required,
                 processing_method, release_type)
            )
            print("temp_qr insert successful")
        except Exception as temp_error:
            print(f"Note: temp_qr insert failed (this is okay): {temp_error}")
        
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
        # Get queue timing inputs (support both legacy avgServiceTime and current processingDays)
        avg_service_time = request.form.get('avgServiceTime', '').strip()
        processing_days = request.form.get('processingDays', '').strip()
        if not avg_service_time and processing_days:
            avg_service_time = processing_days
        morning_start = request.form.get('morningStart', '').strip()
        morning_end = request.form.get('morningEnd', '').strip()
        afternoon_start = request.form.get('afternoonStart', '').strip()
        afternoon_end = request.form.get('afternoonEnd', '').strip()
        staff_count = request.form.get('staffCount', '').strip()
        queue_limit = request.form.get('queueLimit', '').strip()
        processing_method = normalize_processing_method(request.form.get('processingMethod', '').strip())
        release_type = normalize_release_type(request.form.get('releaseType', '').strip())
        # Registration form field toggles (Yes/No from form; default True if missing)
        def form_bool(key, default=True):
            v = request.form.get(key, '').strip().lower()
            if v in ('yes', '1', 'true', 'on'): return True
            if v in ('no', '0', 'false'): return False
            return default
        require_supporting_doc = form_bool('supportingDoc', True)
        require_valid_id = form_bool('validId', True)
        require_student_id = form_bool('studentId', True)
        esign_required = form_bool('esignRequired', True)

        print(f"Queue Type: '{queue_type}', Purpose: '{queue_purpose}', Created By: '{created_by}'")
        print(f"Avg Service Time: {avg_service_time}, Staff Count: {staff_count}, Queue Limit: {queue_limit}")
        print(f"Morning: {morning_start} - {morning_end}, Afternoon: {afternoon_start} - {afternoon_end}")
        print(f"Processing Method: '{processing_method}', Release Type: '{release_type}'")
        
        if not queue_type or not queue_purpose:
            error_msg = "Queue Type and Purpose are required"
            print(f"Validation failed: {error_msg}")
            return jsonify({
                "error": error_msg,
                "qr_image": None
            }), 400

        if not processing_method or not release_type:
            error_msg = "Processing method and release type are required."
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
                       afternoon_start or None, afternoon_end or None, staff_count, queue_limit,
                       require_supporting_doc=require_supporting_doc, require_valid_id=require_valid_id,
                       require_student_id=require_student_id, esign_required=esign_required,
                       processing_method=processing_method, release_type=release_type)
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
            "qr_id": qr_id,
            "processing_days": avg_service_time,
            "processing_method": processing_method,
            "release_type": release_type
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
        if conn is None:
            return jsonify([])
        ensure_queue_mode_columns(conn)
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
            SELECT id, queue_type, queue_purpose, queue_link, created_by, created_at,
                   processing_method, release_type
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
                "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "N/A",
                "processing_method": normalize_processing_method(row[6]) or "Online",
                "release_type": normalize_release_type(row[7]) or "Digital Copy"
            })
        return jsonify(active_qrs)
    except Exception as e:
        print(f"Error fetching temp QR data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/qr_history_data', methods=['GET'])
def qr_history_data():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: Database connection failed")
            return jsonify({"error": "Database connection failed"}), 500

        cur = conn.cursor()

        # Detect available columns first so history still loads on older schemas.
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'qr_history'
            """
        )
        available_columns = {row[0] for row in cur.fetchall()}
        if not available_columns:
            return jsonify([])

        required_columns = ("id", "queue_type", "queue_purpose", "queue_link", "created_by", "created_at")
        missing_required = [col for col in required_columns if col not in available_columns]
        if missing_required:
            return jsonify({
                "error": f"qr_history missing required columns: {', '.join(missing_required)}"
            }), 500

        optional_columns = (
            "avg_service_time",
            "morning_start",
            "morning_end",
            "afternoon_start",
            "afternoon_end",
            "staff_count",
            "processing_method",
            "release_type",
        )
        optional_select_parts = [
            col if col in available_columns else f"NULL AS {col}"
            for col in optional_columns
        ]
        optional_select_sql = ",\n                   ".join(optional_select_parts)

        cur.execute(f"""
            SELECT id, queue_type, queue_purpose, queue_link, created_by, created_at,
                   {optional_select_sql}
            FROM qr_history
            ORDER BY created_at DESC
        """)

        rows = cur.fetchall()
        print(f"Found {len(rows)} QR codes in history")

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
                    "processing_method": normalize_processing_method(row[12]) or "Online",
                    "release_type": normalize_release_type(row[13]) or "Digital Copy",
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
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass



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


def resolve_queue_link_for_qr(cur, qr_id, prefer_active=True):
    """Resolve queue_link from QR tables.

    `prefer_active=True` checks `temp_qr` first because Scan Tracking buttons
    are rendered from active queue IDs.
    """
    lookup_order = ("temp_qr", "qr_history") if prefer_active else ("qr_history", "temp_qr")

    for table in lookup_order:
        try:
            cur.execute(f"SELECT queue_link FROM {table} WHERE id = %s", (qr_id,))
            row = cur.fetchone()
        except Exception:
            # Table may be missing in older deployments; try next source.
            try:
                # Reset transaction state so fallback queries can still run.
                cur.connection.rollback()
            except Exception:
                pass
            row = None

        if row and row[0]:
            return row[0]

    return None


def convert_doc_path_to_url(path_value):
    """Convert stored document path to a public URL."""
    if not path_value:
        return None

    path = str(path_value).replace('\\', '/')
    # New DB-stored documents use /uploads/ path
    if path.startswith('/uploads/'):
        return path
    if path.startswith('uploads/'):
        return f"/{path}"
    # Legacy paths from old filesystem storage
    if path.startswith('/static/'):
        return path
    if path.startswith('static/'):
        return f"/{path}"
    # Fallback: try as /uploads/ path (DB-stored)
    basename = os.path.basename(path)
    return f"/uploads/{basename}"


def normalize_email(value):
    """Return normalized email string (trimmed + lowercased)."""
    return (value or "").strip().lower()


def resolve_entry_email(cur, current_email=None, applicant_id=None, phone=None):
    """Resolve a usable email for an entry from direct or fallback identifiers."""
    normalized = normalize_email(current_email)
    if is_valid_email(normalized):
        return normalized

    fallback_candidates = []
    applicant_key = (applicant_id or "").strip()
    phone_key = (phone or "").strip()
    if applicant_key:
        fallback_candidates.append(("applicant_id", applicant_key))
    if phone_key:
        fallback_candidates.append(("phone", phone_key))

    for field_name, field_value in fallback_candidates:
        try:
            cur.execute(
                f"""
                SELECT email
                FROM queue_entries
                WHERE {field_name} = %s
                  AND email IS NOT NULL
                  AND BTRIM(email) <> ''
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (field_value,),
            )
            row = cur.fetchone()
        except Exception as e:
            print(f"Warning: resolve_entry_email lookup failed on {field_name}: {e}")
            try:
                cur.connection.rollback()
            except Exception:
                pass
            continue

        candidate = normalize_email(row[0]) if row else ""
        if is_valid_email(candidate):
            return candidate

    return normalized


def build_missing_entry_email_lookup(cur, scan_rows):
    """Batch-resolve emails for scan rows that have missing/invalid email."""
    if not scan_rows:
        return {}

    missing_entries = []
    phone_keys = set()
    applicant_keys = set()

    for row in scan_rows:
        entry_id = row[0]
        phone = (row[2] or "").strip()
        current_email = normalize_email(row[3])
        applicant_id = (row[12] or "").strip()

        if is_valid_email(current_email):
            continue

        missing_entries.append((entry_id, phone, applicant_id))
        if phone:
            phone_keys.add(phone)
        if applicant_id:
            applicant_keys.add(applicant_id)

    if not missing_entries:
        return {}

    by_phone = {}
    if phone_keys:
        try:
            cur.execute(
                """
                SELECT phone, email
                FROM queue_entries
                WHERE phone = ANY(%s)
                  AND email IS NOT NULL
                  AND BTRIM(email) <> ''
                ORDER BY created_at DESC, id DESC
                """,
                (list(phone_keys),),
            )
            for phone, email in cur.fetchall():
                phone_value = (phone or "").strip()
                email_value = normalize_email(email)
                if phone_value and is_valid_email(email_value):
                    by_phone.setdefault(phone_value, email_value)
        except Exception as e:
            print(f"Warning: build_missing_entry_email_lookup phone query failed: {e}")
            try:
                cur.connection.rollback()
            except Exception:
                pass

    by_applicant = {}
    if applicant_keys:
        try:
            cur.execute(
                """
                SELECT applicant_id, email
                FROM queue_entries
                WHERE applicant_id = ANY(%s)
                  AND email IS NOT NULL
                  AND BTRIM(email) <> ''
                ORDER BY created_at DESC, id DESC
                """,
                (list(applicant_keys),),
            )
            for applicant_id, email in cur.fetchall():
                applicant_value = (applicant_id or "").strip()
                email_value = normalize_email(email)
                if applicant_value and is_valid_email(email_value):
                    by_applicant.setdefault(applicant_value, email_value)
        except Exception as e:
            print(f"Warning: build_missing_entry_email_lookup applicant query failed: {e}")
            try:
                cur.connection.rollback()
            except Exception:
                pass

    lookup = {}
    for entry_id, phone, applicant_id in missing_entries:
        resolved = by_applicant.get(applicant_id) or by_phone.get(phone)
        if resolved:
            lookup[entry_id] = resolved

    return lookup


def build_legacy_uploaded_doc_lookup(cur, entry_ids):
    """Batch resolve legacy uploaded_documents filenames for entry IDs.

    Returns:
        {entry_id: {"id_doc": "/uploads/...", "req_doc": "...", "signature": "..."}}
    """
    normalized_ids = sorted({
        int(entry_id)
        for entry_id in (entry_ids or [])
        if str(entry_id).isdigit()
    })
    if not normalized_ids:
        return {}

    like_patterns = []
    for entry_id in normalized_ids:
        like_patterns.extend((f"{entry_id}_id%", f"{entry_id}_req%", f"{entry_id}_sig%"))

    try:
        cur.execute(
            """
            SELECT filename
            FROM uploaded_documents
            WHERE filename LIKE ANY(%s)
            ORDER BY created_at DESC, id DESC
            """,
            (like_patterns,),
        )
        rows = cur.fetchall()
    except Exception as e:
        # Table may not exist in older deployments; skip legacy DB fallback in that case.
        print(f"Warning: legacy uploaded_documents batch lookup skipped: {e}")
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return {}

    lookup = {}
    filename_pattern = re.compile(r"^(\d+)_(id|req|sig)")
    doc_key_by_prefix = {"id": "id_doc", "req": "req_doc", "sig": "signature"}

    for row in rows:
        filename = row[0] if row else None
        if not filename:
            continue

        match = filename_pattern.match(str(filename))
        if not match:
            continue

        entry_id = int(match.group(1))
        prefix = match.group(2)
        doc_key = doc_key_by_prefix.get(prefix)
        if not doc_key:
            continue

        entry_docs = lookup.setdefault(entry_id, {})
        # Keep first one (newest due ORDER BY) for deterministic fallback.
        entry_docs.setdefault(doc_key, f"/uploads/{filename}")

    return lookup


def resolve_entry_document_urls(entry_id, id_doc_path=None, req_doc_path=None, signature_path=None, legacy_doc_lookup=None):
    """Resolve document URLs from DB paths, with DB and filesystem fallback for legacy rows."""
    id_doc_url = convert_doc_path_to_url(id_doc_path)
    req_doc_url = convert_doc_path_to_url(req_doc_path)
    signature_url = convert_doc_path_to_url(signature_path)
    use_preloaded_lookup = legacy_doc_lookup is not None
    preloaded_docs = legacy_doc_lookup.get(entry_id, {}) if use_preloaded_lookup else {}

    # Fallback: check DB for legacy naming pattern
    def find_db_file(pattern_prefix, entry_id):
        try:
            conn = get_db_connection()
            if conn is None:
                return None
            ensure_uploaded_documents_table(conn)
            cur = conn.cursor()
            cur.execute("SELECT filename FROM uploaded_documents WHERE filename LIKE %s LIMIT 1", (f"{entry_id}_{pattern_prefix}%",))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return f"/uploads/{row[0]}"
        except Exception:
            pass
        return None

    # Also check filesystem for very old legacy files
    uploads_dir = os.path.join("static", "uploads")
    def find_legacy_file(pattern):
        if not os.path.isdir(uploads_dir):
            return None
        matches = sorted(glob.glob(os.path.join(uploads_dir, pattern)))
        if not matches:
            return None
        return f"/static/uploads/{os.path.basename(matches[0])}"

    if not id_doc_url:
        id_doc_url = preloaded_docs.get("id_doc") if use_preloaded_lookup else None
        if not id_doc_url:
            id_doc_url = (None if use_preloaded_lookup else find_db_file("id", entry_id)) or find_legacy_file(f"{entry_id}_id.*")
    if not req_doc_url:
        req_doc_url = preloaded_docs.get("req_doc") if use_preloaded_lookup else None
        if not req_doc_url:
            req_doc_url = (None if use_preloaded_lookup else find_db_file("req", entry_id)) or find_legacy_file(f"{entry_id}_req.*")
    if not signature_url:
        signature_url = preloaded_docs.get("signature") if use_preloaded_lookup else None
        if not signature_url:
            signature_url = (None if use_preloaded_lookup else find_db_file("sig", entry_id)) or find_legacy_file(f"{entry_id}_sig.*")

    return {
        "id_doc": id_doc_url,
        "req_doc": req_doc_url,
        "signature": signature_url,
    }
    
# ==============================================================  
# GET SCANS FOR A SPECIFIC QR
# ==============================================================

@app.route('/get_qr_scans/<int:qr_id>', methods=['GET'])
def get_qr_scans(qr_id):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500

        cur = conn.cursor()

        queue_link = resolve_queue_link_for_qr(cur, qr_id, prefer_active=True)
        if not queue_link:
            return jsonify({"status": "success", "scans": []}), 200

        match = re.search(r'/queue/([^/]+)/(\d+)', queue_link)
        if not match:
            return jsonify({"status": "error", "message": f"Invalid queue_link format: {queue_link}"}), 500

        queue_slug = match.group(1)
        queue_number = int(match.group(2))

        queue_mode = get_queue_mode(queue_slug, queue_number, cur=cur, ensure_columns=False)
        queue_processing_method = queue_mode.get("processing_method", "Online")
        queue_release_type = queue_mode.get("release_type", "Digital Copy")

        ensure_queue_entries_table(conn, include_column_migrations=False)

        cur.execute("""
            SELECT id, fullname, phone, email, purpose, status, admin_status, created_at, reference_number,
                   id_doc_path, req_doc_path, signature_path, applicant_id, notification_message, queue_type
            FROM queue_entries
            WHERE queue_slug = %s AND queue_number = %s
            ORDER BY 
                CASE 
                    WHEN status = 'waiting' THEN 1
                    WHEN status = 'completed' THEN 2
                    ELSE 3
                END,
                created_at DESC
        """, (queue_slug, queue_number))

        rows = cur.fetchall()
        entry_ids_needing_legacy_lookup = [
            row[0]
            for row in rows
            if not (row[9] and row[10] and row[11])
        ]
        legacy_doc_lookup = build_legacy_uploaded_doc_lookup(cur, entry_ids_needing_legacy_lookup)
        email_fallback_lookup = build_missing_entry_email_lookup(cur, rows)

        scans = []
        for row in rows:
            resolved_email = normalize_email(row[3])
            if not is_valid_email(resolved_email):
                resolved_email = email_fallback_lookup.get(row[0], resolved_email)

            doc_urls = resolve_entry_document_urls(
                row[0],
                id_doc_path=row[9],
                req_doc_path=row[10],
                signature_path=row[11],
                legacy_doc_lookup=legacy_doc_lookup,
            )

            id_doc_url = doc_urls.get("id_doc")
            req_doc_url = doc_urls.get("req_doc")
            signature_url = doc_urls.get("signature")

            scans.append({
                "id": row[0],
                "fullname": row[1] or "Unknown",
                "phone": row[2] or "",
                "email": resolved_email,
                "purpose": row[4] or "",
                "status": row[5] or "waiting",
                "admin_status": (row[6] or "pending").lower(),
                "scanned_at": row[7].strftime('%Y-%m-%d %I:%M %p') if row[7] else "",
                "reference_number": row[8] or "",
                "id_doc_url": id_doc_url,
                "req_doc_url": req_doc_url,
                "signature_url": signature_url,
                "has_documents": bool(id_doc_url or req_doc_url or signature_url),
                "applicant_id": row[12] or "",
                "notification_message": row[13] or "",
                "queue_type": row[14] or "Document",
                "queue_processing_method": queue_processing_method,
                "queue_release_type": queue_release_type
            })

        return jsonify({"status": "success", "scans": scans}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if cur:
            try: cur.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass



@app.route('/download_scans/<int:qr_id>', methods=['GET'])
def download_scans(qr_id):
    """Download all scans for a specific QR as a CSV file (physical proof of who scanned)."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed", 500

        cur = conn.cursor()

        # Prefer active queue IDs from temp_qr to avoid ID collisions with history.
        queue_link = resolve_queue_link_for_qr(cur, qr_id, prefer_active=True)

        if not queue_link:
            return "QR not found", 404

        # Extract queue_slug and queue_number from the queue_link
        match = re.search(r'/queue/([^/]+)/(\d+)', queue_link)
        if not match:
            return "Invalid queue link format", 400

        queue_slug = match.group(1)
        queue_number = int(match.group(2))

        ensure_queue_entries_table(conn, include_column_migrations=False)

        # Fetch entries for this queue
        cur.execute(
            """
            SELECT fullname, phone, email, purpose, status, admin_status, created_at, reference_number, applicant_id
            FROM queue_entries
            WHERE queue_slug = %s AND queue_number = %s
            ORDER BY created_at ASC
            """,
            (queue_slug, queue_number)
        )
        rows = cur.fetchall()

        # Build CSV content
        import csv
        import io as _io

        output = _io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Full Name",
            "Phone",
            "Email",
            "Purpose",
            "Queue Status",
            "Admin Status",
            "Scanned At",
            "Reference Number",
            "Applicant ID",
        ])

        for r in rows:
            fullname, phone, email, purpose, status, admin_status, created_at, ref_no, applicant_id = r
            writer.writerow([
                fullname or "",
                phone or "",
                email or "",
                purpose or "",
                status or "",
                admin_status or "",
                created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else "",
                ref_no or "",
                applicant_id or "",
            ])

        csv_data = output.getvalue()
        output.close()

        from flask import Response
        filename = f"scans_qr_{qr_id}.csv"
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )
    except Exception as e:
        print(f"Error generating scans CSV: {e}")
        import traceback
        traceback.print_exc()
        return "Error generating CSV", 500
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

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

@app.route('/accept_queue_entry/<int:entry_id>', methods=['POST'])
def accept_queue_entry(entry_id):
    try:
        data = request.get_json() or {}
        provided_notification_message = (data.get('notification_message') or '').strip()

        # ✅ admin free input from modal -> normalize to whole number
        provided_processing_time = normalize_processing_time(data.get('processing_time'))

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT fullname, email, created_at, status, queue_type, applicant_id, phone, queue_slug, queue_number
            FROM queue_entries
            WHERE id = %s
        """, (entry_id,))
        row = cur.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Entry not found"}), 404

        full_name, email, created_at, ticket_status, queue_type, applicant_id, phone, queue_slug, queue_number = row

        email = resolve_entry_email(cur, current_email=email, applicant_id=applicant_id, phone=phone)

        user_name = extract_first_name(full_name)
        application_status = "Accepted"

        # Optional fallback if admin didn't type processing time
        processing_days = get_queue_processing_days(queue_slug, queue_number, cur=cur)
        auto_processing_time = normalize_processing_time(format_processing_time_label(processing_days))

        # ✅ final processing_time is always "3" (or "")
        processing_time = provided_processing_time or auto_processing_time or ""

        default_message = (
            "We are pleased to inform you that your application form has been approved by our administrator.\n\n"
            "Please check your email regularly for further instructions and updates regarding your requested document."
        )

        base_message = provided_notification_message or default_message

        # ✅ No "days/days" and no "+ business days."
        processing_line = f"Estimated Document Processing Duration: {processing_time} + Business Days" if processing_time else ""

        if processing_line:
            if "\n\n" in base_message:
                first_part, rest = base_message.split("\n\n", 1)
                notification_message = f"{first_part}\n\n{processing_line}\n\n{rest}"
            else:
                notification_message = f"{base_message}\n\n{processing_line}"
        else:
            notification_message = base_message

        cur.execute("""
            UPDATE queue_entries
            SET admin_status = 'accepted',
                notification_message = %s
            WHERE id = %s
        """, (notification_message, entry_id))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "success",
            "entry_id": entry_id,
            "user_name": user_name,
            "fullname": full_name or "",
            "email": email or "",
            "created_at": created_at.strftime('%B %d, %Y') if created_at else "",
            "queue_type": queue_type or "Document",
            "processing_days": processing_days,
            "processing_time": processing_time,  # ✅ "3"
            "notification_message": notification_message,
            "application_status": application_status,
            "ticket_status": application_status,
            "admin_status": "accepted"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/reject_queue_entry/<int:entry_id>', methods=['POST'])
def reject_queue_entry(entry_id):
    try:
        data = request.get_json() or {}
        provided_notification_message = (data.get('notification_message') or '').strip()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT fullname, email, created_at, status, queue_type, applicant_id, phone, queue_slug, queue_number
            FROM queue_entries
            WHERE id = %s
        """, (entry_id,))
        row = cur.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Entry not found"}), 404

        full_name, email, created_at, ticket_status, queue_type, applicant_id, phone, queue_slug, queue_number = row
        email = resolve_entry_email(
            cur,
            current_email=email,
            applicant_id=applicant_id,
            phone=phone
        )
        user_name = extract_first_name(full_name)
        application_status = "Rejected"
        processing_days = get_queue_processing_days(queue_slug, queue_number, cur=cur)
        processing_time = format_processing_time_label(processing_days)

        notification_message = provided_notification_message or (
            "We regret to inform you that your application form has not been approved by our administrator at this time.\n\n"
            "Please review your submitted information and ensure that all requirements are complete and accurate before submitting a new request."
        )

        cur.execute("""
            UPDATE queue_entries
            SET admin_status = 'rejected',
                notification_message = %s
            WHERE id = %s
        """, (notification_message, entry_id))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "success",
            "entry_id": entry_id,
            "user_name": user_name,
            "fullname": full_name or "",
            "email": email or "",
            "created_at": created_at.strftime('%B %d, %Y') if created_at else "",
            "queue_type": queue_type or "Document",
            "processing_days": processing_days,
            "processing_time": processing_time,
            "notification_message": notification_message or "",
            "application_status": application_status,
            "ticket_status": application_status,
            "admin_status": "rejected"   # ✅ lowercase + consistent
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/view_entry_documents/<int:entry_id>', methods=['GET'])
def view_entry_documents(entry_id):
    """Get document URLs for a specific queue entry."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT id_doc_path, req_doc_path, signature_path, fullname, applicant_id
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
        
        id_doc_path, req_doc_path, signature_path, fullname, applicant_id = row

        doc_urls = resolve_entry_document_urls(
            entry_id,
            id_doc_path=id_doc_path,
            req_doc_path=req_doc_path,
            signature_path=signature_path,
        )
        documents = {k: v for k, v in doc_urls.items() if v}
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "documents": documents,
            "fullname": fullname or "Unknown",
            "applicant_id": applicant_id or ""
        })
    except Exception as e:
        print(f"Error fetching entry documents: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/send_notification', methods=['POST'])
def send_notification():
    """Send notification to queue entries - all or specific ones."""
    try:
        data = request.get_json()
        qr_id = data.get('qr_id')
        entry_ids = data.get('entry_ids', [])  # Empty list means notify all
        notification_message = data.get('message', '').strip()
        
        if not notification_message:
            return jsonify({"status": "error", "message": "Notification message is required"}), 400
        
        if not qr_id:
            return jsonify({"status": "error", "message": "QR ID is required"}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        # Get queue link to find queue_slug and queue_number.
        queue_link = resolve_queue_link_for_qr(cur, qr_id, prefer_active=True)

        if not queue_link:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "QR not found"}), 404

        # Extract queue_slug and queue_number from queue_link
        match = re.search(r'/queue/([^/]+)/(\d+)', queue_link)
        if not match:
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "Invalid queue link"}), 400
        
        queue_slug = match.group(1)
        queue_number = int(match.group(2))
        
        # Build query to update notifications
        if entry_ids and len(entry_ids) > 0:
            # Notify specific entries
            placeholders = ','.join(['%s'] * len(entry_ids))
            cur.execute(
                f"""
                UPDATE queue_entries 
                SET notification_message = %s, notification_sent = TRUE
                WHERE id IN ({placeholders}) AND queue_slug = %s AND queue_number = %s
                """,
                [notification_message] + entry_ids + [queue_slug, queue_number]
            )
        else:
            # Notify all entries in this queue
            cur.execute(
                """
                UPDATE queue_entries 
                SET notification_message = %s, notification_sent = TRUE
                WHERE queue_slug = %s AND queue_number = %s
                """,
                (notification_message, queue_slug, queue_number)
            )
        
        updated_count = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "message": f"Notification sent to {updated_count} entry/entries successfully"
        })
    except Exception as e:
        print(f"Error sending notification: {e}")
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

def find_next_available_queue(queue_type, current_queue_number, current_queue_slug=None):
    """Find the next available queue of the same type and slug."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cur = conn.cursor()
        
        # Find the next queue number of the same type and slug (greater than current)
        # Check both qr_history and temp_qr
        if current_queue_slug:
            # Match by both type AND slug for more precise matching
            cur.execute(
                """
                SELECT queue_number, queue_slug, queue_purpose
                FROM (
                    SELECT queue_number, queue_slug, queue_purpose FROM qr_history 
                    WHERE queue_type = %s AND queue_slug = %s AND queue_number > %s
                    UNION
                    SELECT queue_number, queue_slug, queue_purpose FROM temp_qr 
                    WHERE queue_type = %s AND queue_slug = %s AND queue_number > %s
                ) AS combined
                ORDER BY queue_number ASC
                LIMIT 1
                """,
                (queue_type, current_queue_slug, current_queue_number, queue_type, current_queue_slug, current_queue_number)
            )
        else:
            # Fallback: match by type only
            cur.execute(
                """
                SELECT queue_number, queue_slug, queue_purpose
                FROM (
                    SELECT queue_number, queue_slug, queue_purpose FROM qr_history 
                    WHERE queue_type = %s AND queue_number > %s
                    UNION
                    SELECT queue_number, queue_slug, queue_purpose FROM temp_qr 
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
            return {"queue_number": result[0], "queue_slug": result[1], "queue_purpose": result[2]}
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
            hours_remaining = int(24 - (time_diff.total_seconds() / 3600))
            if hours_remaining <= 1:
                return False, "You can only reschedule once per 24 hours. Please try again in less than 1 hour."
            else:
                return False, f"You can only reschedule once per 24 hours. Please try again in {hours_remaining} hours."
        
        return True, None
    except Exception as e:
        print(f"Error checking reschedule eligibility: {e}")
        return False, str(e)

def auto_enroll_pending_reschedules(queue_slug, queue_number, queue_type):
    """Auto-enroll users with pending reschedules for this queue type and slug."""
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        # Find all pending reschedules for this queue type and slug
        # Match by both slug and type to ensure they're from the same queue series
        cur.execute(
            """
            SELECT id, fullname, phone, purpose, queue_purpose, applicant_id, email
            FROM queue_entries
            WHERE reschedule_status = 'pending' 
            AND queue_type = %s
            AND queue_slug = %s
            AND status = 'rescheduled'
            """,
            (queue_type, queue_slug)
        )
        
        pending_entries = cur.fetchall()
        
        for entry in pending_entries:
            entry_id, fullname, phone, purpose, old_queue_purpose, applicant_id, email = entry
            
            # Create new entry in the new queue
            cur.execute(
                """
                INSERT INTO queue_entries (
                    queue_slug, queue_number, queue_type, queue_purpose,
                    fullname, phone, purpose, applicant_id, email, status, admin_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'waiting', 'pending')
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
                    applicant_id,
                    normalize_email(email),
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

@app.route('/force_auto_enroll/<queue_slug>/<int:queue_number>')
def force_auto_enroll(queue_slug, queue_number):
    """Manually trigger auto-enrollment for pending reschedules."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        # Get queue type from qr_history or temp_qr by matching queue_link pattern
        # Queue link format: https://domain.com/queue/<slug>/<number>
        cur.execute(
            """
            SELECT queue_type FROM (
                SELECT queue_type FROM qr_history 
                WHERE queue_link LIKE %s
                UNION
                SELECT queue_type FROM temp_qr 
                WHERE queue_link LIKE %s
            ) AS combined
            LIMIT 1
            """,
            (f'%/queue/{queue_slug}/{queue_number}', f'%/queue/{queue_slug}/{queue_number}')
        )
        
        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            return jsonify({"error": f"Queue {queue_slug}/{queue_number} not found in qr_history or temp_qr"}), 404
        
        queue_type = result[0]
        cur.close()
        conn.close()
        
        # Trigger auto-enrollment
        auto_enroll_pending_reschedules(queue_slug, queue_number, queue_type)
        
        return jsonify({
            "status": "success",
            "message": f"Auto-enrollment triggered for {queue_slug}/{queue_number}",
            "queue_type": queue_type,
            "note": "Check /debug_queue_entries/{queue_slug}/{queue_number} to verify"
        })
        
    except Exception as e:
        print(f"Error in force auto-enroll: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/debug_queue_entries/<queue_slug>/<int:queue_number>')
def debug_queue_entries(queue_slug, queue_number):
    """Debug endpoint to view all entries for a specific queue."""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT id, fullname, phone, queue_slug, queue_number, 
                   queue_type, queue_purpose, status, reschedule_status,
                   rescheduled_to_queue_number, created_at, last_rescheduled_at
            FROM queue_entries
            WHERE queue_slug = %s AND queue_number = %s
            ORDER BY created_at DESC
            """,
            (queue_slug, queue_number)
        )
        
        rows = cur.fetchall()
        entries = []
        for row in rows:
            entries.append({
                "id": row[0],
                "fullname": row[1],
                "phone": row[2],
                "queue_slug": row[3],
                "queue_number": row[4],
                "queue_type": row[5],
                "queue_purpose": row[6],
                "status": row[7],
                "reschedule_status": row[8],
                "rescheduled_to_queue_number": row[9],
                "created_at": str(row[10]) if row[10] else None,
                "last_rescheduled_at": str(row[11]) if row[11] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "queue": f"{queue_slug}/{queue_number}",
            "total_entries": len(entries),
            "entries": entries
        })
        
    except Exception as e:
        print(f"Error in debug endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
                   fullname, phone, purpose, status, applicant_id, email
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
        
        entry_id_db, queue_slug, queue_number, queue_type, queue_purpose, fullname, phone, purpose, status, applicant_id, email = row
        
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
        
        # Find next available queue of same type and slug
        next_queue = find_next_available_queue(queue_type, queue_number, queue_slug)
        print(f"DEBUG: Looking for next queue after {queue_slug}/{queue_number} of type '{queue_type}'")
        print(f"DEBUG: Found next queue: {next_queue}")
        
        if next_queue:
            # Next queue exists - move user there
            new_queue_slug = next_queue["queue_slug"]
            new_queue_number = next_queue["queue_number"]
            
            # Create new entry in next queue
            print(f"DEBUG: Creating new entry in queue {new_queue_slug}/{new_queue_number}")
            print(f"DEBUG: Entry details - fullname: {fullname}, phone: {phone}, type: {queue_type}, purpose: {queue_purpose}")
            cur.execute(
                """
                INSERT INTO queue_entries (
                    queue_slug, queue_number, queue_type, queue_purpose,
                    fullname, phone, purpose, applicant_id, email, status, admin_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'waiting', 'pending')
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
                    applicant_id,
                    normalize_email(email),
                )
            )
            
            new_entry_id = cur.fetchone()[0]
            print(f"DEBUG: Successfully created new entry with ID: {new_entry_id}")
            
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
            
            print(f"DEBUG: Marked old entry {entry_id} as rescheduled")
            conn.commit()
            print(f"DEBUG: Transaction committed successfully")
            
            # Verify the new entry was created
            cur.execute("SELECT * FROM queue_entries WHERE id = %s", (new_entry_id,))
            verification = cur.fetchone()
            print(f"DEBUG: Verification - New entry exists: {verification is not None}")
            
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
    data = request.get_json() or {}
    fullname = data.get('fullname', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip().lower()
    qr_link = data.get('link', '').strip()

    if not fullname or not phone or not email or not qr_link:
        return jsonify({"status": "error", "message": "Full name, phone, email, and queue link are required"}), 400

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"status": "error", "message": "Please provide a valid email address."}), 400

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
                fullname, phone, email, purpose, status, admin_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'waiting', 'pending')
            RETURNING id
            """,
            (
                queue_slug,
                queue_number,
                queue_type,
                queue_purpose,
                fullname,
                phone,
                email,
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

        # Ensure queue form config + queue mode columns exist
        ensure_queue_form_config_columns(conn)
        ensure_queue_mode_columns(conn)
        
        # Ensure queue_entries table exists
        ensure_queue_entries_table(conn)
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Database migration completed successfully. Queue limit, queue form config, and queue mode columns are ready."
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
        
        # Check if qr_history table exists hahahaahaha
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


@app.route('/queue/<queue_slug>', methods=['GET', 'POST'])
@app.route('/queue/<queue_slug>/', methods=['GET', 'POST'])
def queue_page_default(queue_slug):
    """Fallback route when queue number isn't provided in the URL."""
    return queue_page(queue_slug, 1)


@app.route('/queue/<queue_slug>/<int:queue_number>/waiting/<int:entry_id>')
def queue_waiting(queue_slug, queue_number, entry_id):
    queue_type, queue_purpose = resolve_queue_metadata(queue_slug, queue_number)
    queue_mode = get_queue_mode(queue_slug, queue_number)
    queue_mode_hints = get_queue_mode_hints(
        queue_mode.get("processing_method"),
        queue_mode.get("release_type")
    )

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
                   fullname, phone, purpose, status, created_at,
                   reference_number, email, applicant_id, admin_status, notification_message
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
            "reference_number": row[10],
            "email": row[11],
            "applicant_id": row[12],
            "admin_status": row[13] or "pending",
            "notification_message": row[14] or ""
        }

        queue_type = entry["queue_type"] or queue_type
        queue_purpose = entry["queue_purpose"] or queue_purpose
        ticket_reference = entry["reference_number"] or generate_ticket_reference(queue_slug, entry["id"])
        ticket_qr_url = None
        ticket_proof_url = None
        try:
            ticket_proof_url = url_for('ticket_proof', queue_slug=queue_slug, queue_number=queue_number, entry_id=entry_id)
        except Exception as url_error:
            print(f"Warning: ticket_proof URL unavailable: {url_error}")

        # Only render QR section when ticket_proof endpoint is available.
        if ticket_proof_url:
            try:
                ticket_qr_url = url_for('ticket_qr', queue_slug=queue_slug, queue_number=queue_number, entry_id=entry_id)
            except Exception as url_error:
                print(f"Warning: ticket_qr URL unavailable: {url_error}")
                ticket_qr_url = None

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
            queue_processing_method=queue_mode_hints["processing_method"],
            queue_release_type=queue_mode_hints["release_type"],
            queue_flow_hint=queue_mode_hints["waiting_hint"],
            entry=entry,
            ticket_reference=ticket_reference,
            ticket_qr_url=ticket_qr_url,
            ticket_proof_url=ticket_proof_url,
            recent_entries=recent_entries,
        )
    except Exception as e:
        print(f"Error loading waiting page: {e}")
        import traceback
        traceback.print_exc()
        flash("Unable to load your queue status. Please try again.", "error")
        return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/queue/<queue_slug>/<int:queue_number>', methods=['GET', 'POST'])
def queue_page(queue_slug, queue_number):
    import os  # ✅ FIX 1: REQUIRED
    from werkzeug.utils import secure_filename
    import base64
    from datetime import datetime

    queue_type, queue_purpose = resolve_queue_metadata(queue_slug, queue_number)
    queue_config = get_queue_config(queue_slug, queue_number)
    queue_mode = get_queue_mode(queue_slug, queue_number)
    queue_mode_hints = get_queue_mode_hints(
        queue_mode.get("processing_method"),
        queue_mode.get("release_type")
    )

    queue_limit = get_queue_limit(queue_slug, queue_number)
    current_count = get_queue_entry_count(queue_slug, queue_number)
    queue_full = queue_limit is not None and queue_limit > 0 and current_count >= queue_limit

    if request.method == 'POST':
        ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

        def allowed_file(filename):
            return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

        phone = (request.form.get('phone') or '').strip()
        if not phone:
            flash("Please enter your phone number.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        # ✅ FIX 2: ALWAYS allow ticket retrieval FIRST
        existing_entry_id = check_existing_entry(queue_slug, queue_number, phone)
        if existing_entry_id:
            flash("Welcome back! Here's your existing queue ticket.", "success")
            return redirect(url_for(
                'queue_waiting',
                queue_slug=queue_slug,
                queue_number=queue_number,
                entry_id=existing_entry_id
            ))

        # ✅ Only block NEW registrations
        if queue_full:
            flash("Sorry, this queue is currently full.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        lastname = (request.form.get('lastname') or '').strip()
        firstname = (request.form.get('firstname') or '').strip()
        middleinitial = (request.form.get('middleinitial') or '').strip()
        suffix = (request.form.get('suffix') or '').strip()
        applicant_id = (request.form.get('applicant_id') or '').strip()
        email = normalize_email(request.form.get('email'))
        purpose = (request.form.get('purpose') or '').strip()
        declaration = request.form.get('declaration') == 'on'

        if not all([lastname, firstname, email]):
            flash("Please complete all required fields.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        if queue_config.get("require_student_id", True) and not applicant_id:
            flash("Student / Client ID is required.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        if not declaration:
            flash("Please certify the information before submitting.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        # ✅ FIX 3: Safe fullname construction
        fullname = f"{lastname}, {firstname}"
        if middleinitial:
            fullname += f" {middleinitial}"
        if suffix:
            fullname += f" {suffix}"

        id_doc_file = request.files.get('id_doc')
        req_doc_file = request.files.get('req_doc')
        signature_data = request.form.get('signature_data', '')

        def validate_file(file):
            if not file or file.filename == '':
                return None, None
            if not allowed_file(file.filename):
                raise ValueError("Invalid file type.")
            data = file.read()
            if len(data) > MAX_FILE_SIZE:
                raise ValueError("File too large.")
            ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
            return data, ext

        try:
            id_doc_bytes, id_doc_ext = validate_file(id_doc_file)
            req_doc_bytes, req_doc_ext = validate_file(req_doc_file)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        # ✅ FIX 4: Signature validation
        if queue_config.get("require_valid_id", True):
            if not id_doc_bytes:
                flash("Valid ID upload is required.", "error")
                return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
        else:
            id_doc_bytes, id_doc_ext = None, None

        if queue_config.get("require_supporting_doc", True):
            if not req_doc_bytes:
                flash("Supporting document is required.", "error")
                return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
        else:
            req_doc_bytes, req_doc_ext = None, None

        sig_bytes = None
        if signature_data.startswith("data:image"):
            try:
                sig_bytes = base64.b64decode(signature_data.split(",")[1])
                if len(sig_bytes) > 2 * 1024 * 1024:
                    raise ValueError
            except Exception:
                sig_bytes = None

        if queue_config.get("esign_required", True) and not sig_bytes:
            flash("E-signature is required.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            ensure_queue_entries_table(conn)
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO queue_entries (
                    queue_slug, queue_number, queue_type, queue_purpose,
                    fullname, phone, purpose, applicant_id, email, status, admin_status
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'waiting','pending')
                RETURNING id
            """, (
                queue_slug, queue_number, queue_type, queue_purpose,
                fullname, phone, purpose or None, applicant_id, email
            ))

            entry_id = cur.fetchone()[0]
            conn.commit()

            id_doc_path = None
            req_doc_path = None
            signature_path = None

            if id_doc_bytes:
                id_doc_name = f"{entry_id}_id.{id_doc_ext}"
                content_type = get_content_type(id_doc_name)
                save_file_to_db(id_doc_name, id_doc_bytes, content_type)
                id_doc_path = f"/uploads/{id_doc_name}"

            if req_doc_bytes:
                req_doc_name = f"{entry_id}_req.{req_doc_ext}"
                content_type = get_content_type(req_doc_name)
                save_file_to_db(req_doc_name, req_doc_bytes, content_type)
                req_doc_path = f"/uploads/{req_doc_name}"

            if sig_bytes:
                sig_name = f"{entry_id}_sig.png"
                save_file_to_db(sig_name, sig_bytes, 'image/png')
                signature_path = f"/uploads/{sig_name}"

            cur.execute(
                """
                UPDATE queue_entries
                SET id_doc_path = %s, req_doc_path = %s, signature_path = %s
                WHERE id = %s
                """,
                (id_doc_path, req_doc_path, signature_path, entry_id),
            )
            conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            print(e)
            flash("Failed to save registration.", "error")
            return redirect(url_for('queue_page', queue_slug=queue_slug, queue_number=queue_number))
        finally:
            if cur: cur.close()
            if conn: conn.close()

        return redirect(url_for(
            'queue_waiting',
            queue_slug=queue_slug,
            queue_number=queue_number,
            entry_id=entry_id
        ))

    return render_template(
        "User/User.html",
        queue_type=queue_type,
        queue_purpose=queue_purpose,
        queue_number=queue_number,
        queue_slug=queue_slug,
        queue_processing_method=queue_mode_hints["processing_method"],
        queue_release_type=queue_mode_hints["release_type"],
        queue_flow_hint=queue_mode_hints["registration_hint"],
        queue_full=queue_full,
        queue_limit=queue_limit,
        current_count=current_count,
        queue_require_student_id=queue_config.get("require_student_id", True),
        queue_require_valid_id=queue_config.get("require_valid_id", True),
        queue_require_supporting_doc=queue_config.get("require_supporting_doc", True),
        queue_esign_required=queue_config.get("esign_required", True),
    )



@app.route('/ticket_qr/<queue_slug>/<int:queue_number>/<int:entry_id>')
def ticket_qr(queue_slug, queue_number, entry_id):
    """Generate a QR image that links to the ticket proof page."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed", 500

        ensure_queue_entries_table(conn)
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM queue_entries WHERE id = %s AND queue_slug = %s AND queue_number = %s",
            (entry_id, queue_slug, queue_number)
        )
        row = cur.fetchone()
        if not row:
            return "Ticket not found", 404

        ticket_path = url_for('ticket_proof', queue_slug=queue_slug, queue_number=queue_number, entry_id=entry_id)
        ticket_url = f"{get_public_base_url()}{ticket_path}"

        qr_img = qrcode.make(ticket_url)
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        response = make_response(buffer.getvalue())
        response.headers.set("Content-Type", "image/png")
        return response
    except Exception as e:
        print(f"Error generating ticket QR: {e}")
        return "Error generating QR", 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/ticket_proof/<queue_slug>/<int:queue_number>/<int:entry_id>')
def ticket_proof(queue_slug, queue_number, entry_id):
    """Public ticket proof page for a submitted queue entry."""
    queue_type, queue_purpose = resolve_queue_metadata(queue_slug, queue_number)
    queue_mode = get_queue_mode(queue_slug, queue_number)
    queue_mode_hints = get_queue_mode_hints(
        queue_mode.get("processing_method"),
        queue_mode.get("release_type")
    )
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
            SELECT id, queue_type, queue_purpose, fullname, status, created_at,
                   reference_number, admin_status, notification_message
            FROM queue_entries
            WHERE id = %s AND queue_slug = %s AND queue_number = %s
            """,
            (entry_id, queue_slug, queue_number),
        )
        row = cur.fetchone()
        if not row:
            return "Ticket not found", 404

        entry = {
            "id": row[0],
            "fullname": row[3],
            "status": row[4] or "waiting",
            "created_at": row[5],
            "admin_status": row[7] or "pending",
            "notification_message": row[8] or "",
        }
        queue_type = row[1] or queue_type
        queue_purpose = row[2] or queue_purpose
        ticket_reference = row[6] or generate_ticket_reference(queue_slug, entry_id)

        return render_template(
            "User/TicketProof.html",
            queue_slug=queue_slug,
            queue_number=queue_number,
            queue_type=queue_type,
            queue_purpose=queue_purpose,
            queue_processing_method=queue_mode_hints["processing_method"],
            queue_release_type=queue_mode_hints["release_type"],
            queue_flow_hint=queue_mode_hints["waiting_hint"],
            entry=entry,
            ticket_reference=ticket_reference,
        )
    except Exception as e:
        print(f"Error loading ticket proof: {e}")
        return "Unable to load ticket proof.", 500
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


@app.route('/healthz')
def healthz():
    return "ok", 200


@app.route('/')
def home():
    return redirect(url_for('admin'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
