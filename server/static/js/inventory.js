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
        <div style="overflow-x: auto; width: 100%;">
            <table style="font-size: 0.85rem; min-width: 1300px; border-collapse: collapse; text-align: center; width: 100%;">
                <thead>
                    <tr style="border-bottom: 2px solid #555;">
                        <th rowspan="2" style="width: 250px; text-align: left; padding-left: 15px;">PRODUCT</th>
                        <th colspan="3" style="background-color: #4a2a2a; border-right: 1px solid #666;">WHOLESALE UNIT</th>
                        <th colspan="2" style="background-color: #2a3a4a; border-right: 1px solid #666;">STOCK UNIT (BOTTLE)</th>
                        <th colspan="3" style="background-color: #2a4a2a; border-right: 1px solid #666;">RETAIL SERVING</th>
                        <th rowspan="2" style="background-color: #222;">STOCK LEVEL</th>
                        <th rowspan="2" style="background-color: #222;">REORDER</th>
                        <th rowspan="2" style="background-color: #222;">STATUS</th>
                        <th rowspan="2" style="background-color: #222;">ACTION</th>
                    </tr>
                    <tr style="font-size: 0.75rem; border-bottom: 2px solid #555;">
                        <th style="background-color: #4a2a2a;">NAME</th>
                        <th style="background-color: #4a2a2a;">BTL/UNIT</th>
                        <th style="background-color: #4a2a2a;">COST (cp)</th>
                        <th style="background-color: #2a3a4a;">SRV/BTL</th>
                        <th style="background-color: #2a3a4a;">BTL SELL</th>
                        <th style="background-color: #2a4a2a;">SIZE</th>
                        <th style="background-color: #2a4a2a;">SRV SELL</th>
                        <th style="background-color: #2a4a2a;">MARGIN</th>
                    </tr>
                </thead>
    `;

    for (let cat in groups) {
        const safeCat = cat.replace(/\s+/g, '-');
        html += `<tbody class="cat-group">`;
        html += `<tr class="cat-header" onclick="toggleCategory('${safeCat}')" style="cursor: pointer; user-select: none;">
                    <td colspan="14" style="background-color: #333; text-align: left; padding: 12px; font-weight: bold; color: #d7ba7d; letter-spacing: 1px; border-bottom: 1px solid #444;">
                        <span id="icon_${safeCat}" style="margin-right: 10px;">▼</span> ${cat.toUpperCase()}
                    </td>
                 </tr>`;
        
        groups[cat].forEach(item => {
            const statusColor = (item.status === 'ORDER') ? '#ff4d4d' : '#4dff4d';
            const stockColor = (item.stock_bottle_quantity <= item.reorder_level_bottles) ? '#ff9999' : '#fff';
            
            html += `<tr id="inv_${item._id}" class="cat-row-${safeCat}" style="border-bottom: 1px solid #444; height: 40px;">
                <td contenteditable="true" class="inv-name" style="text-align: left; padding-left: 15px; font-weight: 600;">${item.item_name}</td>
                <td contenteditable="true" class="inv-unit-name" style="color: #bbb;">${item.order_unit}</td>
                <td contenteditable="true" class="inv-bottles-per-unit">${item.bottles_per_order_unit}</td>
                <td contenteditable="true" class="inv-cost-unit" style="font-family: monospace;">${item.unit_cost_copper}</td>
                <td contenteditable="true" class="inv-servings-per-bottle">${item.servings_per_bottle}</td>
                <td contenteditable="true" class="inv-sell-bottle" style="color: #d7ba7d;">${item.sell_price_bottle_copper}</td>
                <td contenteditable="true" class="inv-serve-size" style="color: #bbb;">${item.serve_size}</td>
                <td contenteditable="true" class="inv-sell-serve" style="font-weight:bold;">${item.sell_price_serving_copper}</td>
                <td style="color: #28a745; font-weight:bold;">${item.margin_serving_copper.toFixed(0)}</td>
                <td contenteditable="true" class="inv-stock-bottles" style="font-weight:bold; font-size: 1.1rem; color: ${stockColor}">${item.stock_bottle_quantity.toFixed(1)}</td>
                <td contenteditable="true" class="inv-reorder-lvl">${item.reorder_level_bottles}</td>
                <td style="font-weight:bold; color: ${statusColor};">${item.status}</td>
                <td><button onclick="saveInventory('${item._id}')" style="padding: 4px 10px; cursor: pointer; background: #444; color: #fff; border: 1px solid #666; border-radius: 3px;">Save</button></td>
            </tr>`;
        });
        html += `</tbody>`;
    }
    html += `</table></div>`;
    document.getElementById('inventory-container').innerHTML = html;
}

function toggleCategory(safeCat) {
    const rows = document.querySelectorAll(`.cat-row-${safeCat}`);
    const icon = document.getElementById(`icon_${safeCat}`);
    let isHidden = false;
    
    if (rows.length > 0) {
        isHidden = rows[0].style.display === 'none';
    }

    rows.forEach(row => {
        row.style.display = isHidden ? '' : 'none';
    });

    if (icon) {
        icon.innerText = isHidden ? '▼' : '▶';
    }
}

async function saveInventory(id) {
    const row = document.getElementById(`inv_${id}`);
    const original = inventoryData.find(i => i._id === id);
    
    const costPerOrderUnit = parseFloat(row.querySelector('.inv-cost-unit').innerText) || 0;
    const bottlesPerUnit = parseInt(row.querySelector('.inv-bottles-per-unit').innerText) || 1;
    const servingsPerBottle = parseInt(row.querySelector('.inv-servings-per-bottle').innerText) || 1;
    const sellPriceServe = parseFloat(row.querySelector('.inv-sell-serve').innerText) || 0;
    const stockBottles = parseFloat(row.querySelector('.inv-stock-bottles').innerText) || 0;
    const reorderLvl = parseInt(row.querySelector('.inv-reorder-lvl').innerText) || 0;
    
    const costPerBottle = costPerOrderUnit / bottlesPerUnit;
    const costPerServing = costPerBottle / servingsPerBottle;
    const marginServing = sellPriceServe - costPerServing;
    
    let status = (stockBottles <= reorderLvl) ? "ORDER" : "OK";
    
    // Maintain hidden values like target_restock from the original object
    const payload = {
        ...original,
        item_name: row.querySelector('.inv-name').innerText,
        order_unit: row.querySelector('.inv-unit-name').innerText,
        bottles_per_order_unit: bottlesPerUnit,
        unit_cost_copper: costPerOrderUnit,
        servings_per_bottle: servingsPerBottle,
        serve_size: row.querySelector('.inv-serve-size').innerText,
        cost_per_serving_copper: costPerServing,
        sell_price_serving_copper: sellPriceServe,
        sell_price_bottle_copper: parseFloat(row.querySelector('.inv-sell-bottle').innerText) || 0,
        margin_serving_copper: marginServing,
        stock_bottle_quantity: stockBottles,
        reorder_level_bottles: reorderLvl,
        status: status
    };

    const response = await fetch(`${API_URL}/inventory/${id}`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
    });
    
    if (response.ok) {
        loadInventory();
    }
}