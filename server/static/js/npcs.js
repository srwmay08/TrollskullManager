let npcData = [];

async function loadNpcs() {
    const res = await fetch(`${API_URL}/npcs`);
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
                <th>Noble House</th>
                <th>Story Connection</th>
                <th>PC Affiliation</th>
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
            <td contenteditable="true" class="n-noble">${n.noble_house || ''}</td>
            <td contenteditable="true" class="n-story">${n.story_connection || ''}</td>
            <td contenteditable="true" class="n-pc">${n.pc_affiliation || ''}</td>
            <td><button onclick="saveNpc('${n._id}')">Save</button></td>
        </tr>`;
    });
    document.getElementById('npc-container').innerHTML = html + "</tbody></table>";
}

async function saveNpc(id) {
    const row = document.getElementById(`npc_${id}`);
    const original = npcData.find(n => n._id === id);
    
    const payload = {
        ...original,
        first_name: row.querySelector('.n-first').innerText.trim(),
        last_name: row.querySelector('.n-last').innerText.trim(),
        occupation: row.querySelector('.n-occ').innerText.trim(),
        lifestyle: row.querySelector('.n-life').innerText.trim(),
        faction: row.querySelector('.n-fact').innerText.trim(),
        bar_disposition: parseInt(row.querySelector('.n-bar').innerText) || 0,
        party_disposition: parseInt(row.querySelector('.n-party').innerText) || 0,
        noble_house: row.querySelector('.n-noble').innerText.trim(),
        story_connection: row.querySelector('.n-story').innerText.trim(),
        pc_affiliation: row.querySelector('.n-pc').innerText.trim()
    };
    
    const response = await fetch(`${API_URL}/npcs/${id}`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(payload) 
    });
    
    if (response.ok) {
        alert("NPC Directory Updated & Synced to CSV.");
        loadNpcs();
    }
}