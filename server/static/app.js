const API_URL = "http://localhost:8000/api";
let pendingAutoSales = [];

// NPC State
let npcData = [];
let npcSortCol = "first_name";
let npcSortDir = 1;
let collapsedFactions = {};

// Inventory State
let inventoryData = [];
let invSortCol = "item_name";
let invSortDir = 1;
let collapsedInvCategories = {};

// Calendar of Harptos State Variables
let currentYear = 1492;
let currentMonthIndex = 2;
let currentDay = 30;
let isHoliday = false;
let currentHolidayName = "";
let isShieldmeet = false;

const harptosMonths = ["Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"];

function getFormattedDate() {
    if (isShieldmeet) return `Shieldmeet, ${currentYear} DR`;
    if (isHoliday) return `${currentHolidayName}, ${currentYear} DR`;
    return `${currentDay} ${harptosMonths[currentMonthIndex]}, ${currentYear} DR`;
}

function updateDateDisplay() { document.getElementById('global_date_display').innerText = getFormattedDate(); }

function advanceDate() {
    if (isShieldmeet) { isShieldmeet = false; isHoliday = false; currentHolidayName = ""; currentMonthIndex = 7; currentDay = 1; }
    else if (isHoliday) {
        if (currentHolidayName === "Midsummer" && (currentYear % 4 === 0)) { isShieldmeet = true; currentHolidayName = "Shieldmeet"; isHoliday = true; }
        else { isHoliday = false; currentHolidayName = ""; currentMonthIndex++; if (currentMonthIndex > 11) { currentMonthIndex = 0; currentYear++; } currentDay = 1; }
    } else {
        if (currentDay < 30) { currentDay++; }
        else {
            if (currentMonthIndex === 0) { isHoliday = true; currentHolidayName = "Midwinter"; }
            else if (currentMonthIndex === 3) { isHoliday = true; currentHolidayName = "Greengrass"; }
            else if (currentMonthIndex === 6) { isHoliday = true; currentHolidayName = "Midsummer"; }
            else if (currentMonthIndex === 8) { isHoliday = true; currentHolidayName = "Highharvestide"; }
            else if (currentMonthIndex === 10) { isHoliday = true; currentHolidayName = "Feast of the Moon"; }
            else { currentMonthIndex++; if (currentMonthIndex > 11) { currentMonthIndex = 0; currentYear++; } currentDay = 1; }
        }
    }
    updateDateDisplay();
}

function switchTab(tabId) {
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active-tab'));
    document.getElementById(tabId).classList.add('active-tab');
    if(tabId === 'inventory') loadInventory();
    if(tabId === 'staff') loadStaff();
    if(tabId === 'ledger') loadLedger();
    if(tabId === 'npcs') loadNpcs();
}

async function rollOutcome() {
    const current_date_payload = { month: currentMonthIndex + 1, day: currentDay, year: currentYear, is_holiday: isHoliday, holiday_name: isHoliday ? currentHolidayName : null, is_shieldmeet: isShieldmeet };
    const payload = {
        base_roll: parseInt(document.getElementById('base_roll').value),
        renown_bonus: parseInt(document.getElementById('renown_bonus').value),
        environmental_bonus: parseInt(document.getElementById('env_bonus').value),
        price_strategy: document.getElementById('price_strategy').value,
        current_date: current_date_payload
    };
    const response = await fetch(`${API_URL}/roll`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    document.getElementById('outcome-result').style.display = 'block';
    
    pendingAutoSales = data.auto_sales;
    let salesHtml = "<ul style='padding-left: 20px; font-size: 14px;'>";
    if (pendingAutoSales.length === 0) { salesHtml += "<li>No items sold.</li>"; }
    else { pendingAutoSales.forEach(s => { salesHtml += `<li><strong>${s.quantity}x</strong> ${s.item_name} <span style="color:#28a745; float:right;">+${s.total_price.toFixed(2)} gp</span></li>`; }); }
    salesHtml += "</ul>";
    document.getElementById('out-sales').innerHTML = salesHtml;

    let receiptsHtml = "";
    data.receipts.forEach(r => {
        receiptsHtml += `<div class="receipt-card"><h4>${r.name}</h4><div style="font-size:11px; color:#aaa; margin-bottom: 8px;">Lifestyle: ${r.lifestyle} | Seating: ${r.seat} | Arrived: ${r.hour}</div>`;
        r.items.forEach(item => { receiptsHtml += `<div class="receipt-item"><span>${item.qty}x ${item.name}</span><span>${item.price.toFixed(2)} gp</span></div>`; });
        receiptsHtml += `<div class="receipt-total">Total: ${r.total.toFixed(2)} gp</div></div>`;
    });
    document.getElementById('out-receipts').innerHTML = receiptsHtml;
}

async function saveDay() {
    const dateStr = getFormattedDate();
    const payload = { calendar_date: dateStr, sales: pendingAutoSales };
    const response = await fetch(`${API_URL}/save_day`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });

    if(response.ok) {
        const data = await response.json();
        let message = `Day ${dateStr} saved! Inventory deducted and CSVs synced.`;
        if (data.restocks && data.restocks.length > 0) {
            message += `\n\nAUTOMATIC RESTOCK TRIGGERED:\n`;
            data.restocks.forEach(msg => { message += `- ${msg}\n`; });
        }
        alert(message);
        pendingAutoSales = [];
        document.getElementById('out-sales').innerHTML = "<em>Sales have been committed to the ledger. Inventory deducted.</em>";
        document.getElementById('out-receipts').innerHTML = "";
    }
}

function calcCost(id) {
    const orderCost = parseFloat(document.getElementById(`inv_order_cost_${id}`).value) || 0;
    const qtyPer = parseInt(document.getElementById(`inv_qty_per_${id}`).value) || 1;
    const sellPrice = parseFloat(document.getElementById(`inv_sell_${id}`).value) || 0;
    
    const costPer = orderCost / qtyPer;
    const margin = sellPrice - costPer;

    document.getElementById(`inv_cost_per_${id}`).innerText = costPer.toFixed(2);
    document.getElementById(`inv_margin_${id}`).innerText = margin.toFixed(2);
    
    const stock = parseInt(document.getElementById(`inv_stock_${id}`).value) || 0;
    const reorderLvl = parseInt(document.getElementById(`inv_reorder_lvl_${id}`).value) || 0;
    
    const statusEl = document.getElementById(`inv_status_${id}`);
    if (stock <= reorderLvl) {
        statusEl.innerText = "ORDER";
        statusEl.style.color = "#dc3545";
    } else {
        statusEl.innerText = "OK";
        statusEl.style.color = "#28a745";
    }
}

async function loadInventory() {
    const response = await fetch(`${API_URL}/inventory`);
    inventoryData = await response.json();
    renderInventory();
}

function sortInventory(col) {
    if (invSortCol === col) invSortDir *= -1;
    else { invSortCol = col; invSortDir = 1; }
    renderInventory();
}

function toggleInvCategory(cat) {
    collapsedInvCategories[cat] = !collapsedInvCategories[cat];
    renderInventory();
}

function renderInventory() {
    const groups = {};
    inventoryData.forEach(inv => {
        const cat = inv.category || "Uncategorized";
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(inv);
    });

    for (let cat in groups) {
        groups[cat].sort((a, b) => {
            let valA = a[invSortCol]; let valB = b[invSortCol];
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();
            if (valA < valB) return -1 * invSortDir;
            if (valA > valB) return 1 * invSortDir;
            return 0;
        });
    }

    let html = `
        <table style="font-size: 13px; min-width: 1400px; border-collapse: collapse;">
            <thead>
                <tr>
                    <th rowspan="2" style="cursor:pointer; width: 180px;" onclick="sortInventory('item_name')">CATEGORY / ITEM ⇅</th>
                    <th colspan="3" class="group-header bg-cost">ORDER BY</th>
                    <th colspan="2" class="group-header bg-stock">ITEMS / UNIT DETAILS</th>
                    <th rowspan="2" class="bg-cost">COST PER ITEM</th>
                    <th rowspan="2" class="bg-revenue">SELL PRICE<br>IN COPPER</th>
                    <th rowspan="2" class="bg-revenue">MARGIN<br>IN COPPER</th>
                    <th rowspan="2" class="bg-stock">STOCK UNIT<br>QUANTITY</th>
                    <th rowspan="2" class="bg-stock">REORDER<br>LEVEL</th>
                    <th rowspan="2" class="bg-stock">STATUS</th>
                    <th rowspan="2" class="bg-stock">REORDER<br>QUANTITY</th>
                    <th rowspan="2" style="background-color: #333;">Action</th>
                </tr>
                <tr>
                    <th class="bg-cost" style="width: 80px;">UNIT</th>
                    <th class="bg-cost" style="width: 80px;">QUANTITY</th>
                    <th class="bg-cost" style="width: 90px;">UNIT COST<br>IN COPPER</th>
                    <th class="bg-stock" style="width: 80px;">QUANTITY<br>per UNIT</th>
                    <th class="bg-stock" style="width: 90px;">SERVE SIZE</th>
                </tr>
            </thead>
    `;

    for (let cat in groups) {
        const isCollapsed = collapsedInvCategories[cat];
        html += `
            <tbody>
                <tr onclick="toggleInvCategory('${cat.replace(/'/g, "\\'")}')">
                    <td colspan="14" class="cat-header">
                        ${isCollapsed ? '▶' : '▼'} ${cat.toUpperCase()} (${groups[cat].length} Items)
                    </td>
                </tr>
        `;
        if (!isCollapsed) {
            groups[cat].forEach(item => {
                const statusColor = (item.status === 'ORDER' || item.status === 'Order') ? '#dc3545' : '#28a745';
                html += `
                    <tr>
                        <td><input class="editable-input" type="text" id="inv_name_${item._id}" value="${item.item_name}" style="width: 95%;"></td>
                        
                        <td style="background-color: rgba(107, 36, 36, 0.15); border-left: 1px solid #6b2424;"><input class="editable-input small-input" type="text" id="inv_unit_${item._id}" value="${item.order_unit || 'Unit'}"></td>
                        <td style="background-color: rgba(107, 36, 36, 0.15);"><input class="editable-input small-input" type="number" id="inv_order_qty_${item._id}" value="${item.order_quantity || 1}"></td>
                        <td style="background-color: rgba(107, 36, 36, 0.15); border-right: 1px solid #6b2424;"><input class="editable-input small-input" type="number" id="inv_order_cost_${item._id}" value="${item.unit_cost_copper || 0}" step="0.1" oninput="calcCost('${item._id}')"></td>
                        
                        <td style="background-color: rgba(29, 75, 107, 0.2); border-left: 1px solid #1d4b6b;"><input class="editable-input small-input" type="number" id="inv_qty_per_${item._id}" value="${item.qty_per_unit || 1}" oninput="calcCost('${item._id}')"></td>
                        <td style="background-color: rgba(29, 75, 107, 0.2); border-right: 1px solid #1d4b6b;"><input class="editable-input small-input" style="width: 80px;" type="text" id="inv_serve_${item._id}" value="${item.serve_size || 'Standard'}"></td>
                        
                        <td style="background-color: rgba(107, 36, 36, 0.3); font-weight: bold; text-align: center;"><span id="inv_cost_per_${item._id}" style="color:#d7ba7d;">${(item.cost_per_item_copper || 0).toFixed(2)}</span></td>
                        
                        <td style="background-color: rgba(33, 89, 52, 0.2); border-left: 1px solid #215934;"><input class="editable-input small-input" type="number" id="inv_sell_${item._id}" value="${item.sell_price_copper || 0}" step="0.1" oninput="calcCost('${item._id}')"></td>
                        <td style="background-color: rgba(33, 89, 52, 0.2); border-right: 1px solid #215934; font-weight: bold; text-align: center;"><span id="inv_margin_${item._id}" style="color:#28a745;">${(item.margin_copper || 0).toFixed(2)}</span></td>
                        
                        <td style="background-color: rgba(29, 75, 107, 0.2); border-left: 1px solid #1d4b6b;"><input class="editable-input small-input" type="number" id="inv_stock_${item._id}" value="${item.stock_unit_quantity || 0}" oninput="calcCost('${item._id}')"></td>
                        <td style="background-color: rgba(29, 75, 107, 0.2);"><input class="editable-input small-input" type="number" id="inv_reorder_lvl_${item._id}" value="${item.reorder_level || 0}" oninput="calcCost('${item._id}')"></td>
                        <td style="background-color: rgba(29, 75, 107, 0.2); font-weight: bold; text-align: center;"><span id="inv_status_${item._id}" style="color: ${statusColor};">${item.status || 'OK'}</span></td>
                        <td style="background-color: rgba(29, 75, 107, 0.2); border-right: 1px solid #1d4b6b;"><input class="editable-input small-input" type="number" id="inv_reorder_qty_${item._id}" value="${item.reorder_quantity || 0}"></td>
                        
                        <td><button style="width: 100%; padding: 5px;" onclick="updateInventoryItem('${item._id}', '${cat.replace(/'/g, "\\'")}')">Save</button></td>
                    </tr>
                `;
            });
        }
        html += `</tbody>`;
    }
    html += `</table>`;
    document.getElementById('inventory-container').innerHTML = html;
}

async function updateInventoryItem(id, cat) {
    const payload = {
        item_name: document.getElementById(`inv_name_${id}`).value,
        category: cat,
        order_unit: document.getElementById(`inv_unit_${id}`).value,
        order_quantity: parseInt(document.getElementById(`inv_order_qty_${id}`).value),
        unit_cost_copper: parseFloat(document.getElementById(`inv_order_cost_${id}`).value),
        qty_per_unit: parseInt(document.getElementById(`inv_qty_per_${id}`).value),
        serve_size: document.getElementById(`inv_serve_${id}`).value,
        cost_per_item_copper: parseFloat(document.getElementById(`inv_cost_per_${id}`).innerText),
        sell_price_copper: parseFloat(document.getElementById(`inv_sell_${id}`).value),
        margin_copper: parseFloat(document.getElementById(`inv_margin_${id}`).innerText),
        stock_unit_quantity: parseInt(document.getElementById(`inv_stock_${id}`).value),
        reorder_level: parseInt(document.getElementById(`inv_reorder_lvl_${id}`).value),
        status: document.getElementById(`inv_status_${id}`).innerText,
        reorder_quantity: parseInt(document.getElementById(`inv_reorder_qty_${id}`).value)
    };
    const response = await fetch(`${API_URL}/inventory/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if(response.ok) {
        alert("Inventory Updated and inventory.csv Synced!");
        const idx = inventoryData.findIndex(n => n._id === id);
        if (idx > -1) { inventoryData[idx] = { ...inventoryData[idx], ...payload, _id: id }; }
        renderInventory();
    }
}

async function loadStaff() {
    const response = await fetch(`${API_URL}/staff`);
    const data = await response.json();
    const tbody = document.getElementById('staff-table-body');
    tbody.innerHTML = "";
    data.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${s.name}</td><td>${s.wage} gp</td><td>${s.frequency}</td><td>+${s.bonus}</td>`;
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
    await fetch(`${API_URL}/staff`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    loadStaff();
}

async function loadLedger() {
    const response = await fetch(`${API_URL}/ledger`);
    const data = await response.json();
    const tbody = document.getElementById('ledger-table-body');
    tbody.innerHTML = "";
    data.reverse().forEach(l => {
        const isIncome = l.entry_type === "Income";
        const amountClass = isIncome ? "income-text" : "expense-text";
        const sign = isIncome ? "+" : "-";
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${l.entry_date}</td><td>${l.entry_type}</td><td>${l.description}</td><td class="${amountClass}">${sign}${l.amount.toFixed(2)}</td><td>${l.frequency}</td>`;
        tbody.appendChild(tr);
    });
}

async function submitLedger() {
    const dateStr = getFormattedDate();
    const payload = {
        entry_type: document.getElementById('ledger_type').value,
        description: document.getElementById('ledger_desc').value,
        amount: parseFloat(document.getElementById('ledger_amount').value),
        frequency: document.getElementById('ledger_freq').value,
        entry_date: dateStr
    };
    await fetch(`${API_URL}/ledger`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    document.getElementById('ledger_desc').value = "";
    loadLedger();
}

async function loadReports() {
    const response = await fetch(`${API_URL}/reports`);
    const data = await response.json();
    let totalSales = 0; data.sales.forEach(s => totalSales += s.total_price);
    let totalExpenses = 0; let totalLedgerIncome = 0;
    data.ledger.forEach(l => { if(l.entry_type === "Income") { totalLedgerIncome += l.amount; } else { totalExpenses += l.amount; } });
    const net = (totalSales + totalLedgerIncome) - totalExpenses;
    document.getElementById('report-output').innerHTML = `
        <h3>System Overview</h3>
        <p><strong>Total Recorded Bar Sales:</strong> ${totalSales.toFixed(2)} gp</p>
        <p><strong>Total Ledger Income:</strong> ${totalLedgerIncome.toFixed(2)} gp</p>
        <p><strong>Total Recorded Expenses:</strong> ${totalExpenses.toFixed(2)} gp</p>
        <p><strong>Net Vault Profit/Loss:</strong> <span style="color: ${net >= 0 ? '#28a745' : '#dc3545'}; font-size: 18px; font-weight: bold;">${net.toFixed(2)} gp</span></p>
    `;
}

async function loadNpcs() {
    const response = await fetch(`${API_URL}/npcs`);
    npcData = await response.json();
    renderNpcs();
}

function sortNpcs(col) {
    if (npcSortCol === col) npcSortDir *= -1;
    else { npcSortCol = col; npcSortDir = 1; }
    renderNpcs();
}

function toggleFaction(faction) {
    collapsedFactions[faction] = !collapsedFactions[faction];
    renderNpcs();
}

function renderNpcs() {
    const groups = {};
    npcData.forEach(npc => {
        const affil = npc.faction || "Unaffiliated";
        if (!groups[affil]) groups[affil] = [];
        groups[affil].push(npc);
    });

    for (let affil in groups) {
        groups[affil].sort((a, b) => {
            let valA = a[npcSortCol]; let valB = b[npcSortCol];
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();
            if (valA < valB) return -1 * npcSortDir;
            if (valA > valB) return 1 * npcSortDir;
            return 0;
        });
    }

    let html = `
        <table style="font-size: 12px; min-width: 1400px;">
            <thead>
                <tr>
                    <th style="cursor:pointer;" onclick="sortNpcs('first_name')">First Name ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('last_name')">Last Name ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('nobility_status')">Nobility ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('noble_house')">House ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('lifestyle')">Lifestyle ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('faction')">Faction ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('occupation')">Occupation ⇅</th>
                    <th style="cursor:pointer; width:40px;" onclick="sortNpcs('age')">Age ⇅</th>
                    <th style="cursor:pointer; width:50px;" onclick="sortNpcs('bar_disposition')">Bar Disp ⇅</th>
                    <th style="cursor:pointer; width:50px;" onclick="sortNpcs('party_disposition')">Party Disp ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('story_connection')">Story Connect ⇅</th>
                    <th style="cursor:pointer;" onclick="sortNpcs('pc_affiliation')">PC Affil ⇅</th>
                    <th>Action</th>
                </tr>
            </thead>
    `;

    for (let affil in groups) {
        const isCollapsed = collapsedFactions[affil];
        html += `<tbody><tr class="faction-header cat-header" onclick="toggleFaction('${affil.replace(/'/g, "\\'")}')"><td colspan="13">${isCollapsed ? '▶' : '▼'} ${affil} (${groups[affil].length})</td></tr>`;
        if (!isCollapsed) {
            groups[affil].forEach(npc => {
                html += `
                    <tr>
                        <td><input class="editable-input" type="text" id="npc_fn_${npc._id}" value="${npc.first_name || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_ln_${npc._id}" value="${npc.last_name || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_nobility_${npc._id}" value="${npc.nobility_status || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_house_${npc._id}" value="${npc.noble_house || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_life_${npc._id}" value="${npc.lifestyle || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_faction_${npc._id}" value="${npc.faction || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_occ_${npc._id}" value="${npc.occupation || ''}"></td>
                        <td><input class="editable-input" type="number" id="npc_age_${npc._id}" value="${npc.age || 0}" style="width:100%;"></td>
                        <td><input class="editable-input" type="number" id="npc_bar_${npc._id}" value="${npc.bar_disposition || 0}" style="width:100%;"></td>
                        <td><input class="editable-input" type="number" id="npc_party_${npc._id}" value="${npc.party_disposition || 0}" style="width:100%;"></td>
                        <td><input class="editable-input" type="text" id="npc_story_${npc._id}" value="${npc.story_connection || ''}"></td>
                        <td><input class="editable-input" type="text" id="npc_pc_${npc._id}" value="${npc.pc_affiliation || ''}"></td>
                        <td><button onclick="updateNpcItem('${npc._id}')">Save & Sync CSV</button></td>
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
        nobility_status: document.getElementById(`npc_nobility_${id}`).value,
        noble_house: document.getElementById(`npc_house_${id}`).value,
        lifestyle: document.getElementById(`npc_life_${id}`).value,
        faction: document.getElementById(`npc_faction_${id}`).value,
        occupation: document.getElementById(`npc_occ_${id}`).value,
        age: parseInt(document.getElementById(`npc_age_${id}`).value) || 0,
        bar_disposition: parseInt(document.getElementById(`npc_bar_${id}`).value) || 0,
        party_disposition: parseInt(document.getElementById(`npc_party_${id}`).value) || 0,
        story_connection: document.getElementById(`npc_story_${id}`).value,
        pc_affiliation: document.getElementById(`npc_pc_${id}`).value
    };
    await fetch(`${API_URL}/npcs/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    alert("NPC Updated and npcs.csv Synced!");
    const idx = npcData.findIndex(n => n._id === id);
    if (idx > -1) { npcData[idx] = { ...npcData[idx], ...payload, _id: id }; }
    renderNpcs();
}

window.onload = function() {
    updateDateDisplay();
};