let npcData = [];
let npcCols = [];
let hideNobles = false;

function formatHeader(str) {
    return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

async function loadNpcs() {
    try {
        const res = await fetch('/api/npcs');
        npcData = await res.json();
        
        npcCols = [];
        npcData.forEach(row => {
            Object.keys(row).forEach(k => {
                if (k !== '_id' && !npcCols.includes(k)) npcCols.push(k);
            });
        });
        
        if (npcCols.length === 0) {
            npcCols = ["first_name", "last_name", "lifestyle"]; 
        }
        renderNpcTable();
    } catch (e) {
        console.error("Failed to load NPCs", e);
    }
}

function toggleNobles() {
    hideNobles = !hideNobles;
    renderNpcTable();
}

function renderNpcTable() {
    let html = `
    <div style="margin-bottom: 10px; display: flex; gap: 10px; align-items: center;">
        <button onclick="addNpcColumn()" style="padding: 5px 10px; background: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Column</button>
        <button onclick="addNpcRow()" style="padding: 5px 10px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Add Row</button>
        <button onclick="toggleNobles()" style="padding: 5px 10px; background: #856404; color: white; border: none; border-radius: 3px; cursor: pointer;">
            ${hideNobles ? 'Show Nobles' : 'Hide Nobles'}
        </button>
    </div>
    <div style="overflow-x: auto;">
        <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
            <thead style="background: #333; color: #d7ba7d;">
                <tr>`;
    
    npcCols.forEach((col) => {
        html += `<th style="padding: 8px; border: 1px solid #555;">${formatHeader(col)}</th>`;
    });
    html += `<th style="padding: 8px; border: 1px solid #555;">Actions</th></tr></thead><tbody>`;
    
    // Filter nobles if toggled
    let filteredData = npcData;
    if (hideNobles) {
        filteredData = npcData.filter(n => {
            const isNoble = (n.nobility_status && String(n.nobility_status).trim() !== '') || 
                            (n.noble_house && String(n.noble_house).trim() !== '') ||
                            (n.lifestyle && String(n.lifestyle).toLowerCase() === 'aristocratic');
            return !isNoble;
        });
    }

    filteredData.forEach((row, rowIndex) => {
        html += `<tr id="npc_row_${row._id || 'new_' + rowIndex}">`;
        npcCols.forEach(col => {
            let val = row[col] !== undefined && row[col] !== null ? row[col] : '';
            html += `<td contenteditable="true" data-col="${col}" style="padding: 8px; border: 1px solid #444; background: #222; color: #fff;">${val}</td>`;
        });
        html += `<td style="padding: 8px; border: 1px solid #444; background: #222; white-space: nowrap;">
            <button onclick="saveNpcRow('${row._id || ''}', this)" style="margin-right: 5px;">Save</button>
            <button onclick="deleteNpcRow('${row._id || ''}')" style="color: #ff4444; background: transparent; border: 1px solid #ff4444;">Delete</button>
        </td></tr>`;
    });
    
    html += `</tbody></table></div>`;
    
    let container = document.getElementById('npc-dynamic-container');
    if (container) container.innerHTML = html;
}

function addNpcColumn() { npcCols.push("new_column"); renderNpcTable(); }
function addNpcRow() { npcData.unshift({}); renderNpcTable(); }

async function saveNpcRow(id, btnEl) {
    const tr = btnEl.closest('tr');
    const tds = tr.querySelectorAll('td[contenteditable="true"]');
    
    const payload = {};
    tds.forEach((td) => {
        const colName = td.getAttribute('data-col');
        let val = td.innerText.trim();
        if (val.toLowerCase() === 'true') val = true;
        else if (val.toLowerCase() === 'false') val = false;
        else if (!isNaN(val) && val !== '') val = Number(val);
        if (colName) payload[colName] = val;
    });

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/npcs/${id}` : `/api/npcs`;
    
    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) loadNpcs();
    } catch (e) { console.error(e); }
}

async function deleteNpcRow(id) {
    if (!id) { loadNpcs(); return; }
    if (confirm("Delete this record permanently?")) {
        await fetch(`/api/npcs/${id}`, { method: 'DELETE' });
        loadNpcs();
    }
}

window.loadNpcs = loadNpcs;
document.addEventListener('DOMContentLoaded', loadNpcs);