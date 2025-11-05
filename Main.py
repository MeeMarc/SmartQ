import os
import re
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
        return 1  # Default to 1 if error

def save_qr(queue_type, queue_purpose, queue_link, created_by, queue_number=None):
    """Save QR to database and return the inserted ID."""
    try:
        conn = get_db_connection()
        if conn is None:
            print("Database connection failed")
            return None
            
        cur = conn.cursor()
        # Insert into qr_history first to get the ID
        cur.execute(
            "INSERT INTO qr_history (queue_type, queue_purpose, queue_link, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
            (queue_type, queue_purpose, queue_link, created_by)
        )
        qr_id = cur.fetchone()[0]
        
        # Also insert into temp_qr (if table exists, ignore if it doesn't)
        try:
            cur.execute(
                "INSERT INTO temp_qr (queue_type, queue_purpose, queue_link, created_by) VALUES (%s, %s, %s, %s)",
                (queue_type, queue_purpose, queue_link, created_by)
            )
        except Exception as temp_error:
            print(f"Note: temp_qr insert failed (table may not exist): {temp_error}")
            # Continue anyway, qr_history is the important one
        
        conn.commit()
        cur.close()
        conn.close()
        return qr_id
    except Exception as e:
        print(f"Error saving QR: {e}")
        import traceback
        traceback.print_exc()
        return None


@app.route('/generate_qr_db', methods=['POST'])
def generate_qr_db():
    try:
        queue_type = request.form.get('type', 'General')
        queue_purpose = request.form.get('purpose', 'General')
        created_by = session.get('user_email', 'Unknown')
        
        if not queue_type or not queue_purpose:
            return jsonify({
                "error": "Queue Type and Purpose are required",
                "qr_image": None
            }), 400
        
        # Auto-generate URL based on Queue Type and unique number
        queue_number = get_next_queue_number(queue_type)
        queue_slug = create_slug(queue_type)
        
        # Generate the URL: /queue/<slug>/<number>
        try:
            base = get_public_base_url()
        except Exception as e:
            print(f"Error getting base URL: {e}")
            # Fallback to environment variable or default
            base = os.getenv("PUBLIC_BASE_URL", "https://smartq-vd9k.onrender.com")
            if not base.startswith('http'):
                base = f"https://{base}"
        
        queue_link = f"{base}/queue/{queue_slug}/{queue_number}"
        
        # Save QR and get the ID
        qr_id = save_qr(queue_type, queue_purpose, queue_link, created_by, queue_number)
        
        if qr_id is None:
            return jsonify({
                "error": "Failed to save QR to database",
                "qr_image": None
            }), 500
        
        # Generate QR code with the auto-generated URL
        qr_img = qrcode.make(queue_link)

        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return jsonify({
            "qr_image": qr_base64,
            "queue_link": queue_link,
            "queue_number": queue_number,
            "qr_id": qr_id
        })
    except Exception as e:
        print(f"Error in generate_qr_db: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "qr_image": None
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


@app.route('/delete_temp_qr', methods=['POST'])
def delete_temp_qr():
    qr_id = request.form.get('id')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM temp_qr WHERE id = %s", (qr_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error deleting temp QR: {e}")
        return jsonify({"status": "error", "message": str(e)})


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
    
@app.route('/user')
def user_page():
    return render_template("User/User.html")

@app.route('/queue/<queue_slug>/<int:queue_number>')
def queue_page(queue_slug, queue_number):
    """Dynamic route for auto-generated queue pages."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Find the queue by matching slug pattern and getting the nth queue
        # The slug is created from queue_type, so we need to find queues where
        # the slugified version matches
        slug_normalized = queue_slug.replace('-', ' ')
        
        # Try to find queues where the queue_type (when slugified) matches
        # Get all queue types and find ones that match when slugified
        cur.execute(
            "SELECT queue_type, queue_purpose FROM qr_history ORDER BY id"
        )
        all_queues = cur.fetchall()
        
        # Filter queues where slugified queue_type matches
        matching_queues = []
        for q_type, q_purpose in all_queues:
            if create_slug(q_type) == queue_slug:
                matching_queues.append((q_type, q_purpose))
        
        # Get the queue at the specified number position
        if matching_queues and queue_number <= len(matching_queues):
            queue_type = matching_queues[queue_number - 1][0]
            queue_purpose = matching_queues[queue_number - 1][1]
        else:
            # Fallback: use slug as display name
            queue_type = queue_slug.replace('-', ' ').title()
            queue_purpose = "Queue Registration"
        
        cur.close()
        conn.close()
        
        return render_template("User/User.html", 
                             queue_type=queue_type, 
                             queue_purpose=queue_purpose,
                             queue_number=queue_number)
    except Exception as e:
        print(f"Error loading queue page: {e}")
        return render_template("User/User.html", 
                             queue_type=queue_slug.replace('-', ' ').title(), 
                             queue_purpose="Queue Registration",
                             queue_number=queue_number)





@app.route('/')
def home():
    return redirect(url_for('admin'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
