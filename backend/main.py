from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
import os
from datetime import datetime
import random
import uuid
import asyncio
from contextlib import asynccontextmanager

# --- BACKGROUND LIVE DATA GENERATOR ---
async def live_data_generator():
    """Inserts a realistic sensor reading every 3 seconds to simulate live battery telemetry."""
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")

            # Pick a random battery from the DB
            batteries = conn.execute("SELECT Battery_ID, Max_Voltage_Limit, Thermal_Runaway_Threshold FROM Battery").fetchall()
            if batteries:
                battery = random.choice(batteries)
                b_id = battery['Battery_ID']
                max_v = battery['Max_Voltage_Limit'] or 4.2

                # Simulate realistic fluctuating values (normal operating range)
                voltage   = round(random.uniform(max_v * 0.70, max_v * 0.98), 3)
                current   = round(random.uniform(-5.0, 15.0), 2)
                temp      = round(random.uniform(22.0, 45.0), 1)
                soc       = round(random.uniform(15.0, 98.0), 1)
                # Occasionally spike values to trigger fault detection (1 in 15 chance)
                if random.randint(1, 15) == 1:
                    spike = random.choice(['voltage', 'temp', 'soc'])
                    if spike == 'voltage':
                        voltage = round(max_v + random.uniform(0.5, 1.5), 3)
                    elif spike == 'temp':
                        temp = round(random.uniform(62.0, 78.0), 1)
                    elif spike == 'soc':
                        soc = round(random.uniform(0.0, 4.0), 1)

                r_id = f"LIVE-{uuid.uuid4().hex[:10].upper()}"
                time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cycle = random.randint(100, 800)

                conn.execute("""
                    INSERT INTO Sensor_Reading
                    (Reading_ID, Battery_ID, Timestamp, Voltage_V, Current_A, Temperature_C, SOC_Percentage, Cycle_Count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (r_id, b_id, time_now, voltage, current, temp, soc, cycle))
                conn.commit()

            conn.close()
        except Exception as e:
            print(f"[Live Generator] Error: {e}")
        await asyncio.sleep(3)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background tasks on startup, cancel on shutdown."""
    task = asyncio.create_task(live_data_generator())
    print("[BMS] Live data generator started — inserting readings every 3s.")
    yield
    task.cancel()
    print("[BMS] Live data generator stopped.")

app = FastAPI(title="Smart BMS Database API", lifespan=lifespan)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bms_database.db')
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')

# Serve the static frontend files
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # Required for triggers to fire correctly
    return conn

@app.get("/")
def read_root():
    return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))

@app.get("/api/dashboard")
def get_dashboard_summary():
    """Fetches high-level data utilizing our SQL Views"""
    conn = get_db_connection()
    try:
        v_count = conn.execute("SELECT COUNT(*) FROM Vehicle").fetchone()[0]
        f_count = conn.execute("SELECT COUNT(*) FROM Fault_Log").fetchone()[0]
        live_stats = conn.execute("SELECT * FROM View_Live_Battery_Status LIMIT 25").fetchall()
        return {
            "total_vehicles": v_count,
            "total_faults_logged": f_count,
            "live_batteries": [dict(row) for row in live_stats]
        }
    finally:
        conn.close()

@app.get("/api/faults")
def get_fault_log():
    """Fetches the 10 most recent faults caught by Triggers"""
    conn = get_db_connection()
    try:
        faults = conn.execute("SELECT * FROM Fault_Log ORDER BY Detected_At DESC LIMIT 10").fetchall()
        return [dict(f) for f in faults]
    finally:
        conn.close()

@app.get("/api/live_telemetry")
def get_live_telemetry():
    """Fetches the 15 most recent battery sensor readings simulating live data flow."""
    conn = get_db_connection()
    try:
        query = """
            SELECT s.Reading_ID, s.Timestamp, b.Chemistry_Type, s.Voltage_V, s.Temperature_C, s.SOC_Percentage, s.Current_A
            FROM Sensor_Reading s
            JOIN Battery b ON s.Battery_ID = b.Battery_ID
            ORDER BY s.Timestamp DESC
            LIMIT 15
        """
        readings = conn.execute(query).fetchall()
        return [dict(r) for r in readings]
    finally:
        conn.close()

@app.post("/api/simulate/inject_fault")
def simulate_fault_injection():
    """Teacher Simulation: Manually inserts an over-voltage reading. Trigger catches it."""
    conn = get_db_connection()
    try:
        battery = conn.execute("SELECT Battery_ID, Max_Voltage_Limit FROM Battery LIMIT 1").fetchone()
        b_id = battery['Battery_ID']
        max_v = battery['Max_Voltage_Limit']
        
        anomaly_voltage = max_v + 1.5 
        r_id = f"SIM-VOLT-{uuid.uuid4().hex[:8].upper()}"
        time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute("""
            INSERT INTO Sensor_Reading 
            (Reading_ID, Battery_ID, Timestamp, Voltage_V, Current_A, Temperature_C, SOC_Percentage, Cycle_Count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (r_id, b_id, time_now, anomaly_voltage, 10, 25.0, 50.0, 100))
        
        conn.commit()
        return {"message": f"✅ Injected over-voltage reading {r_id} ({anomaly_voltage}V) into battery {b_id}. Trigger fired → Fault logged!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/simulate/run_diagnostics")
def run_stored_procedure_logic():
    """Teacher Simulation: Mimics the functionality of a Stored Procedure."""
    conn = get_db_connection()
    try:
        total_batteries = conn.execute("SELECT COUNT(*) FROM Battery").fetchone()[0]
        degraded = conn.execute("SELECT Battery_ID, Current_SOH FROM Battery WHERE Current_SOH < 95.0").fetchall()
        
        degraded_list = [{"id": d['Battery_ID'], "soh": d['Current_SOH']} for d in degraded]
        healthy_count = total_batteries - len(degraded_list)
        
        if not degraded:
            return {
                "status": "optimal",
                "total": total_batteries,
                "healthy": healthy_count,
                "degraded": [],
                "message": "All batteries are optimal. No safety procedures required."
            }
            
        safe_profile = conn.execute("SELECT Profile_ID FROM Charging_Profile WHERE Profile_Name LIKE '%Safe%' OR Profile_Name LIKE '%Trickle%' LIMIT 1").fetchone()[0]
        
        for d in degraded:
            b_id = d['Battery_ID']
            soh = d['Current_SOH']
            reason = f"Diagnostics SP found degraded SOH: {soh}%"
            conn.execute("INSERT INTO Charge_Recommendation (Battery_ID, Profile_ID, Reasoning) VALUES (?, ?, ?)", 
                         (b_id, safe_profile, reason))
            
        conn.commit()
        
        return {
            "status": "action_taken",
            "total": total_batteries,
            "healthy": healthy_count,
            "degraded": degraded_list,
            "profile_applied": safe_profile,
            "message": f"Detected degraded batteries. Safe Profile ({safe_profile}) enforced."
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/simulate/inject_soc_fault")
def simulate_soc_fault():
    """Teacher Simulation: Manually inserts a 0% SOC reading. Trigger catches it."""
    conn = get_db_connection()
    try:
        battery = conn.execute("SELECT Battery_ID FROM Battery LIMIT 1").fetchone()
        b_id = battery['Battery_ID']
        
        r_id = f"SIM-SOC-{uuid.uuid4().hex[:8].upper()}"
        time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute("""
            INSERT INTO Sensor_Reading 
            (Reading_ID, Battery_ID, Timestamp, Voltage_V, Current_A, Temperature_C, SOC_Percentage, Cycle_Count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (r_id, b_id, time_now, 3.0, 0, 25.0, 0.0, 100))
        
        conn.commit()
        return {"message": f"✅ Injected Critical SOC (0%) into battery {b_id} [Reading: {r_id}]. Trigger fired → Fault logged!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/simulate/inject_temp_fault")
def simulate_temp_fault():
    """Teacher Simulation: Manually inserts a critical over-temperature reading. Trigger catches it."""
    conn = get_db_connection()
    try:
        battery = conn.execute("SELECT Battery_ID, Max_Voltage_Limit FROM Battery LIMIT 1").fetchone()
        b_id = battery['Battery_ID']
        # Use 80% of this battery's chemistry-specific max voltage — guaranteed safe,
        # so ONLY the over-temperature trigger fires (not over-voltage).
        safe_voltage = round(battery['Max_Voltage_Limit'] * 0.80, 2)
        
        r_id = f"SIM-TEMP-{uuid.uuid4().hex[:8].upper()}"
        time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute("""
            INSERT INTO Sensor_Reading 
            (Reading_ID, Battery_ID, Timestamp, Voltage_V, Current_A, Temperature_C, SOC_Percentage, Cycle_Count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (r_id, b_id, time_now, safe_voltage, 10, 75.0, 50.0, 100))
        
        conn.commit()

        # Verify the trigger actually fired by checking the fault log
        fault = conn.execute(
            "SELECT Fault_ID FROM Fault_Log WHERE Reading_ID = ? LIMIT 1", (r_id,)
        ).fetchone()
        if not fault:
            raise HTTPException(status_code=500, detail="INSERT succeeded but trigger did NOT fire. Check DB triggers.")

        return {"message": f"✅ Injected Critical Temperature (75°C) into battery {b_id} [Reading: {r_id}]. Trigger fired → Fault logged!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

import subprocess

@app.post("/api/simulate/reset_database")
def reset_database():
    """Drops, re-seeds, and resets the database."""
    try:
        setup_script = os.path.join(BASE_DIR, 'database_setup.py')
        subprocess.run(['python', setup_script], check=True)
        return {"message": "Database successfully reset and re-seeded with synthetic data."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

