const API_URL = "http://localhost:8000/api";
let pendingAutoSales = [];
let isDayClosed = false;

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
                currentDay = 1; 
            }
        }
    }
    updateDateDisplay();
}


function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active-tab');
    });
    
    document.getElementById(tabId).classList.add('active-tab');
    
    if (tabId === 'inventory' && typeof loadInventory === 'function') {
        loadInventory();
    }
    if (tabId === 'staff' && typeof loadStaff === 'function') {
        loadStaff();
    }
    if (tabId === 'ledger' && typeof loadLedger === 'function') {
        loadLedger();
    }
    if (tabId === 'npcs' && typeof loadNpcs === 'function') {
        loadNpcs();
    }
}


function toggleHour(hourId) {
    const content = document.getElementById(`hour_content_${hourId}`);
    content.style.display = (content.style.display === 'none') ? 'block' : 'none';
}


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
    
    document.getElementById('out-sales').innerHTML = salesHtml + `</ul><div style="font-weight:bold;">Total: ${sumTotal.toFixed(2)} gp</div>`;

    let hourlyHtml = "";
    
    for (const [hour, patrons] of Object.entries(data.hourly_feedback)) {
        hourlyHtml += `<div style="padding: 5px; border-bottom: 1px solid #444;">
            <div style="cursor:pointer; color: #d7ba7d; font-weight: bold;" onclick="toggleHour('${hour}')">▶ ${hour} (${patrons.length} patrons)</div>
            <div id="hour_content_${hour}" style="display:none; padding-left: 15px; font-size: 0.85em;">${patrons.length > 0 ? patrons.join(", ") : "Empty"}</div>
        </div>`;
    }
    
    document.getElementById('out-npc-hourly').innerHTML = hourlyHtml;
}


async function saveDay() {
    const response = await fetch(`${API_URL}/save_day`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ 
            calendar_date: getFormattedDate(), 
            sales: pendingAutoSales, 
            is_closed: isDayClosed 
        }) 
    });
    
    if (response.ok) { 
        alert("Day Saved successfully!"); 
        pendingAutoSales = []; 
        document.getElementById('out-sales').innerHTML = "<em>Saved.</em>"; 
    }
}


window.onload = () => { 
    updateDateDisplay(); 
    
    if (typeof loadInventory === 'function') {
        loadInventory(); 
    }
};