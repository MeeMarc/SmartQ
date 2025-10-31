from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"  # needed for flash messages

# --- Create SQLite DB if not exists ---
DB_PATH = "users.db"
if not os.path.exists(DB_PATH):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)

# --- Route for Sign-Up Page ---
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

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO users (fullname, email, password) VALUES (?, ?, ?)",
                    (fullname, email, password)
                )
            flash("✅ Account created successfully!")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("⚠️ Email already exists.")
            return redirect(url_for('signup'))

    return render_template('Admin/SignUp.html')


# --- Route for Login Page ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        fullname = request.form['fullname']
        password = request.form['password']

        # Simple login check (for now, just checks DB)
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE fullname=? AND password=?", (fullname, password))
            user = cur.fetchone()
            if user:
                flash("✅ Login successful!")
                return redirect(url_for('admin'))
            else:
                flash("❌ Invalid credentials.")
                return redirect(url_for('login'))

    return render_template('Admin/login.html')


# --- Route for Admin/Home Page ---
@app.route('/admin')
def admin():
    return render_template('Admin/admin.html')

@app.route('/homepage')
def homepage():
    return render_template('Admin2/Homepage.html')


# --- Redirect root to signup ---
@app.route('/')
def home():
    return redirect(url_for('signup'))


if __name__ == '__main__':
    app.run(debug=True)
