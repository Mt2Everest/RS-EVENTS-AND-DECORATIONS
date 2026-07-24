# Import SQLite so we can use a database
import sqlite3

# Import OS so Python can find files
import os

# Location of the database file
DATABASE = os.path.join("database", "rs_events.db")


# Create the database and tables
def create_database():

    # Connect to the SQLite database
    connection = sqlite3.connect(DATABASE)

    # Create a cursor to communicate with the database
    cursor = connection.cursor()

    # Open the schema.sql file
    with open("database/schema.sql", "r") as sql_file:

        # Read all SQL commands
        sql_script = sql_file.read()

    # Run every SQL command
    cursor.executescript(sql_script)

    # Save the changes
    connection.commit()

    # Close the database
    connection.close()

    # Display a success message
    print("Database and tables created successfully!")


# Add a new administrator
def add_admin(username, password, fullname, email):

    # Connect to the database
    connection = sqlite3.connect(DATABASE)

    # Create a cursor
    cursor = connection.cursor()

    # Check if the username already exists
    cursor.execute(
        "SELECT * FROM Admins WHERE Username = ?",
        (username,)
    )

    admin = cursor.fetchone()

    # Only add the admin if it doesn't already exist
    if admin is None:

        cursor.execute("""
            INSERT INTO Admins
            (Username, Password, FullName, Email)

            VALUES (?, ?, ?, ?)
        """, (username, password, fullname, email))

        print("Admin account created!")

    else:

        print("Admin already exists!")

    # Save the changes
    connection.commit()

    # Close the database
    connection.close()