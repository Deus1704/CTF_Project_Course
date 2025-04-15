// Main JavaScript for CTF platform

// Store user session data
let userData = {
    username: '',
    token: '',
    isLoggedIn: false,
    points: 0,
    user_id: null
};

// DOM elements
document.addEventListener('DOMContentLoaded', function() {
    // Handle celebration overlay if it exists
    const celebrationOverlay = document.getElementById('celebration-overlay');
    const closeCelebrationBtn = document.getElementById('close-celebration');

    if (celebrationOverlay) {
        console.log('Celebration overlay found, showing celebration effects');

        // Play success sound
        playSuccessSound();

        // Show confetti
        createConfetti();

        // Add event listener to close button
        if (closeCelebrationBtn) {
            closeCelebrationBtn.addEventListener('click', function() {
                celebrationOverlay.style.display = 'none';

                // If we have challenge data, show the challenge dialog
                if (typeof serverData !== 'undefined' && serverData.challengeId) {
                    console.log('Showing solved challenge dialog with points:', serverData.pointsEarned);
                    setTimeout(() => {
                        showSolvedChallengeDialog(serverData.challengeId, serverData.containerId, serverData.pointsEarned, serverData.challengeName);
                    }, 500);
                }
            });
        }
    }
    // Auth elements
    const loginForm = document.getElementById('login-form');
    const logoutBtn = document.getElementById('logout-btn');
    const authSection = document.getElementById('auth-section');
    const challengeSection = document.getElementById('challenge-section');
    const welcomeMessage = document.getElementById('welcome-message');
    const challengeList = document.getElementById('challenge-list');
    const showProfileBtn = document.getElementById('show-profile-btn');
    const showLeaderboardBtn = document.getElementById('show-leaderboard-btn');
    const userProfileSection = document.getElementById('user-profile');
    const leaderboardSection = document.getElementById('leaderboard');
    const categoryFilter = document.getElementById('category-filter');
    const difficultyFilter = document.getElementById('difficulty-filter');
    const backToChallengesBtn = document.getElementById('back-to-challenges');
    const challengeDetails = document.getElementById('challenge-details');

    // Check if user is already logged in (from localStorage)
    const savedUser = localStorage.getItem('ctf_user');
    if (savedUser) {
        try {
            userData = JSON.parse(savedUser);
            if (userData.token) {
                showLoggedInState();
                loadChallenges();

                // Check if we need to auto-show a challenge (from flag submission redirect)
                if (typeof serverData !== 'undefined' && serverData.autoShow && serverData.challengeId && serverData.containerId) {
                    // Wait a bit for challenges to load
                    setTimeout(() => {
                        showSolvedChallengeDialog(serverData.challengeId, serverData.containerId, serverData.pointsEarned, serverData.challengeName);
                    }, 500);
                }
            }
        } catch (e) {
            console.error('Error parsing saved user data', e);
            localStorage.removeItem('ctf_user');
        }
    }

    // Login form submission
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            login(username, password);
        });
    }

    // Logout button
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            logout();
        });
    }

    // Show profile button
    if (showProfileBtn) {
        showProfileBtn.addEventListener('click', function() {
            // Hide other sections
            if (leaderboardSection) leaderboardSection.classList.add('hidden');

            // Hide challenge list and header
            if (challengeList) challengeList.classList.add('hidden');
            const challengesHeader = document.querySelector('.challenges-header');
            if (challengesHeader) challengesHeader.classList.add('hidden');

            // Show profile section
            if (userProfileSection) {
                userProfileSection.classList.remove('hidden');
                loadUserProfile();
            }
        });
    }

    // Show leaderboard button
    if (showLeaderboardBtn) {
        showLeaderboardBtn.addEventListener('click', function() {
            // Hide other sections
            if (userProfileSection) userProfileSection.classList.add('hidden');
            if (challengeList) challengeList.parentElement.classList.add('hidden');

            // Show leaderboard section
            if (leaderboardSection) {
                leaderboardSection.classList.remove('hidden');
                loadLeaderboard();
            }
        });
    }

    // Category filter
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            filterChallenges();
        });
    }

    // Back to challenges button
    if (backToChallengesBtn) {
        backToChallengesBtn.addEventListener('click', function() {
            // Hide profile section
            if (userProfileSection) userProfileSection.classList.add('hidden');
            if (leaderboardSection) leaderboardSection.classList.add('hidden');

            // Show challenges
            const challengesHeader = document.querySelector('.challenges-header');
            if (challengesHeader) challengesHeader.classList.remove('hidden');
            if (challengeList) challengeList.classList.remove('hidden');
        });
    }

    // Difficulty filter
    if (difficultyFilter) {
        difficultyFilter.addEventListener('change', function() {
            filterChallenges();
        });
    }

    // Function to filter challenges
    function filterChallenges() {
        const category = categoryFilter ? categoryFilter.value : 'all';
        const difficulty = difficultyFilter ? difficultyFilter.value : 'all';

        // Show all challenge categories first
        const categories = document.querySelectorAll('.challenge-category');
        categories.forEach(cat => {
            cat.style.display = 'block';
        });

        // Filter by category
        if (category !== 'all') {
            categories.forEach(cat => {
                const categoryTitle = cat.querySelector('.category-title');
                if (categoryTitle && categoryTitle.textContent.toLowerCase() !== category.toUpperCase()) {
                    cat.style.display = 'none';
                }
            });
        }

        // Filter by difficulty
        if (difficulty !== 'all') {
            const allCards = document.querySelectorAll('.challenge-card');
            allCards.forEach(card => {
                if (!card.classList.contains(`difficulty-${difficulty}`)) {
                    card.style.display = 'none';
                } else {
                    card.style.display = 'block';
                }
            });
        } else {
            // Reset all cards to visible
            const allCards = document.querySelectorAll('.challenge-card');
            allCards.forEach(card => {
                card.style.display = 'block';
            });
        }
    }

    // Helper functions
    function showLoggedInState() {
        userData.isLoggedIn = true;
        if (authSection) authSection.classList.add('hidden');
        if (challengeSection) challengeSection.classList.remove('hidden');
        if (welcomeMessage) {
            welcomeMessage.innerHTML = `
                <span>Welcome, ${userData.username}!</span>
                <span class="user-points-container">Points: <span id="user-points">${userData.points}</span></span>
            `;
        }

        // Save to localStorage
        localStorage.setItem('ctf_user', JSON.stringify(userData));
    }

    // Function to show success message with confetti effect
    function showSuccessMessage(message) {
        // Create success message element
        const successMessage = document.createElement('div');
        successMessage.className = 'success-message';
        successMessage.innerHTML = `
            <div class="success-content">
                <div class="trophy-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path>
                        <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path>
                        <path d="M4 22h16"></path>
                        <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path>
                        <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path>
                        <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path>
                    </svg>
                </div>
                <h3>🎉 Challenge Solved! 🎉</h3>
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

        // Auto-remove after 8 seconds
        setTimeout(() => {
            if (document.body.contains(successMessage)) {
                successMessage.remove();
            }
        }, 8000);

        // Create confetti effect
        createConfetti();
    }

    // Function to show info message
    function showInfoMessage(message) {
        const infoMessage = document.createElement('div');
        infoMessage.className = 'info-message';
        infoMessage.innerHTML = `
            <div class="info-content">
                <h3>ℹ️ Information</h3>
                <p>${message}</p>
                <button class="close-info">Close</button>
            </div>
        `;
        document.body.appendChild(infoMessage);

        // Add close button functionality
        const closeBtn = infoMessage.querySelector('.close-info');
        closeBtn.addEventListener('click', function() {
            infoMessage.remove();
        });

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (document.body.contains(infoMessage)) {
                infoMessage.remove();
            }
        }, 5000);
    }

    // Function to play success sound
    function playSuccessSound() {
        try {
            const audio = new Audio();
            audio.src = '/static/sounds/success.mp3';
            audio.volume = 0.5;
            audio.play();
        } catch (e) {
            console.error('Error playing sound:', e);
        }
    }

    // Function to create enhanced celebration effect
    function showCelebration() {
        // Create celebration container
        const celebrationContainer = document.createElement('div');
        celebrationContainer.className = 'celebration-container';
        document.body.appendChild(celebrationContainer);

        // Create fireworks
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                createFirework(celebrationContainer);
            }, i * 300);
        }

        // Remove celebration after animation completes
        setTimeout(() => {
            celebrationContainer.remove();
        }, 4000);
    }

    // Function to create a firework
    function createFirework(container) {
        const firework = document.createElement('div');
        firework.className = 'firework';

        // Random position
        firework.style.left = Math.random() * 80 + 10 + '%';
        firework.style.top = Math.random() * 40 + 10 + '%';

        // Random color
        const hue = Math.floor(Math.random() * 360);
        firework.style.setProperty('--firework-color', `hsl(${hue}, 100%, 50%)`);

        container.appendChild(firework);

        // Create particles for explosion
        setTimeout(() => {
            createParticles(firework);
            firework.remove();
        }, 300);
    }

    // Function to create particles for firework explosion
    function createParticles(firework) {
        const rect = firework.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;

        const container = firework.parentElement;
        const hue = getComputedStyle(firework).getPropertyValue('--firework-color');

        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = x + 'px';
            particle.style.top = y + 'px';
            particle.style.backgroundColor = hue;

            // Random direction and speed
            const angle = Math.random() * Math.PI * 2;
            const speed = Math.random() * 3 + 2;
            particle.style.setProperty('--angle', angle);
            particle.style.setProperty('--speed', speed);

            container.appendChild(particle);

            // Remove particle after animation
            setTimeout(() => {
                particle.remove();
            }, 1000);
        }
    }

    // Function to create confetti effect
    function createConfetti() {
        const confettiCount = 100;
        const container = document.createElement('div');
        container.className = 'confetti-container';
        document.body.appendChild(container);

        for (let i = 0; i < confettiCount; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.animationDelay = Math.random() * 3 + 's';
            confetti.style.backgroundColor = `hsl(${Math.random() * 360}, 100%, 50%)`;
            container.appendChild(confetti);
        }

        // Remove confetti after animation completes
        setTimeout(() => {
            container.remove();
        }, 6000);
    }

    // Function to load user profile
    async function loadUserProfile() {
        try {
            const response = await fetch('/user/profile', {
                headers: {
                    'Authorization': userData.token
                }
            });

            if (response.ok) {
                const profile = await response.json();
                userData.points = profile.points;

                // Update points display
                const pointsDisplay = document.getElementById('user-points');
                if (pointsDisplay) {
                    pointsDisplay.textContent = profile.points;
                }

                // Get the user profile container
                const userProfileContainer = document.getElementById('user-profile');
                if (userProfileContainer) {
                    // Show the profile section
                    userProfileContainer.classList.remove('hidden');

                    // Hide other sections
                    const leaderboardContainer = document.getElementById('leaderboard');
                    if (leaderboardContainer) leaderboardContainer.classList.add('hidden');

                    const challengesHeader = document.querySelector('.challenges-header');
                    if (challengesHeader) challengesHeader.classList.add('hidden');

                    const challengeList = document.getElementById('challenge-list');
                    if (challengeList) challengeList.classList.add('hidden');
                }

                // Update solved challenges display
                const solvedChallengesContainer = document.getElementById('solved-challenges');
                if (solvedChallengesContainer) {
                    if (profile.solved_challenges && profile.solved_challenges.length > 0) {
                        solvedChallengesContainer.innerHTML = `
                            <div class="profile-section-header">
                                <h3>Solved Challenges</h3>
                                <span class="badge">${profile.solved_challenges.length}</span>
                            </div>
                            <div class="profile-section-content">
                                <ul class="solved-challenges-list"></ul>
                            </div>
                        `;

                        const list = solvedChallengesContainer.querySelector('.solved-challenges-list');
                        profile.solved_challenges.forEach(challenge => {
                            const item = document.createElement('li');
                            item.className = `difficulty-${challenge.difficulty}`;
                            item.innerHTML = `
                                <div class="challenge-info">
                                    <span class="challenge-name">${challenge.name}</span>
                                    <span class="challenge-category">${challenge.category}</span>
                                </div>
                                <span class="challenge-points">${challenge.points} pts</span>
                            `;
                            list.appendChild(item);
                        });
                    } else {
                        solvedChallengesContainer.innerHTML = `
                            <div class="profile-section-header">
                                <h3>Solved Challenges</h3>
                                <span class="badge">0</span>
                            </div>
                            <div class="profile-section-content empty-state">
                                <p>You haven't solved any challenges yet. Start solving to earn points!</p>
                            </div>
                        `;
                    }
                }

                // Update recent submissions display
                const recentSubmissionsContainer = document.createElement('div');
                recentSubmissionsContainer.className = 'recent-submissions';

                if (profile.recent_submissions && profile.recent_submissions.length > 0) {
                    recentSubmissionsContainer.innerHTML = `
                        <div class="profile-section-header">
                            <h3>Recent Submissions</h3>
                            <span class="badge">${profile.recent_submissions.length}</span>
                        </div>
                        <div class="profile-section-content">
                            <ul class="submissions-list"></ul>
                        </div>
                    `;

                    const list = recentSubmissionsContainer.querySelector('.submissions-list');
                    profile.recent_submissions.forEach(submission => {
                        const item = document.createElement('li');
                        item.className = submission.is_correct ? 'correct' : 'incorrect';
                        item.innerHTML = `
                            <div class="submission-info">
                                <span class="submission-challenge">${submission.challenge_name}</span>
                                <span class="submission-date">${submission.submitted_at}</span>
                            </div>
                            <span class="submission-status ${submission.is_correct ? 'correct' : 'incorrect'}">
                                ${submission.is_correct ?
                                    `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>` :
                                    `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`
                                }
                                ${submission.is_correct ? `+${submission.points_awarded} pts` : ''}
                            </span>
                        `;
                        list.appendChild(item);
                    });
                } else {
                    recentSubmissionsContainer.innerHTML = `
                        <div class="profile-section-header">
                            <h3>Recent Submissions</h3>
                            <span class="badge">0</span>
                        </div>
                        <div class="profile-section-content empty-state">
                            <p>No recent submissions. Try submitting a flag!</p>
                        </div>
                    `;
                }

                // Add recent submissions to the profile
                if (userProfileContainer) {
                    // Remove old recent submissions if exists
                    const oldRecentSubmissions = userProfileContainer.querySelector('.recent-submissions');
                    if (oldRecentSubmissions) {
                        oldRecentSubmissions.remove();
                    }

                    // Add new recent submissions
                    userProfileContainer.appendChild(recentSubmissionsContainer);
                }

                // Update achievements display if it exists
                const achievementsContainer = document.getElementById('achievements');
                if (achievementsContainer) {
                    if (profile.achievements && profile.achievements.length > 0) {
                        achievementsContainer.innerHTML = `
                            <div class="profile-section-header">
                                <h3>Achievements</h3>
                                <span class="badge">${profile.achievements.length}</span>
                            </div>
                            <div class="profile-section-content">
                                <ul class="achievements-list"></ul>
                            </div>
                        `;

                        const list = achievementsContainer.querySelector('.achievements-list');
                        profile.achievements.forEach(achievement => {
                            const item = document.createElement('li');
                            item.innerHTML = `
                                <div class="achievement-icon">
                                    ${achievement.badge_image ?
                                        `<img src="${achievement.badge_image}" alt="${achievement.name}">` :
                                        `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>`
                                    }
                                </div>
                                <div class="achievement-info">
                                    <span class="achievement-name">${achievement.name}</span>
                                    <span class="achievement-description">${achievement.description}</span>
                                </div>
                                <span class="achievement-points">+${achievement.points} pts</span>
                            `;
                            list.appendChild(item);
                        });
                    } else {
                        achievementsContainer.innerHTML = `
                            <div class="profile-section-header">
                                <h3>Achievements</h3>
                                <span class="badge">0</span>
                            </div>
                            <div class="profile-section-content empty-state">
                                <p>No achievements yet. Complete challenges to earn achievements!</p>
                            </div>
                        `;
                    }
                }

                // Add user stats summary
                const userStatsSummary = document.createElement('div');
                userStatsSummary.className = 'user-stats-summary';
                userStatsSummary.innerHTML = `
                    <div class="stats-card">
                        <div class="stats-icon points-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="8" x2="12" y2="16"></line>
                                <line x1="8" y1="12" x2="16" y2="12"></line>
                            </svg>
                        </div>
                        <div class="stats-info">
                            <h4>Total Points</h4>
                            <p>${profile.points}</p>
                        </div>
                    </div>
                    <div class="stats-card">
                        <div class="stats-icon solved-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="9 11 12 14 22 4"></polyline>
                                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                            </svg>
                        </div>
                        <div class="stats-info">
                            <h4>Solved</h4>
                            <p>${profile.solved_challenges ? profile.solved_challenges.length : 0}</p>
                        </div>
                    </div>
                    <div class="stats-card">
                        <div class="stats-icon rank-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                            </svg>
                        </div>
                        <div class="stats-info">
                            <h4>Rank</h4>
                            <p id="user-rank">Loading...</p>
                        </div>
                    </div>
                `;

                // Add user stats to the profile
                if (userProfileContainer) {
                    // Remove old stats if exists
                    const oldStats = userProfileContainer.querySelector('.user-stats-summary');
                    if (oldStats) {
                        oldStats.remove();
                    }

                    // Add new stats at the beginning
                    userProfileContainer.insertBefore(userStatsSummary, userProfileContainer.firstChild);
                }

                // Get user rank from leaderboard
                loadLeaderboardForRank();
            }
        } catch (error) {
            console.error('Error loading user profile:', error);
        }
    }

    // Function to show a solved challenge dialog
    function showSolvedChallengeDialog(challengeId, containerId, pointsEarned, challengeName) {
        const modal = document.getElementById('challenge-modal');
        const challengeDetails = document.getElementById('challenge-details');

        if (!challengeDetails || !modal) return;

        // Show the modal
        modal.style.display = 'block';

        // Get challenge details if name is not provided
        if (!challengeName) {
            const challengeCard = document.querySelector(`.challenge-card[data-id="${challengeId}"]`);
            if (challengeCard) {
                const nameEl = challengeCard.querySelector('h3');
                if (nameEl) challengeName = nameEl.textContent;

                // Mark the challenge as solved in the UI
                challengeCard.classList.add('solved');
                const statusBadge = challengeCard.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.textContent = 'SOLVED';
                    statusBadge.classList.remove('active');
                    statusBadge.classList.add('solved');
                }
            }
        }

        // Create the solved challenge content
        challengeDetails.innerHTML = `
            <div id="challenge-content" class="challenge-content solved">
                <div class="challenge-header-bar">
                    <div class="challenge-title-area">
                        <h2>${challengeName || challengeId}</h2>
                        <span class="challenge-difficulty-badge">Completed</span>
                    </div>
                    <div class="challenge-status">
                        <span class="status-badge solved">SOLVED</span>
                    </div>
                </div>

                <div class="challenge-solved-content">
                    <div class="success-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                    </div>
                    <h3>Challenge Completed!</h3>
                    <p>Congratulations! You've successfully solved this challenge.</p>
                    <div class="points-earned">+${pointsEarned} points</div>
                    <div class="challenge-status-info">
                        <div class="status-icon success">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <span>Challenge container has been closed</span>
                    </div>
                </div>

                <div class="challenge-controls">
                    <button id="close-solved-challenge" class="btn-primary">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                        Close
                    </button>
                </div>
            </div>
        `;

        // Add event listener to close button
        const closeBtn = document.getElementById('close-solved-challenge');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                modal.style.display = 'none';
            });
        }

        // Play success sound and show celebration
        playSuccessSound();
        showCelebration();

        // Update user profile and leaderboard
        loadUserProfile();
        loadLeaderboard();
    }

    // Function to load leaderboard just to get user rank
    async function loadLeaderboardForRank() {
        try {
            const response = await fetch('/leaderboard');
            const leaderboardData = await response.json();

            // Find user's rank
            const userRank = leaderboardData.findIndex(user => user.username === userData.username) + 1;

            // Update rank display
            const rankDisplay = document.getElementById('user-rank');
            if (rankDisplay) {
                if (userRank > 0) {
                    rankDisplay.textContent = `#${userRank}`;
                } else {
                    rankDisplay.textContent = 'N/A';
                }
            }
        } catch (error) {
            console.error('Error loading leaderboard for rank:', error);
        }
    }

    // Function to load leaderboard
    async function loadLeaderboard() {
        try {
            const response = await fetch('/leaderboard');
            const leaderboardData = await response.json();

            const leaderboardContainer = document.getElementById('leaderboard');
            if (leaderboardContainer) {
                leaderboardContainer.innerHTML = '<h3>Leaderboard</h3>';

                if (leaderboardData.length === 0) {
                    leaderboardContainer.innerHTML += '<p>No entries yet. Be the first to solve a challenge!</p>';
                    return;
                }

                const table = document.createElement('table');
                table.className = 'leaderboard-table';
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Username</th>
                            <th>Points</th>
                            <th>Solved</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                `;

                const tbody = table.querySelector('tbody');

                leaderboardData.forEach((user, index) => {
                    const row = document.createElement('tr');
                    row.className = user.username === userData.username ? 'current-user' : '';
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${user.username}</td>
                        <td>${user.points}</td>
                        <td>${user.solved_challenges}</td>
                    `;
                    tbody.appendChild(row);
                });

                leaderboardContainer.appendChild(table);
            }
        } catch (error) {
            console.error('Error loading leaderboard:', error);
        }
    }

    function showLoggedOutState() {
        userData = {
            username: '',
            token: '',
            isLoggedIn: false
        };
        if (authSection) authSection.classList.remove('hidden');
        if (challengeSection) challengeSection.classList.add('hidden');
        if (welcomeMessage) welcomeMessage.textContent = '';

        // Clear localStorage
        localStorage.removeItem('ctf_user');
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
                userData.username = data.username;
                userData.token = data.token;
                userData.points = data.points;
                userData.user_id = data.user_id;
                showLoggedInState();
                loadChallenges();
                loadUserProfile();
            } else {
                alert('Login failed: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Login failed. Please try again.');
        }
    }

    function logout() {
        showLoggedOutState();
    }

    async function loadChallenges() {
        try {
            // Fetch challenges from the server
            const response = await fetch('/challenges');
            const challengesData = await response.json();

            // Fetch user's solved challenges
            const userProfileResponse = await fetch('/user/profile', {
                headers: {
                    'Authorization': userData.token
                }
            });
            const userProfile = await userProfileResponse.json();

            // Create a set of solved challenge IDs for quick lookup
            const solvedChallengeIds = new Set();
            if (userProfile.solved_challenges && userProfile.solved_challenges.length > 0) {
                userProfile.solved_challenges.forEach(challenge => {
                    solvedChallengeIds.add(challenge.id);
                });
            }

            // Process challenges based on response format
            let challenges = [];

            if (Array.isArray(challengesData) && challengesData.length > 0) {
                // Check if we have full challenge objects or just IDs
                if (typeof challengesData[0] === 'string') {
                    // We have challenge IDs, map them to objects
                    const challengeDescriptions = {
                        'web-basic': 'A basic web exploitation challenge',
                        'crypto-101': 'Introduction to cryptography challenges',
                        'forensics-pcap': 'Network traffic analysis challenge',
                        'forensics-stego': 'Steganography challenge',
                        'forensics-carving': 'File carving and analysis challenge',
                        'reverse-engineering': 'Binary reverse engineering challenge',
                        'web-sqli': 'SQL injection challenge'
                    };

                    challenges = challengesData.map(id => ({
                        id: id,
                        name: id.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
                        description: challengeDescriptions[id] || 'A CTF challenge',
                        category: id.split('-')[0] || 'misc',
                        difficulty: 'medium',
                        points: 100,
                        solved: solvedChallengeIds.has(id)
                    }));
                } else {
                    // We have full challenge objects
                    challenges = challengesData.map(challenge => ({
                        id: challenge.id,
                        name: challenge.name,
                        description: challenge.description,
                        category: challenge.category,
                        difficulty: challenge.difficulty,
                        points: challenge.points,
                        solved: solvedChallengeIds.has(challenge.id)
                    }));
                }
            }

            // Clear existing challenges
            if (challengeList) {
                challengeList.innerHTML = '';

                if (challenges.length === 0) {
                    challengeList.innerHTML = '<p>No challenges available. Please check back later.</p>';
                    return;
                }

                // Group challenges by category
                const categorizedChallenges = {};
                challenges.forEach(challenge => {
                    if (!categorizedChallenges[challenge.category]) {
                        categorizedChallenges[challenge.category] = [];
                    }
                    categorizedChallenges[challenge.category].push(challenge);
                });

                // Create category sections
                Object.keys(categorizedChallenges).forEach(category => {
                    const categorySection = document.createElement('div');
                    categorySection.className = 'challenge-category';
                    categorySection.innerHTML = `
                        <h2 class="category-title">${category.toUpperCase()}</h2>
                        <div class="category-challenges"></div>
                    `;
                    challengeList.appendChild(categorySection);

                    const categoryContainer = categorySection.querySelector('.category-challenges');

                    // Add challenges for this category
                    categorizedChallenges[category].forEach(challenge => {
                        const challengeCard = document.createElement('div');
                        challengeCard.className = `challenge-card difficulty-${challenge.difficulty} ${challenge.solved ? 'solved' : ''}`;
                        challengeCard.setAttribute('data-id', challenge.id);

                        // Create the HTML content with solved status
                        challengeCard.innerHTML = `
                            <div class="challenge-header">
                                <h3>${challenge.name}</h3>
                                <span class="challenge-points">${challenge.points} pts</span>
                            </div>
                            <div class="challenge-difficulty">${challenge.difficulty}</div>
                            ${challenge.solved ? '<span class="status-badge solved">SOLVED</span>' : ''}
                            <p>${challenge.description}</p>
                            <button class="start-challenge-btn" data-id="${challenge.id}">
                                ${challenge.solved ? 'View Challenge' : 'Start Challenge'}
                            </button>
                        `;
                        categoryContainer.appendChild(challengeCard);

                        // Add event listener to the button
                        const startBtn = challengeCard.querySelector('.start-challenge-btn');
                        startBtn.addEventListener('click', function() {
                            startChallenge(challenge.id);
                        });
                    });
                });
            }
        } catch (error) {
            console.error('Error loading challenges:', error);
            if (challengeList) {
                challengeList.innerHTML = '<p>Error loading challenges. Please try again later.</p>';
            }
        }
    }

    async function startChallenge(challengeId) {
        try {
            console.log(`Starting challenge ${challengeId}`);
            // Show the modal immediately with a loading message
            const modal = document.getElementById('challenge-modal');
            const challengeDetails = document.getElementById('challenge-details');

            if (challengeDetails && modal) {
                modal.style.display = 'block';
                challengeDetails.innerHTML = `
                    <div class="challenge-content loading-state">
                        <div class="loading-spinner"></div>
                        <h2>Starting Challenge...</h2>
                        <p>Please wait while we set up your challenge environment.</p>
                        <div class="setup-steps">
                            <div class="setup-step" id="step-building">Building container...</div>
                            <div class="setup-step" id="step-starting">Starting container...</div>
                            <div class="setup-step" id="step-configuring">Configuring challenge...</div>
                        </div>
                    </div>
                `;

                // Simulate progress for better UX
                setTimeout(() => {
                    document.getElementById('step-building').classList.add('completed');
                }, 800);
                setTimeout(() => {
                    document.getElementById('step-starting').classList.add('completed');
                }, 1600);
                setTimeout(() => {
                    document.getElementById('step-configuring').classList.add('completed');
                }, 2400);
            }

            const response = await fetch(`/challenge/${challengeId}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': userData.token
                },
                body: JSON.stringify({
                    user: userData.username
                })
            });

            const data = await response.json();
            console.log('Challenge start response:', data);

            if (response.ok) {
                // Get challenge details for better UI
                let challengeName = challengeId;
                let challengeDescription = '';
                let challengeDifficulty = 'medium';

                try {
                    // Try to find the challenge card to get more details
                    const challengeCard = document.querySelector(`.challenge-card[data-id="${challengeId}"]`);
                    if (challengeCard) {
                        const nameEl = challengeCard.querySelector('h3');
                        const descEl = challengeCard.querySelector('p');
                        const difficultyEl = challengeCard.querySelector('.challenge-difficulty');

                        if (nameEl) challengeName = nameEl.textContent;
                        if (descEl) challengeDescription = descEl.textContent;
                        if (difficultyEl) challengeDifficulty = difficultyEl.textContent.toLowerCase();
                    }
                } catch (e) {
                    console.error('Error getting challenge details:', e);
                }

                // Add challenge details to the data
                data.challengeName = challengeName;
                data.challengeDescription = challengeDescription;
                data.difficulty = challengeDifficulty;

                showChallengeDetails(challengeId, data);
            } else {
                showErrorMessage('Failed to start challenge: ' + (data.error || 'Unknown error'));
                // Close the modal if there was an error
                if (modal) {
                    modal.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Challenge start error:', error);
            showErrorMessage('Failed to start challenge. Please try again.');
            // Close the modal if there was an error
            const modal = document.getElementById('challenge-modal');
            if (modal) {
                modal.style.display = 'none';
            }
        }
    }

    // Function to show error message
    function showErrorMessage(message) {
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

    function showChallengeDetails(challengeId, data) {
        const modal = document.getElementById('challenge-modal');
        const challengeDetails = document.getElementById('challenge-details');

        if (challengeDetails && modal) {
            // Show the modal immediately
            modal.style.display = 'block';

            // Get difficulty class for styling
            const difficultyClass = data.difficulty ? `difficulty-${data.difficulty}` : '';

            // Check if challenge is already solved
            const solvedClass = data.already_solved ? 'solved' : '';

            challengeDetails.innerHTML = `
                <div id="challenge-content" class="challenge-content ${difficultyClass} ${solvedClass}">
                    <div class="challenge-header-bar">
                        <div class="challenge-title-area">
                            <h2>${data.challengeName || challengeId}</h2>
                            <span class="challenge-difficulty-badge">${data.difficulty || 'medium'}</span>
                        </div>
                        <div class="challenge-status">
                            <span class="status-badge ${data.already_solved ? 'solved' : 'active'}">${data.already_solved ? 'SOLVED' : 'ACTIVE'}</span>
                        </div>
                    </div>

                    <div class="challenge-description">
                        <p>${data.challengeDescription || 'No description available.'}</p>
                    </div>

                    <div class="challenge-connection-info">
                        <h3>Connection Information</h3>
                        <div class="connection-details">
                            <div class="connection-item">
                                <span class="connection-label">Port:</span>
                                <span class="connection-value">${data.port}</span>
                            </div>
                            <div class="connection-item">
                                <span class="connection-label">URL:</span>
                                <span class="connection-value">
                                    <a href="http://localhost:${data.port}" target="_blank" class="challenge-link">
                                        http://localhost:${data.port}
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                            <polyline points="15 3 21 3 21 9"></polyline>
                                            <line x1="10" y1="14" x2="21" y2="3"></line>
                                        </svg>
                                    </a>
                                </span>
                            </div>
                            <div class="connection-item">
                                <span class="connection-label">Container ID:</span>
                                <span class="connection-value monospace">${data.containerId.substring(0, 12)}</span>
                            </div>
                        </div>
                    </div>

                    <div id="timeout-info" class="timeout-info">
                        <h3>Challenge Timer</h3>
                        <p>This challenge will automatically expire in <span id="countdown" class="countdown">10:00</span></p>
                        <div class="progress-bar">
                            <div id="time-remaining" style="width: 100%;"></div>
                        </div>
                    </div>

                    <div class="flag-submission">
                        <h3>Submit Flag</h3>
                        <div class="flag-input-group">
                            <input type="text" id="flag-input" placeholder="Enter flag here (e.g., flag{...})">
                            <button id="submit-flag" class="btn-primary">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <polyline points="9 10 4 15 9 20"></polyline>
                                    <path d="M20 4v7a4 4 0 0 1-4 4H4"></path>
                                </svg>
                                Submit
                            </button>
                        </div>
                    </div>

                    <div class="challenge-controls">
                        <button id="stop-challenge" class="btn-danger" data-container="${data.containerId}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <rect x="9" y="9" width="6" height="6"></rect>
                            </svg>
                            Stop Challenge
                        </button>
                    </div>
                </div>

                <div id="challenge-expired" class="challenge-expired-message">
                    <div class="expired-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                    </div>
                    <h3>Challenge Expired</h3>
                    <p>Your challenge session has ended. The container has been automatically stopped.</p>
                    <p>If you'd like to try again, you can start a new challenge session.</p>
                    <div class="challenge-expired-actions">
                        <button class="btn-restart" id="restart-challenge" data-challenge="${challengeId}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
                            </svg>
                            Start New Session
                        </button>
                        <button class="btn-close" id="close-expired-challenge">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                            Close
                        </button>
                    </div>
                </div>
            `;

            // Close button functionality
            const closeBtn = document.querySelector('.modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    modal.style.display = 'none';
                    // Stop any running timers
                    if (window.statusCheckInterval) clearInterval(window.statusCheckInterval);
                    if (window.localTimerInterval) clearInterval(window.localTimerInterval);
                });
            }

            // Close when clicking outside the modal
            window.addEventListener('click', function(event) {
                if (event.target === modal) {
                    modal.style.display = 'none';
                    // Stop any running timers
                    if (window.statusCheckInterval) clearInterval(window.statusCheckInterval);
                    if (window.localTimerInterval) clearInterval(window.localTimerInterval);
                }
            });

            // For demo purposes, we'll just check if the flag matches
            const submitBtn = document.getElementById('submit-flag');
            const flagInput = document.getElementById('flag-input');
            const stopBtn = document.getElementById('stop-challenge');
            const countdownEl = document.getElementById('countdown');
            const progressBar = document.getElementById('time-remaining');

            // Start the countdown timer
            if (countdownEl && progressBar && data.timeout && data.startTime) {
                startCountdownTimer(countdownEl, progressBar, data.timeout, new Date(data.startTime));
            }

            if (submitBtn && flagInput) {
                submitBtn.addEventListener('click', async function() {
                    const submittedFlag = flagInput.value.trim();

                    // Disable the submit button to prevent multiple submissions
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = `
                        <div class="loading-spinner-small"></div>
                        Submitting...
                    `;

                    try {
                        const response = await fetch('/submit-flag-main', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': userData.token
                            },
                            body: JSON.stringify({
                                flag: submittedFlag,
                                challenge_id: challengeId,
                                container_id: data.containerId
                            })
                        });

                        const result = await response.json();

                        if (response.ok) {
                            if (result.success) {
                                // Update user points in UI
                                if (result.points_earned > 0) {
                                    userData.points += result.points_earned;
                                    // Update points display
                                    const pointsDisplay = document.getElementById('user-points');
                                    if (pointsDisplay) {
                                        pointsDisplay.textContent = userData.points;
                                    }

                                    // Play success sound
                                    playSuccessSound();

                                    // Show celebration animation
                                    showCelebration();

                                    // Show success message with confetti effect
                                    showSuccessMessage(result.message);

                                    // Update the challenge UI to show it's been solved
                                    const challengeContent = document.getElementById('challenge-content');
                                    const statusBadge = document.querySelector('.status-badge');

                                    if (challengeContent) {
                                        challengeContent.classList.add('solved');
                                    }

                                    if (statusBadge) {
                                        statusBadge.textContent = 'SOLVED';
                                        statusBadge.classList.remove('active');
                                        statusBadge.classList.add('solved');
                                    }

                                    // Stop the challenge container after a short delay
                                    setTimeout(() => {
                                        stopChallenge(data.containerId, true);
                                    }, 3000);

                                    // Update the leaderboard and user profile
                                    loadLeaderboard();
                                    loadUserProfile();
                                } else {
                                    // Already solved
                                    showInfoMessage(result.message);
                                }
                            } else {
                                // Incorrect flag
                                showErrorMessage(result.message);

                                // Re-enable the submit button
                                submitBtn.disabled = false;
                                submitBtn.innerHTML = `
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <polyline points="9 10 4 15 9 20"></polyline>
                                        <path d="M20 4v7a4 4 0 0 1-4 4H4"></path>
                                    </svg>
                                    Submit
                                `;
                            }
                        } else {
                            showErrorMessage('Error submitting flag: ' + (result.error || 'Unknown error'));

                            // Re-enable the submit button
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = `
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <polyline points="9 10 4 15 9 20"></polyline>
                                    <path d="M20 4v7a4 4 0 0 1-4 4H4"></path>
                                </svg>
                                Submit
                            `;
                        }
                    } catch (error) {
                        console.error('Error submitting flag:', error);
                        showErrorMessage('Error submitting flag. Please try again.');

                        // Re-enable the submit button
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = `
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="9 10 4 15 9 20"></polyline>
                                <path d="M20 4v7a4 4 0 0 1-4 4H4"></path>
                            </svg>
                            Submit
                        `;
                    }
                });
            }

            if (stopBtn) {
                stopBtn.addEventListener('click', function() {
                    const containerId = this.getAttribute('data-container');
                    stopChallenge(containerId);
                });
            }

            // Add event listener for the restart button
            const restartBtn = document.getElementById('restart-challenge');
            if (restartBtn) {
                restartBtn.addEventListener('click', function() {
                    const challengeId = this.getAttribute('data-challenge');
                    if (challengeId) {
                        // Hide the expired message
                        const challengeExpired = document.getElementById('challenge-expired');
                        if (challengeExpired) {
                            challengeExpired.style.display = 'none';
                        }

                        // Start a new challenge session
                        startChallenge(challengeId);
                    }
                });
            }

            // Add event listener for the close button in expired message
            const closeExpiredBtn = document.getElementById('close-expired-challenge');
            if (closeExpiredBtn) {
                closeExpiredBtn.addEventListener('click', function() {
                    modal.style.display = 'none';
                    // Stop any running timers
                    if (window.statusCheckInterval) clearInterval(window.statusCheckInterval);
                    if (window.localTimerInterval) clearInterval(window.localTimerInterval);
                });
            }
        }
    }

    function startCountdownTimer(countdownEl, progressBar, timeout, startTime) {
        let containerId = null;
        let statusCheckInterval = null;
        let localTimerInterval = null;
        let lastRemainingSeconds = timeout;

        // Find the container ID from the stop button
        const stopBtn = document.getElementById('stop-challenge');
        if (stopBtn) {
            containerId = stopBtn.getAttribute('data-container');
        }

        // Function to update the UI based on remaining time
        const updateUI = (remainingSeconds) => {
            // Update countdown text
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = remainingSeconds % 60;
            countdownEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

            // Update progress bar
            const percentRemaining = (remainingSeconds / timeout) * 100;
            progressBar.style.width = `${percentRemaining}%`;

            // Change color as time runs out
            if (percentRemaining < 25) {
                progressBar.style.backgroundColor = '#d9534f'; // Red
            } else if (percentRemaining < 50) {
                progressBar.style.backgroundColor = '#f0ad4e'; // Yellow
            }

            // If time is up, show the expired message
            if (remainingSeconds <= 0 && lastRemainingSeconds > 0) {
                countdownEl.textContent = 'Expired';
                progressBar.style.width = '0%';

                // Show the expired message with animation
                const timeoutInfo = document.getElementById('timeout-info');
                const challengeContent = document.getElementById('challenge-content');
                const challengeExpired = document.getElementById('challenge-expired');

                if (timeoutInfo) {
                    timeoutInfo.classList.add('expired');
                }

                if (challengeContent && challengeExpired) {
                    // Add fading effect to the challenge content
                    challengeContent.classList.add('fading');

                    // Show the expired message immediately
                    challengeExpired.style.display = 'block';
                }
            }

            lastRemainingSeconds = remainingSeconds;
        };

        // Function to check container status from the server
        const checkContainerStatus = async () => {
            if (!containerId) return;

            try {
                const response = await fetch(`/challenge/${containerId}/status`);

                if (response.ok) {
                    const data = await response.json();

                    // Update UI with server-provided remaining time
                    updateUI(Math.max(0, data.remaining));

                    // If container is no longer running, stop checking
                    if (data.status === 'stopped' || data.status === 'expired' || data.status === 'not_found') {
                        console.log(`Container ${containerId} is ${data.status}, stopping status checks`);
                        clearInterval(statusCheckInterval);
                        clearInterval(localTimerInterval);

                        // If the container was stopped but the UI is still showing, update it
                        if (data.status === 'stopped' || data.status === 'not_found' || data.status === 'expired') {
                            countdownEl.textContent = data.status === 'expired' ? 'Expired' : 'Stopped';
                            progressBar.style.width = '0%';

                            // Show the expired/stopped message
                            const timeoutInfo = document.getElementById('timeout-info');
                            const challengeContent = document.getElementById('challenge-content');
                            const challengeExpired = document.getElementById('challenge-expired');

                            if (timeoutInfo) {
                                timeoutInfo.classList.add('expired');
                            }

                            if (challengeContent && challengeExpired) {
                                // Add fading effect to the challenge content
                                challengeContent.classList.add('fading');

                                // Show the expired message immediately
                                challengeExpired.style.display = 'block';
                            }
                        }
                    }
                } else {
                    // If we get a 404, the container is gone
                    if (response.status === 404) {
                        console.log(`Container ${containerId} not found, stopping status checks`);
                        clearInterval(statusCheckInterval);
                        clearInterval(localTimerInterval);
                        countdownEl.textContent = 'Stopped';
                        progressBar.style.width = '0%';

                        // Show the expired/stopped message
                        const timeoutInfo = document.getElementById('timeout-info');
                        const challengeContent = document.getElementById('challenge-content');
                        const challengeExpired = document.getElementById('challenge-expired');

                        if (timeoutInfo) {
                            timeoutInfo.classList.add('expired');
                        }

                        if (challengeContent && challengeExpired) {
                            // Add fading effect to the challenge content
                            challengeContent.classList.add('fading');

                            // Show the expired message immediately
                            challengeExpired.style.display = 'block';
                        }
                    }
                }
            } catch (error) {
                console.error('Error checking container status:', error);
            }
        };

        // Function for local time updates between server checks
        const updateLocalTimer = () => {
            // Only update locally if we have a valid last remaining time
            if (lastRemainingSeconds > 0) {
                lastRemainingSeconds = Math.max(0, lastRemainingSeconds - 1);
                updateUI(lastRemainingSeconds);
            }
        };

        // Start both timers
        // 1. Check with server every 5 seconds
        statusCheckInterval = setInterval(checkContainerStatus, 5000);
        window.statusCheckInterval = statusCheckInterval;

        // 2. Update locally every second for smoother countdown
        localTimerInterval = setInterval(updateLocalTimer, 1000);
        window.localTimerInterval = localTimerInterval;

        // Initial check
        checkContainerStatus();

        // Return a function to clean up both intervals
        return () => {
            clearInterval(statusCheckInterval);
            clearInterval(localTimerInterval);
            window.statusCheckInterval = null;
            window.localTimerInterval = null;
        };
    }

    async function stopChallenge(containerId, isSolved = false) {
        if (!containerId) return;

        // Show stopping state in the UI
        const challengeContent = document.getElementById('challenge-content');
        const statusBadge = document.querySelector('.status-badge');

        if (challengeContent) {
            // Add stopping class for visual feedback
            challengeContent.classList.add('stopping');

            // Update status badge
            if (statusBadge && !isSolved) {
                statusBadge.textContent = 'STOPPING';
                statusBadge.classList.remove('active');
                statusBadge.classList.add('stopping');
            }

            // Show stopping overlay
            const stoppingOverlay = document.createElement('div');
            stoppingOverlay.className = 'stopping-overlay';

            if (isSolved) {
                stoppingOverlay.innerHTML = `
                    <div class="stopping-content solved-content">
                        <div class="success-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                                <polyline points="22 4 12 14.01 9 11.01"></polyline>
                            </svg>
                        </div>
                        <h3>Challenge Solved!</h3>
                        <p>Congratulations! The challenge container is being cleaned up.</p>
                    </div>
                `;
            } else {
                stoppingOverlay.innerHTML = `
                    <div class="stopping-content">
                        <div class="loading-spinner"></div>
                        <h3>Stopping Challenge...</h3>
                        <p>Please wait while we clean up resources.</p>
                    </div>
                `;
            }

            challengeContent.appendChild(stoppingOverlay);
        }

        try {
            const response = await fetch(`/challenge/${containerId}/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': userData.token
                }
            });

            const data = await response.json();

            if (response.ok) {
                // Update UI elements
                const countdownEl = document.getElementById('countdown');
                const progressBar = document.getElementById('time-remaining');
                const timeoutInfo = document.getElementById('timeout-info');
                const challengeExpired = document.getElementById('challenge-expired');

                if (countdownEl) {
                    countdownEl.textContent = 'Stopped';
                }

                if (progressBar) {
                    progressBar.style.width = '0%';
                }

                if (timeoutInfo) {
                    timeoutInfo.classList.add('expired');
                }

                if (challengeContent && challengeExpired) {
                    // Add fading effect to the challenge content
                    challengeContent.classList.add('fading');

                    // Show the expired message immediately
                    challengeExpired.style.display = 'block';

                    // Update the expired message title
                    const expiredTitle = challengeExpired.querySelector('h3');
                    if (expiredTitle) {
                        expiredTitle.textContent = isSolved ? 'Challenge Solved' : 'Challenge Stopped';
                    }

                    // Update the expired message text
                    const expiredText = challengeExpired.querySelectorAll('p');
                    if (expiredText && expiredText.length > 0) {
                        if (isSolved) {
                            expiredText[0].textContent = 'Congratulations! You have successfully solved this challenge.';
                        } else {
                            expiredText[0].textContent = 'Your challenge session has been manually stopped without being solved.';
                        }
                    }
                }

                // Update status badge to reflect the correct state
                if (statusBadge) {
                    if (isSolved) {
                        statusBadge.textContent = 'SOLVED';
                        statusBadge.className = 'status-badge solved';
                    } else {
                        statusBadge.textContent = 'STOPPED';
                        statusBadge.className = 'status-badge stopped';
                    }
                }

                // Show appropriate message
                if (isSolved) {
                    showSuccessMessage('Challenge solved and stopped successfully!');
                } else {
                    showInfoMessage('Challenge stopped successfully');
                }

                // Stop any running timers
                if (window.statusCheckInterval) clearInterval(window.statusCheckInterval);
                if (window.localTimerInterval) clearInterval(window.localTimerInterval);
            } else {
                // Remove stopping overlay
                const overlay = document.querySelector('.stopping-overlay');
                if (overlay) overlay.remove();

                // Reset status badge
                if (statusBadge) {
                    statusBadge.textContent = 'ERROR';
                    statusBadge.classList.remove('stopping');
                    statusBadge.classList.add('error');
                }

                // Show error message
                showErrorMessage('Failed to stop challenge: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Challenge stop error:', error);

            // Remove stopping overlay
            const overlay = document.querySelector('.stopping-overlay');
            if (overlay) overlay.remove();

            // Reset status badge
            if (statusBadge) {
                statusBadge.textContent = 'ERROR';
                statusBadge.classList.remove('stopping');
                statusBadge.classList.add('error');
            }

            showErrorMessage('Failed to stop challenge. Please try again.');
        }
    }
});
