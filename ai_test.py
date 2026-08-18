# Import the OpenAI client
from openai import OpenAI

# Load variables from the .env file
from dotenv import load_dotenv

# Import OS so Python can read environment variables
import os


# Load the .env file
load_dotenv()

# Read the OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")

# Stop the test if the API key cannot be found
if not api_key:
    raise ValueError(
        "OPENAI_API_KEY was not found in the .env file."
    )

# Create the OpenAI client
client = OpenAI(api_key=api_key)

# Send a simple test request
response = client.responses.create(
    model="gpt-5.6",
    input=(
        "Reply with exactly this sentence: "
        "The RS Events AI connection is working."
    )
)

# Display the AI response in the terminal
print(response.output_text)