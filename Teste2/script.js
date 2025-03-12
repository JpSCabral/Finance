        document.addEventListener('DOMContentLoaded', function() {
            // Initialize date input with today's date
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('date').value = today;
            
            // Load transactions from localStorage
            let transactions = JSON.parse(localStorage.getItem('transactions')) || [];
            
            // Update type-category connection
            const typeSelect = document.getElementById('type');
            const categorySelect = document.getElementById('category');
            
            typeSelect.addEventListener('change', function() {
                updateCategoryOptions();
            });
            
            function updateCategoryOptions() {
                const type = typeSelect.value;
                const options = categorySelect.options;
                
                for (let i = 0; i < options.length; i++) {
                    const option = options[i];
                    if (option.parentNode.label === 'Income') {
                        option.style.display = type === 'income' ? '' : 'none';
                    } else if (option.parentNode.label === 'Expense') {
                        option.style.display = type === 'expense' ? '' : 'none';
                    }
                }
                
                // Reset selection if not applicable
                if ((type === 'income' && categorySelect.value.startsWith('other-expense')) ||
                    (type === 'expense' && categorySelect.value.startsWith('other-income'))) {
                    categorySelect.value = '';
                }
            }
            
            // Transaction form submission
            const transactionForm = document.getElementById('transaction-form');
            
            transactionForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const description = document.getElementById('description').value;
                const amount = parseFloat(document.getElementById('amount').value);
                const date = document.getElementById('date').value;
                const type = document.getElementById('type').value;
                const category = document.getElementById('category').value;
                
                const transaction = {
                    id: Date.now(), // Use timestamp as unique ID
                    description,
                    amount,
                    date,
                    type,
                    category
                };
                
                transactions.push(transaction);
                saveTransactionsAndUpdateUI();
                
                // Reset form
                transactionForm.reset();
                document.getElementById('date').value = today;
            });
            
            // Filter and search functionality
            const searchInput = document.getElementById('search');
            const filterType = document.getElementById('filter-type');
            
            searchInput.addEventListener('input', renderTransactions);
            filterType.addEventListener('change', renderTransactions);
            
            // Delete transaction
            document.addEventListener('click', function(e) {
                if (e.target.classList.contains('delete-btn')) {
                    const id = parseInt(e.target.getAttribute('data-id'));
                    transactions = transactions.filter(t => t.id !== id);
                    saveTransactionsAndUpdateUI();
                }
            });
            
            function saveTransactionsAndUpdateUI() {
                // Sort transactions by date (newest first)
                transactions.sort((a, b) => new Date(b.date) - new Date(a.date));
                
                // Save to localStorage
                localStorage.setItem('transactions', JSON.stringify(transactions));
                
                // Update UI
                renderTransactions();
                updateSummary();
            }
            
            function renderTransactions() {
                const tbody = document.getElementById('transactions-body');
                const emptyState = document.getElementById('empty-state');
                const searchTerm = searchInput.value.toLowerCase();
                const filterValue = filterType.value;
                
                // Filter transactions based on search and filter
                const filteredTransactions = transactions.filter(t => {
                    const matchesSearch = t.description.toLowerCase().includes(searchTerm) || 
                                         t.category.toLowerCase().includes(searchTerm);
                    const matchesFilter = filterValue === 'all' || t.type === filterValue;
                    
                    return matchesSearch && matchesFilter;
                });
                
                // Clear table
                tbody.innerHTML = '';
                
                // Show empty state if no transactions
                if (filteredTransactions.length === 0) {
                    emptyState.style.display = 'block';
                    if (transactions.length > 0) {
                        emptyState.innerHTML = '<p>No transactions match your filters.</p>';
                    } else {
                        emptyState.innerHTML = '<p>No transactions yet. Add one to get started!</p>';
                    }
                } else {
                    emptyState.style.display = 'none';
                    
                    // Render transactions
                    filteredTransactions.forEach(t => {
                        const row = document.createElement('tr');
                        row.className = t.type === 'income' ? 'income-row' : 'expense-row';
                        
                        // Format date
                        const dateObj = new Date(t.date);
                        const formattedDate = dateObj.toLocaleDateString();
                        
                        // Format amount with sign
                        const formattedAmount = t.type === 'income' ? 
                            `+$${t.amount.toFixed(2)}` : 
                            `-$${t.amount.toFixed(2)}`;
                        
                        row.innerHTML = `
                            <td>${formattedDate}</td>
                            <td>${t.description}</td>
                            <td>${t.category || '-'}</td>
                            <td class="amount-cell ${t.type}">${formattedAmount}</td>
                            <td class="action-cell">
                                <button class="delete-btn" data-id="${t.id}">Delete</button>
                            </td>
                        `;
                        
                        tbody.appendChild(row);
                    });
                }
            }
            
            function updateSummary() {
                const totalIncome = transactions
                    .filter(t => t.type === 'income')
                    .reduce((sum, t) => sum + t.amount, 0);
                
                const totalExpenses = transactions
                    .filter(t => t.type === 'expense')
                    .reduce((sum, t) => sum + t.amount, 0);
                
                const balance = totalIncome - totalExpenses;
                
                document.getElementById('total-income').textContent = `$${totalIncome.toFixed(2)}`;
                document.getElementById('total-expenses').textContent = `$${totalExpenses.toFixed(2)}`;
                
                const balanceElement = document.getElementById('balance');
                balanceElement.textContent = `$${balance.toFixed(2)}`;
                
                // Add color based on balance
                if (balance < 0) {
                    balanceElement.style.color = '#e74c3c'; // Red for negative
                } else {
                    balanceElement.style.color = '#2ecc71'; // Green for positive
                }
            }
            
            // Initial render
            updateCategoryOptions();
            renderTransactions();
            updateSummary();
        });
