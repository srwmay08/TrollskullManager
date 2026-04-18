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
        pendingAutoSales = [];
        return;
    }

    document.getElementById('out-title').innerText = `Simulation Results (Total Roll: ${data.total_roll})`;
    pendingAutoSales = data.auto_sales || [];
    
    let salesHtml = "<ul>"; 
    let sumTotal = 0;
    pendingAutoSales.forEach(s => {
        salesHtml += `<li>${s.quantity}x ${s.item_name} = <span class="income-text">+${s.total_price.toFixed(2)} gp</span></li>`;
        sumTotal += s.total_price;
    });
    document.getElementById('out-sales').innerHTML = salesHtml + `</ul><div style="font-weight:bold; font-size:18px;">Total Gross: ${sumTotal.toFixed(2)} gp</div>`;

    let hourlyHtml = "";
    for (const [hour, patrons] of Object.entries(data.hourly_feedback)) {
        hourlyHtml += `
        <div style="padding: 5px; border-bottom: 1px solid #444;">
            <div style="cursor:pointer; color: #d7ba7d; font-weight: bold;" onclick="toggleHour('${hour}')">▶ ${hour} (${patrons.length} patrons)</div>
            <div id="hour_content_${hour}" style="display:none; padding-left: 15px; font-size: 0.85em; margin-top: 5px;">
                ${patrons.length > 0 ? patrons.join(", ") : "Empty"}
            </div>
        </div>`;
    }
    document.getElementById('out-npc-hourly').innerHTML = hourlyHtml;
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