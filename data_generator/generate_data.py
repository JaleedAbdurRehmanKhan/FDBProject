import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta

# Create output directory
output_dir = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("Starting data generation for BMS System...")

# 1. Generate Vehicles (Storage Units/EVs)
NUM_VEHICLES = 25
vehicles_data = []
owners = ["Ahsan", "Fatima", "Bilal", "Zara", "Tariq", "Ayesha", "Usman", "Sana", "Ali", "Hira"]
vehicle_types = ["Electric Vehicle", "Solar Storage", "Grid Backup"]

for i in range(1, NUM_VEHICLES + 1):
    vehicles_data.append({
        "Unit_ID": f"V-{i:03d}",
        "Owner_Name": random.choice(owners) + f" {random.randint(1, 99)}",
        "Unit_Type": random.choice(vehicle_types),
        "Registration_Date": (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 800))).strftime('%Y-%m-%d')
    })
df_vehicles = pd.DataFrame(vehicles_data)
df_vehicles.to_csv(os.path.join(output_dir, "Vehicles.csv"), index=False)
print("Vehicles.csv generated.")

# 2. Generate Batteries (Specialization handles NMC, LFP, LTO)
# Let's say each vehicle has exactly 1 battery bank for simplicity.
batteries_data = []
manufacturers = ["Tesla", "BYD", "Panasonic", "LG Chem", "Contemporary Amperex"]
chemistries = ["NMC", "LFP", "LTO"]

for i, vehicle in enumerate(vehicles_data):
    chem = random.choice(chemistries)
    base_data = {
        "Battery_ID": f"B-{i+1:03d}",
        "Unit_ID": vehicle["Unit_ID"],
        "Manufacturer": random.choice(manufacturers),
        "Manufacture_Date": (datetime.strptime(vehicle["Registration_Date"], '%Y-%m-%d') - timedelta(days=random.randint(10, 100))).strftime('%Y-%m-%d'),
        "Capacity_kWh": random.choice([50, 75, 100, 150]),
        "Chemistry_Type": chem,
        "Current_SOH": round(random.uniform(85.0, 100.0), 2)
    }
    
    # Specialization attributes
    if chem == "NMC":
        base_data["Cobalt_Percentage"] = round(random.uniform(10.0, 33.0), 2)
        base_data["Max_Voltage_Limit"] = 4.2
        base_data["Thermal_Runaway_Threshold"] = None
        base_data["Extreme_Cold_Tolerance_Limit"] = None
    elif chem == "LFP":
        base_data["Cobalt_Percentage"] = None
        base_data["Max_Voltage_Limit"] = 3.65
        base_data["Thermal_Runaway_Threshold"] = 270.0
        base_data["Extreme_Cold_Tolerance_Limit"] = None
    else: # LTO
        base_data["Cobalt_Percentage"] = None
        base_data["Max_Voltage_Limit"] = 2.85
        base_data["Thermal_Runaway_Threshold"] = None
        base_data["Extreme_Cold_Tolerance_Limit"] = -30.0

    batteries_data.append(base_data)

df_batteries = pd.DataFrame(batteries_data)
df_batteries.to_csv(os.path.join(output_dir, "Batteries.csv"), index=False)
print("Batteries.csv generated.")

# 3. Generate Time-Series Sensor Readings (10,000 rows exactly)
# We will simulate high-frequency charging/discharging cycles
NUM_READINGS = 10000
readings_data = []
start_time = datetime.now() - timedelta(days=30)

# Track current SOC per battery to make time series realistic
current_states = {}
for b in batteries_data:
    current_states[b["Battery_ID"]] = {
        "soc": round(random.uniform(20.0, 90.0), 2),
        "cycle_count": random.randint(10, 200),
        "timestamp": start_time,
        "is_charging": random.choice([True, False])
    }

for i in range(1, NUM_READINGS + 1):
    # Pick a random battery to update
    b = random.choice(batteries_data)
    b_id = b["Battery_ID"]
    state = current_states[b_id]
    
    # Progress time by 1-5 minutes
    state["timestamp"] += timedelta(minutes=random.randint(1, 5))
    
    # Simulate battery physics
    if state["is_charging"]:
        state["soc"] += random.uniform(0.1, 1.5)
        current_A = round(random.uniform(50.0, 150.0), 2) # positive current 
        if state["soc"] >= 100:
            state["soc"] = 100
            state["is_charging"] = False
            state["cycle_count"] += 1
    else:
        state["soc"] -= random.uniform(0.1, 1.0)
        current_A = round(random.uniform(-100.0, -10.0), 2) # negative current
        if state["soc"] <= 5:
            state["soc"] = 5
            state["is_charging"] = True

    # Voltage depends on chemistry and SOC
    max_v = b["Max_Voltage_Limit"]
    base_v = max_v * (0.8 + 0.2 * (state["soc"]/100)) # Simple approximation
    voltage_v = round(base_v + random.uniform(-0.05, 0.05), 2)
    
    # Standard temp
    temp_c = round(random.uniform(25.0, 45.0), 2)

    # -------------------------------------------------------------
    # INTENTIONAL FAULT INJECTION (For SQL Triggers later)
    # Approx 1% chance to inject a critical anomaly
    # -------------------------------------------------------------
    if random.random() < 0.01:
        fault_type = random.choice(['Over-Temperature', 'Over-Voltage'])
        if fault_type == 'Over-Temperature':
            temp_c = round(random.uniform(65.0, 85.0), 2) # Dangerous heat
        else:
            voltage_v = round(max_v + random.uniform(0.3, 0.8), 2) # Dangerous overcharge
            
    readings_data.append({
        "Reading_ID": f"R-{i:06d}",
        "Battery_ID": b_id,
        "Timestamp": state["timestamp"].strftime('%Y-%m-%d %H:%M:%S'),
        "Voltage_V": voltage_v,
        "Current_A": current_A,
        "Temperature_C": temp_c,
        "SOC_Percentage": round(state["soc"], 2),
        "Cycle_Count": state["cycle_count"]
    })

df_readings = pd.DataFrame(readings_data)
df_readings = df_readings.sort_values(by="Timestamp") # Sort chronologically
df_readings["Reading_ID"] = [f"R-{i:06d}" for i in range(1, len(df_readings)+1)] # Reindex safely
df_readings.to_csv(os.path.join(output_dir, "Sensor_Readings.csv"), index=False)
print(f"Sensor_Readings.csv generated with {NUM_READINGS} rows.")

# 4. Generate Charging Profiles mapping
profiles = [
    {"Profile_ID": "P-01", "Profile_Name": "Ultra-Fast Charge", "Target_Voltage": 4.2, "Max_Current": 200, "Recommended_Temperature_Range": "20-40"},
    {"Profile_ID": "P-02", "Profile_Name": "Trickle Charge", "Target_Voltage": 3.8, "Max_Current": 10, "Recommended_Temperature_Range": "10-45"},
    {"Profile_ID": "P-03", "Profile_Name": "Cell Balancing", "Target_Voltage": 3.6, "Max_Current": 5, "Recommended_Temperature_Range": "15-35"},
    {"Profile_ID": "P-04", "Profile_Name": "Thermal Safe Mode", "Target_Voltage": 3.4, "Max_Current": 0, "Recommended_Temperature_Range": "0-25"}
]
df_profiles = pd.DataFrame(profiles)
df_profiles.to_csv(os.path.join(output_dir, "Charging_Profiles.csv"), index=False)
print("Charging_Profiles.csv generated.")

print("All datasets successfully created!")
