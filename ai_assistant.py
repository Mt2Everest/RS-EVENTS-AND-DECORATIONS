# ===========================
# IMPORTS
# ===========================

# Import the OpenAI-compatible client used to connect to Groq
from openai import OpenAI

# Import dotenv so the Groq API key can be loaded from .env
from dotenv import load_dotenv

# Import OS so environment variables can be read
import os

# Import JSON so structured AI responses can be processed
import json

# Import regular expressions for simple answer validation
import re

# Import date so the current date can be given to the AI
from datetime import date


# ===========================
# ENVIRONMENT SETUP
# ===========================

# Load variables stored inside the .env file
load_dotenv()

# Read the Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Stop the program if the Groq API key cannot be found
if not GROQ_API_KEY:

    raise ValueError(
        "GROQ_API_KEY could not be found in the .env file."
    )


# ===========================
# GROQ CONNECTION
# ===========================

# Connect to Groq using its OpenAI-compatible API
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# AI model used by the booking assistant
MODEL = "llama-3.3-70b-versatile"


# ===========================
# REQUIRED ENQUIRY INFORMATION
# ===========================

# Information required before an enquiry can be submitted
# The order matches the order the chatbot asks questions
REQUIRED_FIELDS = [

    "event_type",

    "first_name",

    "last_name",

    "email",

    "phone",

    "event_date",

    "event_location",

    "guest_count",

    "budget",

    "requirements"
]


# ===========================
# FIELD QUESTIONS
# ===========================

# Questions used when booking information is missing
FIELD_QUESTIONS = {

    "event_type":
        "What type of event are you planning?",

    "first_name":
        "What is your first name?",

    "last_name":
        "What is your last name?",

    "email":
        "What email address should the organiser use for this enquiry?",

    "phone":
        "What is the best phone number for the organiser to contact you on?",

    "event_date":
        "What date will your event take place?",

    "event_location":
        "Where will the event be held?",

    "guest_count":
        "Approximately how many guests are you expecting?",

    "budget":
        "What budget are you working with for the decorations?",

    "requirements":
        (
            "What decorations or style are you looking for? "
            "You can include colours, themes, props, balloons, "
            "flowers or anything else you would like."
        )
}


# ===========================
# CREATE EMPTY ENQUIRY DRAFT
# ===========================

def create_empty_draft():

    # Create a blank enquiry for a new conversation
    return {

        "first_name": None,

        "last_name": None,

        "email": None,

        "phone": None,

        "event_type": None,

        "event_date": None,

        "event_location": None,

        "guest_count": None,

        "budget": None,

        "requirements": None,

        "additional_information": None
    }


# ===========================
# FIND MISSING INFORMATION
# ===========================

def find_missing_field(draft):

    # Check each required field in the correct question order
    for field in REQUIRED_FIELDS:

        value = draft.get(field)

        # Return the first missing field
        if value is None or value == "":

            return field

    # All required information has been collected
    return None


# ===========================
# SIMPLE ANSWER DETECTION
# ===========================

def detect_simple_answer(
    customer_message,
    current_draft
):

    # Find which field the assistant is currently waiting for
    missing_field = find_missing_field(
        current_draft
    )

    # Remove unnecessary spaces
    message = customer_message.strip()


    # ===========================
    # EVENT TYPE
    # ===========================

    # Treat a short text answer as the event type
    if missing_field == "event_type":

        if (
            len(message) > 0
            and len(message.split()) <= 8
        ):

            return {
                "event_type": message,
                "confirmation": "unclear"
            }


    # ===========================
    # FIRST NAME
    # ===========================

    # Treat a short text answer as the first name
    if missing_field == "first_name":

        if (
            len(message.split()) <= 2
            and not any(
                character.isdigit()
                for character in message
            )
        ):

            return {
                "first_name": message,
                "confirmation": "unclear"
            }


    # ===========================
    # LAST NAME
    # ===========================

    # Treat a short text answer as the last name
    if missing_field == "last_name":

        if (
            len(message.split()) <= 3
            and not any(
                character.isdigit()
                for character in message
            )
        ):

            return {
                "last_name": message,
                "confirmation": "unclear"
            }


    # ===========================
    # EMAIL
    # ===========================

    # Recognise an email address directly
    if missing_field == "email":

        if (
            "@" in message
            and "." in message
        ):

            return {
                "email": message,
                "confirmation": "unclear"
            }


    # ===========================
    # PHONE
    # ===========================

    # Recognise a phone number directly
    if missing_field == "phone":

        phone_characters = re.sub(
            r"[^\d+]",
            "",
            message
        )

        if len(phone_characters) >= 8:

            return {
                "phone": message,
                "confirmation": "unclear"
            }


    # ===========================
    # GUEST COUNT
    # ===========================

    # Treat a standalone number as the guest count
    if missing_field == "guest_count":

        cleaned_number = message.replace(
            ",",
            ""
        )

        if cleaned_number.isdigit():

            return {
                "guest_count": int(cleaned_number),
                "confirmation": "unclear"
            }


        # Recognise answers such as "around 30 guests"
        guest_match = re.search(
            r"\b(\d[\d,]*)\s*(guests?|people|persons?)?\b",
            message,
            re.IGNORECASE
        )

        if guest_match:

            guest_number = (
                guest_match
                .group(1)
                .replace(",", "")
            )

            return {
                "guest_count": int(guest_number),
                "confirmation": "unclear"
            }


    # ===========================
    # BUDGET
    # ===========================

    # Treat a standalone number as the budget
    if missing_field == "budget":

        cleaned_budget = (
            message
            .replace("$", "")
            .replace(",", "")
            .strip()
        )

        try:

            budget_number = float(
                cleaned_budget
            )

            return {
                "budget": budget_number,
                "confirmation": "unclear"
            }

        except ValueError:

            pass


    # No simple answer was detected
    return None


# ===========================
# ANALYSE CUSTOMER MESSAGE
# ===========================

def analyse_customer_message(
    customer_message,
    current_draft
):

    # First try to understand obvious short answers using Python
    simple_answer = detect_simple_answer(
        customer_message,
        current_draft
    )

    # Return immediately if Python understood the answer
    if simple_answer is not None:

        return simple_answer


    # Give the AI today's date
    today = date.today().isoformat()

    # Find which field is currently missing
    expected_field = find_missing_field(
        current_draft
    )


    # ===========================
    # GROQ TOOL DEFINITION
    # ===========================

    tools = [

        {

            "type": "function",

            "function": {

                "name": "extract_booking_information",

                "description": (
                    "Extract booking information explicitly "
                    "provided by the customer."
                ),

                "parameters": {

                    "type": "object",

                    "properties": {

                        # Every optional field can be null
                        "first_name": {
                            "type": ["string", "null"]
                        },

                        "last_name": {
                            "type": ["string", "null"]
                        },

                        "email": {
                            "type": ["string", "null"]
                        },

                        "phone": {
                            "type": ["string", "null"]
                        },

                        "event_type": {
                            "type": ["string", "null"]
                        },

                        "event_date": {
                            "type": ["string", "null"],
                            "description":
                                "Event date formatted as YYYY-MM-DD."
                        },

                        "event_location": {
                            "type": ["string", "null"]
                        },

                        "guest_count": {
                            "type": ["integer", "null"]
                        },

                        "budget": {
                            "type": ["number", "null"]
                        },

                        "requirements": {
                            "type": ["string", "null"]
                        },

                        "additional_information": {
                            "type": ["string", "null"]
                        },

                        "confirmation": {

                            "type": "string",

                            "enum": [
                                "yes",
                                "no",
                                "unclear"
                            ]
                        }
                    },

                    # Require all keys so the returned structure stays consistent
                    "required": [
                        "first_name",
                        "last_name",
                        "email",
                        "phone",
                        "event_type",
                        "event_date",
                        "event_location",
                        "guest_count",
                        "budget",
                        "requirements",
                        "additional_information",
                        "confirmation"
                    ],

                    # Prevent unexpected fields
                    "additionalProperties": False
                }
            }
        }
    ]


    # ===========================
    # AI INSTRUCTIONS
    # ===========================

    system_message = f"""
You are the RS Events & Decorations AI Booking Assistant.

Today's date is {today}.

Current enquiry information:

{json.dumps(current_draft, indent=2)}

The next missing field is:

{expected_field}

IMPORTANT:
The customer's latest message may be a short answer to the
question asking for the next missing field.

Examples:

If the missing field is event_type and the customer says:
"Wedding"
then event_type must be Wedding.

If the missing field is first_name and the customer says:
"Anwesh"
then first_name must be Anwesh.

If the missing field is guest_count and the customer says:
"1000"
then guest_count must be 1000.

If the missing field is budget and the customer says:
"1500"
then budget must be 1500.

Rules:

1. Never invent information.
2. Extract only information the customer explicitly provides.
3. Understand short answers using the expected missing field.
4. If the customer corrects something, return the corrected value.
5. Convert clear dates to YYYY-MM-DD.
6. Never guess missing information.
7. For every field the customer does not provide, return null.
8. Budget must be a number without a dollar sign.
9. Guest count must be an integer.
10. Requirements includes decorations, colours, themes,
    balloons, flowers, props or event styling.
11. Additional information is optional information for the organiser.
12. If the customer clearly confirms everything is correct,
    set confirmation to "yes".
13. If the customer says information is incorrect,
    set confirmation to "no".
14. Otherwise set confirmation to "unclear".
"""


    # ===========================
    # SEND REQUEST TO GROQ
    # ===========================

    response = client.chat.completions.create(

        model=MODEL,

        messages=[

            {
                "role": "system",
                "content": system_message
            },

            {
                "role": "user",
                "content": customer_message
            }

        ],

        tools=tools,

        tool_choice={
            "type": "function",

            "function": {
                "name": "extract_booking_information"
            }
        },

        temperature=0
    )


    # Read the structured tool call
    tool_call = (
        response
        .choices[0]
        .message
        .tool_calls[0]
    )


    # Convert the returned JSON into Python data
    extracted_information = json.loads(
        tool_call.function.arguments
    )


    return extracted_information


# ===========================
# UPDATE ENQUIRY DRAFT
# ===========================

def update_draft(
    current_draft,
    extracted_information
):

    # Check every recognised enquiry field
    for field in current_draft:

        if field in extracted_information:

            value = extracted_information[
                field
            ]

            # Ignore null and blank values
            if value is not None and value != "":

                current_draft[
                    field
                ] = value


    return current_draft


# ===========================
# CREATE CONFIRMATION SUMMARY
# ===========================

def create_confirmation_summary(draft):

    # Read the customer's budget
    budget = draft.get(
        "budget"
    )


    # Format numerical budgets as currency
    if isinstance(
        budget,
        (int, float)
    ):

        budget_display = (
            f"${budget:,.2f}"
        )

    else:

        budget_display = budget


    # Build the full summary shown before submission
    summary = (

        "Please check that all of the following information "
        "is correct:\n\n"

        f"Event Type: "
        f"{draft.get('event_type')}\n"

        f"Name: "
        f"{draft.get('first_name')} "
        f"{draft.get('last_name')}\n"

        f"Email: "
        f"{draft.get('email')}\n"

        f"Phone: "
        f"{draft.get('phone')}\n"

        f"Event Date: "
        f"{draft.get('event_date')}\n"

        f"Event Location: "
        f"{draft.get('event_location')}\n"

        f"Guest Count: "
        f"{draft.get('guest_count')}\n"

        f"Budget: "
        f"{budget_display}\n"

        f"Decoration Requirements: "
        f"{draft.get('requirements')}\n"

        f"Additional Information: "
        f"{draft.get('additional_information') or 'None provided'}\n\n"

        "Is all of this information correct?\n\n"

        "Please reply YES to submit your enquiry, "
        "or tell me what information you would like corrected."
    )


    return summary