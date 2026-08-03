# ===========================
# IMPORTS
# ===========================

# Import SQLite for database communication
import sqlite3

# Import OS for file paths
import os


# ===========================
# DATABASE LOCATION
# ===========================

DATABASE = os.path.join("database", "rs_events.db")

SCHEMA_FILE = os.path.join("database", "schema.sql")


# ===========================
# DATABASE CONNECTION
# ===========================

def get_connection():

    # Connect to the SQLite database
    connection = sqlite3.connect(DATABASE)

    # Allow database rows to be accessed using column names
    connection.row_factory = sqlite3.Row

    # Enable foreign key support
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ===========================
# TABLE COLUMN CHECK
# ===========================

def column_exists(connection, table_name, column_name):

    cursor = connection.cursor()

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    for column in columns:

        if column["name"] == column_name:
            return True

    return False


# ===========================
# DATABASE MIGRATION
# ===========================

def migrate_database(connection):

    cursor = connection.cursor()

    # Add account roles to an older Admins table
    if not column_exists(connection, "Admins", "Role"):

        cursor.execute("""
            ALTER TABLE Admins
            ADD COLUMN Role TEXT NOT NULL DEFAULT 'employee'
        """)

    # Add enquiry creation date to older databases
    if not column_exists(connection, "Enquiries", "CreatedAt"):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN CreatedAt TEXT
        """)

        cursor.execute("""
            UPDATE Enquiries
            SET CreatedAt = CURRENT_TIMESTAMP
            WHERE CreatedAt IS NULL
        """)

    # Add enquiry editing date
    if not column_exists(connection, "Enquiries", "UpdatedAt"):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN UpdatedAt TEXT
        """)

    # Add recently deleted date
    if not column_exists(connection, "Enquiries", "DeletedAt"):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN DeletedAt TEXT
        """)

    # Existing accounts other than Rani become employees
    cursor.execute("""
        UPDATE Admins
        SET Role = 'employee'
        WHERE Username != 'rani'
    """)

    # Rani always remains the supreme administrator
    cursor.execute("""
        UPDATE Admins
        SET Role = 'admin'
        WHERE Username = 'rani'
    """)

    connection.commit()


# ===========================
# CREATE DATABASE
# ===========================

def create_database():

    # Create the database directory if it does not exist
    os.makedirs("database", exist_ok=True)

    connection = get_connection()

    cursor = connection.cursor()

    # Read and execute the SQL schema
    with open(SCHEMA_FILE, "r", encoding="utf-8") as schema_file:

        schema = schema_file.read()

        cursor.executescript(schema)

    connection.commit()

    # Update an existing database with required columns
    migrate_database(connection)

    connection.close()


# ===========================
# CREATE PERMANENT RANI ACCOUNT
# ===========================

def add_admin(username, password, full_name, email):

    connection = get_connection()

    cursor = connection.cursor()

    # Check whether Rani's account already exists
    cursor.execute("""
        SELECT AdminID
        FROM Admins
        WHERE Username = 'rani'
    """)

    existing_rani = cursor.fetchone()

    if existing_rani is None:

        # Create Rani as the supreme administrator
        cursor.execute("""
            INSERT INTO Admins
            (
                Username,
                Password,
                FullName,
                Email,
                Role
            )
            VALUES (?, ?, ?, ?, 'admin')
        """, (
            username,
            password,
            full_name,
            email
        ))

    else:

        # Ensure Rani can never lose administrator access
        cursor.execute("""
            UPDATE Admins
            SET Role = 'admin'
            WHERE Username = 'rani'
        """)

    connection.commit()

    connection.close()