const API_URL = "http://localhost:8000/api";
let pendingAutoSales = [];
let isDayClosed = false;

let npcData = [];
let inventoryData = [];

let currentYear = 1492;
let currentMonthIndex = 2;
let currentDay = 30;
let isHoliday = false;
let currentHolidayName = "";
let isShieldmeet = false;

const harptosMonths = [
    "Hammer", 
    "Alturiak", 
    "Ches", 
    "Tarsakh", 
    "Mirtul", 
    "Kythorn", 
    "Flamerule", 
    "Eleasis", 
    "Eleint", 
    "Marpenoth", 
    "Uktar", 
    "Nightal"
];


function getFormattedDate() {
    if (isShieldmeet) {
        return `Shieldmeet, ${currentYear} DR`;
    }
    if (isHoliday) {
        return `${currentHolidayName}, ${currentYear} DR`;
    }
    return `${currentDay} ${harptosMonths[currentMonthIndex]}, ${currentYear} DR`;
}


function updateDateDisplay() { 
    document.getElementById('global_date_display').innerText = getFormattedDate(); 
}


function advanceDate() {
    if (isShieldmeet) { 
        isShieldmeet = false; isHoliday = false; currentHolidayName = ""; currentMonthIndex = 7; currentDay = 1; 
    } else if (isHoliday) {
        if (currentHolidayName === "Midsummer" && (currentYear % 4 === 0)) { 
            isShieldmeet = true; currentHolidayName = "Shieldmeet"; isHoliday = true; 
        } else { 
            isHoliday = false; currentHolidayName = ""; currentMonthIndex++; currentDay = 1; 
        }
    } else {
        if (currentDay < 30) { currentDay++; } else {
            if (currentMonthIndex === 0) { isHoliday = true; currentHolidayName = "Midwinter"; }
            else if (currentMonthIndex === 3) { isHoliday = true; currentHolidayName = "Greengrass"; }
            else if (currentMonthIndex === 6) { isHoliday = true; currentHolidayName = "Midsummer"; }
            else if (currentMonthIndex === 8) { isHoliday = true; currentHolidayName = "Highharvestide"; }
            else if (currentMonthIndex === 10) { isHoliday = true; currentHolidayName = "Feast of the Moon"; }
            else { currentMonthIndex++; currentDay = 1; }
        }
    }
    updateDateDisplay();
}


function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active-tab'));
    document.getElementById(tabId).classList.add('active-tab');
    if (tabId === 'inventory') loadInventory();
    if (tabId === 'staff') loadStaff();
    if (tabId === 'ledger') loadLedger();
    if (tabId === 'npcs') loadNpcs();
}


function toggleHour(hourId) {
    const content = document.getElementById(`hour_content_${hourId}`);
    content.style.display = (content.style.display === 'none') ? 'block' : 'none';
}


async function rollOutcome() {
    isDayClosed = document.getElementById('is_closed').checked;
    const payload = {
        base_roll: parseInt(document.getElementById('base_roll').value) || 0,
        renown_bonus: parseInt(document.getElementById('renown_bonus').value) || 0,
        environmental_bonus: parseInt(document.getElementById('env_bonus').value) || 0,
        price_strategy: document.getElementById('price_strategy').value,
        open_hour: parseInt(document.getElementById('open_hour').value) || 12,
        close_hour: parseInt(document.getElementById('close_hour').value) || 24,
        is_closed: isDayClosed,
        current_date: { month: currentMonthIndex + 1, day: currentDay, year: currentYear, is_holiday: isHoliday, holiday_name: isHoliday ? currentHolidayName : null, is_shieldmeet: isShieldmeet }
    };
    
    const response = await fetch(`${API_URL}/roll`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    document.getElementById('outcome-result').style.display = 'block';

    if (data.is_closed) {
        document.getElementById('out-title').innerText = "TAVERN IS CLOSED FOR THE DAY";
        document.getElementById('out-sales').innerHTML = "";
        document.getElementById('out-npc-hourly').innerHTML = "";
        pendingAutoSales = [];
        return;
    }

    document.getElementById('out-title').innerText = `Simulation Results (Total Roll: ${data.total_roll})`;
    pendingAutoSales = data.auto_sales || [];
    let salesHtml = "<ul>"; let sumTotal = 0;
    pendingAutoSales.forEach(s => {
        salesHtml += `<li>${s.quantity}x ${s.item_name} = <span class="income-text">+${s.total_price.toFixed(2)} gp</span></li>`;
        sumTotal += s.total_price;
    });
    document.getElementById('out-sales').innerHTML = salesHtml + `</ul><div style="font-weight:bold;">Total: ${sumTotal.toFixed(2)} gp</div>`;

    let hourlyHtml = "";
    for (const [hour, patrons] of Object.entries(data.hourly_feedback)) {
        hourlyHtml += `<div style="padding: 5px; border-bottom: 1px solid #444;">
            <div style="cursor:pointer; color: #d7ba7d; font-weight: bold;" onclick="toggleHour('${hour}')">▶ ${hour} (${patrons.length} patrons)</div>
            <div id="hour_content_${hour}" style="display:none; padding-left: 15px; font-size: 0.85em;">${patrons.length > 0 ? patrons.join(", ") : "Empty"}</div>
        </div>`;
    }
    document.getElementById('out-npc-hourly').innerHTML = hourlyHtml;
}


async function saveDay() {
    const response = await fetch(`${API_URL}/save_day`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ calendar_date: getFormattedDate(), sales: pendingAutoSales, is_closed: isDayClosed }) });
    if (response.ok) { alert("Day Saved successfully!"); pendingAutoSales = []; document.getElementById('out-sales').innerHTML = "<em>Saved.</em>"; }
}


async function syncInventoryFromCSV() {
    const res = await fetch(`${API_URL}/inventory/sync`);
    if (res.ok) {
        alert("Inventory Re-Synced from your local CSV file!");
        loadInventory();
    }
}


async function loadInventory() {
    const res = await fetch(`${API_URL}/inventory`);
    inventoryData = await res.json();
    renderInventoryTable();
}


function renderInventoryTable() {
    const groups = {};
    inventoryData.forEach(inv => {
        let invCat = inv.category || "Uncategorized";
        if (!groups[invCat]) groups[invCat] = [];
        groups[invCat].push(inv);
    });

    let html = `
        <table style="font-size: 13px; min-width: 1400px; border-collapse: collapse; text-align: center; width: 100%;">
            <thead>
                <tr>
                    <th rowspan="2" style="width: 120px;">CATEGORY</th>
                    <th rowspan="2" style="width: 150px;">ITEM</th>
                    <th colspan="3" style="background-color: #5a3232;">ORDER BY</th>
                    <th colspan="2" style="background-color: #324a5a;">ITEMS / UNIT DETAILS</th>
                    <th rowspan="2" style="background-color: #5a3232;">COST PER ITEM</th>
                    <th rowspan="2" style="background-color: #325a3c;">SELL PRICE<br>IN COPPER</th>
                    <th rowspan="2" style="background-color: #325a3c;">MARGIN<br>IN COPPER</th>
                    <th rowspan="2" style="background-color: #324a5a;">STOCK UNIT<br>QUANTITY</th>
                    <th rowspan="2" style="background-color: #324a5a;">REORDER<br>LEVEL</th>
                    <th rowspan="2" style="background-color: #324a5a;">STATUS</th>
                    <th rowspan="2" style="background-color: #324a5a;">REORDER<br>QUANTITY</th>
                    <th rowspan="2" style="background-color: #222;">Action</th>
                </tr>
                <tr>
                    <th style="background-color: #5a3232;">UNIT</th>
                    <th style="background-color: #5a3232;">QUANTITY</th>
                    <th style="background-color: #5a3232;">UNIT COST<br>(COPPER)</th>
                    <th style="background-color: #324a5a;">QUANTITY<br>per UNIT</th>
                    <th style="background-color: #324a5a;">SERVE SIZE</th>
                </tr>
            </thead>
    `;

    for (let cat in groups) {
        html += `<tbody><tr><td colspan="15" style="background-color: #444; text-align: left; padding: 8px; font-weight: bold;">▼ ${cat.toUpperCase()}</td></tr>`;
        groups[cat].forEach(item => {
            const statusColor = (item.status === 'ORDER' || item.status === 'Order') ? '#ff4d4d' : '#4dff4d';
            html += `<tr id="inv_${item._id}">
                <td contenteditable="true" class="inv-cat" style="text-align: left; padding-left: 5px;">${item.category}</td>
                <td contenteditable="true" class="inv-name" style="text-align: left; padding-left: 5px;">${item.item_name}</td>
                <td contenteditable="true" class="inv-unit" style="background-color: rgba(90, 50, 50, 0.2);">${item.order_unit}</td>
                <td contenteditable="true" class="inv-ord-qty" style="background-color: rgba(90, 50, 50, 0.2);">${item.order_quantity}</td>
                <td contenteditable="true" class="inv-cost-cp" style="background-color: rgba(90, 50, 50, 0.2);">${item.unit_cost_copper}</td>
                <td contenteditable="true" class="inv-qty-per" style="background-color: rgba(50, 74, 90, 0.2);">${item.qty_per_unit}</td>
                <td contenteditable="true" class="inv-serve" style="background-color: rgba(50, 74, 90, 0.2);">${item.serve_size}</td>
                <td style="color: #d7ba7d; font-weight:bold;">${item.cost_per_item_copper.toFixed(2)}</td>
                <td contenteditable="true" class="inv-sell" style="background-color: rgba(50, 90, 60, 0.2); font-weight:bold;">${item.sell_price_copper}</td>
                <td style="color: #28a745; font-weight:bold;">${item.margin_copper.toFixed(2)}</td>
                <td contenteditable="true" class="inv-stock" style="font-weight:bold; font-size: 14px; background-color: rgba(50, 74, 90, 0.3);">${item.stock_unit_quantity}</td>
                <td contenteditable="true" class="inv-reorder-lvl" style="background-color: rgba(50, 74, 90, 0.2);">${item.reorder_level}</td>
                <td style="font-weight:bold; color: ${statusColor}; background-color: rgba(50, 74, 90, 0.2);">${item.status}</td>
                <td contenteditable="true" class="inv-reorder-qty" style="background-color: rgba(50, 74, 90, 0.2);">${item.reorder_quantity}</td>
                <td><button onclick="saveInventory('${item._id}')">Save</button></td>
            </tr>`;
        });
        html += `</tbody>`;
    }
    html += `</table>`;
    document.getElementById('inventory-container').innerHTML = html;
}


async function saveInventory(id) {
    const row = document.getElementById(`inv_${id}`);
    const original = inventoryData.find(i => i._id === id);
    
    const unitCost = parseFloat(row.querySelector('.inv-cost-cp').innerText) || 0;
    const qtyPerUnit = parseInt(row.querySelector('.inv-qty-per').innerText) || 1;
    const sellPrice = parseFloat(row.querySelector('.inv-sell').innerText) || 0;
    
    const costPerItem = unitCost / qtyPerUnit;
    const margin = sellPrice - costPerItem;
    const stock = parseInt(row.querySelector('.inv-stock').innerText) || 0;
    const reorderLvl = parseInt(row.querySelector('.inv-reorder-lvl').innerText) || 0;
    const status = stock <= reorderLvl ? "ORDER" : "OK";

    const payload = {
        ...original,
        category: row.querySelector('.inv-cat').innerText,
        item_name: row.querySelector('.inv-name').innerText,
        order_unit: row.querySelector('.inv-unit').innerText,
        order_quantity: parseInt(row.querySelector('.inv-ord-qty').innerText) || 1,
        unit_cost_copper: unitCost,
        qty_per_unit: qtyPerUnit,
        serve_size: row.querySelector('.inv-serve').innerText,
        cost_per_item_copper: costPerItem,
        sell_price_copper: sellPrice,
        margin_copper: margin,
        stock_unit_quantity: stock,
        reorder_level: reorderLvl,
        status: status,
        reorder_quantity: parseInt(row.querySelector('.inv-reorder-qty').innerText) || 0
    };

    await fetch(`${API_URL}/inventory/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    loadInventory();
}


async function loadStaff() {
    const res = await fetch(`${API_URL}/staff`);
    const data = await res.json();
    document.getElementById('staff-table-body').innerHTML = data.map(s => `
        <tr id="staff_${s._id}">
            <td contenteditable="true" class="st-name">${s.name}</td>
            <td contenteditable="true" class="st-wage">${s.wage}</td>
            <td><input type="text" class="st-freq" value="${s.frequency}" style="width:80px; background:#444; color:#fff; border:none; padding:4px;"></td>
            <td contenteditable="true" class="st-bonus">${s.bonus}</td>
            <td><button onclick="saveStaff('${s._id}')">Save</button></td>
        </tr>`).join('');
}


async function saveStaff(id) {
    const row = document.getElementById(`staff_${id}`);
    const payload = {
        name: row.querySelector('.st-name').innerText,
        wage: parseFloat(row.querySelector('.st-wage').innerText) || 0,
        frequency: row.querySelector('.st-freq').value,
        bonus: parseInt(row.querySelector('.st-bonus').innerText) || 0
    };
    await fetch(`${API_URL}/staff/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    alert("Staff Record Updated.");
    loadStaff();
}


async function loadNpcs() {
    const res = await fetch(`${API_URL}/npcs`);
    npcData = await res.json();
    let html = `
    <table style="font-size:12px; width:100%; border-collapse: collapse;">
        <thead>
            <tr>
                <th>First Name</th>
                <th>Last Name</th>
                <th>Occupation</th>
                <th>Lifestyle</th>
                <th>Faction</th>
                <th>Bar Disp</th>
                <th>Party Disp</th>
                <th>Noble House</th>
                <th>Story Connection</th>
                <th>PC Affiliation</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
    `;
    npcData.forEach(n => {
        html += `<tr id="npc_${n._id}">
            <td contenteditable="true" class="n-first">${n.first_name || ''}</td>
            <td contenteditable="true" class="n-last">${n.last_name || ''}</td>
            <td contenteditable="true" class="n-occ">${n.occupation || ''}</td>
            <td contenteditable="true" class="n-life">${n.lifestyle || ''}</td>
            <td contenteditable="true" class="n-fact">${n.faction || ''}</td>
            <td contenteditable="true" class="n-bar">${n.bar_disposition || 0}</td>
            <td contenteditable="true" class="n-party">${n.party_disposition || 0}</td>
            <td contenteditable="true" class="n-noble">${n.noble_house || ''}</td>
            <td contenteditable="true" class="n-story">${n.story_connection || ''}</td>
            <td contenteditable="true" class="n-pc">${n.pc_affiliation || ''}</td>
            <td><button onclick="saveNpc('${n._id}')">Save</button></td>
        </tr>`;
    });
    document.getElementById('npc-container').innerHTML = html + "</tbody></table>";
}


async function saveNpc(id) {
    const row = document.getElementById(`npc_${id}`);
    const original = npcData.find(n => n._id === id);
    const payload = {
        ...original,
        first_name: row.querySelector('.n-first').innerText,
        last_name: row.querySelector('.n-last').innerText,
        occupation: row.querySelector('.n-occ').innerText,
        lifestyle: row.querySelector('.n-life').innerText,
        faction: row.querySelector('.n-fact').innerText,
        bar_disposition: parseInt(row.querySelector('.n-bar').innerText) || 0,
        party_disposition: parseInt(row.querySelector('.n-party').innerText) || 0,
        noble_house: row.querySelector('.n-noble').innerText,
        story_connection: row.querySelector('.n-story').innerText,
        pc_affiliation: row.querySelector('.n-pc').innerText
    };
    await fetch(`${API_URL}/npcs/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    alert("NPC Directory Updated.");
    loadNpcs();
}


async function loadLedger() {
    const res = await fetch(`${API_URL}/ledger`);
    const data = await res.json();
    document.getElementById('ledger-table-body').innerHTML = data.reverse().map(l => `
        <tr>
            <td>${l.entry_date}</td>
            <td>${l.entry_type}</td>
            <td>${l.description}</td>
            <td class="${l.entry_type === 'Income' ? 'income-text' : 'expense-text'}">${l.amount}</td>
            <td>${l.frequency}</td>
            <td></td>
        </tr>
    `).join('');
}


window.onload = () => { 
    updateDateDisplay(); 
    loadInventory(); 
};