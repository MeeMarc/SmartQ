from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2 import errors
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"  # for flash messages

# --- NeonDB PostgreSQL connection config ---
DB_HOST = "ep-aged-mud-a1d1uiez-pooler.ap-southeast-1.aws.neon.tech"
DB_NAME = "neondb"
DB_USER = "neondb_owner"
DB_PASSWORD = "npg_rU8X0gbciPlF"
DB_PORT = "5432"

# --- Function to get DB connection ---
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn

# --- Route: Signup ---
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
            return redirect(url_for('signup'))
        except Exception as e:
            flash(f"❌ Error: {str(e)}")
            return redirect(url_for('signup'))

    return render_template('Admin/SignUp.html')

# --- Route: Login ---
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

            if not check_password_hash(user[3], password):  # password column
                flash("❌ Incorrect password.")
                return redirect(url_for('login'))

            flash("✅ Login successful!")
            return redirect(url_for('homepage'))

        except Exception as e:
            flash(f"❌ Error: {str(e)}")
            return redirect(url_for('login'))

    return render_template('Admin/login.html')

# --- Homepage/Admin ---
@app.route('/homepage')
def homepage():
    return render_template('Admin2/Homepage.html')

@app.route('/admin')
def admin():
    return render_template('Admin/admin.html')

# --- Redirect root to signup ---
@app.route('/')
def home():
    return redirect(url_for('signup'))

if __name__ == '__main__':
    app.run(debug=True)
