# ===========================
# IMPORTS
# ===========================

# Import SQLite so Python can communicate with the database
import sqlite3

# Import OS so database files can be located
import os


# ===========================
# DATABASE LOCATIONS
# ===========================

# Location of the SQLite database
DATABASE = os.path.join(
    "database",
    "rs_events.db"
)

# Location of the SQL database structure
SCHEMA_FILE = os.path.join(
    "database",
    "schema.sql"
)


# ===========================
# DATABASE CONNECTION
# ===========================

def get_connection():

    # Connect to the SQLite database
    connection = sqlite3.connect(DATABASE)

    # Allow database columns to be accessed by name
    connection.row_factory = sqlite3.Row

    # Enable foreign key relationships
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ===========================
# COLUMN CHECK
# ===========================

def column_exists(
    connection,
    table_name,
    column_name
):

    cursor = connection.cursor()

    # Retrieve information about the selected table
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    # Check whether the requested column exists
    for column in columns:

        if column["name"] == column_name:
            return True

    return False


# ===========================
# DATABASE MIGRATION
# ===========================

def migrate_database(connection):

    cursor = connection.cursor()


    # Add account roles to older databases
    if not column_exists(
        connection,
        "Admins",
        "Role"
    ):

        cursor.execute("""
            ALTER TABLE Admins
            ADD COLUMN Role TEXT
            NOT NULL DEFAULT 'employee'
        """)


    # Add enquiry creation date
    if not column_exists(
        connection,
        "Enquiries",
        "CreatedAt"
    ):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN CreatedAt TEXT
        """)


    # Add enquiry update date
    if not column_exists(
        connection,
        "Enquiries",
        "UpdatedAt"
    ):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN UpdatedAt TEXT
        """)


    # Add recently deleted date
    if not column_exists(
        connection,
        "Enquiries",
        "DeletedAt"
    ):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN DeletedAt TEXT
        """)


    # Add customer enquiry reference
    if not column_exists(
        connection,
        "Enquiries",
        "ReferenceCode"
    ):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN ReferenceCode TEXT
        """)


    # Add event location
    if not column_exists(
        connection,
        "Enquiries",
        "EventLocation"
    ):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN EventLocation TEXT
        """)


    # Add decoration requirements
    if not column_exists(
        connection,
        "Enquiries",
        "Requirements"
    ):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN Requirements TEXT
        """)


    # Add optional organiser information
    if not column_exists(
        connection,
        "Enquiries",
        "AdditionalInformation"
    ):

        cursor.execute("""
            ALTER TABLE Enquiries
            ADD COLUMN AdditionalInformation TEXT
        """)


    # Existing accounts other than Rani remain employees
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


    # Ensure enquiry reference numbers remain unique
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_enquiry_reference
        ON Enquiries(ReferenceCode)
    """)

    connection.commit()


# ===========================
# CREATE DATABASE
# ===========================

def create_database():

    # Create the database folder when required
    os.makedirs(
        "database",
        exist_ok=True
    )

    connection = get_connection()

    cursor = connection.cursor()

    # Read the database schema
    with open(
        SCHEMA_FILE,
        "r",
        encoding="utf-8"
    ) as schema_file:

        sql_script = schema_file.read()

    # Create all required tables
    cursor.executescript(sql_script)

    connection.commit()

    # Update older database versions
    migrate_database(connection)

    connection.close()

    print(
        "Database and tables created successfully!"
    )


# ===========================
# PERMANENT RANI ADMIN
# ===========================

def add_admin(
    username,
    password,
    full_name,
    email
):

    connection = get_connection()

    cursor = connection.cursor()

    # Check whether Rani already exists
    cursor.execute("""
        SELECT AdminID
        FROM Admins
        WHERE Username = 'rani'
    """)

    rani = cursor.fetchone()

    # Create Rani when required
    if rani is None:

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

        print(
            "Rani administrator account created!"
        )

    else:

        # Ensure Rani can never lose administrator privileges
        cursor.execute("""
            UPDATE Admins
            SET Role = 'admin'
            WHERE Username = 'rani'
        """)

        print(
            "Rani administrator account protected!"
        )

    connection.commit()

    connection.close()


# ===========================
# CREATE AI ENQUIRY
# ===========================

def create_ai_enquiry(draft):

    connection = get_connection()

    cursor = connection.cursor()


    # Store the customer's personal details
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
        draft["first_name"],
        draft["last_name"],
        draft["email"],
        draft["phone"]
    ))


    # Store the newly created customer ID
    customer_id = cursor.lastrowid


    # Create a message for existing dashboard displays
    message = (
        f"Requirements: {draft['requirements']}\n"
        f"Additional Information: "
        f"{draft.get('additional_information') or 'None provided'}"
    )


    # Store the AI-created enquiry
    cursor.execute("""
        INSERT INTO Enquiries
        (
            CustomerID,
            EventType,
            EventDate,
            EventLocation,
            GuestCount,
            Budget,
            Requirements,
            AdditionalInformation,
            Message,
            Status,
            CreatedAt
        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            'Pending',
            CURRENT_TIMESTAMP
        )
    """, (
        customer_id,
        draft["event_type"],
        draft["event_date"],
        draft["event_location"],
        draft["guest_count"],
        draft["budget"],
        draft["requirements"],
        draft.get("additional_information"),
        message
    ))


    # Retrieve the new enquiry ID
    enquiry_id = cursor.lastrowid


    # Create an easy-to-read enquiry reference
    reference_code = (
        f"RS-{enquiry_id:05d}"
    )


    # Store the enquiry reference
    cursor.execute("""
        UPDATE Enquiries
        SET ReferenceCode = ?
        WHERE EnquiryID = ?
    """, (
        reference_code,
        enquiry_id
    ))


    connection.commit()

    connection.close()

    return reference_code


# ===========================
# FIND CUSTOMER ENQUIRY
# ===========================

def find_customer_enquiry(
    reference_code,
    email
):

    connection = get_connection()

    cursor = connection.cursor()

    # Find a pending enquiry using both reference and email
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

        WHERE UPPER(Enquiries.ReferenceCode) = UPPER(?)

        AND LOWER(Customers.Email) = LOWER(?)

        AND Enquiries.Status = 'Pending'
    """, (
        reference_code.strip(),
        email.strip()
    ))

    enquiry = cursor.fetchone()

    connection.close()

    # Return nothing when verification fails
    if enquiry is None:
        return None


    # Convert the database enquiry into the same format
    # used by the AI Booking Assistant
    return {

        "reference_code":
            enquiry["ReferenceCode"],

        "first_name":
            enquiry["FirstName"],

        "last_name":
            enquiry["LastName"],

        "email":
            enquiry["Email"],

        "phone":
            enquiry["Phone"],

        "event_type":
            enquiry["EventType"],

        "event_date":
            enquiry["EventDate"],

        "event_location":
            enquiry["EventLocation"],

        "guest_count":
            enquiry["GuestCount"],

        "budget":
            enquiry["Budget"],

        "requirements":
            enquiry["Requirements"],

        "additional_information":
            enquiry["AdditionalInformation"]
    }


# ===========================
# UPDATE CUSTOMER ENQUIRY
# ===========================

def update_customer_enquiry(
    reference_code,
    verified_email,
    draft
):

    connection = get_connection()

    cursor = connection.cursor()


    # Find the enquiry and connected customer
    cursor.execute("""
        SELECT
            Enquiries.EnquiryID,
            Enquiries.CustomerID

        FROM Enquiries

        INNER JOIN Customers
            ON Enquiries.CustomerID =
               Customers.CustomerID

        WHERE UPPER(Enquiries.ReferenceCode) = UPPER(?)

        AND LOWER(Customers.Email) = LOWER(?)

        AND Enquiries.Status = 'Pending'
    """, (
        reference_code.strip(),
        verified_email.strip()
    ))

    enquiry = cursor.fetchone()


    # Stop when verification no longer matches
    if enquiry is None:

        connection.close()

        return False


    enquiry_id = enquiry["EnquiryID"]

    customer_id = enquiry["CustomerID"]


    # Update the customer's personal information
    cursor.execute("""
        UPDATE Customers

        SET
            FirstName = ?,
            LastName = ?,
            Email = ?,
            Phone = ?

        WHERE CustomerID = ?
    """, (
        draft["first_name"],
        draft["last_name"],
        draft["email"],
        draft["phone"],
        customer_id
    ))


    # Rebuild the dashboard message
    message = (
        f"Requirements: {draft['requirements']}\n"
        f"Additional Information: "
        f"{draft.get('additional_information') or 'None provided'}"
    )


    # Update the enquiry
    cursor.execute("""
        UPDATE Enquiries

        SET
            EventType = ?,
            EventDate = ?,
            EventLocation = ?,
            GuestCount = ?,
            Budget = ?,
            Requirements = ?,
            AdditionalInformation = ?,
            Message = ?,
            UpdatedAt = CURRENT_TIMESTAMP

        WHERE EnquiryID = ?

        AND Status = 'Pending'
    """, (
        draft["event_type"],
        draft["event_date"],
        draft["event_location"],
        draft["guest_count"],
        draft["budget"],
        draft["requirements"],
        draft.get("additional_information"),
        message,
        enquiry_id
    ))


    connection.commit()

    connection.close()

    return True
# ===========================
# INVENTORY AVAILABILITY
# ===========================

def get_inventory_availability(event_date):
    # Return stock still available on a particular event date
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT Inventory.ItemID, Inventory.ItemName, Inventory.Category,
               Inventory.Quantity, Inventory.AvailableQuantity, Inventory.HirePrice,
               MAX(0, Inventory.AvailableQuantity - COALESCE(SUM(InventoryReservations.QuantityReserved), 0)) AS DateAvailableQuantity
        FROM Inventory
        LEFT JOIN InventoryReservations
          ON Inventory.ItemID = InventoryReservations.ItemID
         AND InventoryReservations.EventDate = ?
         AND InventoryReservations.EnquiryID IN (
             SELECT EnquiryID FROM Enquiries WHERE Status != 'Deleted'
         )
        GROUP BY Inventory.ItemID
        ORDER BY Inventory.Category, Inventory.ItemName
    """, (event_date,))
    rows = cursor.fetchall()
    connection.close()
    return [dict(row) for row in rows]

# ===========================
# ENQUIRY INVENTORY ALLOCATION
# ===========================

def get_enquiry_inventory_allocation(enquiry_id):
    # Return the enquiry plus all inventory and quantities available for its date
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT Enquiries.EnquiryID, Enquiries.ReferenceCode, Enquiries.EventType,
               Enquiries.EventDate, Enquiries.EventLocation, Enquiries.Status,
               Customers.FirstName, Customers.LastName
        FROM Enquiries
        INNER JOIN Customers ON Enquiries.CustomerID = Customers.CustomerID
        WHERE Enquiries.EnquiryID = ?
          AND Enquiries.Status != 'Deleted'
    """, (enquiry_id,))
    enquiry = cursor.fetchone()

    if enquiry is None:
        connection.close()
        return None, []

    cursor.execute("""
        SELECT Inventory.ItemID, Inventory.ItemName, Inventory.Category,
               Inventory.Quantity, Inventory.AvailableQuantity, Inventory.HirePrice,
               COALESCE(CurrentReservation.QuantityReserved, 0) AS QuantityReserved,
               MAX(0, Inventory.AvailableQuantity
                   - COALESCE(OtherReservations.OtherReserved, 0)) AS MaximumForThisEnquiry
        FROM Inventory
        LEFT JOIN InventoryReservations AS CurrentReservation
          ON CurrentReservation.ItemID = Inventory.ItemID
         AND CurrentReservation.EnquiryID = ?
        LEFT JOIN (
            SELECT IR.ItemID, SUM(IR.QuantityReserved) AS OtherReserved
            FROM InventoryReservations IR
            INNER JOIN Enquiries E ON E.EnquiryID = IR.EnquiryID
            WHERE IR.EventDate = ?
              AND IR.EnquiryID != ?
              AND E.Status != 'Deleted'
            GROUP BY IR.ItemID
        ) AS OtherReservations ON OtherReservations.ItemID = Inventory.ItemID
        ORDER BY Inventory.Category, Inventory.ItemName
    """, (enquiry_id, enquiry["EventDate"], enquiry_id))

    items = cursor.fetchall()
    connection.close()
    return dict(enquiry), [dict(item) for item in items]


def save_enquiry_inventory_allocation(enquiry_id, quantities):
    # Validate and replace an enquiry's inventory allocation as one transaction
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT EventDate FROM Enquiries
        WHERE EnquiryID = ? AND Status != 'Deleted'
    """, (enquiry_id,))
    enquiry = cursor.fetchone()
    if enquiry is None:
        connection.close()
        return False, "Enquiry could not be found."

    event_date = enquiry["EventDate"]

    for item_id, quantity in quantities.items():
        if quantity < 0:
            connection.close()
            return False, "Inventory quantities cannot be negative."

        cursor.execute("""
            SELECT Inventory.ItemName, Inventory.AvailableQuantity,
                   COALESCE(SUM(InventoryReservations.QuantityReserved), 0) AS OtherReserved
            FROM Inventory
            LEFT JOIN InventoryReservations
              ON Inventory.ItemID = InventoryReservations.ItemID
             AND InventoryReservations.EventDate = ?
             AND InventoryReservations.EnquiryID != ?
             AND InventoryReservations.EnquiryID IN (
                 SELECT EnquiryID FROM Enquiries WHERE Status != 'Deleted'
             )
            WHERE Inventory.ItemID = ?
            GROUP BY Inventory.ItemID
        """, (event_date, enquiry_id, item_id))
        item = cursor.fetchone()
        if item is None:
            connection.close()
            return False, "An inventory item could not be found."

        maximum = max(0, item["AvailableQuantity"] - item["OtherReserved"])
        if quantity > maximum:
            connection.close()
            return False, f"Only {maximum} of {item['ItemName']} are available on {event_date}."

    try:
        cursor.execute("DELETE FROM InventoryReservations WHERE EnquiryID = ?", (enquiry_id,))
        for item_id, quantity in quantities.items():
            if quantity > 0:
                cursor.execute("""
                    INSERT INTO InventoryReservations
                    (EnquiryID, ItemID, EventDate, QuantityReserved)
                    VALUES (?, ?, ?, ?)
                """, (enquiry_id, item_id, event_date, quantity))
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        return False, "The inventory allocation could not be saved."

    connection.close()
    return True, "Inventory allocation saved successfully."


# ===========================
# QUOTE CALCULATOR
# ===========================

def get_enquiry_quote(enquiry_id):
    # Retrieve the enquiry, allocated inventory, and any saved quote
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT Enquiries.EnquiryID, Enquiries.ReferenceCode, Enquiries.EventType,
               Enquiries.EventDate, Enquiries.EventLocation, Enquiries.GuestCount,
               Enquiries.Budget, Enquiries.Status, Customers.FirstName,
               Customers.LastName, Customers.Email, Customers.Phone
        FROM Enquiries
        INNER JOIN Customers ON Enquiries.CustomerID = Customers.CustomerID
        WHERE Enquiries.EnquiryID = ? AND Enquiries.Status != 'Deleted'
    """, (enquiry_id,))

    enquiry = cursor.fetchone()

    if enquiry is None:
        connection.close()
        return None, [], None

    cursor.execute("""
        SELECT Inventory.ItemID, Inventory.ItemName, Inventory.Category,
               Inventory.HirePrice, InventoryReservations.QuantityReserved,
               (COALESCE(Inventory.HirePrice, 0) * InventoryReservations.QuantityReserved) AS ItemCost
        FROM InventoryReservations
        INNER JOIN Inventory ON InventoryReservations.ItemID = Inventory.ItemID
        WHERE InventoryReservations.EnquiryID = ?
        ORDER BY Inventory.Category, Inventory.ItemName
    """, (enquiry_id,))

    items = cursor.fetchall()

    cursor.execute("SELECT * FROM Quotes WHERE EnquiryID = ?", (enquiry_id,))
    quote = cursor.fetchone()

    connection.close()

    return dict(enquiry), [dict(item) for item in items], dict(quote) if quote else None


def save_enquiry_quote(enquiry_id, setup_cost, delivery_cost, labour_cost, other_cost, other_description):
    # Validate and save a quote estimate
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT EnquiryID FROM Enquiries WHERE EnquiryID = ? AND Status != 'Deleted'",
        (enquiry_id,)
    )

    if cursor.fetchone() is None:
        connection.close()
        return False, "Enquiry could not be found."

    if any(cost < 0 for cost in [setup_cost, delivery_cost, labour_cost, other_cost]):
        connection.close()
        return False, "Quote costs cannot be negative."

    # Inventory cost is always recalculated from the saved allocation
    cursor.execute("""
        SELECT COALESCE(
            SUM(InventoryReservations.QuantityReserved * COALESCE(Inventory.HirePrice, 0)),
            0
        ) AS InventorySubtotal
        FROM InventoryReservations
        INNER JOIN Inventory ON InventoryReservations.ItemID = Inventory.ItemID
        WHERE InventoryReservations.EnquiryID = ?
    """, (enquiry_id,))

    inventory_subtotal = float(cursor.fetchone()["InventorySubtotal"] or 0)
    total = inventory_subtotal + setup_cost + delivery_cost + labour_cost + other_cost

    cursor.execute("""
        INSERT INTO Quotes
        (EnquiryID, InventorySubtotal, SetupCost, DeliveryCost, LabourCost,
         OtherCost, OtherDescription, EstimatedTotal, QuoteStatus, CreatedAt, UpdatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Estimate', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(EnquiryID) DO UPDATE SET
            InventorySubtotal = excluded.InventorySubtotal,
            SetupCost = excluded.SetupCost,
            DeliveryCost = excluded.DeliveryCost,
            LabourCost = excluded.LabourCost,
            OtherCost = excluded.OtherCost,
            OtherDescription = excluded.OtherDescription,
            EstimatedTotal = excluded.EstimatedTotal,
            QuoteStatus = 'Estimate',
            UpdatedAt = CURRENT_TIMESTAMP
    """, (
        enquiry_id, inventory_subtotal, setup_cost, delivery_cost,
        labour_cost, other_cost, other_description, total
    ))

    connection.commit()
    connection.close()

    return True, "Quote estimate saved successfully."