let pendingAutoSales = [];
let isDayClosed = false;

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
        current_date: { 
            month: currentMonthIndex + 1, 
            day: currentDay, 
            year: currentYear, 
            is_holiday: isHoliday, 
            holiday_name: isHoliday ? currentHolidayName : null, 
            is_shieldmeet: isShieldmeet 
        }
    };
    
    const response = await fetch(`${API_URL}/roll`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
    });
    
    const data = await response.json();
    document.getElementById('outcome-result').style.display = 'block';

    if (data.is_closed) {
        document.getElementById('out-title').innerText = "TAVERN IS CLOSED FOR THE DAY";
        document.getElementById('out-sales').innerHTML = "";
        document.getElementById('out-npc-hourly').innerHTML = "";
        document.getElementById('out-receipts').innerHTML = "";
        document.getElementById('out-gross').innerText = "0.00 gp";
        document.getElementById('out-profit').innerText = "0.00 gp";
        pendingAutoSales = [];
        return;
    }

    document.getElementById('out-title').innerText = `Simulation Results (Total Roll: ${data.total_roll})`;
    pendingAutoSales = data.auto_sales || [];
    
    // Render Aggregate Sales
    let salesHtml = "<ul style='padding-left: 20px;'>"; 
    pendingAutoSales.forEach(s => {
        salesHtml += `<li>${s.quantity}x ${s.item_name}</li>`;
    });
    document.getElementById('out-sales').innerHTML = salesHtml + `</ul>`;

    // Render Financial Summary
    document.getElementById('out-gross').innerText = `${(data.total_gross || 0).toFixed(2)} gp`;
    
    const profitEl = document.getElementById('out-profit');
    const profit = data.total_profit || 0;
    profitEl.innerText = `${profit.toFixed(2)} gp`;
    profitEl.style.color = profit >= 0 ? '#28a745' : '#ff4d4d';

    // Render Hourly Presence
    let hourlyHtml = "";
    for (const [hour, patrons] of Object.entries(data.hourly_feedback || {})) {
        hourlyHtml += `
        <div style="padding: 5px; border-bottom: 1px solid #444;">
            <div style="cursor:pointer; color: #d7ba7d; font-weight: bold;" onclick="toggleHour('${hour}')">▶ ${hour} (${patrons.length} patrons)</div>
            <div id="hour_content_${hour}" style="display:none; padding-left: 15px; font-size: 0.85em; margin-top: 5px;">
                ${patrons.length > 0 ? patrons.join(", ") : "Empty"}
            </div>
        </div>`;
    }
    document.getElementById('out-npc-hourly').innerHTML = hourlyHtml;

    // Render Individual Receipts
    let receiptsHtml = "";
    if (data.receipts && data.receipts.length > 0) {
        data.receipts.forEach(r => {
            receiptsHtml += `<div style="border: 1px solid #444; padding: 10px; margin-bottom: 10px; background: #111; border-radius: 4px;">`;
            receiptsHtml += `<strong style="color: #d7ba7d; font-size: 14px;">${r.name}</strong> <span style="color: #aaa; font-size: 12px;">(${r.lifestyle}) - ${r.hour}</span><br/>`;
            receiptsHtml += `<ul style="margin: 5px 0; padding-left: 20px; font-size: 0.9em; list-style-type: square;">`;
            r.items.forEach(i => {
                receiptsHtml += `<li>${i.qty}x ${i.name} = ${(i.price).toFixed(2)} gp</li>`;
            });
            receiptsHtml += `</ul>`;
            receiptsHtml += `<div style="text-align: right; margin-top: 5px; border-top: 1px dashed #444; padding-top: 5px;"><strong>Total Paid: <span class="income-text">${r.total.toFixed(2)} gp</span></strong></div>`;
            receiptsHtml += `</div>`;
        });
    } else {
        receiptsHtml = "<p style='color: #aaa;'>No patrons bought items. Ensure your inventory has stock > 0.</p>";
    }
    document.getElementById('out-receipts').innerHTML = receiptsHtml;
}

async function saveDay() {
    const payload = { 
        calendar_date: getFormattedDate(), 
        sales: pendingAutoSales, 
        is_closed: isDayClosed 
    };

    const response = await fetch(`${API_URL}/save_day`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
    });
    
    if (response.ok) { 
        alert("Day Saved successfully! Inventory and Ledger have been updated."); 
        pendingAutoSales = []; 
        document.getElementById('out-sales').innerHTML = "<em>Sales committed to ledger.</em>"; 
    }
}