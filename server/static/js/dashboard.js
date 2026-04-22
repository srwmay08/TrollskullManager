let currentDayData = null; 
let pendingRenownChange = 0;

// Fetch current staff bonuses and map them directly to your new CSV columns
async function fetchStaffBonusDisplay() {
    try {
        const res = await fetch('/api/staff');
        if (!res.ok) return;
        const staff = await res.json();
        
        let srvBonus = 0;
        let secBonus = 0;
        
        staff.forEach(s => {
            let tempSrv = 0;
            let tempSec = 0;

            for (const key in s) {
                const cleanKey = key.toLowerCase().trim();
                // Explicitly look for your new column names
                if (cleanKey.includes('service')) {
                    tempSrv = parseInt(s[key]) || 0;
                }
                if (cleanKey.includes('security')) {
                    tempSec = parseInt(s[key]) || 0;
                }
            }
            
            srvBonus += tempSrv;
            secBonus += tempSec;
        });
        
        const srvInput = document.getElementById('staff_service_bonus');
        if (srvInput) srvInput.value = srvBonus;
        
        const secInput = document.getElementById('staff_security_bonus');
        if (secInput) secInput.value = secBonus;
        
    } catch (e) {
        console.error("Could not fetch staff bonus for dashboard.", e);
    }
}

window.fetchStaffBonusDisplay = fetchStaffBonusDisplay;

document.addEventListener('DOMContentLoaded', () => {
    fetchStaffBonusDisplay();
    
    const savedRenown = localStorage.getItem('tavern_renown');
    if (savedRenown !== null) {
        const renownInput = document.getElementById('renown_bonus');
        if (renownInput) renownInput.value = savedRenown;
    }
});

async function rollOutcome() {
    const tavernRoll = parseInt(document.getElementById('tavern_roll').value) || 0;
    const serviceRoll = parseInt(document.getElementById('service_roll').value) || 0;
    const securityRoll = parseInt(document.getElementById('security_roll').value) || 0;
    
    const rawDiceTotal = tavernRoll + serviceRoll + securityRoll;
    if (rawDiceTotal >= 110) pendingRenownChange = 3;
    else if (rawDiceTotal >= 95) pendingRenownChange = 2;
    else if (rawDiceTotal >= 80) pendingRenownChange = 1;
    else if (rawDiceTotal <= 20) pendingRenownChange = -3;
    else if (rawDiceTotal <= 30) pendingRenownChange = -2;
    else if (rawDiceTotal <= 40) pendingRenownChange = -1;
    else pendingRenownChange = 0;

    const calculatedBaseRoll = tavernRoll + serviceRoll + securityRoll;
    const renownBonus = parseInt(document.getElementById('renown_bonus').value) || 0;
    const envBonus = parseInt(document.getElementById('env_bonus').value) || 0;
    const priceStrategy = document.getElementById('price_strategy').value || "Standard";
    const openHour = parseInt(document.getElementById('open_hour').value) || 12;
    const closeHour = parseInt(document.getElementById('close_hour').value) || 24;
    const isClosed = document.getElementById('is_closed').checked;

    let currentDate = null;
    if (typeof window.harptos_state !== 'undefined') {
        currentDate = window.harptos_state;
    }

    const payload = {
        base_roll: calculatedBaseRoll,
        renown_bonus: renownBonus,
        environmental_bonus: envBonus,
        current_date: currentDate,
        price_strategy: priceStrategy,
        open_hour: openHour,
        close_hour: closeHour,
        is_closed: isClosed
    };

    try {
        const response = await fetch('/api/roll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            alert("Error simulating day. Check backend console.");
            return;
        }

        currentDayData = await response.json();
        renderDashboardOutcome(currentDayData);

    } catch (err) {
        console.error("Failed to fetch /api/roll:", err);
    }
}

function renderDashboardOutcome(data) {
    const resultContainer = document.getElementById('outcome-result');
    resultContainer.style.display = 'block';

    if (data.is_closed) {
        document.getElementById('out-gross').innerText = "0.00 gp";
        document.getElementById('out-profit').innerText = "0.00 gp";
        document.getElementById('out-sales').innerHTML = "<p>Tavern was closed today.</p>";
        document.getElementById('out-npc-hourly').innerHTML = "";
        document.getElementById('out-renown-shift').innerHTML = "";
        return;
    }

    document.getElementById('out-gross').innerText = parseFloat(data.total_gross).toFixed(2) + " gp";
    document.getElementById('out-profit').innerText = parseFloat(data.total_profit).toFixed(2) + " gp";

    document.getElementById('out-renown-shift').innerHTML = `
        <div class="summary-box" style="border-color: ${pendingRenownChange > 0 ? '#28a745' : (pendingRenownChange < 0 ? '#dc3545' : '#444')}">
            <h4>Daily Renown Shift</h4>
            <div class="value" style="color: ${pendingRenownChange > 0 ? '#28a745' : (pendingRenownChange < 0 ? '#dc3545' : '#aaa')}">
                ${pendingRenownChange > 0 ? '+' : ''}${pendingRenownChange}
            </div>
            <div style="font-size: 0.75rem; color: #888; margin-top: 5px;">Applied when day is saved.</div>
        </div>
    `;

    let salesHtml = `
        <table style="width:100%; text-align:left; border-collapse: collapse; font-size: 0.9rem;">
            <thead>
                <tr style="border-bottom: 1px solid #555; color: #aaa;">
                    <th style="padding: 5px;">Item</th>
                    <th style="padding: 5px; text-align: center;">Sold</th>
                    <th style="padding: 5px; text-align: center;">Stock (-Btls)</th>
                </tr>
            </thead>
            <tbody>`;
            
    (data.auto_sales || []).forEach(s => {
        salesHtml += `
            <tr style="border-bottom: 1px solid #333;">
                <td style="padding: 5px;">${s.item_name}</td>
                <td style="padding: 5px; text-align: center;">${s.quantity}</td>
                <td style="padding: 5px; text-align: center; color: #ff9999;">${parseFloat(s.stock_deduction).toFixed(2)}</td>
            </tr>`;
    });
    salesHtml += `</tbody></table>`;
    document.getElementById('out-sales').innerHTML = salesHtml;

    const receiptsByHour = {};
    (data.receipts || []).forEach(r => {
        if (!receiptsByHour[r.hour]) receiptsByHour[r.hour] = [];
        receiptsByHour[r.hour].push(r);
    });

    let hourlyHtml = `<div style="display:flex; flex-direction:column; gap:10px;">`;
    
    if (data.daily_events && data.daily_events.length > 0) {
        hourlyHtml += `
        <div style="border: 1px solid #856404; background: #fff3cd; border-radius: 4px; padding: 12px; margin-bottom: 10px;">
            <h4 style="margin-top:0; color: #856404; font-size: 1rem;">Daily Events & Hooks</h4>
            <ul style="margin: 0; padding-left: 20px; color: #856404; font-size: 0.9rem;">
                ${data.daily_events.map(e => `<li>${e}</li>`).join('')}
            </ul>
        </div>`;
    }

    Object.keys(data.hourly_feedback || {}).forEach((hour, idx) => {
        const patrons = data.hourly_feedback[hour] || [];
        const hourReceipts = receiptsByHour[hour] || [];
        const safeId = `hour-block-${idx}`;

        hourlyHtml += `
        <div style="border: 1px solid #444; background: #222; border-radius: 4px; overflow: hidden;">
            <div onclick="toggleHour('${safeId}')" style="padding: 12px; cursor: pointer; background: #333; display: flex; justify-content: space-between; align-items: center; user-select: none;">
                <span style="font-size: 1.1rem;"><strong style="color: #d7ba7d;">${hour}</strong> &mdash; ${patrons.length} Patrons</span>
                <span id="icon-${safeId}" style="color: #aaa;">▶</span>
            </div>
            
            <div id="${safeId}" style="display: none; padding: 15px; border-top: 1px solid #444; background: #1a1a1a;">
                <h4 style="margin-top:0; color:#bbb; font-size: 0.9rem;">Present in Tavern</h4>
                <div style="font-size: 0.85rem; color:#ccc; margin-bottom: 15px; line-height: 1.4;">
                    ${patrons.length > 0 ? patrons.join(', ') : 'Empty.'}
                </div>

                <h4 style="margin-top:0; color:#d7ba7d; border-bottom: 1px solid #444; padding-bottom: 5px; font-size: 0.9rem;">Receipts</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 10px;">
                    ${hourReceipts.length > 0 ? hourReceipts.map(r => `
                        <div style="padding: 8px; background: #2a2a2a; border-left: 3px solid #28a745; border-radius: 3px;">
                            <div style="font-size: 0.85rem; margin-bottom: 5px;">
                                <strong style="color: #fff;">${r.name}</strong> 
                                <span style="color:#888; font-size: 0.75rem;">(${r.lifestyle})</span>
                            </div>
                            ${(r.items || []).map(i => `
                                <div style="display:flex; justify-content:space-between; font-size: 0.8rem; color: #ddd;">
                                    <span>${i.qty}x ${i.name}</span>
                                    <span>${parseFloat(i.price).toFixed(2)} gp</span>
                                </div>
                            `).join('')}
                            <div style="text-align:right; font-size: 0.85rem; font-weight: bold; color:#28a745; margin-top: 5px; border-top: 1px solid #444; padding-top: 3px;">
                                ${parseFloat(r.total).toFixed(2)} gp
                            </div>
                        </div>
                    `).join('') : '<div style="font-size:0.85rem; color:#666;">No purchases this hour.</div>'}
                </div>
            </div>
        </div>`;
    });
    
    hourlyHtml += `</div>`;
    document.getElementById('out-npc-hourly').innerHTML = hourlyHtml;
}

function toggleHour(blockId) {
    const content = document.getElementById(blockId);
    const icon = document.getElementById(`icon-${blockId}`);
    if (!content) return;
    
    const isHidden = content.style.display === 'none';
    content.style.display = isHidden ? 'block' : 'none';
    if(icon) icon.innerText = isHidden ? '▼' : '▶';
}

async function saveDay() {
    if (!currentDayData) {
        alert("Please generate a day first before attempting to save.");
        return;
    }

    let dateStr = "Unknown Date";
    if (typeof window.getFormattedDate === 'function') {
        dateStr = window.getFormattedDate();
    } else {
        const displayEl = document.getElementById('global_date_display');
        if (displayEl && displayEl.innerText) dateStr = displayEl.innerText;
    }

    const validSales = (currentDayData.auto_sales || []).map(sale => {
        return {
            item_name: sale.item_name,
            original_item_name: sale.original_item_name,
            quantity: sale.quantity,
            stock_deduction: sale.stock_deduction,
            total_price: sale.total_price,
            sale_date: dateStr 
        };
    });

    const payload = {
        calendar_date: dateStr,
        sales: validSales,
        is_closed: currentDayData.is_closed || false,
        pay_wages: true,
        receipts: currentDayData.receipts || []
    };

    try {
        const response = await fetch('/api/save_day', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert("Day successfully saved to Ledger!");
            
            const currentRenown = parseInt(document.getElementById('renown_bonus').value) || 0;
            const newRenown = currentRenown + pendingRenownChange;
            localStorage.setItem('tavern_renown', newRenown);
            document.getElementById('renown_bonus').value = newRenown;
            pendingRenownChange = 0;
            
            currentDayData = null;
            document.getElementById('outcome-result').style.display = 'none';
            
            if (typeof loadLedger === 'function') loadLedger();
            if (typeof loadInventory === 'function') loadInventory();
        } else {
            alert("Failed to save the day.");
        }
    } catch (err) {
        console.error("Save Error:", err);
    }
}