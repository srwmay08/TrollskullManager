const API_URL = "http://localhost:8000/api";

let currentYear = 1492;
let currentMonthIndex = 2;
let currentDay = 30;
let isHoliday = false;
let currentHolidayName = "";
let isShieldmeet = false;

const harptosMonths = [
    "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", 
    "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"
];

function getFormattedDate() {
    if (isShieldmeet) return `Shieldmeet, ${currentYear} DR`;
    if (isHoliday) return `${currentHolidayName}, ${currentYear} DR`;
    return `${currentDay} ${harptosMonths[currentMonthIndex]}, ${currentYear} DR`;
}

function updateDateDisplay() { 
    document.getElementById('global_date_display').innerText = getFormattedDate(); 
}

function advanceDate() {
    if (isShieldmeet) { 
        isShieldmeet = false; isHoliday = false; currentHolidayName = ""; currentMonthIndex = 7; currentDay = 1; 
    } else if (isHoliday) {
        if (currentHolidayName === "Midsummer" && (currentYear % 4 === 0)) { 
            isShieldmeet = true; currentHolidayName = "Shieldmeet"; isHoliday = true; 
        } else { 
            isHoliday = false; currentHolidayName = ""; currentMonthIndex++; currentDay = 1; 
        }
    } else {
        if (currentDay < 30) { currentDay++; } else {
            if (currentMonthIndex === 0) { isHoliday = true; currentHolidayName = "Midwinter"; }
            else if (currentMonthIndex === 3) { isHoliday = true; currentHolidayName = "Greengrass"; }
            else if (currentMonthIndex === 6) { isHoliday = true; currentHolidayName = "Midsummer"; }
            else if (currentMonthIndex === 8) { isHoliday = true; currentHolidayName = "Highharvestide"; }
            else if (currentMonthIndex === 10) { isHoliday = true; currentHolidayName = "Feast of the Moon"; }
            else { currentMonthIndex++; currentDay = 1; }
        }
    }
    updateDateDisplay();
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active-tab'));
    document.getElementById(tabId).classList.add('active-tab');
    
    // Call the specific load functions from the other modules
    if (tabId === 'inventory' && typeof loadInventory === 'function') loadInventory();
    if (tabId === 'staff' && typeof loadStaff === 'function') loadStaff();
    if (tabId === 'ledger' && typeof loadLedger === 'function') loadLedger();
    if (tabId === 'npcs' && typeof loadNpcs === 'function') loadNpcs();
}

window.onload = () => { 
    updateDateDisplay(); 
    if (typeof loadInventory === 'function') loadInventory(); 
};