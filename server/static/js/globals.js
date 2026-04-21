// Harptos Calendar State
let currentYear = 1492;
let currentMonthIndex = 2; // Ches
let currentDay = 30;
let isHoliday = false;
let currentHolidayName = "";
let isShieldmeet = false;

const harptosMonths = [
    "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", 
    "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"
];

// Expose this globally so dashboard.js can grab it for the ledger saves
window.harptos_state = {
    month: currentMonthIndex + 1,
    day: currentDay,
    year: currentYear,
    is_holiday: isHoliday,
    holiday_name: currentHolidayName,
    is_shieldmeet: isShieldmeet
};

function getFormattedDate() {
    if (isShieldmeet) return `Shieldmeet, ${currentYear} DR`;
    if (isHoliday) return `${currentHolidayName}, ${currentYear} DR`;
    return `${currentDay} ${harptosMonths[currentMonthIndex]}, ${currentYear} DR`;
}

function updateDateDisplay() { 
    const display = document.getElementById('global_date_display');
    if (display) {
        display.innerText = getFormattedDate(); 
    }
    
    // Keep the global state synced for when dashboard.js needs it
    window.harptos_state = {
        month: currentMonthIndex + 1,
        day: currentDay,
        year: currentYear,
        is_holiday: isHoliday,
        holiday_name: currentHolidayName,
        is_shieldmeet: isShieldmeet
    };
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
                isHoliday = true; currentHolidayName = "Midwinter"; 
            } else if (currentMonthIndex === 3) { 
                isHoliday = true; currentHolidayName = "Greengrass"; 
            } else if (currentMonthIndex === 6) { 
                isHoliday = true; currentHolidayName = "Midsummer"; 
            } else if (currentMonthIndex === 8) { 
                isHoliday = true; currentHolidayName = "Highharvestide"; 
            } else if (currentMonthIndex === 10) { 
                isHoliday = true; currentHolidayName = "Feast of the Moon"; 
            } else { 
                currentMonthIndex++; 
                currentDay = 1; 
            }
        }
    }
    updateDateDisplay();
}

// Restores tab navigation functionality
function switchTab(tabId) {
    // 1. Hide all tabs and remove active class
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active-tab');
        tab.style.display = 'none'; 
    });
    
    // 2. Show the target tab
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.classList.add('active-tab');
        targetTab.style.display = 'block';
    }
    
    // 3. Trigger the specific data load for the opened tab
    if (tabId === 'inventory' && typeof window.loadInventory === 'function') window.loadInventory();
    if (tabId === 'staff' && typeof window.loadStaff === 'function') window.loadStaff();
    if (tabId === 'ledger' && typeof window.loadLedger === 'function') window.loadLedger();
    if (tabId === 'npcs' && typeof window.loadNpcs === 'function') window.loadNpcs();
}

// Initialize the app state on page load
document.addEventListener('DOMContentLoaded', () => {
    updateDateDisplay();
    
    // Ensure all tabs except the active one are hidden on initial load
    document.querySelectorAll('.tab-content').forEach(tab => {
        if(!tab.classList.contains('active-tab')) {
            tab.style.display = 'none';
        } else {
            tab.style.display = 'block';
        }
    });
});