async function loadStaff() {
    const res = await fetch(`${API_URL}/staff`);
    const data = await res.json();
    document.getElementById('staff-table-body').innerHTML = data.map(s => `
        <tr id="staff_${s._id}">
            <td contenteditable="true" class="st-name">${s.name}</td>
            <td contenteditable="true" class="st-wage">${s.wage}</td>
            <td>
                <select class="st-freq" style="background:#444; color:#fff; border:none; padding:4px;">
                    <option value="Daily" ${s.frequency === 'Daily' ? 'selected' : ''}>Daily</option>
                    <option value="Weekly" ${s.frequency === 'Weekly' ? 'selected' : ''}>Weekly</option>
                    <option value="Monthly" ${s.frequency === 'Monthly' ? 'selected' : ''}>Monthly</option>
                </select>
            </td>
            <td contenteditable="true" class="st-bonus">${s.bonus}</td>
            <td><button onclick="saveStaff('${s._id}')">Save</button></td>
        </tr>`).join('');
}

async function saveStaff(id) {
    const row = document.getElementById(`staff_${id}`);
    const payload = {
        name: row.querySelector('.st-name').innerText,
        wage: parseFloat(row.querySelector('.st-wage').innerText) || 0,
        frequency: row.querySelector('.st-freq').value,
        bonus: parseInt(row.querySelector('.st-bonus').innerText) || 0
    };
    
    const response = await fetch(`${API_URL}/staff/${id}`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
    });
    
    if(response.ok) {
        alert("Staff Record Updated.");
        loadStaff();
    }
}