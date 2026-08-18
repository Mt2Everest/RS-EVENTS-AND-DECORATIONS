# Import the OpenAI-compatible client
from openai import OpenAI

# Load variables stored in the .env file
from dotenv import load_dotenv

# Import OS to read environment variables
import os


# Load the .env file
load_dotenv()

# Read the Groq API key
api_key = os.getenv("GROQ_API_KEY")

# Stop the program if the API key cannot be found
if not api_key:
    raise ValueError(
        "GROQ_API_KEY was not found in the .env file."
    )


# Connect the client to Groq
client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)


# Send a test message
response = client.chat.completions.create(

    # Use a Groq-supported model
    model="llama-3.3-70b-versatile",

    messages=[

        {
            "role": "system",
            "content": (
                "You are the RS Events & Decorations "
                "AI Booking Assistant."
            )
        },

        {
            "role": "user",
            "content": (
                "Reply with exactly this sentence: "
                "The RS Events Groq connection is working."
            )
        }

    ]
)


# Display the AI response
print(response.choices[0].message.content)