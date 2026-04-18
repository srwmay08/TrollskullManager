let inventoryData = [];

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

    const response = await fetch(`${API_URL}/inventory/${id}`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
    });
    
    if (response.ok) {
        alert("Inventory item saved successfully.");
        loadInventory();
    }
}