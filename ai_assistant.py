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
from datetime import date, datetime

# Import ContextVar so validation feedback stays safe between user requests
from contextvars import ContextVar


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
MODEL = "openai/gpt-oss-20b"


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
# Validation messages can temporarily override these questions for one request.
VALIDATION_FEEDBACK = ContextVar(
    "validation_feedback",
    default=None
)


class ValidationQuestionDictionary(dict):

    # Return specific validation feedback when the latest answer was invalid
    def __getitem__(self, key):

        feedback = VALIDATION_FEEDBACK.get()

        if (
            feedback is not None
            and feedback.get("field") == key
        ):

            VALIDATION_FEEDBACK.set(None)
            return feedback.get("message")

        return super().__getitem__(key)


FIELD_QUESTIONS = ValidationQuestionDictionary({

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
        (
            "What date will your event take place? "
            "Please include the day, month and year."
        ),

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
})


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
# VALIDATION HELPERS
# ===========================


def set_validation_feedback(field, message):

    # Store a helpful explanation for the next question shown to the customer
    VALIDATION_FEEDBACK.set({
        "field": field,
        "message": message
    })


def clear_validation_feedback():

    # Remove any validation message left from an earlier request
    VALIDATION_FEEDBACK.set(None)


def validate_name(value, field_name):

    # Names must contain letters and may include spaces, apostrophes or hyphens
    if value is None:
        return False, None, (
            f"I still need your {field_name.replace('_', ' ')}. "
            "Please enter it using letters only."
        )

    cleaned = str(value).strip()

    if cleaned == "":
        return False, None, (
            f"Your {field_name.replace('_', ' ')} cannot be blank. "
            "Please enter it using letters only."
        )

    if any(character.isdigit() for character in cleaned):
        return False, None, (
            f"That does not look like a valid {field_name.replace('_', ' ')} "
            "because it contains numbers. Please use letters only, "
            "for example 'Rani'."
        )

    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]+", cleaned):
        return False, None, (
            f"That does not look like a valid {field_name.replace('_', ' ')}. "
            "Please use letters, spaces, apostrophes or hyphens only."
        )

    return True, cleaned, None


def validate_email(value):

    # Email must use a normal name@example.com structure
    if value is None:
        return False, None, (
            "I still need a valid email address. Please enter an email "
            "such as name@example.com."
        )

    cleaned = str(value).strip()

    # If the customer wrote a sentence containing an email, extract the email itself
    email_match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        cleaned
    )

    if email_match:
        return True, email_match.group(0), None

    if "@" not in cleaned:
        return False, None, (
            "That does not look like a valid email address because it is "
            "missing an @ symbol. Please enter an email such as "
            "name@example.com."
        )

    local_part, _, domain = cleaned.partition("@")

    if local_part.strip() == "":
        return False, None, (
            "That email address is missing the part before the @ symbol. "
            "Please enter an email such as name@example.com."
        )

    if "." not in domain:
        return False, None, (
            "That email address is missing a complete domain, such as "
            "gmail.com. Please enter an email such as name@example.com."
        )

    return False, None, (
        "That does not appear to be a valid email address. Please use a "
        "format such as name@example.com."
    )


def validate_phone(value):

    # Phone numbers may contain normal formatting but must contain 10 to 15 digits
    if value is None:
        return False, None, (
            "I still need a valid phone number. Please enter a number "
            "containing 10 to 15 digits, for example 0412 345 678."
        )

    cleaned = str(value).strip()

    if re.search(r"[A-Za-z]", cleaned):
        return False, None, (
            "That does not look like a valid phone number because it contains "
            "letters. Please enter 10 to 15 digits, for example 0412 345 678."
        )

    digits = re.sub(r"\D", "", cleaned)

    if len(digits) < 10:
        return False, None, (
            f"That phone number only contains {len(digits)} digits. "
            "Please enter a phone number containing at least 10 digits, "
            "for example 0412 345 678."
        )

    if len(digits) > 15:
        return False, None, (
            f"That phone number contains {len(digits)} digits, which is too many. "
            "Please enter a phone number containing between 10 and 15 digits."
        )

    return True, digits, None


def parse_event_date(value):

    # Convert common date formats into YYYY-MM-DD and reject incomplete/past dates
    if value is None:
        return False, None, (
            "I still need the full event date. Please include the day, month "
            "and year, for example 18 December 2026 or 18/12/2026."
        )

    original = str(value).strip()

    if original == "":
        return False, None, (
            "The event date cannot be blank. Please include the day, month "
            "and year, for example 18 December 2026."
        )

    cleaned = original

    # Remove a weekday at the beginning, such as 'Tuesday'.
    cleaned = re.sub(
        r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*,?\s+",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    # Convert ordinal endings: 18th -> 18, 21st -> 21.
    cleaned = re.sub(
        r"(\d+)(st|nd|rd|th)",
        r"\1",
        cleaned,
        flags=re.IGNORECASE
    )

    month_words = (
        "january|february|march|april|may|june|july|august|"
        "september|october|november|december|jan|feb|mar|apr|"
        "jun|jul|aug|sep|sept|oct|nov|dec"
    )

    contains_month_word = re.search(
        rf"\b({month_words})\b",
        cleaned,
        re.IGNORECASE
    )

    contains_four_digit_year = re.search(r"\b(?:19|20)\d{2}\b", cleaned)
    contains_numeric_year = re.search(r"[/-]\d{2,4}\s*$", cleaned)

    if (
        contains_month_word
        and not contains_four_digit_year
        and not contains_numeric_year
    ):
        return False, None, (
            "I can understand the day and month, but the year is missing. "
            "Please include the year too, for example 18 December 2026."
        )

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d.%m.%Y",
        "%d.%m.%y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y"
    ]

    parsed_date = None

    for date_format in formats:
        try:
            parsed_date = datetime.strptime(
                cleaned,
                date_format
            ).date()
            break
        except ValueError:
            continue

    # Accept an unambiguous US-style entry such as 10/21/26.
    if parsed_date is None:
        numeric_match = re.fullmatch(
            r"(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})",
            cleaned
        )

        if numeric_match:
            first_number = int(numeric_match.group(1))
            second_number = int(numeric_match.group(2))

            if second_number > 12 and first_number <= 12:
                for date_format in ("%m/%d/%Y", "%m/%d/%y"):
                    try:
                        parsed_date = datetime.strptime(
                            cleaned,
                            date_format
                        ).date()
                        break
                    except ValueError:
                        continue

    if parsed_date is None:
        return False, None, (
            "I could not recognise that as a complete valid date. Please include "
            "the day, month and year, for example 18 December 2026 or "
            "18/12/2026."
        )

    if parsed_date < date.today():
        return False, None, (
            f"That event date ({parsed_date.strftime('%d %B %Y')}) is in the past. "
            "Please enter a future event date."
        )

    return True, parsed_date.isoformat(), None


def validate_guest_count(value):

    # Guest count must be a positive whole number. Values such as 1000 are valid.
    if value is None:
        return False, None, (
            "I need the number of guests as a whole number, for example 80 or 1000."
        )

    if isinstance(value, int):
        guest_count = value
    else:
        text = str(value).replace(",", "").strip()
        match = re.search(r"-?\d+", text)

        if not match:
            return False, None, (
                "I could not find a guest number in that answer. Please enter "
                "a whole number, for example 80 or 1000."
            )

        guest_count = int(match.group(0))

    if guest_count <= 0:
        return False, None, (
            "The guest count must be greater than 0. Please enter a positive "
            "whole number, for example 80."
        )

    return True, guest_count, None


def validate_budget(value):

    # Budget must be a positive number.
    if value is None:
        return False, None, (
            "I need a numerical decoration budget, for example 1500 or $1,500."
        )

    if isinstance(value, (int, float)):
        budget = float(value)
    else:
        cleaned = (
            str(value)
            .replace("$", "")
            .replace(",", "")
            .strip()
        )

        try:
            budget = float(cleaned)
        except ValueError:
            return False, None, (
                "I could not recognise that as a budget. Please enter a numerical "
                "amount, for example 1500 or $1,500."
            )

    if budget <= 0:
        return False, None, (
            "The decoration budget must be greater than $0. Please enter a "
            "positive amount, for example 1500."
        )

    return True, budget, None


def validate_field_value(field, value):

    # Run the correct validation rule for structured customer information.
    if field == "first_name":
        return validate_name(value, "first_name")

    if field == "last_name":
        return validate_name(value, "last_name")

    if field == "email":
        return validate_email(value)

    if field == "phone":
        return validate_phone(value)

    if field == "event_date":
        return parse_event_date(value)

    if field == "guest_count":
        return validate_guest_count(value)

    if field == "budget":
        return validate_budget(value)

    if value is None:
        return True, None, None

    if isinstance(value, str):
        return True, value.strip(), None

    return True, value, None


def validate_extracted_information(
    extracted_information,
    expected_field,
    customer_message
):

    # Validate every structured value before anything is saved to the enquiry draft.
    validated = dict(extracted_information)
    first_invalid_field = None
    first_error_message = None

    fields_to_validate = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "event_date",
        "guest_count",
        "budget"
    ]

    for field in fields_to_validate:

        if field not in validated:
            continue

        value = validated.get(field)

        if value is None or value == "":
            continue

        valid, normalised_value, error_message = validate_field_value(
            field,
            value
        )

        if valid:
            validated[field] = normalised_value
        else:
            validated[field] = None

            if first_invalid_field is None:
                first_invalid_field = field
                first_error_message = error_message

    # If the expected field is still missing, inspect the raw answer as well.
    # This provides specific explanations such as 'the year is missing'.
    if (
        expected_field in fields_to_validate
        and (
            validated.get(expected_field) is None
            or validated.get(expected_field) == ""
        )
    ):

        valid, normalised_value, error_message = validate_field_value(
            expected_field,
            customer_message
        )

        if valid:
            validated[expected_field] = normalised_value
            first_invalid_field = None
            first_error_message = None
        else:
            first_invalid_field = expected_field
            first_error_message = error_message

    if first_invalid_field is not None:
        validated["__invalid_field"] = first_invalid_field
        set_validation_feedback(
            first_invalid_field,
            first_error_message
        )

    return validated


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

    # Clear any old validation feedback before processing a new message
    clear_validation_feedback()

    # Find which field is currently missing
    expected_field = find_missing_field(
        current_draft
    )

    # First try to understand obvious short answers using Python
    simple_answer = detect_simple_answer(
        customer_message,
        current_draft
    )

    # Validate short answers before returning them
    if simple_answer is not None:

        return validate_extracted_information(
            simple_answer,
            expected_field,
            customer_message
        )

    # Give the AI today's date
    today = date.today().isoformat()


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
15. Never invent a missing year for an event date. If the customer does not provide a year, return event_date as null.
16. Never invent missing digits in a phone number or missing parts of an email address.
17. Python performs the final validation, so preserve the customer's explicitly provided information accurately.
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


    # Validate Groq's extracted values before they are saved
    return validate_extracted_information(
        extracted_information,
        expected_field,
        customer_message
    )


# ===========================
# UPDATE ENQUIRY DRAFT
# ===========================

def update_draft(
    current_draft,
    extracted_information
):

    # If an answer failed validation, keep that field empty so the app asks
    # for it again using the specific validation explanation.
    invalid_field = extracted_information.get(
        "__invalid_field"
    )

    if invalid_field in current_draft:
        current_draft[invalid_field] = None

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
# ===========================
# AI INVENTORY MATCHING
# ===========================

def recommend_inventory(requirements, inventory_items):
    # Match natural descriptions and synonyms to real inventory only
    if not inventory_items:
        return []

    catalogue = [{
        "item_id": item["ItemID"],
        "item_name": item["ItemName"],
        "category": item["Category"],
        "available_quantity": item["DateAvailableQuantity"],
        "hire_price": item["HirePrice"]
    } for item in inventory_items]

    system_prompt = """
Match the customer's event-decoration request to the supplied inventory.
Use meaning, style and synonyms, not exact wording only. For example, a request
for 'royal looking chairs' may match fancy wooden chairs and fancy metal chairs.
Recommend multiple sensible alternatives when appropriate. Never invent items.
Only select catalogue items with available_quantity greater than 0.
Return JSON only: {"matches":[{"item_id":1,"reason":"short reason"}]}.
Return at most 5 matches. If nothing is similar, return {"matches":[]}.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps({"requirements": requirements, "inventory": catalogue})}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )

    result = json.loads(response.choices[0].message.content)
    lookup = {item["ItemID"]: item for item in inventory_items}
    matches = []

    for suggestion in result.get("matches", []):
        item = lookup.get(suggestion.get("item_id"))
        if item and item["DateAvailableQuantity"] > 0:
            matches.append({
                "item_name": item["ItemName"],
                "category": item["Category"],
                "available_quantity": item["DateAvailableQuantity"],
                "hire_price": item["HirePrice"],
                "reason": suggestion.get("reason", "Similar to your request")
            })
    return matches


def format_inventory_suggestions(matches, event_date):
    # Turn inventory matches into a customer-friendly chatbot response
    if not matches:
        return (
            f"I couldn't find a close inventory match currently available for {event_date}. "
            "The organiser may still be able to arrange something suitable."
        )

    lines = [f"Based on what you described, you may like these items available for {event_date}:"]
    for match in matches:
        price = match["hire_price"]
        price_text = f"${price:.2f}" if price is not None else "price on request"
        lines.append(
            f"- {match['item_name']} ({match['category'] or 'General'}): "
            f"{match['available_quantity']} available, {price_text}. {match['reason']}"
        )
    lines.append("These are similar suggestions; the organiser can confirm the final selection with you.")
    return "\n".join(lines)