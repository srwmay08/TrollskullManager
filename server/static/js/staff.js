async function loadStaff() {
    const res = await fetch('/api/staff');
    const data = await res.json();
    document.getElementById('staff-table-body').innerHTML = data.map(s => `
        <tr id="staff_${s._id}">
            <td contenteditable="true" class="st-name">${s.name || ''}</td>
            <td>
                <select class="st-role" style="background:#444; color:#fff; border:none; padding:4px;">
                    <option value="General" ${s.role === 'General' ? 'selected' : ''}>General</option>
                    <option value="Bouncer" ${s.role === 'Bouncer' ? 'selected' : ''}>Bouncer</option>
                    <option value="Entertainer" ${s.role === 'Entertainer' ? 'selected' : ''}>Entertainer</option>
                    <option value="Manager" ${s.role === 'Manager' ? 'selected' : ''}>Manager</option>
                </select>
            </td>
            <td contenteditable="true" class="st-wage">${s.wage || 0}</td>
            <td>
                <select class="st-freq" style="background:#444; color:#fff; border:none; padding:4px;">
                    <option value="Daily" ${s.frequency === 'Daily' ? 'selected' : ''}>Daily</option>
                    <option value="Weekly" ${s.frequency === 'Weekly' ? 'selected' : ''}>Weekly</option>
                    <option value="Tenday" ${s.frequency === 'Tenday' ? 'selected' : ''}>Tenday</option>
                    <option value="Monthly" ${s.frequency === 'Monthly' ? 'selected' : ''}>Monthly</option>
                </select>
            </td>
            <td contenteditable="true" class="st-bonus">${s.bonus || 0}</td>
            <td><button onclick="saveStaff('${s._id}')">Save</button></td>
        </tr>`).join('');
}

async function saveStaff(id) {
    const row = document.getElementById(`staff_${id}`);
    const payload = {
        name: row.querySelector('.st-name').innerText.trim(),
        role: row.querySelector('.st-role').value,
        wage: parseFloat(row.querySelector('.st-wage').innerText) || 0.0,
        frequency: row.querySelector('.st-freq').value,
        bonus: parseInt(row.querySelector('.st-bonus').innerText) || 0
    };
    
    const response = await fetch(`/api/staff/${id}`, { 
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (response.ok) {
        alert("Staff updated successfully.");
        loadStaff();
    } else {
        alert("Failed to update staff.");
    }
}