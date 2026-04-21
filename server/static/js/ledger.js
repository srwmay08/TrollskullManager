let ledgerData = [];
let ledgerCols = [];

async function loadLedger() {
    try {
        const res = await fetch('/api/ledger');
        ledgerData = await res.json();
        
        ledgerCols = [];
        ledgerData.forEach(row => {
            Object.keys(row).forEach(k => {
                if (k !== '_id' && !ledgerCols.includes(k)) ledgerCols.push(k);
            });
        });
        
        if (ledgerCols.length === 0) {
            ledgerCols = ["entry_date", "entry_type", "description", "amount"]; 
        }
        renderLedgerTable();
    } catch (e) {
        console.error("Failed to load Ledger", e);
    }
}

function renderLedgerTable() {
    let html = `
    <div style="margin-bottom: 10px; display: flex; gap: 10px;">
        <button onclick="addLedgerColumn()" style="padding: 5px 10px; background: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Column</button>
        <button onclick="addLedgerRow()" style="padding: 5px 10px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Row</button>
    </div>
    <div style="overflow-x: auto;">
        <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
            <thead style="background: #333; color: #d7ba7d;">
                <tr>`;
    
    ledgerCols.forEach((col) => {
        html += `<th contenteditable="true" style="padding: 8px; border: 1px solid #555;">${col}</th>`;
    });
    html += `<th style="padding: 8px; border: 1px solid #555;">Actions</th></tr></thead><tbody>`;
    
    ledgerData.forEach((row, rowIndex) => {
        html += `<tr id="ledger_row_${row._id || 'new_' + rowIndex}">`;
        ledgerCols.forEach(col => {
            let val = row[col] !== undefined && row[col] !== null ? row[col] : '';
            html += `<td contenteditable="true" style="padding: 8px; border: 1px solid #444; background: #222; color: #fff;">${val}</td>`;
        });
        html += `<td style="padding: 8px; border: 1px solid #444; background: #222; white-space: nowrap;">
            <button onclick="saveLedgerRow('${row._id || ''}', this)" style="margin-right: 5px;">Save</button>
            <button onclick="deleteLedgerRow('${row._id || ''}')" style="color: #ff4444; background: transparent; border: 1px solid #ff4444;">Delete</button>
        </td></tr>`;
    });
    
    html += `</tbody></table></div>`;
    
    let container = document.getElementById('ledger-dynamic-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'ledger-dynamic-container';
        const tab = document.getElementById('ledger');
        const oldTable = tab.querySelector('table');
        if (oldTable) oldTable.style.display = 'none'; 
        tab.appendChild(container);
    }
    container.innerHTML = html;
}

function addLedgerColumn() { ledgerCols.push("new_column"); renderLedgerTable(); }
function addLedgerRow() { ledgerData.unshift({}); renderLedgerTable(); }

async function saveLedgerRow(id, btnEl) {
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
    const url = id ? `/api/ledger/${id}` : `/api/ledger`;
    
    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) loadLedger();
    } catch (e) { console.error(e); }
}

async function deleteLedgerRow(id) {
    if (!id) { loadLedger(); return; }
    if (confirm("Delete this record permanently?")) {
        await fetch(`/api/ledger/${id}`, { method: 'DELETE' });
        loadLedger();
    }
}

window.loadLedger = loadLedger;
document.addEventListener('DOMContentLoaded', loadLedger);