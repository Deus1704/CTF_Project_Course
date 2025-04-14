// Admin Panel JavaScript

// Store admin session data
let adminData = {
    username: '',
    token: '',
    isLoggedIn: false,
    isAdmin: false
};

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const adminLoginSection = document.getElementById('admin-login-section');
    const adminDashboard = document.getElementById('admin-dashboard');
    const adminLoginForm = document.getElementById('admin-login-form');
    const adminLogoutBtn = document.getElementById('admin-logout-btn');
    const adminUsername = document.getElementById('admin-username');
    
    // Tab elements
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    // Table elements
    const usersTable = document.getElementById('users-table');
    const challengesTable = document.getElementById('challenges-table');
    const submissionsTable = document.getElementById('submissions-table');
    
    // Search inputs
    const userSearch = document.getElementById('user-search');
    const challengeSearch = document.getElementById('challenge-search');
    const submissionSearch = document.getElementById('submission-search');
    
    // Refresh buttons
    const refreshUsers = document.getElementById('refresh-users');
    const refreshChallenges = document.getElementById('refresh-challenges');
    const refreshSubmissions = document.getElementById('refresh-submissions');
    const refreshStats = document.getElementById('refresh-stats');
    
    // Add challenge button and modal
    const addChallengeBtn = document.getElementById('add-challenge');
    const addChallengeModal = document.getElementById('add-challenge-modal');
    const addChallengeForm = document.getElementById('add-challenge-form');
    const modalClose = document.querySelector('.modal-close');
    
    // Check if admin is already logged in (from localStorage)
    const savedAdmin = localStorage.getItem('ctf_admin');
    if (savedAdmin) {
        try {
            const parsedAdmin = JSON.parse(savedAdmin);
            adminData = parsedAdmin;
            if (adminData.isLoggedIn && adminData.isAdmin) {
                showAdminDashboard();
                loadAllData();
            }
        } catch (e) {
            console.error('Error parsing saved admin data:', e);
            localStorage.removeItem('ctf_admin');
        }
    }
    
    // Admin login form submission
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('admin-username-input').value;
            const password = document.getElementById('admin-password-input').value;
            
            if (username && password) {
                login(username, password);
            }
        });
    }
    
    // Admin logout button
    if (adminLogoutBtn) {
        adminLogoutBtn.addEventListener('click', function() {
            logout();
        });
    }
    
    // Tab switching
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button and corresponding pane
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Search functionality
    if (userSearch) {
        userSearch.addEventListener('input', function() {
            filterTable(usersTable, this.value);
        });
    }
    
    if (challengeSearch) {
        challengeSearch.addEventListener('input', function() {
            filterTable(challengesTable, this.value);
        });
    }
    
    if (submissionSearch) {
        submissionSearch.addEventListener('input', function() {
            filterTable(submissionsTable, this.value);
        });
    }
    
    // Refresh buttons
    if (refreshUsers) {
        refreshUsers.addEventListener('click', function() {
            loadUsers();
        });
    }
    
    if (refreshChallenges) {
        refreshChallenges.addEventListener('click', function() {
            loadChallenges();
        });
    }
    
    if (refreshSubmissions) {
        refreshSubmissions.addEventListener('click', function() {
            loadSubmissions();
        });
    }
    
    if (refreshStats) {
        refreshStats.addEventListener('click', function() {
            loadStats();
        });
    }
    
    // Add challenge modal
    if (addChallengeBtn) {
        addChallengeBtn.addEventListener('click', function() {
            if (addChallengeModal) {
                addChallengeModal.style.display = 'block';
                
                // Set default points based on difficulty
                const difficultySelect = document.getElementById('challenge-difficulty');
                const pointsInput = document.getElementById('challenge-points');
                
                if (difficultySelect && pointsInput) {
                    // Set initial value
                    updatePointsBasedOnDifficulty(difficultySelect.value, pointsInput);
                    
                    // Update when difficulty changes
                    difficultySelect.addEventListener('change', function() {
                        updatePointsBasedOnDifficulty(this.value, pointsInput);
                    });
                }
            }
        });
    }
    
    // Close modal
    if (modalClose) {
        modalClose.addEventListener('click', function() {
            if (addChallengeModal) {
                addChallengeModal.style.display = 'none';
            }
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === addChallengeModal) {
            addChallengeModal.style.display = 'none';
        }
    });
    
    // Add challenge form submission
    if (addChallengeForm) {
        addChallengeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                name: document.getElementById('challenge-name').value,
                description: document.getElementById('challenge-description').value,
                category: document.getElementById('challenge-category').value,
                difficulty: document.getElementById('challenge-difficulty').value,
                points: parseInt(document.getElementById('challenge-points').value),
                challenge_id: document.getElementById('challenge-id').value
            };
            
            addChallenge(formData);
        });
    }
    
    // Helper function to update points based on difficulty
    function updatePointsBasedOnDifficulty(difficulty, pointsInput) {
        switch (difficulty) {
            case 'easy':
                pointsInput.value = 100;
                break;
            case 'medium':
                pointsInput.value = 250;
                break;
            case 'hard':
                pointsInput.value = 500;
                break;
            default:
                pointsInput.value = 100;
        }
    }
    
    // Helper function to filter tables
    function filterTable(table, query) {
        if (!table || !query) return;
        
        const rows = table.querySelectorAll('tbody tr');
        const lowerQuery = query.toLowerCase();
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(lowerQuery)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    // API functions
    async function login(username, password) {
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Check if user is admin
                const userResponse = await fetch('/user/profile', {
                    headers: {
                        'Authorization': data.token
                    }
                });
                
                if (userResponse.ok) {
                    const userData = await userResponse.json();
                    
                    // Store admin data
                    adminData = {
                        username: data.username,
                        token: data.token,
                        isLoggedIn: true,
                        isAdmin: userData.is_admin || false
                    };
                    
                    if (adminData.isAdmin) {
                        // Save to localStorage
                        localStorage.setItem('ctf_admin', JSON.stringify(adminData));
                        
                        // Show admin dashboard
                        showAdminDashboard();
                        
                        // Load all data
                        loadAllData();
                    } else {
                        showError('You do not have admin privileges.');
                        logout();
                    }
                } else {
                    showError('Failed to get user profile.');
                }
            } else {
                showError('Login failed: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Login error:', error);
            showError('Login failed. Please try again.');
        }
    }
    
    function logout() {
        adminData = {
            username: '',
            token: '',
            isLoggedIn: false,
            isAdmin: false
        };
        
        // Remove from localStorage
        localStorage.removeItem('ctf_admin');
        
        // Show login section
        if (adminLoginSection) adminLoginSection.classList.remove('hidden');
        if (adminDashboard) adminDashboard.classList.add('hidden');
    }
    
    function showAdminDashboard() {
        if (adminLoginSection) adminLoginSection.classList.add('hidden');
        if (adminDashboard) adminDashboard.classList.remove('hidden');
        if (adminUsername) adminUsername.textContent = adminData.username;
    }
    
    function loadAllData() {
        loadUsers();
        loadChallenges();
        loadSubmissions();
        loadStats();
    }
    
    async function loadUsers() {
        try {
            const response = await fetch('/admin/users', {
                headers: {
                    'Authorization': adminData.token
                }
            });
            
            if (response.ok) {
                const users = await response.json();
                renderUsersTable(users);
                updateStats('users', users.length);
            } else {
                const data = await response.json();
                showError('Failed to load users: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error loading users:', error);
            showError('Failed to load users. Please try again.');
        }
    }
    
    async function loadChallenges() {
        try {
            const response = await fetch('/admin/challenges', {
                headers: {
                    'Authorization': adminData.token
                }
            });
            
            if (response.ok) {
                const challenges = await response.json();
                renderChallengesTable(challenges);
                updateStats('challenges', challenges.length);
                updateDifficultyChart(challenges);
                updateCategoryChart(challenges);
            } else {
                const data = await response.json();
                showError('Failed to load challenges: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error loading challenges:', error);
            showError('Failed to load challenges. Please try again.');
        }
    }
    
    async function loadSubmissions() {
        try {
            const response = await fetch('/admin/submissions', {
                headers: {
                    'Authorization': adminData.token
                }
            });
            
            if (response.ok) {
                const submissions = await response.json();
                renderSubmissionsTable(submissions);
                updateStats('submissions', submissions.length);
                updateStats('solves', submissions.filter(s => s.is_correct).length);
            } else {
                const data = await response.json();
                showError('Failed to load submissions: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error loading submissions:', error);
            showError('Failed to load submissions. Please try again.');
        }
    }
    
    async function loadStats() {
        // This function will be called by the individual data loading functions
        // to update the stats cards and charts
    }
    
    function updateStats(type, value) {
        switch (type) {
            case 'users':
                document.getElementById('total-users').textContent = value;
                break;
            case 'challenges':
                document.getElementById('total-challenges').textContent = value;
                break;
            case 'submissions':
                document.getElementById('total-submissions').textContent = value;
                break;
            case 'solves':
                document.getElementById('total-solves').textContent = value;
                break;
        }
    }
    
    function updateDifficultyChart(challenges) {
        const easy = challenges.filter(c => c.difficulty === 'easy').length;
        const medium = challenges.filter(c => c.difficulty === 'medium').length;
        const hard = challenges.filter(c => c.difficulty === 'hard').length;
        const total = challenges.length;
        
        if (total === 0) return;
        
        const easyPercent = (easy / total) * 100;
        const mediumPercent = (medium / total) * 100;
        const hardPercent = (hard / total) * 100;
        
        document.querySelector('.easy-bar').style.height = `${easyPercent}%`;
        document.querySelector('.medium-bar').style.height = `${mediumPercent}%`;
        document.querySelector('.hard-bar').style.height = `${hardPercent}%`;
    }
    
    function updateCategoryChart(challenges) {
        // Get all unique categories
        const categories = [...new Set(challenges.map(c => c.category))];
        const categoryBars = document.querySelector('.category-bars');
        
        if (!categoryBars) return;
        
        // Clear existing bars
        categoryBars.innerHTML = '';
        
        // Count challenges by category
        const categoryCounts = {};
        categories.forEach(category => {
            categoryCounts[category] = challenges.filter(c => c.category === category).length;
        });
        
        const total = challenges.length;
        
        if (total === 0) return;
        
        // Create bars for each category
        categories.forEach(category => {
            const percent = (categoryCounts[category] / total) * 100;
            
            const bar = document.createElement('div');
            bar.className = 'chart-bar';
            bar.innerHTML = `
                <div class="bar-fill ${category}-bar" style="height: ${percent}%"></div>
                <div class="bar-label">${category}</div>
            `;
            
            categoryBars.appendChild(bar);
        });
    }
    
    function renderUsersTable(users) {
        if (!usersTable) return;
        
        const tbody = usersTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        users.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email || 'N/A'}</td>
                <td>${user.points}</td>
                <td>${user.solved_challenges}</td>
                <td>${user.created_at}</td>
                <td>${user.last_login || 'Never'}</td>
                <td>${user.is_admin ? 'Yes' : 'No'}</td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn edit-btn" data-id="${user.id}">Edit</button>
                        ${!user.is_admin ? `<button class="action-btn admin-btn" data-id="${user.id}">Make Admin</button>` : ''}
                    </div>
                </td>
            `;
            
            tbody.appendChild(row);
            
            // Add event listeners for action buttons
            const makeAdminBtn = row.querySelector('.admin-btn');
            if (makeAdminBtn) {
                makeAdminBtn.addEventListener('click', function() {
                    const userId = this.getAttribute('data-id');
                    makeUserAdmin(userId);
                });
            }
        });
    }
    
    function renderChallengesTable(challenges) {
        if (!challengesTable) return;
        
        const tbody = challengesTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        challenges.forEach(challenge => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${challenge.id}</td>
                <td>${challenge.name}</td>
                <td>${challenge.category}</td>
                <td>${challenge.difficulty}</td>
                <td>${challenge.points}</td>
                <td>${challenge.solve_count}</td>
                <td><span class="status-badge ${challenge.is_active ? 'status-active' : 'status-inactive'}">${challenge.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>${challenge.created_at}</td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn edit-btn" data-id="${challenge.id}">Edit</button>
                        <button class="action-btn toggle-btn" data-id="${challenge.id}">${challenge.is_active ? 'Disable' : 'Enable'}</button>
                    </div>
                </td>
            `;
            
            tbody.appendChild(row);
            
            // Add event listeners for action buttons
            const toggleBtn = row.querySelector('.toggle-btn');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function() {
                    const challengeId = this.getAttribute('data-id');
                    toggleChallenge(challengeId);
                });
            }
        });
    }
    
    function renderSubmissionsTable(submissions) {
        if (!submissionsTable) return;
        
        const tbody = submissionsTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        submissions.forEach(submission => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${submission.id}</td>
                <td>${submission.username}</td>
                <td>${submission.challenge_name}</td>
                <td><span class="status-badge ${submission.is_correct ? 'status-correct' : 'status-incorrect'}">${submission.is_correct ? 'Correct' : 'Incorrect'}</span></td>
                <td>${submission.points_awarded}</td>
                <td>${submission.submitted_at}</td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    async function makeUserAdmin(userId) {
        try {
            const response = await fetch(`/admin/make-admin/${userId}`, {
                method: 'POST',
                headers: {
                    'Authorization': adminData.token
                }
            });
            
            if (response.ok) {
                showSuccess('User has been made an admin.');
                loadUsers();
            } else {
                const data = await response.json();
                showError('Failed to make user admin: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error making user admin:', error);
            showError('Failed to make user admin. Please try again.');
        }
    }
    
    async function toggleChallenge(challengeId) {
        try {
            const response = await fetch(`/admin/toggle-challenge/${challengeId}`, {
                method: 'POST',
                headers: {
                    'Authorization': adminData.token
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                showSuccess(`Challenge "${data.name}" is now ${data.is_active ? 'active' : 'inactive'}.`);
                loadChallenges();
            } else {
                const data = await response.json();
                showError('Failed to toggle challenge: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error toggling challenge:', error);
            showError('Failed to toggle challenge. Please try again.');
        }
    }
    
    async function addChallenge(formData) {
        try {
            const response = await fetch('/admin/add-challenge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': adminData.token
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                showSuccess('Challenge added successfully.');
                
                // Close the modal
                if (addChallengeModal) {
                    addChallengeModal.style.display = 'none';
                }
                
                // Reset the form
                if (addChallengeForm) {
                    addChallengeForm.reset();
                }
                
                // Reload challenges
                loadChallenges();
            } else {
                const data = await response.json();
                showError('Failed to add challenge: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error adding challenge:', error);
            showError('Failed to add challenge. Please try again.');
        }
    }
    
    // Notification functions
    function showSuccess(message) {
        const successMessage = document.createElement('div');
        successMessage.className = 'success-message';
        successMessage.innerHTML = `
            <div class="success-content">
                <h3>✅ Success</h3>
                <p>${message}</p>
                <button class="close-success">Close</button>
            </div>
        `;
        document.body.appendChild(successMessage);
        
        // Add close button functionality
        const closeBtn = successMessage.querySelector('.close-success');
        closeBtn.addEventListener('click', function() {
            successMessage.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (document.body.contains(successMessage)) {
                successMessage.remove();
            }
        }, 5000);
    }
    
    function showError(message) {
        const errorMessage = document.createElement('div');
        errorMessage.className = 'error-message';
        errorMessage.innerHTML = `
            <div class="error-content">
                <h3>❌ Error</h3>
                <p>${message}</p>
                <button class="close-error">Close</button>
            </div>
        `;
        document.body.appendChild(errorMessage);
        
        // Add close button functionality
        const closeBtn = errorMessage.querySelector('.close-error');
        closeBtn.addEventListener('click', function() {
            errorMessage.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (document.body.contains(errorMessage)) {
                errorMessage.remove();
            }
        }, 5000);
    }
});
