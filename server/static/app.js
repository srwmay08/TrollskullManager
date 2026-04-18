const API_URL = "http://localhost:8000/api";
let pendingAutoSales = [];

let npcData = [];
let npcSortCol = "first_name";
let npcSortDir = 1;
let collapsedFactions = {};

function switchTab(tabId) {
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.classList.remove('active-tab');
    });
    document.getElementById(tabId).classList.add('active-tab');
    
    if(tabId === 'inventory') loadInventory();
    if(tabId === 'staff') loadStaff();
    if(tabId === 'ledger') loadLedger();
    if(tabId === 'npcs') loadNpcs();
}

async function rollOutcome() {
    const payload = {
        base_roll: parseInt(document.getElementById('base_roll').value),
        renown_bonus: parseInt(document.getElementById('renown_bonus').value),
        environmental_bonus: parseInt(document.getElementById('env_bonus').value)
    };

    const response = await fetch(`${API_URL}/roll`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    const data = await response.json();
    
    document.getElementById('outcome-result').style.display = 'block';
    document.getElementById('out-title').innerText = `Roll: ${data.total_roll} (Includes +${data.staff_bonus_applied} Staff Bonus)`;
    document.getElementById('out-desc').innerText = data.outcome;
    document.getElementById('out-main').innerText = data.main_patrons;
    document.getElementById('out-vip').innerText = data.vip_patrons;
    
    pendingAutoSales = data.auto_sales;
    
    let salesHtml = "<strong>Auto-Generated Sales based on patrons:</strong><ul>";
    if (pendingAutoSales.length === 0) {
        salesHtml += "<li>None.</li>";
    } else {
        pendingAutoSales.forEach(s => {
            salesHtml += `<li>${s.quantity}x ${s.item_name} for ${s.total_price.toFixed(2)} gp</li>`;
        });
    }
    salesHtml += "</ul>";
    document.getElementById('out-sales').innerHTML = salesHtml;

    let hourlyHtml = "<strong>Hourly Patron Arrivals (From NPC Database):</strong><ul style='list-style-type: none; padding: 0;'>";
    data.hourly_breakdown.forEach(h => {
        let patronNames = h.patrons.length > 0 ? h.patrons.join(", ") : "None";
        hourlyHtml += `<li><strong style="color:#d7ba7d;">${h.hour}:</strong> ${patronNames}</li>`;
    });
    hourlyHtml += "</ul>";
    document.getElementById('out-hourly').innerHTML = hourlyHtml;
}

async function saveDay() {
    const dateStr = document.getElementById('global_date').value;
    
    if(!dateStr) {
        alert("Please enter a Current Date in the top right corner.");
        return;
    }

    const payload = {
        calendar_date: dateStr,
        sales: pendingAutoSales
    };

    const response = await fetch(`${API_URL}/save_day`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if(response.ok) {
        alert(`Day ${dateStr} saved successfully! Sales and Daily Wages recorded.`);
        pendingAutoSales = [];
        document.getElementById('out-sales').innerHTML = "<em>Sales have been committed to the ledger.</em>";
        document.getElementById('out-hourly').innerHTML = "<em>Tavern is now closed for the day.</em>";
    }
}

async function submitManualSale() {
    const dateStr = document.getElementById('global_date').value;
    const payload = {
        item_name: document.getElementById('sale_item').value,
        quantity: parseInt(document.getElementById('sale_qty').value),
        total_price: parseFloat(document.getElementById('sale_price').value),
        sale_date: dateStr
    };

    const response = await fetch(`${API_URL}/sales`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if(response.ok) {
        alert("Manual sale recorded.");
        document.getElementById('sale_item').value = "";
        document.getElementById('sale_price').value = "0.0";
    }
}

async function loadInventory() {
    const response = await fetch(`${API_URL}/inventory`);
    const data = await response.json();
    const tbody = document.getElementById('inventory-table-body');
    tbody.innerHTML = "";
    
    data.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input class="editable-input" type="text" id="inv_name_${item._id}" value="${item.item_name}"></td>
            <td><input class="editable-input" type="number" id="inv_hand_${item._id}" value="${item.stock_on_hand}"></td>
            <td><input class="editable-input" type="number" id="inv_order_${item._id}" value="${item.stock_on_order}"></td>
            <td><input class="editable-input" type="number" id="inv_per_${item._id}" value="${item.units_per}"></td>
            <td><input class="editable-input" type="number" id="inv_price_${item._id}" value="${item.unit_price}" step="0.1"></td>
            <td><button onclick="updateInventoryItem('${item._id}')">Save</button></td>
        `;
        tbody.appendChild(tr);
    });
}

async function updateInventoryItem(id) {
    const payload = {
        item_name: document.getElementById(`inv_name_${id}`).value,
        stock_on_hand: parseInt(document.getElementById(`inv_hand_${id}`).value),
        stock_on_order: parseInt(document.getElementById(`inv_order_${id}`).value),
        units_per: parseInt(document.getElementById(`inv_per_${id}`).value),
        unit_price: parseFloat(document.getElementById(`inv_price_${id}`).value)
    };

    const response = await fetch(`${API_URL}/inventory/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if(response.ok) {
        alert("Item updated.");
    }
}

async function loadStaff() {
    const response = await fetch(`${API_URL}/staff`);
    const data = await response.json();
    const tbody = document.getElementById('staff-table-body');
    tbody.innerHTML = "";
    
    data.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${s.name}</td>
            <td>${s.wage} gp</td>
            <td>${s.frequency}</td>
            <td>+${s.bonus}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function addStaff() {
    const payload = {
        name: document.getElementById('staff_name').value,
        wage: parseFloat(document.getElementById('staff_wage').value),
        frequency: document.getElementById('staff_freq').value,
        bonus: parseInt(document.getElementById('staff_bonus').value)
    };

    const response = await fetch(`${API_URL}/staff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if(response.ok) {
        alert("Staff added.");
        document.getElementById('staff_name').value = "";
        loadStaff();
    }
}

async function loadLedger() {
    const response = await fetch(`${API_URL}/ledger`);
    const data = await response.json();
    const tbody = document.getElementById('ledger-table-body');
    tbody.innerHTML = "";
    
    data.reverse().forEach(l => {
        const tr = document.createElement('tr');
        const isIncome = l.entry_type === "Income";
        const amountClass = isIncome ? "income-text" : "expense-text";
        const sign = isIncome ? "+" : "-";
        
        tr.innerHTML = `
            <td>${l.entry_date}</td>
            <td>${l.entry_type}</td>
            <td>${l.description}</td>
            <td class="${amountClass}">${sign}${l.amount.toFixed(2)}</td>
            <td>${l.frequency}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function submitLedger() {
    const dateStr = document.getElementById('global_date').value;
    const payload = {
        entry_type: document.getElementById('ledger_type').value,
        description: document.getElementById('ledger_desc').value,
        amount: parseFloat(document.getElementById('ledger_amount').value),
        frequency: document.getElementById('ledger_freq').value,
        entry_date: dateStr
    };

    const response = await fetch(`${API_URL}/ledger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if(response.ok) {
        alert("Entry recorded.");
        document.getElementById('ledger_desc').value = "";
        loadLedger();
    }
}

async function loadReports() {
    const response = await fetch(`${API_URL}/reports`);
    const data = await response.json();
    
    let totalSales = 0;
    data.sales.forEach(s => totalSales += s.total_price);
    
    let totalExpenses = 0;
    let totalLedgerIncome = 0;
    
    data.ledger.forEach(l => {
        if(l.entry_type === "Income") {
            totalLedgerIncome += l.amount;
        } else {
            totalExpenses += l.amount;
        }
    });
    
    const net = (totalSales + totalLedgerIncome) - totalExpenses;
    
    const out = document.getElementById('report-output');
    out.innerHTML = `
        <h3>System Overview</h3>
        <p><strong>Total Recorded Bar Sales:</strong> ${totalSales.toFixed(2)} gp</p>
        <p><strong>Total Ledger Income (Grants/Sponsors):</strong> ${totalLedgerIncome.toFixed(2)} gp</p>
        <p><strong>Total Recorded Expenses (Guilds/Wages/Repairs):</strong> ${totalExpenses.toFixed(2)} gp</p>
        <p><strong>Net Vault Profit/Loss:</strong> <span style="color: ${net >= 0 ? '#28a745' : '#dc3545'}; font-size: 18px; font-weight: bold;">${net.toFixed(2)} gp</span></p>
        <p><em>(Data spans all recorded dates in the database)</em></p>
    `;
}

async function loadNpcs() {
    const response = await fetch(`${API_URL}/npcs`);
    npcData = await response.json();
    renderNpcs();
}

function sortNpcs(col) {
    if (npcSortCol === col) {
        npcSortDir *= -1;
    } else {
        npcSortCol = col;
        npcSortDir = 1;
    }
    renderNpcs();
}

function toggleFaction(faction) {
    collapsedFactions[faction] = !collapsedFactions[faction];
    renderNpcs();
}

function renderNpcs() {
    const groups = {};
    npcData.forEach(npc => {
        const affil = npc.affiliation || "Unaffiliated";
        if (!groups[affil]) groups[affil] = [];
        groups[affil].push(npc);
    });

    for (let affil in groups) {
        groups[affil].sort((a, b) => {
            let valA = a[npcSortCol];
            let valB = b[npcSortCol];
            
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();
            
            if (valA < valB) return -1 * npcSortDir;
            if (valA > valB) return 1 * npcSortDir;
            return 0;
        });
    }

    let html = `
        <table style="font-size: 14px;">
            <thead>
                <tr>
                    <th style="cursor:pointer;" onclick="sortNpcs('first_name')">First Name ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('last_name')">Last Name ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('type')">Type ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('lifestyle')">Lifestyle ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('affiliation')">Affiliation ⇅</th>
                    <th style="cursor:pointer; width:60px;" onclick="sortNpcs('age')">Age ⇅</th>
                    <th style="cursor:pointer; width:60px;" onclick="sortNpcs('bar_disposition')">Bar Disp ⇅</th>
                    <th style="cursor:pointer; width:60px;" onclick="sortNpcs('party_disposition')">Party Disp ⇅</th>
                    <th>Action</th>
                </tr>
            </thead>
    `;

    for (let affil in groups) {
        const isCollapsed = collapsedFactions[affil];
        html += `
            <tbody>
                <tr class="faction-header" onclick="toggleFaction('${affil.replace(/'/g, "\\'")}')">
                    <td colspan="9" style="background-color: #333; cursor: pointer; color: #d7ba7d; font-weight: bold; padding: 10px;">
                        ${isCollapsed ? '▶' : '▼'} ${affil} (${groups[affil].length})
                    </td>
                </tr>
        `;
        if (!isCollapsed) {
            groups[affil].forEach(npc => {
                html += `
                    <tr>
                        <td><input class="editable-input" type="text" id="npc_fn_${npc._id}" value="${npc.first_name || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_ln_${npc._id}" value="${npc.last_name || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_type_${npc._id}" value="${npc.type || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_life_${npc._id}" value="${npc.lifestyle || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_affil_${npc._id}" value="${npc.affiliation || ''}"></td>
                        <td><input class="editable-input" type="number" id="npc_age_${npc._id}" value="${npc.age || 0}" style="width:100%;"></td>
                        <td><input class="editable-input" type="number" id="npc_bar_${npc._id}" value="${npc.bar_disposition || 0}" style="width:100%;"></td>
                        <td><input class="editable-input" type="number" id="npc_party_${npc._id}" value="${npc.party_disposition || 0}" style="width:100%;"></td>
                        <td><button onclick="updateNpcItem('${npc._id}')">Save</button></td>
                    </tr>
                `;
            });
        }
        html += `</tbody>`;
    }
    html += `</table>`;

    document.getElementById('npc-container').innerHTML = html;
}

async function updateNpcItem(id) {
    const payload = {
        first_name: document.getElementById(`npc_fn_${id}`).value,
        last_name: document.getElementById(`npc_ln_${id}`).value,
        type: document.getElementById(`npc_type_${id}`).value,
        lifestyle: document.getElementById(`npc_life_${id}`).value,
        affiliation: document.getElementById(`npc_affil_${id}`).value,
        age: parseInt(document.getElementById(`npc_age_${id}`).value) || 0,
        bar_disposition: parseInt(document.getElementById(`npc_bar_${id}`).value) || 0,
        party_disposition: parseInt(document.getElementById(`npc_party_${id}`).value) || 0
    };

    const response = await fetch(`${API_URL}/npcs/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if(response.ok) {
        alert("NPC updated.");
        const idx = npcData.findIndex(n => n._id === id);
        if (idx > -1) {
            npcData[idx] = { ...npcData[idx], ...payload, _id: id };
        }
        renderNpcs();
    }
}

window.onload = function() {
    loadInventory();
};