let staffData = [];
let staffCols = [];

async function loadStaff() {
    try {
        const res = await fetch('/api/staff');
        staffData = await res.json();
        
        staffCols = [];
        staffData.forEach(row => {
            Object.keys(row).forEach(k => {
                if (k !== '_id' && !staffCols.includes(k)) staffCols.push(k);
            });
        });
        
        if (staffCols.length === 0) {
            staffCols = ["name", "role", "wage", "frequency", "bonus"]; 
        }
        renderStaffTable();
    } catch (e) {
        console.error("Failed to load Staff", e);
    }
}

function renderStaffTable() {
    let html = `
    <div style="margin-bottom: 10px; display: flex; gap: 10px;">
        <button onclick="addStaffColumn()" style="padding: 5px 10px; background: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Column</button>
        <button onclick="addStaffRow()" style="padding: 5px 10px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Row</button>
    </div>
    <div style="overflow-x: auto;">
        <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
            <thead style="background: #333; color: #d7ba7d;">
                <tr>`;
    
    staffCols.forEach((col) => {
        html += `<th contenteditable="true" style="padding: 8px; border: 1px solid #555;">${col}</th>`;
    });
    html += `<th style="padding: 8px; border: 1px solid #555;">Actions</th></tr></thead><tbody>`;
    
    staffData.forEach((row, rowIndex) => {
        html += `<tr id="staff_row_${row._id || 'new_' + rowIndex}">`;
        staffCols.forEach(col => {
            let val = row[col] !== undefined && row[col] !== null ? row[col] : '';
            html += `<td contenteditable="true" style="padding: 8px; border: 1px solid #444; background: #222; color: #fff;">${val}</td>`;
        });
        html += `<td style="padding: 8px; border: 1px solid #444; background: #222; white-space: nowrap;">
            <button onclick="saveStaffRow('${row._id || ''}', this)" style="margin-right: 5px;">Save</button>
            <button onclick="deleteStaffRow('${row._id || ''}')" style="color: #ff4444; background: transparent; border: 1px solid #ff4444;">Delete</button>
        </td></tr>`;
    });
    
    html += `</tbody></table></div>`;
    
    // Safely inject without destroying the static HTML shell
    let container = document.getElementById('staff-dynamic-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'staff-dynamic-container';
        const tab = document.getElementById('staff');
        const oldTable = tab.querySelector('table');
        if (oldTable) oldTable.style.display = 'none'; 
        tab.appendChild(container);
    }
    container.innerHTML = html;
}

function addStaffColumn() { staffCols.push("new_column"); renderStaffTable(); }
function addStaffRow() { staffData.unshift({}); renderStaffTable(); }

async function saveStaffRow(id, btnEl) {
    const tr = btnEl.closest('tr');
    const ths = tr.closest('table').querySelectorAll('th');
    const tds = tr.querySelectorAll('td[contenteditable="true"]');
    
    const payload = {};
    tds.forEach((td, idx) => {
        const colName = ths[idx].innerText.trim();
        let val = td.innerText.trim();
        if (val.toLowerCase() === 'true') val = true;
        else if (val.toLowerCase() === 'false') val = false;
        else if (!isNaN(val) && val !== '') val = Number(val);
        if (colName && colName !== "Actions") payload[colName] = val;
    });

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/staff/${id}` : `/api/staff`;
    
    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) loadStaff();
    } catch (e) { console.error(e); }
}

async function deleteStaffRow(id) {
    if (!id) { loadStaff(); return; }
    if (confirm("Delete this record permanently?")) {
        await fetch(`/api/staff/${id}`, { method: 'DELETE' });
        loadStaff();
    }
}

window.loadStaff = loadStaff;
document.addEventListener('DOMContentLoaded', loadStaff);