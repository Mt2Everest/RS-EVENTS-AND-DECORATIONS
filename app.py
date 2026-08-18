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
    jsonify,
    send_from_directory
)

# Import database functions
from database import (
    create_database,
    add_admin,
    get_connection,
    create_ai_enquiry,
    find_customer_enquiry,
    update_customer_enquiry,
    get_inventory_availability,
    get_enquiry_inventory_allocation,
    save_enquiry_inventory_allocation,
    get_enquiry_quote,
    save_enquiry_quote,
    find_customer_quote,
    accept_enquiry_as_booking,
    get_booking_confirmation,
    get_in_progress_bookings,
    complete_in_progress_booking,
    get_enquiry_inspiration_images,
    add_enquiry_inspiration_image,
    find_enquiry_for_image_upload,
    get_all_services,
    get_service,
    add_service,
    update_service,
    delete_service
)

# Import AI Booking Assistant functions
from ai_assistant import (
    create_empty_draft,
    analyse_customer_message,
    update_draft,
    find_missing_field,
    create_confirmation_summary,
    recommend_inventory,
    format_inventory_suggestions,
    FIELD_QUESTIONS
)

# Import secure filename handling for customer image uploads
from werkzeug.utils import secure_filename

# Import UUIDs so uploaded image filenames cannot clash
from uuid import uuid4

# Import OS for upload folders and file paths
import os

# Import regular expressions for quote-reference detection
import re

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


# Store customer inspiration images outside the public static folder
INSPIRATION_UPLOAD_FOLDER = os.path.join(
    "uploads",
    "inspiration"
)

# Allow common image formats only
ALLOWED_INSPIRATION_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

# Limit each upload request to 15 MB
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

os.makedirs(
    INSPIRATION_UPLOAD_FOLDER,
    exist_ok=True
)


# ===========================
# INPUT VALIDATION
# ===========================

def valid_email(email):
    # Require a normal email structure without accepting obvious malformed input
    return re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",
        email.strip()
    ) is not None


def valid_phone(phone):
    # Accept common Australian/international formatting while requiring 8-15 digits
    digits = re.sub(
        r"\D",
        "",
        phone
    )

    return 8 <= len(digits) <= 15


def valid_positive_integer(value, maximum=None):
    # Validate quantities such as guest counts and inventory allocations
    try:
        number = int(value)
    except (TypeError, ValueError):
        return False

    if number <= 0:
        return False

    if maximum is not None and number > maximum:
        return False

    return True


def valid_non_negative_money(value):
    # Validate budgets and prices without allowing negative values
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False

    return number >= 0


# Check whether an uploaded file has an allowed image extension
def allowed_inspiration_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_INSPIRATION_EXTENSIONS
    )


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
    # Display live services and starting prices
    return render_template(
        "services.html",
        services=get_all_services()
    )


# Display the gallery page
# ===========================
# SERVICE AND PRICING MANAGEMENT
# ===========================

@app.route("/manage-services")
@login_required
def manage_services():
    # Employees can view services while Rani can manage them
    return render_template(
        "manage_services.html",
        services=get_all_services(),
        role=session.get("role")
    )

@app.route("/manage-services/add", methods=["GET", "POST"])
@admin_required
def add_service_page():
    error = None
    if request.method == "POST":
        name = request.form.get("service_name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price_text = request.form.get("starting_price", "").strip()
        if not name or not category or not description or not price_text:
            error = "All service fields are required."
        else:
            try:
                price = float(price_text)
            except ValueError:
                error = "Starting price must be a valid number."
            else:
                if price < 0:
                    error = "Starting price cannot be negative."

                elif price > 1000000:
                    error = "Starting price is too large. Please check the value."
                else:
                    add_service(name, category, description, price)
                    return redirect(url_for("manage_services"))
    return render_template("service_form.html", page_title="Add Service", service=None, error=error)

@app.route("/manage-services/<int:service_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_service_page(service_id):
    service = get_service(service_id)
    if service is None:
        return redirect(url_for("manage_services"))
    error = None
    if request.method == "POST":
        name = request.form.get("service_name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price_text = request.form.get("starting_price", "").strip()
        if not name or not category or not description or not price_text:
            error = "All service fields are required."
        else:
            try:
                price = float(price_text)
            except ValueError:
                error = "Starting price must be a valid number."
            else:
                if price < 0:
                    error = "Starting price cannot be negative."

                elif price > 1000000:
                    error = "Starting price is too large. Please check the value."
                else:
                    update_service(service_id, name, category, description, price)
                    return redirect(url_for("manage_services"))
    return render_template("service_form.html", page_title="Edit Service", service=service, error=error)

@app.route("/manage-services/<int:service_id>/delete", methods=["POST"])
@admin_required
def delete_service_page(service_id):
    # Only Rani can delete services
    delete_service(service_id)
    return redirect(url_for("manage_services"))


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


        # ===========================
        # CUSTOMER QUOTE LOOKUP
        # ===========================

        lower_message = customer_message.lower()

        # Start quote lookup when the customer asks about their quote
        if (
            session.get("ai_stage") not in [
                "quote_reference",
                "quote_email"
            ]
            and (
                "my quote" in lower_message
                or "my estimate" in lower_message
                or "check quote" in lower_message
                or "quote status" in lower_message
                or "how much is my quote" in lower_message
            )
        ):

            session["ai_stage"] = "quote_reference"

            return jsonify({
                "reply":
                    "I can check the estimate prepared for your enquiry. "
                    "Please provide your enquiry reference, for example RS-00009.",
                "stage": "quote_reference"
            })


        # Collect the enquiry reference before asking for the email
        if session.get("ai_stage") == "quote_reference":

            reference_match = re.search(
                r"\bRS-\d{1,10}\b",
                customer_message,
                re.IGNORECASE
            )

            if reference_match is None:

                return jsonify({
                    "reply":
                        "Please enter the enquiry reference in the format "
                        "RS-00009.",
                    "stage": "quote_reference"
                })

            session["quote_reference"] = (
                reference_match.group(0).upper()
            )

            session["ai_stage"] = "quote_email"

            return jsonify({
                "reply":
                    "Thank you. For privacy, please enter the email address "
                    "used when the enquiry was submitted.",
                "stage": "quote_email"
            })


        # Verify the reference and email before displaying pricing
        if session.get("ai_stage") == "quote_email":

            verified_quote = find_customer_quote(
                session.get("quote_reference", ""),
                customer_message
            )

            if verified_quote is None:

                return jsonify({
                    "reply":
                        "I couldn't verify an enquiry using that reference "
                        "and email address. Please check the email and try "
                        "again, or type 'check quote' to restart.",
                    "stage": "quote_email"
                })


            # A verified enquiry may not have been priced by Rani yet
            if verified_quote.get("EstimatedTotal") is None:

                session["ai_stage"] = "collecting"

                return jsonify({
                    "reply":
                        f"I found {verified_quote['ReferenceCode']}, but an "
                        "estimated quote has not been prepared by the organiser "
                        "yet. Your enquiry is still recorded and Rani can "
                        "prepare the estimate from the owner dashboard.",
                    "stage": "collecting"
                })


            total = float(
                verified_quote["EstimatedTotal"]
            )

            quote_status = (
                verified_quote.get("QuoteStatus")
                or "Estimate"
            )

            session["ai_stage"] = "collecting"

            session.pop(
                "quote_reference",
                None
            )

            return jsonify({
                "reply":
                    f"Your current quote for "
                    f"{verified_quote['ReferenceCode']} is "
                    f"${total:,.2f}. "
                    f"Quote status: {quote_status}. "
                    "This amount is a quote/estimate from RS Events & "
                    "Decorations and this website does not process payments.",
                "stage": "collecting"
            })


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
                        "to discuss or edit your enquiry later. "
                        "If you have inspiration photos, you can now use "
                        "the Inspiration Image Upload section below and "
                        "enter this reference plus the same email address.",
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
        # CHECK INVENTORY AND SUGGEST SIMILAR ITEMS
        # ===========================

        # Read stock availability for the customer's selected date
        inventory_items = get_inventory_availability(draft["event_date"])

        # Use AI meaning/synonym matching rather than exact item-name matching
        inventory_matches = recommend_inventory(
            draft["requirements"],
            inventory_items
        )

        # Create the suggestion message shown to the customer
        inventory_message = format_inventory_suggestions(
            inventory_matches,
            draft["event_date"]
        )

        session["inventory_suggestions"] = inventory_matches

        # ===========================
        # ASK FOR OPTIONAL INFORMATION
        # ===========================

        session["ai_stage"] = "additional_information"

        return jsonify({
            "reply":
                "Thank you, I now have all of the required "
                "information for your enquiry.\n\n"
                + inventory_message
                + "\n\n"
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

    # Remove any quote lookup details
    session.pop(
        "quote_reference",
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
# CUSTOMER INSPIRATION IMAGE UPLOAD
# ===========================

@app.route(
    "/assistant/inspiration-upload",
    methods=["POST"]
)
def upload_inspiration_images():

    reference_code = request.form.get(
        "reference_code",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    uploaded_files = request.files.getlist(
        "inspiration_images"
    )

    # Require customer verification details
    if reference_code == "" or email == "":

        return redirect(
            url_for(
                "assistant",
                upload_error=(
                    "Enter your enquiry reference and the same "
                    "email address used for the enquiry."
                )
            )
        )


    if not valid_email(email):

        return redirect(
            url_for(
                "assistant",
                upload_error=(
                    "Please enter a valid email address."
                )
            )
        )


    enquiry = find_enquiry_for_image_upload(
        reference_code,
        email
    )

    if enquiry is None:

        return redirect(
            url_for(
                "assistant",
                upload_error=(
                    "The enquiry reference and email address "
                    "could not be verified."
                )
            )
        )


    # Remove blank file inputs
    uploaded_files = [
        file
        for file in uploaded_files
        if file is not None
        and file.filename
    ]

    if len(uploaded_files) == 0:

        return redirect(
            url_for(
                "assistant",
                upload_error=(
                    "Choose at least one inspiration image."
                )
            )
        )


    # Keep the feature manageable for the business owner
    if len(uploaded_files) > 5:

        return redirect(
            url_for(
                "assistant",
                upload_error=(
                    "Please upload a maximum of 5 images at a time."
                )
            )
        )


    saved_count = 0

    for uploaded_file in uploaded_files:

        original_filename = secure_filename(
            uploaded_file.filename
        )

        if (
            original_filename == ""
            or not allowed_inspiration_file(
                original_filename
            )
            or uploaded_file.mimetype not in {
                "image/png",
                "image/jpeg",
                "image/webp"
            }
        ):

            return redirect(
                url_for(
                    "assistant",
                    upload_error=(
                        "Only PNG, JPG, JPEG and WEBP "
                        "inspiration images are allowed."
                    )
                )
            )


        extension = original_filename.rsplit(
            ".",
            1
        )[1].lower()

        stored_filename = (
            f"{enquiry['EnquiryID']}_"
            f"{uuid4().hex}.{extension}"
        )

        upload_path = os.path.join(
            INSPIRATION_UPLOAD_FOLDER,
            stored_filename
        )

        uploaded_file.save(
            upload_path
        )

        add_enquiry_inspiration_image(
            enquiry["EnquiryID"],
            stored_filename,
            original_filename
        )

        saved_count += 1


    return redirect(
        url_for(
            "assistant",
            upload_success=(
                f"{saved_count} inspiration image"
                f"{'s' if saved_count != 1 else ''} "
                "uploaded successfully."
            )
        )
    )


# ===========================
# STAFF INSPIRATION IMAGE VIEW
# ===========================

@app.route(
    "/inspiration-images/<path:filename>"
)
@login_required
def inspiration_image(filename):

    # Only logged-in Rani/employees can view customer uploads
    return send_from_directory(
        INSPIRATION_UPLOAD_FOLDER,
        filename
    )


@app.route(
    "/enquiries/<int:enquiry_id>/inspiration"
)
@login_required
def enquiry_inspiration(enquiry_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            Enquiries.EnquiryID,
            Enquiries.ReferenceCode,
            Enquiries.EventType,
            Enquiries.EventDate,
            Customers.FirstName,
            Customers.LastName
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID = Customers.CustomerID
        WHERE Enquiries.EnquiryID = ?
          AND Enquiries.Status != 'Deleted'
    """, (
        enquiry_id,
    ))

    enquiry = cursor.fetchone()
    connection.close()

    if enquiry is None:

        return redirect(
            url_for("dashboard")
        )


    images = get_enquiry_inspiration_images(
        enquiry_id
    )

    return render_template(
        "inspiration_images.html",
        enquiry=enquiry,
        images=images
    )


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
            Customers.Phone,
            Quotes.EstimatedTotal,
            Quotes.QuoteStatus
        FROM Enquiries
        INNER JOIN Customers
            ON Enquiries.CustomerID =
               Customers.CustomerID
        LEFT JOIN Quotes
            ON Enquiries.EnquiryID = Quotes.EnquiryID
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
            AND Status IN ('Pending', 'In Progress')
        """, (
            eventtype,
            eventdate,
            guests,
            budget,
            message,
            enquiry_id
        ))

        # Keep any existing inventory allocations linked to the updated event date
        cursor.execute("""
            UPDATE InventoryReservations
            SET EventDate = ?
            WHERE EnquiryID = ?
        """, (eventdate, enquiry_id))

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
        AND Enquiries.Status IN ('Pending', 'In Progress')
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
# ACCEPT ENQUIRY AS BOOKING
# ===========================

@app.route(
    "/enquiries/<int:enquiry_id>/accept-booking",
    methods=["POST"]
)
@admin_required
def accept_booking(enquiry_id):

    # Only Rani can convert an enquiry into a confirmed booking
    accepted, result = accept_enquiry_as_booking(
        enquiry_id
    )

    if not accepted:

        return redirect(
            url_for(
                "enquiry_quote",
                enquiry_id=enquiry_id,
                error=result
            )
        )

    return redirect(
        url_for(
            "booking_confirmation",
            booking_id=result
        )
    )


# ===========================
# BOOKING CONFIRMATION PAGE
# ===========================

@app.route(
    "/bookings/<int:booking_id>/confirmation"
)
@login_required
def booking_confirmation(booking_id):

    booking, allocated_items = get_booking_confirmation(
        booking_id
    )

    if booking is None:

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "booking_confirmation.html",
        booking=booking,
        allocated_items=allocated_items
    )



# ===========================
# COMPLETE IN PROGRESS BOOKING
# ===========================

@app.route(
    "/enquiries/<int:enquiry_id>/complete",
    methods=["POST"]
)
@admin_required
def complete_enquiry(enquiry_id):

    # Completed bookings are moved from In Progress into the Archive
    completed = complete_in_progress_booking(
        enquiry_id
    )

    if completed:

        return redirect(
            url_for("in_progress")
        )

    return redirect(
        url_for("dashboard")
    )


# ===========================
# IN PROGRESS BOOKINGS
# ===========================

@app.route("/in-progress")
@login_required
def in_progress():

    # Both Rani and employees can view accepted bookings
    bookings = get_in_progress_bookings()

    return render_template(
        "in_progress.html",
        bookings=bookings,
        role=session.get("role")
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

        # Remove related inventory reservation records
        cursor.execute("""
            DELETE FROM InventoryReservations
            WHERE EnquiryID = ?
        """, (
            enquiry_id,
        ))

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
# QUOTE CALCULATOR
# ===========================

@app.route(
    "/enquiries/<int:enquiry_id>/quote",
    methods=["GET", "POST"]
)
@admin_required
def enquiry_quote(enquiry_id):
    error = request.args.get("error")
    success = request.args.get("success")

    enquiry, allocated_items, quote = get_enquiry_quote(enquiry_id)

    if enquiry is None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        try:
            setup_cost = float(request.form.get("setup_cost", "0") or 0)
            delivery_cost = float(request.form.get("delivery_cost", "0") or 0)
            labour_cost = float(request.form.get("labour_cost", "0") or 0)
            other_cost = float(request.form.get("other_cost", "0") or 0)
        except ValueError:
            error = "All quote costs must be valid numbers."
        else:
            other_description = request.form.get("other_description", "").strip()

            if min(setup_cost, delivery_cost, labour_cost, other_cost) < 0:
                error = "Quote costs cannot be negative."
            else:
                saved, message = save_enquiry_quote(
                    enquiry_id,
                    setup_cost,
                    delivery_cost,
                    labour_cost,
                    other_cost,
                    other_description
                )

                if saved:
                    return redirect(url_for(
                        "enquiry_quote",
                        enquiry_id=enquiry_id,
                        success=message
                    ))

                error = message

        enquiry, allocated_items, quote = get_enquiry_quote(enquiry_id)

    return render_template(
        "quote_calculator.html",
        enquiry=enquiry,
        allocated_items=allocated_items,
        quote=quote,
        error=error,
        success=success
    )


# ===========================
# ENQUIRY INVENTORY ALLOCATION
# ===========================

@app.route(
    "/enquiries/<int:enquiry_id>/inventory",
    methods=["GET", "POST"]
)
@admin_required
def allocate_enquiry_inventory(enquiry_id):

    error = None
    success = request.args.get("success")

    enquiry, inventory_items = get_enquiry_inventory_allocation(enquiry_id)

    if enquiry is None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        quantities = {}

        # Read and validate every inventory quantity entered by Rani
        for item in inventory_items:
            field_name = f"quantity_{item['ItemID']}"
            raw_quantity = request.form.get(field_name, "0").strip()

            try:
                quantity = int(raw_quantity or 0)
            except ValueError:
                error = f"Quantity for {item['ItemName']} must be a whole number."
                break

            if quantity < 0:
                error = f"Quantity for {item['ItemName']} cannot be negative."
                break

            quantities[item["ItemID"]] = quantity

        if error is None:
            saved, message = save_enquiry_inventory_allocation(
                enquiry_id, quantities
            )

            if saved:
                return redirect(url_for(
                    "allocate_enquiry_inventory",
                    enquiry_id=enquiry_id,
                    success="Inventory allocation saved successfully."
                ))

            error = message

        # Reload availability after an unsuccessful save attempt
        enquiry, inventory_items = get_enquiry_inventory_allocation(enquiry_id)

    return render_template(
        "allocate_inventory.html",
        enquiry=enquiry,
        inventory_items=inventory_items,
        error=error,
        success=success
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
# INVENTORY MANAGEMENT
# ===========================

@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():

    error = None
    success = None

    # Only Rani can add new inventory items
    if request.method == "POST":

        if (
            session.get("role") != "admin"
            or session.get("username") != "rani"
        ):
            return redirect(url_for("inventory"))

        item_name = request.form.get("item_name", "").strip()
        category = request.form.get("category", "").strip()
        quantity_text = request.form.get("quantity", "").strip()
        hire_price_text = request.form.get("hire_price", "").strip()

        # Validate all required inventory information
        try:
            quantity = int(quantity_text)
            hire_price = float(hire_price_text)

            if quantity <= 0:
                error = "Total quantity must be a whole number of at least 1."
            elif hire_price < 0:
                error = "Hire price cannot be negative."

        except ValueError:
            error = "Quantity must be a whole number and hire price must be a valid number."

        if item_name == "" or category == "":
            error = "Item name and category are required."

        if error is None:

            connection = get_connection()
            cursor = connection.cursor()

            # Add the new item and make the full quantity available
            cursor.execute("""
                INSERT INTO Inventory
                (
                    ItemName,
                    Category,
                    Quantity,
                    AvailableQuantity,
                    HirePrice
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                item_name,
                category,
                quantity,
                quantity,
                hire_price
            ))

            connection.commit()
            connection.close()

            success = "Inventory item added successfully."

    connection = get_connection()
    cursor = connection.cursor()

    # Display inventory alphabetically by category and item name
    cursor.execute("""
        SELECT *
        FROM Inventory
        ORDER BY Category ASC, ItemName ASC
    """)

    inventory_items = cursor.fetchall()
    connection.close()

    return render_template(
        "inventory.html",
        inventory_items=inventory_items,
        error=error,
        success=success,
        role=session.get("role")
    )


# ===========================
# EDIT INVENTORY ITEM
# ===========================

@app.route(
    "/inventory/<int:item_id>/edit",
    methods=["POST"]
)
@admin_required
def edit_inventory_item(item_id):

    item_name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "").strip()
    quantity_text = request.form.get("quantity", "").strip()
    available_text = request.form.get("available_quantity", "").strip()
    hire_price_text = request.form.get("hire_price", "").strip()

    try:
        quantity = int(quantity_text)
        available_quantity = int(available_text)
        hire_price = float(hire_price_text)

        # Prevent impossible inventory values
        if (
            quantity <= 0
            or available_quantity < 0
            or available_quantity > quantity
            or hire_price < 0
        ):
            raise ValueError

    except ValueError:
        return redirect(url_for("inventory"))

    if item_name == "" or category == "":
        return redirect(url_for("inventory"))

    connection = get_connection()
    cursor = connection.cursor()

    # Update the selected inventory item
    cursor.execute("""
        UPDATE Inventory
        SET
            ItemName = ?,
            Category = ?,
            Quantity = ?,
            AvailableQuantity = ?,
            HirePrice = ?
        WHERE ItemID = ?
    """, (
        item_name,
        category,
        quantity,
        available_quantity,
        hire_price,
        item_id
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("inventory"))


# ===========================
# DELETE INVENTORY ITEM
# ===========================

@app.route(
    "/inventory/<int:item_id>/delete",
    methods=["POST"]
)
@admin_required
def delete_inventory_item(item_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Permanently remove the selected inventory item
    cursor.execute("""
        DELETE FROM Inventory
        WHERE ItemID = ?
    """, (
        item_id,
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("inventory"))

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