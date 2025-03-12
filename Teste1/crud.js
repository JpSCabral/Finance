function editTransaction(id) {
    fetch(`/api/transactions/${id}`)
        .then(response => response.json())
        .then(data => {
            // Populate the form with existing data
            document.getElementById('date').value = data.date;
            document.getElementById('description').value = data.description;
            // ... populate other fields
            
            modal.style.display = 'flex';
        })
        .catch(error => console.error('Error fetching transaction details:', error));
}

function deleteTransaction(id) {
    if (confirm('Are you sure you want to delete this transaction?')) {
        fetch(`/api/transactions/${id}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                alert('Transaction deleted successfully!');
                fetchTransactions(); // Refresh the list
                loadDashboardData(); // Update dashboard numbers
            }
        })
        .catch(error => console.error('Error deleting transaction:', error));
    }
}