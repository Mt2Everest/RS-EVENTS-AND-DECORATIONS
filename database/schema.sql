-- ===========================
-- CUSTOMERS TABLE
-- Stores customer contact information
-- ===========================

CREATE TABLE IF NOT EXISTS Customers (

    CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,

    FirstName TEXT NOT NULL,

    LastName TEXT NOT NULL,

    Email TEXT NOT NULL,

    Phone TEXT NOT NULL

);


-- ===========================
-- ACCOUNTS TABLE
-- Stores Rani and employee login accounts
-- ===========================

CREATE TABLE IF NOT EXISTS Admins (

    AdminID INTEGER PRIMARY KEY AUTOINCREMENT,

    Username TEXT NOT NULL UNIQUE,

    Password TEXT NOT NULL,

    FullName TEXT NOT NULL,

    Email TEXT NOT NULL UNIQUE,

    Role TEXT NOT NULL DEFAULT 'employee'

);


-- ===========================
-- SERVICES TABLE
-- Stores services offered by the business
-- ===========================

CREATE TABLE IF NOT EXISTS Services (

    ServiceID INTEGER PRIMARY KEY AUTOINCREMENT,

    ServiceName TEXT NOT NULL,

    Description TEXT,

    Price REAL

);


-- ===========================
-- INVENTORY TABLE
-- Stores decoration inventory information
-- ===========================

CREATE TABLE IF NOT EXISTS Inventory (

    InventoryID INTEGER PRIMARY KEY AUTOINCREMENT,

    ItemName TEXT NOT NULL,

    Quantity INTEGER NOT NULL DEFAULT 0,

    AvailabilityStatus TEXT NOT NULL DEFAULT 'Available'

);


-- ===========================
-- ENQUIRIES TABLE
-- Stores customer event enquiries
-- ===========================

CREATE TABLE IF NOT EXISTS Enquiries (

    EnquiryID INTEGER PRIMARY KEY AUTOINCREMENT,

    CustomerID INTEGER NOT NULL,

    EventType TEXT NOT NULL,

    EventDate TEXT NOT NULL,

    GuestCount INTEGER,

    Budget REAL,

    Message TEXT,

    Status TEXT NOT NULL DEFAULT 'Pending',

    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UpdatedAt TEXT,

    DeletedAt TEXT,

    FOREIGN KEY (CustomerID)
        REFERENCES Customers(CustomerID)

);


-- ===========================
-- BOOKINGS TABLE
-- Stores confirmed customer bookings
-- ===========================

CREATE TABLE IF NOT EXISTS Bookings (

    BookingID INTEGER PRIMARY KEY AUTOINCREMENT,

    EnquiryID INTEGER NOT NULL,

    BookingDate TEXT,

    BookingStatus TEXT NOT NULL DEFAULT 'Confirmed',

    FOREIGN KEY (EnquiryID)
        REFERENCES Enquiries(EnquiryID)

);