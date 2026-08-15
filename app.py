from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)

# Session security
app.secret_key = "shinedoor-admin-secret-key"


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def init_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Create bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            car_model TEXT NOT NULL,
            service TEXT NOT NULL,
            address TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Check existing columns
    cursor.execute("PRAGMA table_info(bookings)")
    columns = [column[1] for column in cursor.fetchall()]

    # Add status column if old database doesn't have it
    if "status" not in columns:
        cursor.execute("""
            ALTER TABLE bookings
            ADD COLUMN status TEXT DEFAULT 'Pending'
        """)

    conn.commit()
    conn.close()


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    return render_template("index.html")


# ==========================================
# CUSTOMER BOOKING
# ==========================================

@app.route("/booking", methods=["GET", "POST"])
def booking():

    if request.method == "POST":

        # Get form data
        name = request.form["name"]
        phone = request.form["phone"]
        car_model = request.form["car_model"]
        service = request.form["service"]
        address = request.form["address"]
        booking_date = request.form["booking_date"]
        booking_time = request.form["booking_time"]
        message = request.form.get("message", "")

        # Save booking
        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bookings
            (
                name,
                phone,
                car_model,
                service,
                address,
                booking_date,
                booking_time,
                message,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            car_model,
            service,
            address,
            booking_date,
            booking_time,
            message,
            "Pending"
        ))

        conn.commit()
        conn.close()

        # Show success page
        return render_template(
            "booking.html",
            success=True,
            name=name,
            phone=phone,
            service=service,
            booking_date=booking_date,
            booking_time=booking_time
        )

    return render_template(
        "booking.html",
        success=False
    )


# ==========================================
# ADMIN LOGIN
# ==========================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # Temporary admin credentials
        if username == "admin" and password == "shinedoor123":

            session["admin_logged_in"] = True

            return redirect("/admin")

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
def admin():

    # Check login
    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    # Get search and filter values
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query
    query = """
        SELECT *
        FROM bookings
        WHERE 1=1
    """

    params = []

    # Search
    if search:

        query += """
            AND (
                name LIKE ?
                OR phone LIKE ?
                OR car_model LIKE ?
                OR service LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    # Status filter
    if status:

        query += """
            AND status = ?
        """

        params.append(status)

    # Latest bookings first
    query += """
        ORDER BY id DESC
    """

    cursor.execute(query, params)

    bookings = cursor.fetchall()


    # ======================================
    # DASHBOARD STATISTICS
    # ======================================

    # Total bookings
    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
    """)

    total = cursor.fetchone()[0]


    # Pending
    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'Pending'
    """)

    pending = cursor.fetchone()[0]


    # Confirmed
    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'Confirmed'
    """)

    confirmed = cursor.fetchone()[0]


    # Completed
    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'Completed'
    """)

    completed = cursor.fetchone()[0]


    # Cancelled
    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE status = 'Cancelled'
    """)

    cancelled = cursor.fetchone()[0]


    conn.close()


    # Send data to dashboard
    return render_template(
        "admin.html",
        bookings=bookings,
        total=total,
        pending=pending,
        confirmed=confirmed,
        completed=completed,
        cancelled=cancelled,
        search=search,
        status=status
    )


# ==========================================
# UPDATE BOOKING STATUS
# ==========================================

@app.route(
    "/admin/update/<int:booking_id>",
    methods=["POST"]
)
def update_booking(booking_id):

    # Check admin login
    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    status = request.form.get("status")

    # Allowed statuses
    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Completed",
        "Cancelled"
    ]

    if status not in allowed_statuses:

        return redirect("/admin")


    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET status = ?
        WHERE id = ?
    """, (
        status,
        booking_id
    ))

    conn.commit()
    conn.close()


    return redirect("/admin")


# ==========================================
# ADMIN LOGOUT
# ==========================================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect("/admin/login")


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )