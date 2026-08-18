-- Create the Customers table
CREATE TABLE IF NOT EXISTS Customers (

    CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,

    FirstName TEXT NOT NULL,

    LastName TEXT NOT NULL,

    Email TEXT NOT NULL,

    Phone TEXT NOT NULL

);


-- Create the login accounts table
CREATE TABLE IF NOT EXISTS Admins (

    AdminID INTEGER PRIMARY KEY AUTOINCREMENT,

    Username TEXT NOT NULL UNIQUE,

    Password TEXT NOT NULL,

    FullName TEXT NOT NULL,

    Email TEXT NOT NULL UNIQUE,

    Role TEXT NOT NULL DEFAULT 'employee'

);


-- Create the Services table
CREATE TABLE IF NOT EXISTS Services (

    ServiceID INTEGER PRIMARY KEY AUTOINCREMENT,

    ServiceName TEXT NOT NULL,

    Category TEXT,

    Description TEXT,

    StartingPrice REAL

);


-- Create the Inventory table
CREATE TABLE IF NOT EXISTS Inventory (

    ItemID INTEGER PRIMARY KEY AUTOINCREMENT,

    ItemName TEXT NOT NULL,

    Category TEXT,

    Quantity INTEGER NOT NULL DEFAULT 0,

    AvailableQuantity INTEGER NOT NULL DEFAULT 0,

    HirePrice REAL

);


-- Create the Enquiries table
CREATE TABLE IF NOT EXISTS Enquiries (

    EnquiryID INTEGER PRIMARY KEY AUTOINCREMENT,

    ReferenceCode TEXT UNIQUE,

    CustomerID INTEGER NOT NULL,

    EventType TEXT NOT NULL,

    EventDate TEXT NOT NULL,

    EventLocation TEXT,

    GuestCount INTEGER,

    Budget REAL,

    Requirements TEXT,

    AdditionalInformation TEXT,

    Message TEXT,

    Status TEXT NOT NULL DEFAULT 'Pending',

    CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,

    UpdatedAt TEXT,

    DeletedAt TEXT,

    FOREIGN KEY (CustomerID)
        REFERENCES Customers(CustomerID)

);


-- Create the Bookings table
CREATE TABLE IF NOT EXISTS Bookings (

    BookingID INTEGER PRIMARY KEY AUTOINCREMENT,

    EnquiryID INTEGER NOT NULL,

    BookingDate TEXT,

    BookingStatus TEXT
        NOT NULL DEFAULT 'Confirmed',

    TotalPrice REAL,

    FOREIGN KEY (EnquiryID)
        REFERENCES Enquiries(EnquiryID)

);
-- Store inventory allocated to enquiries on particular event dates
CREATE TABLE IF NOT EXISTS InventoryReservations (
    ReservationID INTEGER PRIMARY KEY AUTOINCREMENT,
    EnquiryID INTEGER NOT NULL,
    ItemID INTEGER NOT NULL,
    EventDate TEXT NOT NULL,
    QuantityReserved INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (EnquiryID) REFERENCES Enquiries(EnquiryID),
    FOREIGN KEY (ItemID) REFERENCES Inventory(ItemID)
);