# ===========================
# IMPORTS
# ===========================

# Import Flask features used by the website
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for
)

# Import database setup functions
from database import create_database, add_admin, get_connection

# Import timedelta for Remember Me
from datetime import timedelta

# Import wraps for protected route decorators
from functools import wraps


# ===========================
# APPLICATION SETUP
# ===========================

app = Flask(__name__)

# Protect login session cookies
app.secret_key = "rs-events-private-secret-key-2026"

# Remember selected logins for 30 days
app.permanent_session_lifetime = timedelta(days=30)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ===========================
# LOGIN PROTECTION
# ===========================

def login_required(route_function):

    @wraps(route_function)
    def protected_route(*args, **kwargs):

        # Send logged-out users to the login page
        if session.get("logged_in") is not True:
            return redirect(url_for("login"))

        return route_function(*args, **kwargs)

    return protected_route


def admin_required(route_function):

    @wraps(route_function)
    def protected_route(*args, **kwargs):

        # Require a login first
        if session.get("logged_in") is not True:
            return redirect(url_for("login"))

        # Only Rani's administrator account may continue
        if (
            session.get("role") != "admin"
            or session.get("username") != "rani"
        ):
            return redirect(url_for("dashboard"))

        return route_function(*args, **kwargs)

    return protected_route


# ===========================
# PUBLIC WEBSITE PAGES
# ===========================

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


# ===========================
# CONTACT AND ENQUIRY FORM
# ===========================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    success = None
    error = None

    if request.method == "POST":

        # Collect and clean customer information
        firstname = request.form["firstname"].strip()
        lastname = request.form["lastname"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()

        # Collect event information
        eventtype = request.form["eventtype"].strip()
        eventdate = request.form["eventdate"]
        guests = request.form["guests"]
        budget = request.form["budget"]
        message = request.form["message"].strip()

        # Validate required information
        if (
            firstname == ""
            or lastname == ""
            or email == ""
            or phone == ""
            or eventtype == ""
            or eventdate == ""
        ):
            error = "Please complete all required fields."

        else:

            connection = get_connection()
            cursor = connection.cursor()

            # Add the customer
            cursor.execute("""
                INSERT INTO Customers
                (
                    FirstName,
                    LastName,
                    Email,
                    Phone
                )
                VALUES (?, ?, ?, ?)
            """, (
                firstname,
                lastname,
                email,
                phone
            ))

            customer_id = cursor.lastrowid

            # Add the enquiry as a new pending request
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
                VALUES (?, ?, ?, ?, ?, ?, 'Pending')
            """, (
                customer_id,
                eventtype,
                eventdate,
                guests,
                budget,
                message
            ))

            connection.commit()
            connection.close()

            success = "Your enquiry has been submitted successfully."

    return render_template(
        "contact.html",
        success=success,
        error=error
    )


# ===========================
# ACCOUNT LOGIN
# ===========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("logged_in") is True:
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]
        remember_me = request.form.get("remember_me")

        connection = get_connection()
        cursor = connection.cursor()

        # Check the submitted account details
        cursor.execute("""
            SELECT *
            FROM Admins
            WHERE Username = ?
            AND Password = ?
        """, (
            username,
            password
        ))

        account = cursor.fetchone()

        connection.close()

        if account is not None:

            session.clear()

            session["logged_in"] = True
            session["username"] = account["Username"]
            session["full_name"] = account["FullName"]
            session["role"] = account["Role"]

            # Keep the login for 30 days when selected
            session.permanent = remember_me == "yes"

            return redirect(url_for("dashboard"))

        error = "Incorrect username or password."

    return render_template(
        "login.html",
        error=error
    )


# ===========================
# LOGOUT
# ===========================

@app.route("/logout")
@login_required
def logout():

    session.clear()

    return redirect(url_for("login"))


# ===========================
# ACTIVE ENQUIRY DASHBOARD
# ===========================

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_connection()
    cursor = connection.cursor()

    # Only retrieve active pending enquiries
    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID = Customers.CustomerID
        WHERE Enquiries.Status = 'Pending'
        ORDER BY Enquiries.EnquiryID DESC
    """)

    enquiries = cursor.fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        enquiries=enquiries,
        username=session.get("username"),
        role=session.get("role")
    )


# ===========================
# EDIT ENQUIRY
# ===========================

@app.route("/enquiries/<int:enquiry_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        firstname = request.form["firstname"].strip()
        lastname = request.form["lastname"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()

        eventtype = request.form["eventtype"].strip()
        eventdate = request.form["eventdate"]
        guests = request.form["guests"]
        budget = request.form["budget"]
        message = request.form["message"].strip()

        # Find the customer connected to this enquiry
        cursor.execute("""
            SELECT CustomerID
            FROM Enquiries
            WHERE EnquiryID = ?
        """, (enquiry_id,))

        enquiry_record = cursor.fetchone()

        if enquiry_record is None:

            connection.close()

            return redirect(url_for("dashboard"))

        customer_id = enquiry_record["CustomerID"]

        # Update customer details
        cursor.execute("""
            UPDATE Customers
            SET
                FirstName = ?,
                LastName = ?,
                Email = ?,
                Phone = ?
            WHERE CustomerID = ?
        """, (
            firstname,
            lastname,
            email,
            phone,
            customer_id
        ))

        # Update event details
        cursor.execute("""
            UPDATE Enquiries
            SET
                EventType = ?,
                EventDate = ?,
                GuestCount = ?,
                Budget = ?,
                Message = ?,
                UpdatedAt = CURRENT_TIMESTAMP
            WHERE EnquiryID = ?
            AND Status = 'Pending'
        """, (
            eventtype,
            eventdate,
            guests,
            budget,
            message,
            enquiry_id
        ))

        connection.commit()
        connection.close()

        return redirect(url_for("dashboard"))

    # Retrieve the enquiry for the editing form
    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID = Customers.CustomerID
        WHERE Enquiries.EnquiryID = ?
        AND Enquiries.Status = 'Pending'
    """, (enquiry_id,))

    enquiry = cursor.fetchone()

    connection.close()

    if enquiry is None:
        return redirect(url_for("dashboard"))

    return render_template(
        "edit_enquiry.html",
        enquiry=enquiry
    )


# ===========================
# COMPLETE ENQUIRY
# ===========================

@app.route("/enquiries/<int:enquiry_id>/complete", methods=["POST"])
@admin_required
def complete_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Move the enquiry into the archive
    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Completed',
            UpdatedAt = CURRENT_TIMESTAMP,
            DeletedAt = NULL
        WHERE EnquiryID = ?
        AND Status = 'Pending'
    """, (enquiry_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


# ===========================
# ARCHIVE
# ===========================

@app.route("/archive")
@admin_required
def archive():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID = Customers.CustomerID
        WHERE Enquiries.Status = 'Completed'
        ORDER BY Enquiries.UpdatedAt DESC
    """)

    enquiries = cursor.fetchall()

    connection.close()

    return render_template(
        "archive.html",
        enquiries=enquiries
    )


# ===========================
# RESTORE ARCHIVED ENQUIRY
# ===========================

@app.route("/enquiries/<int:enquiry_id>/restore-archive", methods=["POST"])
@admin_required
def restore_archived_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Pending',
            UpdatedAt = CURRENT_TIMESTAMP
        WHERE EnquiryID = ?
        AND Status = 'Completed'
    """, (enquiry_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("archive"))


# ===========================
# MOVE TO RECENTLY DELETED
# ===========================

@app.route("/enquiries/<int:enquiry_id>/delete", methods=["POST"])
@admin_required
def delete_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Soft-delete the enquiry instead of immediately removing it
    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Deleted',
            DeletedAt = CURRENT_TIMESTAMP,
            UpdatedAt = CURRENT_TIMESTAMP
        WHERE EnquiryID = ?
        AND Status != 'Deleted'
    """, (enquiry_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


# ===========================
# RECENTLY DELETED
# ===========================

@app.route("/recently-deleted")
@admin_required
def recently_deleted():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID = Customers.CustomerID
        WHERE Enquiries.Status = 'Deleted'
        ORDER BY Enquiries.DeletedAt DESC
    """)

    enquiries = cursor.fetchall()

    connection.close()

    return render_template(
        "recently_deleted.html",
        enquiries=enquiries
    )


# ===========================
# RESTORE DELETED ENQUIRY
# ===========================

@app.route("/enquiries/<int:enquiry_id>/restore", methods=["POST"])
@admin_required
def restore_deleted_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Pending',
            DeletedAt = NULL,
            UpdatedAt = CURRENT_TIMESTAMP
        WHERE EnquiryID = ?
        AND Status = 'Deleted'
    """, (enquiry_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("recently_deleted"))


# ===========================
# PERMANENTLY DELETE ENQUIRY
# ===========================

@app.route("/enquiries/<int:enquiry_id>/permanent-delete", methods=["POST"])
@admin_required
def permanently_delete_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Find the connected customer before deleting the enquiry
    cursor.execute("""
        SELECT CustomerID
        FROM Enquiries
        WHERE EnquiryID = ?
        AND Status = 'Deleted'
    """, (enquiry_id,))

    enquiry = cursor.fetchone()

    if enquiry is not None:

        customer_id = enquiry["CustomerID"]

        # Remove related booking records first
        cursor.execute("""
            DELETE FROM Bookings
            WHERE EnquiryID = ?
        """, (enquiry_id,))

        # Permanently remove the enquiry
        cursor.execute("""
            DELETE FROM Enquiries
            WHERE EnquiryID = ?
            AND Status = 'Deleted'
        """, (enquiry_id,))

        # Check whether the customer has any remaining enquiries
        cursor.execute("""
            SELECT COUNT(*) AS EnquiryCount
            FROM Enquiries
            WHERE CustomerID = ?
        """, (customer_id,))

        remaining = cursor.fetchone()["EnquiryCount"]

        # Remove unused customer details
        if remaining == 0:

            cursor.execute("""
                DELETE FROM Customers
                WHERE CustomerID = ?
            """, (customer_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("recently_deleted"))


# ===========================
# EMPLOYEE MANAGEMENT
# ===========================

@app.route("/employees", methods=["GET", "POST"])
@admin_required
def manage_employees():

    error = None
    success = None

    if request.method == "POST":

        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()
        username = request.form["username"].strip()
        password = request.form["password"]

        if (
            full_name == ""
            or email == ""
            or username == ""
            or password == ""
        ):
            error = "All employee fields are required."

        elif username.lower() == "rani":
            error = "The username rani is reserved."

        elif len(username) < 3:
            error = "The username must contain at least 3 characters."

        elif len(password) < 6:
            error = "The password must contain at least 6 characters."

        else:

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT AdminID
                FROM Admins
                WHERE Username = ?
                OR Email = ?
            """, (
                username,
                email
            ))

            existing_account = cursor.fetchone()

            if existing_account is not None:
                error = "That username or email is already being used."

            else:

                cursor.execute("""
                    INSERT INTO Admins
                    (
                        Username,
                        Password,
                        FullName,
                        Email,
                        Role
                    )
                    VALUES (?, ?, ?, ?, 'employee')
                """, (
                    username,
                    password,
                    full_name,
                    email
                ))

                connection.commit()

                success = "Employee added successfully."

            connection.close()

    connection = get_connection()
    cursor = connection.cursor()

    # Never include Rani in the removable employee list
    cursor.execute("""
        SELECT *
        FROM Admins
        WHERE Role = 'employee'
        AND Username != 'rani'
        ORDER BY FullName ASC
    """)

    employees = cursor.fetchall()

    connection.close()

    return render_template(
        "employees.html",
        employees=employees,
        error=error,
        success=success
    )


# ===========================
# REMOVE EMPLOYEE
# ===========================

@app.route("/employees/<int:employee_id>/remove", methods=["POST"])
@admin_required
def remove_employee(employee_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Only employee accounts can be removed
    cursor.execute("""
        DELETE FROM Admins
        WHERE AdminID = ?
        AND Role = 'employee'
        AND Username != 'rani'
    """, (employee_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("manage_employees"))


# ===========================
# START APPLICATION
# ===========================

if __name__ == "__main__":

    create_database()

    # Rani is always recreated or maintained as supreme admin
    add_admin(
        "rani",
        "password123",
        "Rani Swami",
        "rani@rsevents.com"
    )

    app.run(debug=True)