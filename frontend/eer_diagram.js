document.addEventListener('DOMContentLoaded', () => {
    // We use the DOT language to explicitly map to standard Chen Notation shapes
    // shape=box for Entities
    // shape=diamond for Relationships
    // shape=ellipse for Attributes
    // shape=triangle for Specialization (is-a)

    const dotSource = `
    graph EER {
        // Global styling for dark aesthetic
        bgcolor="transparent"
        node [fontname="Inter, sans-serif", fontsize=18, style="filled", color="#3b82f6", fillcolor="#1e293b", fontcolor="#f8fafc", penwidth=2.5]
        edge [fontname="Inter, sans-serif", fontsize=20, fontcolor="#fbbf24", labelfontcolor="#fbbf24", color="#94a3b8", penwidth=2.5]



        // --- ATTRIBUTES (ELLIPSES) ---
        node [shape=ellipse, fillcolor="#1e293b", color="#10b981"] // Green stroke for attributes
        
        // Vehicle Attributes
        v_id [label=<<U>Unit_ID</U>>] // Primary Key underlined
        v_owner [label="Owner_Name"]
        v_type [label="Unit_Type"]

        // Battery Attributes
        b_id [label=<<U>Battery_ID</U>>]
        b_mfg [label="Manufacturer"]
        b_cap [label="Capacity_kWh"]
        b_chem [label="Chemistry_Type"]

        // Specific Battery Attributes
        nmc_cobalt [label="Cobalt_Percentage"]
        lfp_thermal [label="Thermal_Threshold"]
        lto_cold [label="Cold_Tolerance"]

        // Sensor Reading Attributes
        r_id [label=<<U>Reading_ID</U>>]
        r_time [label="Timestamp"]
        r_volt [label="Voltage_V"]
        r_temp [label="Temperature_C"]
        r_soc [label="SOC_Percentage"]

        // Fault Attributes
        f_id [label=<<U>Fault_ID</U>>]
        f_type [label="Fault_Type"]

        // --- ENTITIES (BOXES) ---
        node [shape=box, fillcolor="#0f172a", color="#3b82f6", height=0.6] // Blue stroke for entities
        
        Vehicle [label="Vehicle / Storage"]
        Battery [label="Battery"]
        
        NMC_Battery [label="NMC_Battery"]
        LFP_Battery [label="LFP_Battery"]
        LTO_Battery [label="LTO_Battery"]

        // Weak Entity: Sensor Reading (Double Box in Chen, simulated here)
        Sensor_Reading [label="Sensor_Reading", peripheries=2]
        
        Fault_Log [label="Fault_Log"]

        // --- RELATIONSHIPS (DIAMONDS) ---
        node [shape=diamond, fillcolor="#0f172a", color="#ef4444", height=0.8] // Red stroke for relationships

        Has [label="Has"]
        Logs [label="Logs", peripheries=2] // Weak relationship
        Triggers [label="Triggers"]

        // --- SPECIALIZATION (TRIANGLE) ---
        node [shape=triangle, fillcolor="#0f172a", color="#f59e0b", orientation=180] // pointing down
        Is_A [label=" d "] // d = Disjoint

        // --- CONNECTIONS ---

        // Vehicle -> Attributes
        Vehicle -- v_id
        Vehicle -- v_owner
        Vehicle -- v_type

        // Vehicle -> Has -> Battery (1 to Many)
        Vehicle -- Has [label=" 1"]
        Has -- Battery [label=" N"]

        // Battery -> Attributes
        Battery -- b_id
        Battery -- b_mfg
        Battery -- b_cap
        Battery -- b_chem

        // Battery -> Specialization -> Subclasses
        Battery -- Is_A
        Is_A -- NMC_Battery
        Is_A -- LFP_Battery
        Is_A -- LTO_Battery

        // Subclass -> specific attributes
        NMC_Battery -- nmc_cobalt
        LFP_Battery -- lfp_thermal
        LTO_Battery -- lto_cold

        // Battery -> Logs -> Sensor Reading (1 to Many Weak)
        Battery -- Logs [label=" 1"]
        Logs -- Sensor_Reading [label=" N"]

        // Sensor Reading -> Attributes
        Sensor_Reading -- r_id
        Sensor_Reading -- r_time
        Sensor_Reading -- r_volt
        Sensor_Reading -- r_temp
        Sensor_Reading -- r_soc

        // Sensor Reading -> Triggers -> Fault Log (1 to Many)
        Sensor_Reading -- Triggers [label=" 1"]
        Triggers -- Fault_Log [label=" N"]

        // Fault -> Attributes
        Fault_Log -- f_id
        Fault_Log -- f_type
    }
    `;

    // Render using Viz.js
    const viz = new Viz();
    const container = document.getElementById('graph-output');

    viz.renderSVGElement(dotSource)
    .then(function(element) {
        container.innerHTML = ''; // Clear loader
        // Responsive scaling mapping to modern CSS
        element.style.width = '100%';
        element.style.height = 'auto';
        element.style.maxHeight = '700px';
        container.appendChild(element);
    })
    .catch(error => {
        container.innerHTML = '<span style="color:red">Error rendering graph!</span>';
        console.error(error);
    });
});
