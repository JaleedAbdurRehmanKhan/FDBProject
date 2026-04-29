-- Battery Management System (BMS) SQLite Schema
-- Adheres to 3NF and EER Specialization Mappings

PRAGMA foreign_keys = ON;

-- 1. VEHICLE / STORAGE UNIT Table
CREATE TABLE IF NOT EXISTS Vehicle (
    Unit_ID TEXT PRIMARY KEY,
    Owner_Name TEXT NOT NULL,
    Unit_Type TEXT NOT NULL,
    Registration_Date DATE NOT NULL
);

-- 2. BATTERY Table (Superclass)
CREATE TABLE IF NOT EXISTS Battery (
    Battery_ID TEXT PRIMARY KEY,
    Unit_ID TEXT NOT NULL,
    Manufacturer TEXT NOT NULL,
    Manufacture_Date DATE NOT NULL,
    Capacity_kWh REAL NOT NULL,
    Chemistry_Type TEXT NOT NULL, -- Discriminator: NMC, LFP, LTO
    Current_SOH REAL NOT NULL CHECK (Current_SOH >= 0 AND Current_SOH <= 100),
    
    -- Specialization Attributes mapped onto the unified table (Table-per-hierarchy)
    -- This guarantees high query performance for time-series aggregation while retaining EER semantics
    Cobalt_Percentage REAL,
    Max_Voltage_Limit REAL,
    Thermal_Runaway_Threshold REAL,
    Extreme_Cold_Tolerance_Limit REAL,

    FOREIGN KEY (Unit_ID) REFERENCES Vehicle (Unit_ID) ON DELETE CASCADE
);

-- 3. CHARGING PROFILE Table (Static Configurations)
CREATE TABLE IF NOT EXISTS Charging_Profile (
    Profile_ID TEXT PRIMARY KEY,
    Profile_Name TEXT NOT NULL,
    Target_Voltage REAL NOT NULL,
    Max_Current REAL NOT NULL,
    Recommended_Temperature_Range TEXT
);

-- 4. SENSOR READING Table (High-Frequency Time-Series Data)
-- This acts as a Weak Entity linked closely to Battery
CREATE TABLE IF NOT EXISTS Sensor_Reading (
    Reading_ID TEXT PRIMARY KEY,
    Battery_ID TEXT NOT NULL,
    Timestamp DATETIME NOT NULL,
    Voltage_V REAL NOT NULL,
    Current_A REAL NOT NULL,
    Temperature_C REAL NOT NULL,
    SOC_Percentage REAL NOT NULL CHECK (SOC_Percentage >= 0 AND SOC_Percentage <= 100),
    Cycle_Count INTEGER NOT NULL,

    FOREIGN KEY (Battery_ID) REFERENCES Battery (Battery_ID) ON DELETE CASCADE
);

-- 5. FAULT LOG Table (Populated by Triggers)
CREATE TABLE IF NOT EXISTS Fault_Log (
    Fault_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Battery_ID TEXT NOT NULL,
    Reading_ID TEXT NOT NULL,
    Fault_Type TEXT NOT NULL,
    Severity TEXT NOT NULL,
    Detected_At DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (Battery_ID) REFERENCES Battery (Battery_ID) ON DELETE CASCADE,
    FOREIGN KEY (Reading_ID) REFERENCES Sensor_Reading (Reading_ID) ON DELETE CASCADE
);

-- 6. CHARGE RECOMMENDATION Table (Populated by Procedural Logic)
CREATE TABLE IF NOT EXISTS Charge_Recommendation (
    Recommendation_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Battery_ID TEXT NOT NULL,
    Profile_ID TEXT NOT NULL,
    Reasoning TEXT NOT NULL,
    Recommended_At DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (Battery_ID) REFERENCES Battery (Battery_ID) ON DELETE CASCADE,
    FOREIGN KEY (Profile_ID) REFERENCES Charging_Profile (Profile_ID) ON DELETE CASCADE
);

-- ==========================================
-- SQL TRIGGERS (AUTOMATIC FAULT DETECTION)
-- ==========================================

-- Trigger 1: Over-Temperature Detection
CREATE TRIGGER IF NOT EXISTS trigger_over_temperature
AFTER INSERT ON Sensor_Reading
WHEN NEW.Temperature_C > 60.0
BEGIN
    INSERT INTO Fault_Log (Battery_ID, Reading_ID, Fault_Type, Severity)
    VALUES (NEW.Battery_ID, NEW.Reading_ID, 'Critical Over-Temperature', 'FATAL');
END;

-- Trigger 2: Over-Voltage Detection
-- Compares the real-time voltage against the specific Chemistry Maximum Voltage limit
CREATE TRIGGER IF NOT EXISTS trigger_over_voltage
AFTER INSERT ON Sensor_Reading
WHEN NEW.Voltage_V > (SELECT Max_Voltage_Limit FROM Battery WHERE Battery_ID = NEW.Battery_ID)
BEGIN
    INSERT INTO Fault_Log (Battery_ID, Reading_ID, Fault_Type, Severity)
    VALUES (NEW.Battery_ID, NEW.Reading_ID, 'Over-Voltage Detected', 'WARNING');
END;

-- Trigger 3: Critical State of Charge (SOC)
CREATE TRIGGER IF NOT EXISTS trigger_critical_soc
AFTER INSERT ON Sensor_Reading
WHEN NEW.SOC_Percentage < 5.0
BEGIN
    INSERT INTO Fault_Log (Battery_ID, Reading_ID, Fault_Type, Severity)
    VALUES (NEW.Battery_ID, NEW.Reading_ID, 'Critical Depletion (SOC < 5%)', 'WARNING');
END;

-- ==========================================
-- ADVANCED SQL VIEWS (ANALYTICS)
-- ==========================================

-- View 1: Real-Time Battery Monitor 
-- Connects static hierarchy data with the latest sensor reading
CREATE VIEW IF NOT EXISTS View_Live_Battery_Status AS
SELECT 
    b.Battery_ID, 
    b.Chemistry_Type, 
    b.Current_SOH,
    v.Owner_Name,
    s.SOC_Percentage, 
    s.Temperature_C, 
    s.Voltage_V
FROM Battery b
JOIN Vehicle v ON b.Unit_ID = v.Unit_ID
JOIN (
    SELECT Battery_ID, MAX(Timestamp) as Latest_Time
    FROM Sensor_Reading
    GROUP BY Battery_ID
) latest ON b.Battery_ID = latest.Battery_ID
JOIN Sensor_Reading s ON latest.Battery_ID = s.Battery_ID AND latest.Latest_Time = s.Timestamp;
