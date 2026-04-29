document.addEventListener('DOMContentLoaded', () => {

    // --- TAB LOGIC ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active to clicked
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');

            // If switching to telemetry tab, pull fresh data immediately
            if(targetId === 'tab-telemetry') {
                loadTelemetry();
            }
        });
    });


    // --- DATA LOGIC ---
    const faultTableBody = document.getElementById('fault-table-body');
    const telemetryTableBody = document.getElementById('telemetry-table-body');
    const simResponse = document.getElementById('sim-response');
    const batteryCardsGrid = document.getElementById('battery-cards-grid');
    const viewStatsPill = document.getElementById('view-stats');

    // Inject row-flash keyframe once
    if (!document.getElementById('row-flash-style')) {
        const s = document.createElement('style');
        s.id = 'row-flash-style';
        s.textContent = `
            @keyframes rowFlash {
                0%   { background: rgba(52, 211, 153, 0.25); }
                100% { background: transparent; }
            }
            .row-flash { animation: rowFlash 1s ease-out; }
        `;
        document.head.appendChild(s);
    }

    // Fetch Dashboard View (SQL View: View_Live_Battery_Status)
    async function loadDashboardView() {
        try {
            const res = await fetch('/api/dashboard');
            const data = await res.json();
            const batteries = data.live_batteries;

            const now = new Date().toLocaleTimeString();
            viewStatsPill.textContent = `${data.total_vehicles} Vehicles · ${data.total_faults_logged} Faults · Updated ${now}`;

            batteryCardsGrid.innerHTML = '';
            batteries.forEach(b => {
                const sohColor = b.Current_SOH >= 95 ? '#4ade80' : b.Current_SOH >= 85 ? '#facc15' : '#f87171';
                const tempColor = b.Temperature_C > 60 ? '#f87171' : '#e2e8f0';
                const tr = document.createElement('tr');
                tr.className = 'row-flash';
                tr.innerHTML = `
                    <td><strong>${b.Battery_ID}</strong></td>
                    <td>${b.Owner_Name}</td>
                    <td><span class="badge" style="font-size:0.7rem">${b.Chemistry_Type}</span></td>
                    <td style="color:${sohColor}; font-weight:bold">${b.Current_SOH.toFixed(1)}%</td>
                    <td>${b.SOC_Percentage.toFixed(1)}%</td>
                    <td>${b.Voltage_V.toFixed(2)}</td>
                    <td style="color:${tempColor}">${b.Temperature_C.toFixed(1)}</td>
                `;
                batteryCardsGrid.appendChild(tr);
            });
        } catch (err) {
            batteryCardsGrid.innerHTML = `<tr><td colspan="7" style="color:#f87171; text-align:center">❌ Failed to load SQL View data.</td></tr>`;
            console.error("Failed to load dashboard view.", err);
        }
    }


    async function loadFaults() {
        try {
            const res = await fetch('/api/faults');
            const faults = await res.json();
            
            faultTableBody.innerHTML = ''; 
            
            faults.forEach(f => {
                const tr = document.createElement('tr');
                let severityHTML = f.Severity;
                if(f.Severity === 'FATAL') severityHTML = `<span style="color:#ef4444; font-weight:bold">${f.Severity}</span>`;
                else if(f.Severity === 'WARNING') severityHTML = `<span style="color:#f59e0b; font-weight:bold">${f.Severity}</span>`;

                tr.innerHTML = `
                    <td>#${f.Fault_ID}</td>
                    <td>${f.Battery_ID}</td>
                    <td>${severityHTML}</td>
                    <td>${f.Fault_Type}</td>
                    <td>${f.Detected_At}</td>
                `;
                faultTableBody.appendChild(tr);
            });
        } catch (err) {
            console.error("Failed to load faults.", err);
        }
    }

    // Chart.js Setup
    const ctx = document.getElementById('telemetryChart').getContext('2d');
    const telemetryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Voltage (V)',
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    data: [],
                    yAxisID: 'y',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Temperature (°C)',
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    data: [],
                    yAxisID: 'y1',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { labels: { color: '#e2e8f0' } }
            },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: {
                    type: 'linear', display: true, position: 'left',
                    ticks: { color: '#3b82f6' }, grid: { color: 'rgba(255,255,255,0.05)' },
                    title: { display: true, text: 'Voltage (V)', color: '#3b82f6' }
                },
                y1: {
                    type: 'linear', display: true, position: 'right',
                    ticks: { color: '#ef4444' }, grid: { drawOnChartArea: false },
                    title: { display: true, text: 'Temperature (°C)', color: '#ef4444' }
                }
            }
        }
    });

    // Fetch Live Telemetry
    async function loadTelemetry() {
        try {
            const res = await fetch('/api/live_telemetry');
            const telemetry = await res.json();
            
            telemetryTableBody.innerHTML = '';
            
            // Chart arrays
            const labels = [];
            const voltages = [];
            const temps = [];
            
            // Telemetry is fetched DESC, so we reverse it for the chart to show left-to-right timeline
            const chartData = [...telemetry].reverse();
            chartData.forEach(t => {
                // Extract just time for X axis
                const timeStr = t.Timestamp.split(' ')[1];
                labels.push(timeStr);
                voltages.push(t.Voltage_V);
                temps.push(t.Temperature_C);
            });
            
            telemetryChart.data.labels = labels;
            telemetryChart.data.datasets[0].data = voltages;
            telemetryChart.data.datasets[1].data = temps;
            telemetryChart.update();
            
            telemetry.forEach(t => {
                const tr = document.createElement('tr');
                let voltColor = t.Voltage_V > 4.5 ? '#ef4444' : '#e2e8f0';
                let tempColor = t.Temperature_C > 60 ? '#ef4444' : '#e2e8f0';

                tr.innerHTML = `
                    <td style="color:#94a3b8">${t.Timestamp}</td>
                    <td><span class="badge" style="font-size:0.7rem">${t.Chemistry_Type}</span></td>
                    <td style="color:${voltColor}; font-weight:bold">${t.Voltage_V.toFixed(2)}</td>
                    <td>${t.Current_A.toFixed(2)}</td>
                    <td style="color:${tempColor}; font-weight:bold">${t.Temperature_C.toFixed(1)}</td>
                    <td>${t.SOC_Percentage.toFixed(1)}%</td>
                `;
                telemetryTableBody.appendChild(tr);
            });
        } catch (err) {
            console.error("Failed to load telemetry.", err);
        }
    }


    // --- SIMULATOR BUTTONS ---
    document.getElementById('btn-inject-fault').addEventListener('click', async () => {
        simResponse.innerText = "Injecting volatile reading into Database...";
        try {
            const res = await fetch('/api/simulate/inject_fault', { method: 'POST' });
            const data = await res.json();
            simResponse.innerText = `✅ Success: ${data.message}`;
            loadFaults(); // Refresh immediately
        } catch(err) {
            simResponse.innerText = "❌ Error connecting to Backend.";
        }
    });

    document.getElementById('btn-run-diagnostics').addEventListener('click', async () => {
        simResponse.innerHTML = "<div class='loader' style='font-size:14px;'>Scanning all battery health states (SOH)...</div>";
        try {
            const res = await fetch('/api/simulate/run_diagnostics', { method: 'POST' });
            const data = await res.json();
            
            let html = `
                <div style="margin-bottom: 15px; font-weight: 600; font-size: 1.1rem;">✅ Diagnostic Complete</div>
                <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                    <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); padding: 15px; border-radius: 8px; flex: 1; text-align: center;">
                        <div style="font-size: 28px; font-weight: 800; color: #4ade80;">${data.healthy} <span style="font-size:16px; color:#94a3b8; font-weight:400;">/ ${data.total}</span></div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top:5px;">Healthy (SOH ≥ 95%)</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 15px; border-radius: 8px; flex: 1; text-align: center;">
                        <div style="font-size: 28px; font-weight: 800; color: #f87171;">${data.degraded.length}</div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top:5px;">Degraded (Requires Action)</div>
                    </div>
                </div>
            `;
            
            if (data.status === 'action_taken' && data.degraded.length > 0) {
                html += `<div style="font-size: 14px; margin-bottom: 10px; color: #fcd34d;">⚠️ <b>Action Taken:</b> ${data.message}</div>`;
                html += `<ul style="list-style: none; padding: 0; margin: 0; font-size: 13px; max-height: 120px; overflow-y: auto; background: rgba(0,0,0,0.2); border-radius: 5px; padding: 10px;">`;
                data.degraded.forEach(b => {
                    html += `<li style="padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between;">
                        <span>Battery <b>${b.id}</b></span>
                        <span>SOH: <span style="color: #f87171; font-weight:bold;">${b.soh}%</span></span>
                    </li>`;
                });
                html += `</ul>`;
            } else {
                html += `<div style="color: #4ade80; font-size: 14px; background: rgba(34, 197, 94, 0.1); padding: 10px; border-radius: 5px;">${data.message}</div>`;
            }
            
            simResponse.innerHTML = html;
        } catch(err) {
            simResponse.innerHTML = "<div style='color: #ef4444; padding: 10px; background: rgba(239, 68, 68, 0.1); border-radius: 5px;'>❌ Error connecting to Backend.</div>";
        }
    });
    document.getElementById('btn-inject-soc-fault').addEventListener('click', async () => {
        simResponse.innerText = "Injecting Critical SOC Fault (0%)...";
        try {
            const res = await fetch('/api/simulate/inject_soc_fault', { method: 'POST' });
            const data = await res.json();
            simResponse.innerText = `✅ Success: ${data.message}`;
            loadFaults();
        } catch(err) {
            simResponse.innerText = "❌ Error connecting to Backend.";
        }
    });

    document.getElementById('btn-inject-temp-fault').addEventListener('click', async () => {
        simResponse.innerText = "Injecting Critical Temperature Fault (75°C)...";
        try {
            const res = await fetch('/api/simulate/inject_temp_fault', { method: 'POST' });
            const data = await res.json();
            simResponse.innerText = `✅ Success: ${data.message}`;
            loadFaults();
        } catch(err) {
            simResponse.innerText = "❌ Error connecting to Backend.";
        }
    });

    document.getElementById('btn-reset-db').addEventListener('click', async () => {
        simResponse.innerHTML = "<div class='loader' style='font-size:14px;'>Resetting and Re-seeding entire SQLite Database... Please wait (~2 seconds).</div>";
        try {
            const res = await fetch('/api/simulate/reset_database', { method: 'POST' });
            const data = await res.json();
            simResponse.innerHTML = `<div style="color: #4ade80;">✅ Success: ${data.message}</div>`;
            loadFaults();
            loadTelemetry();
        } catch(err) {
            simResponse.innerHTML = "<div style='color: #ef4444;'>❌ Error connecting to Backend.</div>";
        }
    });

    // Initial load
    loadFaults();
    loadTelemetry();
    loadDashboardView();

    // --- AUTO-REFRESH: Fault log every 3 seconds (always) ---
    setInterval(() => {
        loadFaults();
    }, 3000);

    // --- AUTO-REFRESH: Telemetry every 3 seconds (always) ---
    setInterval(() => {
        loadTelemetry();
    }, 3000);

    // --- AUTO-REFRESH: SQL View every 3 seconds ---
    setInterval(() => {
        loadDashboardView();
    }, 3000);


    // --- LIVE INDICATOR: pulse dot in header ---
    const liveDot = document.createElement('span');
    liveDot.id = 'live-dot';
    liveDot.title = 'Live data is streaming every 3 seconds';
    liveDot.style.cssText = `
        display: inline-block;
        width: 10px; height: 10px;
        background: #4ade80;
        border-radius: 50%;
        margin-left: 10px;
        vertical-align: middle;
        animation: livePulse 1.5s ease-in-out infinite;
        box-shadow: 0 0 6px #4ade80;
    `;

    // Add pulse keyframes dynamically
    if (!document.getElementById('live-pulse-style')) {
        const style = document.createElement('style');
        style.id = 'live-pulse-style';
        style.textContent = `
            @keyframes livePulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.4; transform: scale(0.7); }
            }
        `;
        document.head.appendChild(style);
    }

    const header = document.querySelector('h1, header h2, .header-title, nav');
    if (header) header.appendChild(liveDot);

});
