function displayTransactions(transactions) {
    const tbody = document.querySelector('table tbody');
    tbody.innerHTML = ''; // Clear existing rows
    
    transactions.forEach(transaction => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(transaction.date).toLocaleDateString()}</td>
            <td>${transaction.description}</td>
            <td>${transaction.category}</td>
            <td><span class="transaction-type ${transaction.type}">${transaction.type}</span></td>
            <td class="${transaction.type === 'income' ? 'positive' : 'negative'}">$${transaction.amount.toFixed(2)}</td>
            <td>
                <button class="btn btn-primary" onclick="editTransaction(${transaction.id})">Edit</button>
                <button class="btn btn-danger" onclick="deleteTransaction(${transaction.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}