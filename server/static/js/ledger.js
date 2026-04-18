async function loadLedger() {
    const res = await fetch(`${API_URL}/ledger`);
    const data = await res.json();
    
    document.getElementById('ledger-table-body').innerHTML = data.reverse().map(l => {
        const amountClass = l.entry_type === 'Income' ? 'income-text' : 'expense-text';
        const sign = l.entry_type === 'Income' ? '+' : '-';
        return `
            <tr>
                <td>${l.entry_date}</td>
                <td>${l.entry_type}</td>
                <td>${l.description}</td>
                <td class="${amountClass}">${sign}${l.amount.toFixed(2)}</td>
                <td>${l.frequency}</td>
                <td></td>
            </tr>
        `;
    }).join('');
}