let npcData = [];

async function loadNpcs() {
    const res = await fetch(`/api/npcs`);
    npcData = await res.json();
    let html = `
    <table style="font-size:12px; width:100%; border-collapse: collapse;">
        <thead>
            <tr>
                <th>First Name</th>
                <th>Last Name</th>
                <th>Occupation</th>
                <th>Lifestyle</th>
                <th>Faction</th>
                <th>Bar Disp</th>
                <th>Party Disp</th>
                <th>Quest Giver</th>
                <th>Quest Chance</th>
                <th>Quest Hook Text</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
    `;
    npcData.forEach(n => {
        html += `<tr id="npc_${n._id}">
            <td contenteditable="true" class="n-first">${n.first_name || ''}</td>
            <td contenteditable="true" class="n-last">${n.last_name || ''}</td>
            <td contenteditable="true" class="n-occ">${n.occupation || ''}</td>
            <td contenteditable="true" class="n-life">${n.lifestyle || ''}</td>
            <td contenteditable="true" class="n-fact">${n.faction || ''}</td>
            <td contenteditable="true" class="n-bar">${n.bar_disposition || 0}</td>
            <td contenteditable="true" class="n-party">${n.party_disposition || 0}</td>
            <td><input type="checkbox" class="n-qg" ${n.is_quest_giver ? 'checked' : ''}></td>
            <td contenteditable="true" class="n-qc">${n.quest_trigger_chance || 0.05}</td>
            <td contenteditable="true" class="n-hook">${n.quest_hook_text || ''}</td>
            <td><button onclick="saveNpc('${n._id}')">Save</button></td>
        </tr>`;
    });
    html += `</tbody></table>`;
    document.getElementById('npcs-table-container').innerHTML = html;
}

async function saveNpc(id) {
    const row = document.getElementById(`npc_${id}`);
    const payload = {
        first_name: row.querySelector('.n-first').innerText.trim(),
        last_name: row.querySelector('.n-last').innerText.trim(),
        occupation: row.querySelector('.n-occ').innerText.trim(),
        lifestyle: row.querySelector('.n-life').innerText.trim(),
        faction: row.querySelector('.n-fact').innerText.trim(),
        age: 0,
        bar_disposition: parseInt(row.querySelector('.n-bar').innerText) || 0,
        party_disposition: parseInt(row.querySelector('.n-party').innerText) || 0,
        nobility_status: "",
        noble_house: "",
        story_connection: "",
        pc_affiliation: "",
        is_quest_giver: row.querySelector('.n-qg').checked,
        quest_trigger_chance: parseFloat(row.querySelector('.n-qc').innerText) || 0.0,
        quest_hook_text: row.querySelector('.n-hook').innerText.trim()
    };
    
    const response = await fetch(`/api/npcs/${id}`, { 
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (response.ok) {
        alert("NPC updated successfully.");
    } else {
        alert("Failed to update NPC.");
    }
}