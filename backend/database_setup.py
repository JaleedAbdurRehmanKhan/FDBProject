import sqlite3
import pandas as pd
import os

def initialize_database():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    db_path = os.path.join(base_dir, 'bms_database.db')
    schema_path = os.path.join(base_dir, 'schema.sql')
    data_dir = os.path.join(project_dir, 'data_generator')

    # Connect to SQLite (creates file if not exists)
    print(f"Connecting to Database: {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Execute Schema to Create Tables and Triggers
    print("Executing schema.sql...")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_script = f.read()
    cursor.executescript(schema_script)
    
    # 2. Ingest Data from CSVs efficiently
    def ingest_csv(table_name, csv_file):
        csv_path = os.path.join(data_dir, csv_file)
        if os.path.exists(csv_path):
            print(f"Ingesting {csv_file} into '{table_name}' table...")
            df = pd.read_csv(csv_path)
            # Use pandas direct SQL to insert
            df.to_sql(table_name, conn, if_exists='append', index=False)
            print(f" -> Inserted {len(df)} rows.")
        else:
            print(f"Warning: {csv_path} not found.")

    # Due to foreign key constraints, the order of insertion matters immensely
    # Vehicle -> Battery -> Charging_Profile -> Sensor_Reading
    try:
        cursor.execute("BEGIN TRANSACTION")
        
        # Clear existing data purely for reliable setup if ran multiple times
        cursor.execute("DELETE FROM Charging_Profile")
        cursor.execute("DELETE FROM Sensor_Reading")
        cursor.execute("DELETE FROM Battery")
        cursor.execute("DELETE FROM Vehicle")
        cursor.execute("DELETE FROM Fault_Log")
        cursor.execute("DELETE FROM Charge_Recommendation")

        ingest_csv('Vehicle', 'Vehicles.csv')
        ingest_csv('Charging_Profile', 'Charging_Profiles.csv')
        ingest_csv('Battery', 'Batteries.csv')
        
        print("Ingesting Sensor_Readings.csv (10,000 rows)... This will fire SQL Triggers automatically.")
        # We read the sensor readings and insert them row by row or in chunks 
        # so the SQLite triggers can correctly fire and populate the Fault_Log table.
        # df.to_sql is fast, but we'll do it natively to guarantee triggers fire perfectly.
        df_readings = pd.read_csv(os.path.join(data_dir, 'Sensor_Readings.csv'))
        
        # Fast executemany for 10,000 rows is practically instantaneous
        readings_records = df_readings.values.tolist()
        insert_query = """
            INSERT INTO Sensor_Reading 
            (Reading_ID, Battery_ID, Timestamp, Voltage_V, Current_A, Temperature_C, SOC_Percentage, Cycle_Count) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_query, readings_records)
        print(f" -> Inserted {len(df_readings)} rows.")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database setup failed: {e}")
    finally:
        # Before closing, let's check if the Triggers actually worked!
        cursor.execute("SELECT COUNT(*) FROM Fault_Log")
        faults_caught = cursor.fetchone()[0]
        print("\n==================================")
        print(f"SETUP COMPLETE: {faults_caught} Faults were automatically detected and logged by your SQL Triggers!")
        print("==================================\n")
        
        conn.close()

if __name__ == "__main__":
    initialize_database()
