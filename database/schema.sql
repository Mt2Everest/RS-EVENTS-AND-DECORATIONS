-- RS Events & Decorations Database
-- This SQL script creates all database tables required
-- for the booking management system.


-- CUSTOMERS TABLE
-- Stores the personal details of customers who submit
-- an enquiry through the website.

CREATE TABLE IF NOT EXISTS Customers (

    -- Unique customer identification number
    CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Customer's first name
    FirstName TEXT NOT NULL,

    -- Customer's last name
    LastName TEXT NOT NULL,

    -- Customer's email address
    Email TEXT NOT NULL,

    -- Customer's contact phone number
    Phone TEXT

);


-- ADMINS TABLE
-- Stores the login details of business owners who can
-- access the owner dashboard.

CREATE TABLE IF NOT EXISTS Admins (

    -- Unique administrator identification number
    AdminID INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Administrator username
    Username TEXT NOT NULL UNIQUE,

    -- Administrator password
    Password TEXT NOT NULL,

    -- Administrator's full name
    FullName TEXT NOT NULL,

    -- Administrator email address
    Email TEXT NOT NULL

);


-- SERVICES TABLE
-- Stores every service offered by the business.
-- These services can later be displayed on the website.

CREATE TABLE IF NOT EXISTS Services (

    -- Unique service identification number
    ServiceID INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Name of the service
    ServiceName TEXT NOT NULL,

    -- Service category
    Category TEXT NOT NULL,

    -- Description of the service
    Description TEXT NOT NULL,

    -- Starting price of the service
    StartingPrice REAL NOT NULL

);


-- INVENTORY TABLE
-- Stores all equipment and decoration items owned
-- by the business.

CREATE TABLE IF NOT EXISTS Inventory (

    -- Unique inventory identification number
    ItemID INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Name of the inventory item
    ItemName TEXT NOT NULL,

    -- Inventory category
    Category TEXT NOT NULL,

    -- Total quantity owned
    Quantity INTEGER NOT NULL,

    -- Quantity currently available for hire
    AvailableQuantity INTEGER NOT NULL,

    -- Hire price of the inventory item
    HirePrice REAL NOT NULL

);


-- ENQUIRIES TABLE
-- Stores booking enquiries submitted by customers
-- before they are approved as bookings.

CREATE TABLE IF NOT EXISTS Enquiries (

    -- Unique enquiry identification number
    EnquiryID INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Customer who submitted the enquiry
    CustomerID INTEGER NOT NULL,

    -- Type of event
    EventType TEXT NOT NULL,

    -- Planned event date
    EventDate TEXT NOT NULL,

    -- Estimated number of guests
    GuestCount INTEGER,

    -- Customer's estimated budget
    Budget REAL,

    -- Additional information supplied by the customer
    Message TEXT,

    -- Current enquiry status
    Status TEXT DEFAULT 'Pending',

    -- Date the enquiry was submitted
    DateSubmitted TEXT,

    -- Link this enquiry to the Customers table
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)

);


-- BOOKINGS TABLE
-- Stores confirmed bookings after an enquiry has
-- been approved by the business owner.

CREATE TABLE IF NOT EXISTS Bookings (

    -- Unique booking identification number
    BookingID INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Related enquiry identification number
    EnquiryID INTEGER NOT NULL,

    -- Date the booking was confirmed
    BookingDate TEXT,

    -- Date of the booked event
    EventDate TEXT NOT NULL,

    -- Current booking status
    BookingStatus TEXT DEFAULT 'Confirmed',

    -- Total booking cost
    TotalPrice REAL,

    -- Link this booking to the Enquiries table
    FOREIGN KEY (EnquiryID) REFERENCES Enquiries(EnquiryID)

);