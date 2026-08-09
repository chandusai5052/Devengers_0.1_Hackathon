from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.secret_key = "campuscare-demo-secret-key"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "campuscare.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS lost_found (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        item_type TEXT NOT NULL,
        contact TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Submitted',
        created_at TEXT NOT NULL
    );
    """)

    count = conn.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
    if count == 0:
        now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        seed = [
            ("Internal Exams Schedule Released",
             "The internal examination schedule is now available. Students are requested to check the department notice board.",
             "Academic", now),
            ("Hack Devengers 1.0",
             "Submit your innovative project before 7:00 PM today. Good luck, hackers!",
             "Event", now),
            ("Campus Cleanliness Drive",
             "A cleanliness drive will be conducted near Block B at 10:00 AM.",
             "Campus", now),
        ]
        conn.executemany(
            "INSERT INTO announcements(title,description,category,created_at) VALUES(?,?,?,?)",
            seed
        )
    conn.commit()
    conn.close()

@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}

@app.route("/")
def login():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.post("/login")
def do_login():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if not name or not email:
        flash("Please enter your name and email.")
        return redirect(url_for("login"))
    session["user"] = {"name": name, "email": email}
    return redirect(url_for("dashboard"))

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def require_login():
    return bool(session.get("user"))

@app.route("/dashboard")
def dashboard():
    if not require_login():
        return redirect(url_for("login"))
    conn = get_db()
    announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY id DESC LIMIT 3"
    ).fetchall()
    complaints = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    lost = conn.execute("SELECT COUNT(*) FROM lost_found").fetchone()[0]
    conn.close()
    return render_template(
        "dashboard.html",
        announcements=announcements,
        complaint_count=complaints,
        lost_count=lost
    )

@app.route("/announcements", methods=["GET", "POST"])
def announcements():
    if not require_login():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "General")
        if title and description:
            conn.execute(
                "INSERT INTO announcements(title,description,category,created_at) VALUES(?,?,?,?)",
                (title, description, category, datetime.now().strftime("%d %b %Y, %I:%M %p"))
            )
            conn.commit()
            flash("Announcement added successfully.")
        return redirect(url_for("announcements"))
    rows = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("announcements.html", announcements=rows)

@app.route("/lost-found", methods=["GET", "POST"])
def lost_found():
    if not require_login():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        data = (
            request.form.get("item_name", "").strip(),
            request.form.get("description", "").strip(),
            request.form.get("location", "").strip(),
            request.form.get("item_type", "Lost"),
            request.form.get("contact", "").strip(),
            datetime.now().strftime("%d %b %Y, %I:%M %p")
        )
        if all(data[:3]) and data[4]:
            conn.execute(
                "INSERT INTO lost_found(item_name,description,location,item_type,contact,created_at) VALUES(?,?,?,?,?,?)",
                data
            )
            conn.commit()
            flash("Lost & Found report submitted.")
        return redirect(url_for("lost_found"))
    rows = conn.execute("SELECT * FROM lost_found ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("lost_found.html", items=rows)

@app.route("/complaints", methods=["GET", "POST"])
def complaints():
    if not require_login():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        if title and description and location:
            conn.execute(
                "INSERT INTO complaints(title,description,location,status,created_at) VALUES(?,?,?,?,?)",
                (title, description, location, "Submitted",
                 datetime.now().strftime("%d %b %Y, %I:%M %p"))
            )
            conn.commit()
            flash("Complaint submitted successfully.")
        return redirect(url_for("complaints"))
    rows = conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("complaints.html", complaints=rows)

@app.route("/emergency")
def emergency():
    if not require_login():
        return redirect(url_for("login"))
    contacts = [
        ("Campus Security", "Campus Security Office", "tel:+919999999999", "24/7"),
        ("College Office", "Main Administration Office", "tel:+918888888888", "9 AM – 5 PM"),
        ("Medical Help", "Campus First Aid", "tel:+917777777777", "24/7"),
        ("Emergency Services", "Police / Fire / Ambulance", "tel:112", "24/7"),
    ]
    return render_template("emergency.html", contacts=contacts)

@app.route("/ai-assistant")
def ai_assistant():
    if not require_login():
        return redirect(url_for("login"))
    return render_template("ai_assistant.html")

@app.post("/api/chat")
def chat():
    if not require_login():
        return jsonify({"reply": "Please login first."}), 401

    message = request.json.get("message", "").lower().strip()

    responses = [
        (["hello", "hi", "hey"], "Hello! 👋 I am CampusCare AI. How can I help you today?"),
        (["exam", "exams", "test"], "Please check the Announcements section for the latest examination updates."),
        (["lost", "found", "lost item"], "Use Lost & Found to report a lost or found item. Add the item name, location and contact details."),
        (["complaint", "problem", "issue"], "You can submit a campus complaint from the Complaints section and track its status."),
        (["emergency", "security", "ambulance", "police", "fire"], "Open Emergency Hub for one-click access to campus and emergency contacts."),
        (["announcement", "notice", "notices"], "The Announcements page contains academic, event and campus notices."),
        (["event", "events"], "Check Announcements for upcoming campus events."),
        (["contact", "office"], "You can find important college contacts in the Emergency Hub."),
        (["thank", "thanks"], "You're welcome! 😊"),
    ]

    reply = "I can help with announcements, exams, lost & found, complaints, emergencies and campus information. Try asking: 'How do I report a lost item?'"
    for keywords, answer in responses:
        if any(k in message for k in keywords):
            reply = answer
            break

    return jsonify({"reply": reply})

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
