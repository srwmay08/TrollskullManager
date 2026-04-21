let inventoryData = [];
let inventoryCols = [];

// Helper to clean up DB keys for display
function formatHeader(str) {
    return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

async function loadInventory() {
    try {
        const res = await fetch('/api/inventory');
        inventoryData = await res.json();
        
        inventoryCols = [];
        inventoryData.forEach(row => {
            Object.keys(row).forEach(k => {
                if (k !== '_id' && !inventoryCols.includes(k)) inventoryCols.push(k);
            });
        });
        
        if (inventoryCols.length === 0) {
            inventoryCols = ["category", "item_name", "stock_bottle_quantity", "sell_price_serving_copper"]; 
        }
        renderInventoryTable();
    } catch (e) {
        console.error("Failed to load Inventory", e);
    }
}

function renderInventoryTable() {
    let html = `
    <div style="margin-bottom: 10px; display: flex; gap: 10px;">
        <button onclick="addInventoryColumn()" style="padding: 5px 10px; background: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Column</button>
        <button onclick="addInventoryRow()" style="padding: 5px 10px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Row</button>
    </div>
    <div style="overflow-x: auto;">
        <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;">
            <thead style="background: #333; color: #d7ba7d;">
                <tr>`;
    
    // Display clean headers
    inventoryCols.forEach((col) => {
        html += `<th style="padding: 8px; border: 1px solid #555; white-space: nowrap;">${formatHeader(col)}</th>`;
    });
    html += `<th style="padding: 8px; border: 1px solid #555;">Actions</th></tr></thead><tbody>`;
    
    // Group items by category
    const categories = [...new Set(inventoryData.map(item => item.category || 'Uncategorized'))].sort();

    categories.forEach(cat => {
        // Add Category Header Row
        html += `<tr style="background-color: #444;">
                    <td colspan="${inventoryCols.length + 1}" style="padding: 10px; font-weight: bold; color: #d7ba7d; border: 1px solid #555; text-transform: uppercase;">
                        Category: ${cat}
                    </td>
                 </tr>`;
        
        const catItems = inventoryData.filter(i => (i.category || 'Uncategorized') === cat);
        
        catItems.forEach((row, rowIndex) => {
            html += `<tr id="inv_row_${row._id || 'new_' + rowIndex}">`;
            inventoryCols.forEach(col => {
                let val = row[col] !== undefined && row[col] !== null ? row[col] : '';
                // Decouple data display from the JSON key via data-col attribute
                html += `<td contenteditable="true" data-col="${col}" style="padding: 8px; border: 1px solid #444; background: #222; color: #fff;">${val}</td>`;
            });
            html += `<td style="padding: 8px; border: 1px solid #444; background: #222; white-space: nowrap;">
                <button onclick="saveInventoryRow('${row._id || ''}', this)" style="margin-right: 5px;">Save</button>
                <button onclick="deleteInventoryRow('${row._id || ''}')" style="color: #ff4444; background: transparent; border: 1px solid #ff4444;">Delete</button>
            </td></tr>`;
        });
    });
    
    html += `</tbody></table></div>`;
    
    let container = document.getElementById('inventory-dynamic-container');
    if (container) container.innerHTML = html;
}

function addInventoryColumn() { inventoryCols.push("new_column"); renderInventoryTable(); }
function addInventoryRow() { inventoryData.unshift({ category: 'Uncategorized' }); renderInventoryTable(); }

async function saveInventoryRow(id, btnEl) {
    const tr = btnEl.closest('tr');
    const tds = tr.querySelectorAll('td[contenteditable="true"]');
    
    const payload = {};
    tds.forEach((td) => {
        const colName = td.getAttribute('data-col'); // Use raw DB key
        let val = td.innerText.trim();
        if (val.toLowerCase() === 'true') val = true;
        else if (val.toLowerCase() === 'false') val = false;
        else if (!isNaN(val) && val !== '') val = Number(val);
        if (colName) payload[colName] = val;
    });

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/inventory/${id}` : `/api/inventory`;
    
    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) loadInventory();
    } catch (e) { console.error(e); }
}

async function deleteInventoryRow(id) {
    if (!id) { loadInventory(); return; }
    if (confirm("Delete this record permanently?")) {
        await fetch(`/api/inventory/${id}`, { method: 'DELETE' });
        loadInventory();
    }
}

window.loadInventory = loadInventory;
document.addEventListener('DOMContentLoaded', loadInventory);