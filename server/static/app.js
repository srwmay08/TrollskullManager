const API_URL = "http://localhost:8000/api";
let pendingAutoSales = [];

function switchTab(tabId) {
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.classList.remove('active-tab');
    });
    document.getElementById(tabId).classList.add('active-tab');
    
    if(tabId === 'inventory') loadInventory();
    if(tabId === 'staff') loadStaff();
    if(tabId === 'ledger') loadLedger();
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

window.onload = function() {
    loadInventory();
};