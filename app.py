# Import Flask so we can create the website
from flask import Flask, render_template

# Create the Flask application
app = Flask(__name__)

# Display the home page when the user visits the website
@app.route("/")
def home():
    return render_template("index.html")

# Run the Flask server
if __name__ == "__main__":
    app.run(debug=True)