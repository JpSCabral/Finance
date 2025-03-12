function loadDashboardData() {
    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            document.querySelector('.card:nth-child(1) .amount').textContent = `$${data.balance.toFixed(2)}`;
            document.querySelector('.card:nth-child(2) .amount').textContent = `$${data.income.toFixed(2)}`;
            document.querySelector('.card:nth-child(3) .amount').textContent = `$${data.expenses.toFixed(2)}`;
            // Load charts here if you implement them
        })
        .catch(error => console.error('Error loading dashboard:', error));
}