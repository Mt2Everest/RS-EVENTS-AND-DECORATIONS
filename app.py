# IMPORTS

# Import Flask features used by the website
from flask import Flask, render_template, request, redirect, session, url_for

# Import database setup functions
from database import create_database, add_admin

# Import SQLite for database communication
import sqlite3

# Import OS for file paths
import os

# Import timedelta for the 30-day Remember Me option
from datetime import timedelta


# APPLICATION SETUP

# Create the Flask application
app = Flask(__name__)

# Secret key used to protect login sessions
app.secret_key = "rs-events-private-secret-key-2026"

# Remember permanent sessions for 30 days
app.permanent_session_lifetime = timedelta(days=30)

# Additional session cookie protection
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Location of the SQLite database
DATABASE = os.path.join("database", "rs_events.db")


# PUBLIC WEBSITE PAGES

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/assistant")
def assistant():
    return render_template("assistant.html")


# CONTACT AND ENQUIRY FORM

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        # Collect customer information
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        email = request.form["email"]
        phone = request.form["phone"]

        # Collect event information
        eventtype = request.form["eventtype"]
        eventdate = request.form["eventdate"]
        guests = request.form["guests"]
        budget = request.form["budget"]
        message = request.form["message"]

        # Connect to the database
        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        # Save the customer
        cursor.execute("""
            INSERT INTO Customers
            (FirstName, LastName, Email, Phone)
            VALUES (?, ?, ?, ?)
        """, (
            firstname,
            lastname,
            email,
            phone
        ))

        # Store the new CustomerID
        customer_id = cursor.lastrowid

        # Save the enquiry
        cursor.execute("""
            INSERT INTO Enquiries
            (
                CustomerID,
                EventType,
                EventDate,
                GuestCount,
                Budget,
                Message,
                Status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            eventtype,
            eventdate,
            guests,
            budget,
            message,
            "Pending"
        ))

        # Save database changes
        connection.commit()
        connection.close()

        return redirect(url_for("contact"))

    return render_template("contact.html")


# OWNER LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():

    # Send logged-in administrators to the dashboard
    if session.get("logged_in") is True:
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":

        # Collect login information
        username = request.form["username"].strip()
        password = request.form["password"]

        # Check whether Remember Me was selected
        remember_me = request.form.get("remember_me")

        # Connect to the database
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # Search for matching administrator details
        cursor.execute("""
            SELECT *
            FROM Admins
            WHERE Username = ?
            AND Password = ?
        """, (
            username,
            password
        ))

        admin = cursor.fetchone()

        connection.close()

        # Login successful
        if admin is not None:

            # Remove any previous session information
            session.clear()

            # Save the administrator's login session
            session["logged_in"] = True
            session["username"] = admin["Username"]

            # Remember login for 30 days when selected
            session.permanent = remember_me == "yes"

            return redirect(url_for("dashboard"))

        # Login unsuccessful
        error = "Incorrect username or password."

    return render_template("login.html", error=error)


# PROTECTED OWNER DASHBOARD

@app.route("/dashboard")
def dashboard():

    # Block anyone who is not logged in
    if session.get("logged_in") is not True:
        return redirect(url_for("login"))

    # Connect to the database
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # Retrieve all customer enquiries
    cursor.execute("""
        SELECT *
        FROM Customers
        INNER JOIN Enquiries
        ON Customers.CustomerID = Enquiries.CustomerID
        ORDER BY EnquiryID DESC
    """)

    enquiries = cursor.fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        enquiries=enquiries,
        username=session.get("username")
    )


# ADMIN MANAGEMENT

@app.route("/admins", methods=["GET", "POST"])
def manage_admins():

    # Block anyone who is not logged in
    if session.get("logged_in") is not True:
        return redirect(url_for("login"))

    error = None
    success = None

    # Add a new administrator
    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()

        # Basic backend validation
        if username == "" or password == "" or full_name == "" or email == "":
            error = "All administrator fields are required."

        elif len(username) < 3:
            error = "The username must contain at least 3 characters."

        elif len(password) < 6:
            error = "The password must contain at least 6 characters."

        else:

            connection = sqlite3.connect(DATABASE)
            cursor = connection.cursor()

            # Check whether the username already exists
            cursor.execute("""
                SELECT Username
                FROM Admins
                WHERE Username = ?
            """, (username,))

            existing_admin = cursor.fetchone()

            if existing_admin is not None:
                error = "That username is already being used."

            else:

                # Add the new administrator
                cursor.execute("""
                    INSERT INTO Admins
                    (Username, Password, FullName, Email)
                    VALUES (?, ?, ?, ?)
                """, (
                    username,
                    password,
                    full_name,
                    email
                ))

                connection.commit()

                success = "Administrator added successfully."

            connection.close()

    # Retrieve the administrator list
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT Username, FullName, Email
        FROM Admins
        ORDER BY FullName ASC
    """)

    admins = cursor.fetchall()

    connection.close()

    return render_template(
        "admins.html",
        admins=admins,
        error=error,
        success=success,
        current_username=session.get("username")
    )


# REMOVE ADMINISTRATOR

@app.route("/admins/remove/<username>", methods=["POST"])
def remove_admin(username):

    # Block anyone who is not logged in
    if session.get("logged_in") is not True:
        return redirect(url_for("login"))

    current_username = session.get("username")

    # Do not allow the logged-in administrator to delete themselves
    if username == current_username:
        return redirect(
            url_for(
                "manage_admins",
                remove_error="You cannot remove your own administrator account."
            )
        )

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Count how many administrator accounts exist
    cursor.execute("""
        SELECT COUNT(*)
        FROM Admins
    """)

    admin_count = cursor.fetchone()[0]

    # Make sure at least one administrator remains
    if admin_count <= 1:

        connection.close()

        return redirect(
            url_for(
                "manage_admins",
                remove_error="The final administrator account cannot be removed."
            )
        )

    # Remove the selected administrator
    cursor.execute("""
        DELETE FROM Admins
        WHERE Username = ?
    """, (username,))

    connection.commit()
    connection.close()

    return redirect(
        url_for(
            "manage_admins",
            removed="Administrator removed successfully."
        )
    )


# OWNER LOGOUT

@app.route("/logout")
def logout():

    # Delete all login session information
    session.clear()

    return redirect(url_for("login"))


# START APPLICATION

if __name__ == "__main__":

    # Create database tables if they do not exist
    create_database()

    # Create the default administrator account
    add_admin(
        "rani",
        "password123",
        "Rani Swami",
        "rani@rsevents.com"
    )

    # Start the Flask development server
    app.run(debug=True)