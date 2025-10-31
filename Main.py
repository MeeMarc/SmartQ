from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import psycopg2
from psycopg2 import errors
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import io
import base64

app = Flask(__name__)
app.secret_key = "secret123"  # for flash messages

# --- NeonDB PostgreSQL connection config ---
DB_HOST = "ep-aged-mud-a1d1uiez-pooler.ap-southeast-1.aws.neon.tech"
DB_NAME = "neondb"
DB_USER = "neondb_owner"
DB_PASSWORD = "npg_rU8X0gbciPlF"
DB_PORT = "5432"


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )


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
def admin_settings():
    if 'user_email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    email = session['user_email']
    conn = get_db_connection()
    cur = conn.cursor()

    # ✅ Correct column name
    cur.execute("SELECT fullname, email FROM users WHERE email = %s", (email,))
    admin = cur.fetchone()

    if request.method == 'POST':
        fullname = request.form['fullname']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password:
            if new_password != confirm_password:
                flash("Passwords do not match.")
            else:
                hashed_pw = generate_password_hash(new_password)
                cur.execute(
                    "UPDATE users SET fullname = %s, password = %s WHERE email = %s",
                    (fullname, hashed_pw, email)
                )
                flash("✅ Name and password updated successfully!")
        else:
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


@app.route('/')
def home():
    return redirect(url_for('signup'))


if __name__ == '__main__':
    app.run(debug=True)
