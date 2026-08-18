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
    url_for,
    jsonify
)

# Import database functions
from database import (
    create_database,
    add_admin,
    get_connection,
    create_ai_enquiry
)

# Import AI Booking Assistant functions
from ai_assistant import (
    create_empty_draft,
    analyse_customer_message,
    update_draft,
    find_missing_field,
    create_confirmation_summary,
    FIELD_QUESTIONS
)

# Import timedelta for Remember Me
from datetime import timedelta

# Import wraps for protected routes
from functools import wraps


# ===========================
# APPLICATION SETUP
# ===========================

# Create the Flask application
app = Flask(__name__)

# Protect login sessions
app.secret_key = "rs-events-private-secret-key-2026"

# Remember selected logins for 30 days
app.permanent_session_lifetime = timedelta(days=30)

# Protect login cookies
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ===========================
# LOGIN PROTECTION
# ===========================

# Require a valid employee or administrator login
def login_required(route_function):

    @wraps(route_function)
    def protected_route(*args, **kwargs):

        # Redirect logged-out users to login
        if session.get("logged_in") is not True:
            return redirect(url_for("login"))

        return route_function(*args, **kwargs)

    return protected_route


# Require Rani's supreme administrator account
def admin_required(route_function):

    @wraps(route_function)
    def protected_route(*args, **kwargs):

        # Require the user to be logged in
        if session.get("logged_in") is not True:
            return redirect(url_for("login"))

        # Only Rani can access administrator functions
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

# Display the home page
@app.route("/")
def home():
    return render_template("index.html")


# Display the services page
@app.route("/services")
def services():
    return render_template("services.html")


# Display the gallery page
@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


# Display the About Us page
@app.route("/about")
def about():
    return render_template("about.html")


# ===========================
# AI BOOKING ASSISTANT PAGE
# ===========================

@app.route("/assistant")
def assistant():

    # Create a new enquiry draft when there is no active conversation
    if "ai_draft" not in session:

        session["ai_draft"] = create_empty_draft()

        session["ai_stage"] = "collecting"

    # Display the chatbot page
    return render_template("assistant.html")


# ===========================
# AI BOOKING ASSISTANT MESSAGE
# ===========================

@app.route("/assistant/message", methods=["POST"])
def assistant_message():

    try:

        # Read the customer's message from the chatbot
        request_data = request.get_json()

        if request_data is None:

            return jsonify({
                "error": "No message was received."
            }), 400

        customer_message = request_data.get(
            "message",
            ""
        ).strip()

        # Reject empty messages
        if customer_message == "":

            return jsonify({
                "error": "Please enter a message."
            }), 400


        # Create a draft if the session does not have one
        if "ai_draft" not in session:

            session["ai_draft"] = create_empty_draft()

            session["ai_stage"] = "collecting"


        # Retrieve the current enquiry draft
        draft = session["ai_draft"]

        # Retrieve the current stage of the conversation
        stage = session.get(
            "ai_stage",
            "collecting"
        )


        # ===========================
        # NEW ENQUIRY AFTER SUBMISSION
        # ===========================

        if stage == "submitted":

            lower_message = customer_message.lower()

            # Allow the customer to start another enquiry
            if (
                "new enquiry" in lower_message
                or "another enquiry" in lower_message
                or lower_message in [
                    "yes",
                    "start again",
                    "new"
                ]
            ):

                draft = create_empty_draft()

                session["ai_draft"] = draft

                session["ai_stage"] = "collecting"

                return jsonify({
                    "reply":
                        "Of course! Let's create a new enquiry. "
                        "What type of event are you planning?"
                })

            return jsonify({
                "reply":
                    "Your previous enquiry has already been submitted. "
                    "If you would like to create another enquiry, "
                    "please type 'new enquiry'."
            })


        # ===========================
        # ADDITIONAL INFORMATION
        # ===========================

        if stage == "additional_information":

            lower_message = customer_message.lower().strip()

            # Recognise when the customer has nothing else to add
            no_additional_information = [
                "no",
                "none",
                "nothing",
                "no thanks",
                "no thank you",
                "that's all",
                "thats all",
                "nothing else"
            ]

            if lower_message in no_additional_information:

                draft["additional_information"] = None

            else:

                # Store anything the customer wants passed to the organiser
                draft["additional_information"] = customer_message

            # Save the updated draft
            session["ai_draft"] = draft

            # Move to final confirmation
            session["ai_stage"] = "confirming"

            # Display every collected detail
            confirmation = create_confirmation_summary(
                draft
            )

            return jsonify({
                "reply": confirmation,
                "stage": "confirming"
            })


        # ===========================
        # FINAL CONFIRMATION
        # ===========================

        if stage == "confirming":

            lower_message = customer_message.lower().strip()

            confirmation_words = [
                "yes",
                "yes correct",
                "yes that's correct",
                "yes thats correct",
                "correct",
                "confirmed",
                "confirm",
                "everything is correct",
                "all correct",
                "looks good",
                "submit"
            ]

            # Submit only after explicit customer confirmation
            if lower_message in confirmation_words:

                # Check once more that all required information exists
                missing_field = find_missing_field(
                    draft
                )

                if missing_field is not None:

                    session["ai_stage"] = "collecting"

                    question = FIELD_QUESTIONS[
                        missing_field
                    ]

                    return jsonify({
                        "reply":
                            "I still need one piece of information "
                            "before I can submit your enquiry. "
                            + question
                    })

                # Create the enquiry in SQLite
                reference_code = create_ai_enquiry(
                    draft
                )

                # Mark the conversation as submitted
                session["ai_stage"] = "submitted"

                session["ai_reference"] = reference_code

                return jsonify({
                    "reply":
                        "Your enquiry has been submitted successfully! "
                        f"Your enquiry reference is {reference_code}. "
                        "Please keep this reference in case you need "
                        "to discuss or edit your enquiry later.",
                    "submitted": True,
                    "reference": reference_code
                })


            # Let Groq detect corrections stated naturally
            extracted_information = analyse_customer_message(
                customer_message,
                draft
            )

            # Apply corrections to the enquiry
            draft = update_draft(
                draft,
                extracted_information
            )

            session["ai_draft"] = draft

            # Check whether a correction removed required information
            missing_field = find_missing_field(
                draft
            )

            if missing_field is not None:

                session["ai_stage"] = "collecting"

                return jsonify({
                    "reply":
                        "No problem, I've updated that. "
                        + FIELD_QUESTIONS[missing_field]
                })


            # Display the corrected information again
            confirmation = create_confirmation_summary(
                draft
            )

            return jsonify({
                "reply":
                    "No problem. Here is the updated information:\n\n"
                    + confirmation,
                "stage": "confirming"
            })


        # ===========================
        # COLLECT BOOKING INFORMATION
        # ===========================

        # Extract any information contained in the latest message
        extracted_information = analyse_customer_message(
            customer_message,
            draft
        )

        # Store the newly extracted information
        draft = update_draft(
            draft,
            extracted_information
        )

        session["ai_draft"] = draft


        # Find the next required piece of information
        missing_field = find_missing_field(
            draft
        )

        # Ask only for missing information
        if missing_field is not None:

            return jsonify({
                "reply":
                    FIELD_QUESTIONS[
                        missing_field
                    ],
                "stage": "collecting"
            })


        # ===========================
        # ASK FOR OPTIONAL INFORMATION
        # ===========================

        session["ai_stage"] = "additional_information"

        return jsonify({
            "reply":
                "Thank you, I now have all of the required "
                "information for your enquiry.\n\n"
                "Is there any additional information you would "
                "like to include? Please state it and I will refer "
                "it to the organiser for you! If you'd like the "
                "organiser to contact you, please state that in "
                "your additional information.\n\n"
                "If you have nothing else to add, simply reply "
                "'No'.",
            "stage": "additional_information"
        })


    # Display a safe error if the AI service fails
    except Exception as error:

        print(
            "AI Booking Assistant Error:",
            error
        )

        return jsonify({
            "error":
                "The AI Booking Assistant is temporarily unavailable. "
                "Please try again."
        }), 500


# ===========================
# RESET AI BOOKING ASSISTANT
# ===========================

@app.route("/assistant/reset", methods=["POST"])
def reset_assistant():

    # Remove the existing AI enquiry draft
    session.pop(
        "ai_draft",
        None
    )

    # Remove the conversation stage
    session.pop(
        "ai_stage",
        None
    )

    # Remove any previously generated reference
    session.pop(
        "ai_reference",
        None
    )

    # Create a fresh enquiry draft
    session["ai_draft"] = create_empty_draft()

    session["ai_stage"] = "collecting"

    return jsonify({
        "reply":
            "Your previous conversation has been cleared. "
            "What type of event are you planning?"
    })


# ===========================
# CONTACT AND ENQUIRY FORM
# ===========================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    success = None
    error = None

    if request.method == "POST":

        # Collect customer information
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

            error = (
                "Please complete all required fields."
            )

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

            # Add the enquiry
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

            success = (
                "Your enquiry has been submitted successfully."
            )

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

    # Redirect already logged-in users
    if session.get("logged_in") is True:
        return redirect(
            url_for("dashboard")
        )

    error = None

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]

        remember_me = request.form.get(
            "remember_me"
        )

        connection = get_connection()
        cursor = connection.cursor()

        # Check the account details
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

            # Store the login
            session["logged_in"] = True

            session["username"] = account[
                "Username"
            ]

            session["full_name"] = account[
                "FullName"
            ]

            session["role"] = account[
                "Role"
            ]

            # Remember login for 30 days when selected
            session.permanent = (
                remember_me == "yes"
            )

            return redirect(
                url_for("dashboard")
            )

        error = (
            "Incorrect username or password."
        )

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

    # Clear the login session
    session.clear()

    return redirect(
        url_for("login")
    )


# ===========================
# ACTIVE ENQUIRY DASHBOARD
# ===========================

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_connection()
    cursor = connection.cursor()

    # Retrieve active enquiries
    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID =
               Customers.CustomerID
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

@app.route(
    "/enquiries/<int:enquiry_id>/edit",
    methods=["GET", "POST"]
)
@admin_required
def edit_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        firstname = request.form[
            "firstname"
        ].strip()

        lastname = request.form[
            "lastname"
        ].strip()

        email = request.form[
            "email"
        ].strip()

        phone = request.form[
            "phone"
        ].strip()

        eventtype = request.form[
            "eventtype"
        ].strip()

        eventdate = request.form[
            "eventdate"
        ]

        guests = request.form[
            "guests"
        ]

        budget = request.form[
            "budget"
        ]

        message = request.form[
            "message"
        ].strip()

        # Find the customer connected to this enquiry
        cursor.execute("""
            SELECT CustomerID
            FROM Enquiries
            WHERE EnquiryID = ?
        """, (
            enquiry_id,
        ))

        enquiry_record = cursor.fetchone()

        if enquiry_record is None:

            connection.close()

            return redirect(
                url_for("dashboard")
            )

        customer_id = enquiry_record[
            "CustomerID"
        ]

        # Update customer information
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

        # Update event information
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

        return redirect(
            url_for("dashboard")
        )

    # Retrieve the enquiry for editing
    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID =
               Customers.CustomerID
        WHERE Enquiries.EnquiryID = ?
        AND Enquiries.Status = 'Pending'
    """, (
        enquiry_id,
    ))

    enquiry = cursor.fetchone()

    connection.close()

    if enquiry is None:

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "edit_enquiry.html",
        enquiry=enquiry
    )


# ===========================
# COMPLETE ENQUIRY
# ===========================

@app.route(
    "/enquiries/<int:enquiry_id>/complete",
    methods=["POST"]
)
@admin_required
def complete_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Move the enquiry to the archive
    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Completed',
            UpdatedAt = CURRENT_TIMESTAMP,
            DeletedAt = NULL
        WHERE EnquiryID = ?
        AND Status = 'Pending'
    """, (
        enquiry_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("dashboard")
    )


# ===========================
# ARCHIVE
# ===========================

@app.route("/archive")
@admin_required
def archive():

    connection = get_connection()
    cursor = connection.cursor()

    # Retrieve completed enquiries
    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID =
               Customers.CustomerID
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

@app.route(
    "/enquiries/<int:enquiry_id>/restore-archive",
    methods=["POST"]
)
@admin_required
def restore_archived_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Restore the enquiry to the dashboard
    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Pending',
            UpdatedAt = CURRENT_TIMESTAMP
        WHERE EnquiryID = ?
        AND Status = 'Completed'
    """, (
        enquiry_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("archive")
    )


# ===========================
# MOVE TO RECENTLY DELETED
# ===========================

@app.route(
    "/enquiries/<int:enquiry_id>/delete",
    methods=["POST"]
)
@admin_required
def delete_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Soft-delete the enquiry
    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Deleted',
            DeletedAt = CURRENT_TIMESTAMP,
            UpdatedAt = CURRENT_TIMESTAMP
        WHERE EnquiryID = ?
        AND Status != 'Deleted'
    """, (
        enquiry_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("dashboard")
    )


# ===========================
# RECENTLY DELETED
# ===========================

@app.route("/recently-deleted")
@admin_required
def recently_deleted():

    connection = get_connection()
    cursor = connection.cursor()

    # Retrieve deleted enquiries
    cursor.execute("""
        SELECT
            Enquiries.*,
            Customers.FirstName,
            Customers.LastName,
            Customers.Email,
            Customers.Phone
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID =
               Customers.CustomerID
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

@app.route(
    "/enquiries/<int:enquiry_id>/restore",
    methods=["POST"]
)
@admin_required
def restore_deleted_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Restore the enquiry
    cursor.execute("""
        UPDATE Enquiries
        SET
            Status = 'Pending',
            DeletedAt = NULL,
            UpdatedAt = CURRENT_TIMESTAMP
        WHERE EnquiryID = ?
        AND Status = 'Deleted'
    """, (
        enquiry_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("recently_deleted")
    )


# ===========================
# PERMANENTLY DELETE ENQUIRY
# ===========================

@app.route(
    "/enquiries/<int:enquiry_id>/permanent-delete",
    methods=["POST"]
)
@admin_required
def permanently_delete_enquiry(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Find the related customer
    cursor.execute("""
        SELECT CustomerID
        FROM Enquiries
        WHERE EnquiryID = ?
        AND Status = 'Deleted'
    """, (
        enquiry_id,
    ))

    enquiry = cursor.fetchone()

    if enquiry is not None:

        customer_id = enquiry[
            "CustomerID"
        ]

        # Remove related booking records
        cursor.execute("""
            DELETE FROM Bookings
            WHERE EnquiryID = ?
        """, (
            enquiry_id,
        ))

        # Permanently remove the enquiry
        cursor.execute("""
            DELETE FROM Enquiries
            WHERE EnquiryID = ?
            AND Status = 'Deleted'
        """, (
            enquiry_id,
        ))

        # Check whether customer still has other enquiries
        cursor.execute("""
            SELECT COUNT(*) AS EnquiryCount
            FROM Enquiries
            WHERE CustomerID = ?
        """, (
            customer_id,
        ))

        remaining = cursor.fetchone()[
            "EnquiryCount"
        ]

        # Remove unused customer information
        if remaining == 0:

            cursor.execute("""
                DELETE FROM Customers
                WHERE CustomerID = ?
            """, (
                customer_id,
            ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("recently_deleted")
    )


# ===========================
# EMPLOYEE MANAGEMENT
# ===========================

@app.route(
    "/employees",
    methods=["GET", "POST"]
)
@admin_required
def manage_employees():

    error = None
    success = None

    if request.method == "POST":

        full_name = request.form[
            "full_name"
        ].strip()

        email = request.form[
            "email"
        ].strip()

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]

        # Validate employee information
        if (
            full_name == ""
            or email == ""
            or username == ""
            or password == ""
        ):

            error = (
                "All employee fields are required."
            )

        elif username.lower() == "rani":

            error = (
                "The username rani is reserved."
            )

        elif len(username) < 3:

            error = (
                "The username must contain at least "
                "3 characters."
            )

        elif len(password) < 6:

            error = (
                "The password must contain at least "
                "6 characters."
            )

        else:

            connection = get_connection()
            cursor = connection.cursor()

            # Check whether username or email exists
            cursor.execute("""
                SELECT AdminID
                FROM Admins
                WHERE Username = ?
                OR Email = ?
            """, (
                username,
                email
            ))

            existing_account = (
                cursor.fetchone()
            )

            if existing_account is not None:

                error = (
                    "That username or email is "
                    "already being used."
                )

            else:

                # Create an employee account
                cursor.execute("""
                    INSERT INTO Admins
                    (
                        Username,
                        Password,
                        FullName,
                        Email,
                        Role
                    )
                    VALUES (
                        ?, ?, ?, ?, 'employee'
                    )
                """, (
                    username,
                    password,
                    full_name,
                    email
                ))

                connection.commit()

                success = (
                    "Employee added successfully."
                )

            connection.close()

    connection = get_connection()
    cursor = connection.cursor()

    # Retrieve employee accounts only
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

@app.route(
    "/employees/<int:employee_id>/remove",
    methods=["POST"]
)
@admin_required
def remove_employee(employee_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Remove employee accounts only
    cursor.execute("""
        DELETE FROM Admins
        WHERE AdminID = ?
        AND Role = 'employee'
        AND Username != 'rani'
    """, (
        employee_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("manage_employees")
    )


# ===========================
# START APPLICATION
# ===========================

if __name__ == "__main__":

    # Create and update database tables
    create_database()

    # Ensure Rani remains supreme administrator
    add_admin(
        "rani",
        "password123",
        "Rani Swami",
        "rani@rsevents.com"
    )

    # Start the Flask development server
    app.run(debug=True)