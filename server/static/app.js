const API_URL = "http://localhost:8000/api";
let pendingAutoSales = [];

let npcData = [];
let npcSortCol = "first_name";
let npcSortDir = 1;
let collapsedFactions = {};

let inventoryData = [];
let invSortCol = "item_name";
let invSortDir = 1;
let collapsedInvCategories = {};

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
        isShieldmeet = false; 
        isHoliday = false; 
        currentHolidayName = ""; 
        currentMonthIndex = 7; 
        currentDay = 1; 
    } else if (isHoliday) {
        if (currentHolidayName === "Midsummer" && (currentYear % 4 === 0)) { 
            isShieldmeet = true; 
            currentHolidayName = "Shieldmeet"; 
            isHoliday = true; 
        } else { 
            isHoliday = false; 
            currentHolidayName = ""; 
            currentMonthIndex++; 
            if (currentMonthIndex > 11) { 
                currentMonthIndex = 0; 
                currentYear++; 
            } 
            currentDay = 1; 
        }
    } else {
        if (currentDay < 30) { 
            currentDay++; 
        } else {
            if (currentMonthIndex === 0) { 
                isHoliday = true; 
                currentHolidayName = "Midwinter"; 
            } else if (currentMonthIndex === 3) { 
                isHoliday = true; 
                currentHolidayName = "Greengrass"; 
            } else if (currentMonthIndex === 6) { 
                isHoliday = true; 
                currentHolidayName = "Midsummer"; 
            } else if (currentMonthIndex === 8) { 
                isHoliday = true; 
                currentHolidayName = "Highharvestide"; 
            } else if (currentMonthIndex === 10) { 
                isHoliday = true; 
                currentHolidayName = "Feast of the Moon"; 
            } else { 
                currentMonthIndex++; 
                if (currentMonthIndex > 11) { 
                    currentMonthIndex = 0; 
                    currentYear++; 
                } 
                currentDay = 1; 
            }
        }
    }
    updateDateDisplay();
}

function switchTab(tabId) {
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.classList.remove('active-tab');
    });
    
    document.getElementById(tabId).classList.add('active-tab');
    
    if (tabId === 'inventory') {
        loadInventory();
    }
    if (tabId === 'staff') {
        loadStaff();
    }
    if (tabId === 'ledger') {
        loadLedger();
    }
    if (tabId === 'npcs') {
        loadNpcs();
    }
}

function toggleHour(hourId) {
    const row = document.getElementById(hourId);
    const prevRow = row.previousElementSibling;
    
    if (row.style.display === 'table-row') {
        row.style.display = 'none';
        prevRow.cells[0].innerHTML = prevRow.cells[0].innerHTML.replace('▼', '▶');
    } else {
        row.style.display = 'table-row';
        prevRow.cells[0].innerHTML = prevRow.cells[0].innerHTML.replace('▶', '▼');
    }
}

async function adjustDisp(index, delta, type) {
    if (index < 0) {
        return;
    }
    
    const res = await fetch(`${API_URL}/npcs/disposition/adjust`, {
        method: 'PUT', 
        headers: { 
            'Content-Type': 'application/json' 
        },
        body: JSON.stringify({ 
            index: index, 
            delta: delta, 
            disp_type: type 
        })
    });
    
    if (res.ok) {
        let el = document.getElementById(`disp_${type}_${index}`);
        if (el) {
            el.innerText = parseInt(el.innerText) + delta;
        }
    }
}

async function rollOutcome() {
    const current_date_payload = { 
        month: currentMonthIndex + 1, 
        day: currentDay, 
        year: currentYear, 
        is_holiday: isHoliday, 
        holiday_name: isHoliday ? currentHolidayName : null, 
        is_shieldmeet: isShieldmeet 
    };
    
    const payload = {
        base_roll: parseInt(document.getElementById('base_roll').value),
        renown_bonus: parseInt(document.getElementById('renown_bonus').value),
        environmental_bonus: parseInt(document.getElementById('env_bonus').value),
        price_strategy: document.getElementById('price_strategy').value,
        current_date: current_date_payload
    };
    
    const response = await fetch(`${API_URL}/roll`, { 
        method: 'POST', 
        headers: { 
            'Content-Type': 'application/json' 
        }, 
        body: JSON.stringify(payload) 
    });
    
    const data = await response.json();
    
    document.getElementById('outcome-result').style.display = 'block';
    
    let staffBonus = data.staff_bonus_applied || 0;
    document.getElementById('out-title').innerText = `Roll: ${data.total_roll} (Includes +${staffBonus} Staff Bonus)`;
    
    let outcomeText = data.outcome || "Daily simulation complete.";
    document.getElementById('out-desc').innerText = outcomeText;
    
    let tablePatrons = data.table_patrons || 0;
    document.getElementById('out-tables').innerText = `${tablePatrons} / 44`;
    
    let barPatrons = data.bar_patrons || 0;
    document.getElementById('out-bar').innerText = `${barPatrons} / 10`;
    
    let vipPatrons = data.vip_patrons || 0;
    document.getElementById('out-vip').innerText = `${vipPatrons} / 10`;
    
    let standingPatrons = data.standing_patrons || 0;
    let maxStanding = data.max_standing || 0;
    document.getElementById('out-standing').innerText = `${standingPatrons} / ${maxStanding}`;

    pendingAutoSales = data.auto_sales || [];
    
    let salesHtml = "<ul>"; 
    let sumTotal = 0;
    
    if (pendingAutoSales.length === 0) {
        salesHtml += "<li>None. (No inventory to sell)</li>";
    } else {
        pendingAutoSales.forEach(s => {
            salesHtml += `<li>${s.quantity}x ${s.item_name} = <span class="income-text">+${s.total_price.toFixed(2)} gp</span></li>`;
            sumTotal += s.total_price;
        });
    }
    
    salesHtml += `</ul><div style="font-size:18px; margin-left:15px; font-weight:bold;">Tavern Gross Sales: <span class="income-text">+${sumTotal.toFixed(2)} gp</span></div>`;
    document.getElementById('out-sales').innerHTML = salesHtml;
}

async function saveDay() {
    const dateStr = getFormattedDate();
    const payload = { 
        calendar_date: dateStr, 
        sales: pendingAutoSales 
    };
    
    const response = await fetch(`${API_URL}/save_day`, { 
        method: 'POST', 
        headers: { 
            'Content-Type': 'application/json' 
        }, 
        body: JSON.stringify(payload) 
    });
    
    if (response.ok) {
        const data = await response.json();
        alert(`Day ${dateStr} saved! Inventory deducted.`);
        pendingAutoSales = [];
        document.getElementById('out-sales').innerHTML = "<em>Sales have been committed to the ledger. Inventory deducted.</em>";
    }
}

async function submitManualSale() {
    const dateStr = getFormattedDate();
    
    const payload = {
        item_name: document.getElementById('sale_item').value,
        quantity: parseInt(document.getElementById('sale_qty').value),
        total_price: parseFloat(document.getElementById('sale_price').value),
        sale_date: dateStr
    };
    
    const response = await fetch(`${API_URL}/sales`, { 
        method: 'POST', 
        headers: { 
            'Content-Type': 'application/json' 
        }, 
        body: JSON.stringify(payload) 
    });
    
    if (response.ok) {
        alert("Manual sale recorded.");
        document.getElementById('sale_item').value = ""; 
        document.getElementById('sale_price').value = "0.0";
    }
}

function calcCost(id, primaryId) {
    if (!primaryId) {
        primaryId = id;
    }
    
    const orderCost = parseFloat(document.getElementById(`inv_order_cost_${primaryId}`).value) || 0;
    const qtyPer = parseInt(document.getElementById(`inv_qty_per_${primaryId}`).value) || 1;
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

async function addInventory() {
    const payload = {
        category: document.getElementById('new_inv_cat').value,
        item_name: document.getElementById('new_inv_name').value,
        order_unit: document.getElementById('new_inv_unit').value,
        order_quantity: parseInt(document.getElementById('new_inv_order_qty').value || 1),
        unit_cost_copper: parseFloat(document.getElementById('new_inv_cost').value || 0),
        qty_per_unit: parseInt(document.getElementById('new_inv_qty_per').value || 1),
        serve_size: document.getElementById('new_inv_serve').value,
        cost_per_item_copper: 0,
        sell_price_copper: parseFloat(document.getElementById('new_inv_sell').value || 0),
        margin_copper: 0,
        stock_unit_quantity: parseInt(document.getElementById('new_inv_stock').value || 0),
        reorder_level: parseInt(document.getElementById('new_inv_reorder_lvl').value || 0),
        reorder_quantity: parseInt(document.getElementById('new_inv_reorder_qty').value || 0),
        status: "OK"
    };
    
    const costPer = payload.unit_cost_copper / payload.qty_per_unit;
    payload.cost_per_item_copper = costPer;
    payload.margin_copper = payload.sell_price_copper - costPer;
    
    const res = await fetch(`${API_URL}/inventory`, { 
        method: 'POST', 
        headers: { 
            'Content-Type': 'application/json' 
        }, 
        body: JSON.stringify(payload) 
    });
    
    if (res.ok) { 
        document.getElementById('new_inv_name').value = ""; 
        loadInventory(); 
    }
}

function sortInventory(col) {
    if (invSortCol === col) {
        invSortDir *= -1;
    } else { 
        invSortCol = col; 
        invSortDir = 1; 
    }
    renderInventory();
}

function toggleInvCategory(cat) {
    collapsedInvCategories[cat] = !collapsedInvCategories[cat];
    renderInventory();
}

function renderInventory() {
    const groups = {};
    
    inventoryData.forEach(inv => {
        let invCat = inv.category || inv['Category'] || "Uncategorized";
        if (!groups[invCat]) {
            groups[invCat] = [];
        }
        groups[invCat].push(inv);
    });

    for (let cat in groups) {
        groups[cat].sort((a, b) => {
            let valA = a.item_name || a['Item Name'] || "Unknown Item";
            let valB = b.item_name || b['Item Name'] || "Unknown Item";
            
            if (valA.toLowerCase() < valB.toLowerCase()) {
                return -1 * invSortDir;
            }
            if (valA.toLowerCase() > valB.toLowerCase()) {
                return 1 * invSortDir;
            }
            return 0;
        });
    }

    let html = `
        <table style="font-size: 13px; min-width: 1600px; border-collapse: collapse;">
            <thead>
                <tr>
                    <th rowspan="2" style="cursor:pointer; width: 140px;" onclick="sortInventory('category')">CATEGORY ⇅</th>
                    <th rowspan="2" style="cursor:pointer; width: 140px;" onclick="sortInventory('item_name')">ITEM ⇅</th>
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

    const getPId = (item) => {
        return item._id || item._csv_index || Math.random().toString(36).substring(7);
    };

    for (let cat in groups) {
        const isCollapsed = collapsedInvCategories[cat];
        let arrowIcon = isCollapsed ? '▶' : '▼';
        let groupLength = groups[cat].length;
        let safeCat = cat.replace(/'/g, "\\'");
        
        html += `
            <tbody>
                <tr onclick="toggleInvCategory('${safeCat}')">
                    <td colspan="15" class="cat-header" style="background-color: #444; padding: 10px; font-weight: bold; cursor: pointer;">
                        ${arrowIcon} ${cat.toUpperCase()} (${groupLength} Variants)
                    </td>
                </tr>
        `;
        
        if (!isCollapsed) {
            const itemsByName = {};
            
            groups[cat].forEach(item => {
                const name = item.item_name || item['Item Name'] || "Unknown Item";
                if (!itemsByName[name]) {
                    itemsByName[name] = [];
                }
                itemsByName[name].push(item);
            });

            Object.keys(itemsByName).forEach(name => {
                const variants = itemsByName[name];
                const rowspan = variants.length;
                const primaryId = getPId(variants[0]);

                variants.forEach((item, index) => {
                    const itemId = getPId(item);
                    let itemStatus = item.status || 'OK';
                    const statusColor = (itemStatus === 'ORDER' || itemStatus === 'Order') ? '#dc3545' : '#28a745';
                    
                    const itemName = item.item_name || item['Item Name'] || "Unknown Item";
                    const itemCat = item.category || item['Category'] || "Uncategorized";
                    const orderUnit = item.order_unit || "Unit";
                    const orderQty = item.order_quantity || 1;
                    const unitCost = item.unit_cost_copper || 0;
                    const qtyPer = item.qty_per_unit || item['Units Per'] || 1;
                    const serveSize = item.serve_size || "Standard";
                    const costPerItem = item.cost_per_item_copper || 0;
                    let legacyPrice = item['Unit Price'] ? item['Unit Price'] * 100 : 0;
                    const sellPrice = item.sell_price_copper || legacyPrice;
                    const margin = item.margin_copper || 0;
                    const stockQty = item.stock_unit_quantity || item['Stock on Hand'] || 0;
                    const reorderLvl = item.reorder_level || 0;
                    const reorderQty = item.reorder_quantity || 0;

                    html += `<tr>`;
                    
                    if (index === 0) {
                        html += `
                            <td rowspan="${rowspan}"><input class="editable-input" type="text" id="inv_cat_${primaryId}" value="${itemCat}" style="width: 95%;"></td>
                            <td rowspan="${rowspan}"><input class="editable-input" type="text" id="inv_name_${primaryId}" value="${itemName}" style="width: 95%;"></td>
                            <td rowspan="${rowspan}" style="background-color: rgba(107, 36, 36, 0.15); border-left: 1px solid #6b2424;"><input class="editable-input small-input" type="text" id="inv_unit_${primaryId}" value="${orderUnit}"></td>
                            <td rowspan="${rowspan}" style="background-color: rgba(107, 36, 36, 0.15);"><input class="editable-input small-input" type="number" id="inv_order_qty_${primaryId}" value="${orderQty}"></td>
                            <td rowspan="${rowspan}" style="background-color: rgba(107, 36, 36, 0.15); border-right: 1px solid #6b2424;"><input class="editable-input small-input" type="number" id="inv_order_cost_${primaryId}" value="${unitCost}" step="0.1" oninput="calcCost('${itemId}', '${primaryId}')"></td>
                            <td rowspan="${rowspan}" style="background-color: rgba(29, 75, 107, 0.2); border-left: 1px solid #1d4b6b;"><input class="editable-input small-input" type="number" id="inv_qty_per_${primaryId}" value="${qtyPer}" oninput="calcCost('${itemId}', '${primaryId}')"></td>
                        `;
                    }

                    html += `
                            <td style="background-color: rgba(29, 75, 107, 0.2); border-right: 1px solid #1d4b6b;"><input class="editable-input small-input" style="width: 80px;" type="text" id="inv_serve_${itemId}" value="${serveSize}"></td>
                            <td style="background-color: rgba(107, 36, 36, 0.3); font-weight: bold; text-align: center;"><span id="inv_cost_per_${itemId}" style="color:#d7ba7d;">${costPerItem.toFixed(2)}</span></td>
                            <td style="background-color: rgba(33, 89, 52, 0.2); border-left: 1px solid #215934;"><input class="editable-input small-input" type="number" id="inv_sell_${itemId}" value="${sellPrice}" step="0.1" oninput="calcCost('${itemId}', '${primaryId}')"></td>
                            <td style="background-color: rgba(33, 89, 52, 0.2); border-right: 1px solid #215934; font-weight: bold; text-align: center;"><span id="inv_margin_${itemId}" style="color:#28a745;">${margin.toFixed(2)}</span></td>
                            <td style="background-color: rgba(29, 75, 107, 0.2); border-left: 1px solid #1d4b6b;"><input class="editable-input small-input" type="number" id="inv_stock_${itemId}" value="${stockQty}" oninput="calcCost('${itemId}', '${primaryId}')"></td>
                            <td style="background-color: rgba(29, 75, 107, 0.2);"><input class="editable-input small-input" type="number" id="inv_reorder_lvl_${itemId}" value="${reorderLvl}" oninput="calcCost('${itemId}', '${primaryId}')"></td>
                            <td style="background-color: rgba(29, 75, 107, 0.2); font-weight: bold; text-align: center;"><span id="inv_status_${itemId}" style="color: ${statusColor};">${itemStatus}</span></td>
                            <td style="background-color: rgba(29, 75, 107, 0.2); border-right: 1px solid #1d4b6b;"><input class="editable-input small-input" type="number" id="inv_reorder_qty_${itemId}" value="${reorderQty}"></td>
                            <td><button style="width: 100%; padding: 5px;" onclick="updateInventoryItem('${itemId}', '${primaryId}')">Save</button></td>
                        </tr>
                    `;
                });
            });
        }
        html += `</tbody>`;
    }
    
    html += `</table>`;
    document.getElementById('inventory-container').innerHTML = html;
}

async function updateInventoryItem(id, primaryId) {
    if (!primaryId) {
        primaryId = id;
    }
    
    const payload = {
        category: document.getElementById(`inv_cat_${primaryId}`).value,
        item_name: document.getElementById(`inv_name_${primaryId}`).value,
        order_unit: document.getElementById(`inv_unit_${primaryId}`).value,
        order_quantity: parseInt(document.getElementById(`inv_order_qty_${primaryId}`).value),
        unit_cost_copper: parseFloat(document.getElementById(`inv_order_cost_${primaryId}`).value),
        qty_per_unit: parseInt(document.getElementById(`inv_qty_per_${primaryId}`).value),
        serve_size: document.getElementById(`inv_serve_${id}`).value,
        cost_per_item_copper: parseFloat(document.getElementById(`inv_cost_per_${id}`).innerText),
        sell_price_copper: parseFloat(document.getElementById(`inv_sell_${id}`).value),
        margin_copper: parseFloat(document.getElementById(`inv_margin_${id}`).innerText),
        stock_unit_quantity: parseInt(document.getElementById(`inv_stock_${id}`).value),
        reorder_level: parseInt(document.getElementById(`inv_reorder_lvl_${id}`).value),
        status: document.getElementById(`inv_status_${id}`).innerText,
        reorder_quantity: parseInt(document.getElementById(`inv_reorder_qty_${id}`).value)
    };
    
    const response = await fetch(`${API_URL}/inventory/${id}`, { 
        method: 'PUT', 
        headers: { 
            'Content-Type': 'application/json' 
        }, 
        body: JSON.stringify(payload) 
    });
    
    if (response.ok) {
        alert("Inventory Updated and inventory.csv Synced!");
        loadInventory();
    }
}

async function loadNpcs() {
    const response = await fetch(`${API_URL}/npcs`);
    npcData = await response.json();
    
    const tbody = document.getElementById('npc-container');
    let html = `
        <table style="font-size: 12px; width: 100%;">
            <thead>
                <tr>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Faction</th>
                    <th>Occupation</th>
                    <th>Lifestyle</th>
                    <th>Bar Disp</th>
                    <th>Party Disp</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    npcData.forEach(npc => {
        const fName = npc.first_name || npc['First Name'] || '';
        const lName = npc.last_name || npc['Last Name'] || '';
        const fact = npc.faction || npc['Affiliation'] || '';
        const occ = npc.occupation || npc['Occupation'] || '';
        const life = npc.lifestyle || npc['Lifestyle'] || '';
        const bar = npc.bar_disposition || npc['Bar Disposition'] || 0;
        const party = npc.party_disposition || npc['Party Disposition'] || 0;
        
        html += `
            <tr>
                <td><input class="editable-input" value="${fName}"></td>
                <td><input class="editable-input" value="${lName}"></td>
                <td><input class="editable-input" value="${fact}"></td>
                <td><input class="editable-input" value="${occ}"></td>
                <td><input class="editable-input" value="${life}"></td>
                <td><input class="editable-input small-input" type="number" value="${bar}"></td>
                <td><input class="editable-input small-input" type="number" value="${party}"></td>
            </tr>
        `;
    });
    
    html += `</tbody></table>`;
    tbody.innerHTML = html;
}

async function loadLedger() {
    const response = await fetch(`${API_URL}/ledger`);
    const data = await response.json();
    const tbody = document.getElementById('ledger-table-body');
    
    tbody.innerHTML = "";
    
    data.reverse().forEach(l => {
        const isIncome = l.entry_type === "Income";
        const tr = document.createElement('tr');
        
        let amountClass = isIncome ? 'income-text' : 'expense-text';
        let amountSign = isIncome ? '+' : '-';
        
        tr.innerHTML = `
            <td>${l.entry_date}</td>
            <td>${l.entry_type}</td>
            <td>${l.description}</td>
            <td class="${amountClass}">${amountSign}${l.amount}</td>
            <td>${l.frequency}</td>
            <td></td>
        `;
        
        tbody.appendChild(tr);
    });
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
            <td>${s.wage}</td>
            <td>${s.frequency}</td>
            <td>${s.bonus}</td>
            <td></td>
        `;
        tbody.appendChild(tr);
    });
}

async function loadReports() {
    const response = await fetch(`${API_URL}/reports`);
    const data = await response.json();
    
    let totalSales = 0; 
    let totalExpenses = 0; 
    let totalLedgerIncome = 0;
    
    data.sales.forEach(s => {
        totalSales += s.total_price;
    });
    
    data.ledger.forEach(l => {
        if (l.entry_type === "Income") { 
            totalLedgerIncome += l.amount; 
        } else { 
            totalExpenses += l.amount; 
        }
    });
    
    const net = (totalSales + totalLedgerIncome) - totalExpenses;
    let netColor = net >= 0 ? '#28a745' : '#dc3545';
    
    document.getElementById('report-output').innerHTML = `
        <h3>System Overview</h3>
        <p><strong>Total Recorded Bar Sales:</strong> ${totalSales.toFixed(2)} gp</p>
        <p><strong>Total Ledger Income:</strong> ${totalLedgerIncome.toFixed(2)} gp</p>
        <p><strong>Total Recorded Expenses:</strong> ${totalExpenses.toFixed(2)} gp</p>
        <p><strong>Net Vault Profit/Loss:</strong> <span style="color: ${netColor}; font-size: 18px; font-weight: bold;">${net.toFixed(2)} gp</span></p>
    `;
}

window.onload = function() {
    updateDateDisplay();
    loadInventory();
};