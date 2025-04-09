// Main JavaScript for CTF platform

// Store user session data
let userData = {
    username: '',
    token: '',
    isLoggedIn: false
};

// DOM elements
document.addEventListener('DOMContentLoaded', function() {
    // Auth elements
    const loginForm = document.getElementById('login-form');
    const logoutBtn = document.getElementById('logout-btn');
    const authSection = document.getElementById('auth-section');
    const challengeSection = document.getElementById('challenge-section');
    const welcomeMessage = document.getElementById('welcome-message');
    const challengeList = document.getElementById('challenge-list');
    const challengeDetails = document.getElementById('challenge-details');

    // Check if user is already logged in (from localStorage)
    const savedUser = localStorage.getItem('ctf_user');
    if (savedUser) {
        try {
            userData = JSON.parse(savedUser);
            if (userData.token) {
                showLoggedInState();
                loadChallenges();
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

    // Helper functions
    function showLoggedInState() {
        userData.isLoggedIn = true;
        if (authSection) authSection.classList.add('hidden');
        if (challengeSection) challengeSection.classList.remove('hidden');
        if (welcomeMessage) welcomeMessage.textContent = `Welcome, ${userData.username}!`;

        // Save to localStorage
        localStorage.setItem('ctf_user', JSON.stringify(userData));
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
                userData.username = username;
                userData.token = data.token;
                showLoggedInState();
                loadChallenges();
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
            const challengeIds = await response.json();

            // Map challenge IDs to challenge objects with descriptions
            const challengeDescriptions = {
                'web-basic': 'A basic web exploitation challenge',
                'crypto-101': 'Introduction to cryptography challenges',
                'pwn-starter': 'Basic binary exploitation'
            };

            const challenges = challengeIds.map(id => ({
                id: id,
                name: id.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
                description: challengeDescriptions[id] || 'A CTF challenge'
            }));

            // Clear existing challenges
            if (challengeList) {
                challengeList.innerHTML = '';

                if (challenges.length === 0) {
                    challengeList.innerHTML = '<p>No challenges available. Please check back later.</p>';
                    return;
                }

                // Add each challenge to the list
                challenges.forEach(challenge => {
                    const challengeCard = document.createElement('div');
                    challengeCard.className = 'challenge-card';
                    challengeCard.innerHTML = `
                        <h3>${challenge.name}</h3>
                        <p>${challenge.description}</p>
                        <button class="start-challenge-btn" data-id="${challenge.id}">Start Challenge</button>
                    `;
                    challengeList.appendChild(challengeCard);

                    // Add event listener to the button
                    const startBtn = challengeCard.querySelector('.start-challenge-btn');
                    startBtn.addEventListener('click', function() {
                        startChallenge(challenge.id);
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

            if (response.ok) {
                showChallengeDetails(challengeId, data);
            } else {
                alert('Failed to start challenge: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Challenge start error:', error);
            alert('Failed to start challenge. Please try again.');
        }
    }

    function showChallengeDetails(challengeId, data) {
        if (challengeDetails) {
            challengeDetails.classList.remove('hidden');
            challengeDetails.innerHTML = `
                <h2>Challenge Started</h2>
                <p>Your challenge is running on port: ${data.port}</p>
                <div class="terminal">
                    <p>Connect to the challenge at: <a href="http://localhost:${data.port}" target="_blank">http://localhost:${data.port}</a></p>
                    <p>Good luck!</p>
                </div>
                <div class="flag-submission">
                    <h3>Submit Flag</h3>
                    <input type="text" id="flag-input" placeholder="Enter flag here">
                    <button id="submit-flag">Submit</button>
                </div>
                <div class="challenge-controls">
                    <button id="stop-challenge" data-container="${data.containerId}">Stop Challenge</button>
                </div>
            `;

            // For demo purposes, we'll just check if the flag matches
            const submitBtn = document.getElementById('submit-flag');
            const flagInput = document.getElementById('flag-input');
            const stopBtn = document.getElementById('stop-challenge');

            if (submitBtn && flagInput) {
                submitBtn.addEventListener('click', function() {
                    const submittedFlag = flagInput.value.trim();
                    if (submittedFlag === data.flag) {
                        alert('Congratulations! Flag is correct!');
                    } else {
                        alert('Incorrect flag. Try again!');
                    }
                });
            }

            if (stopBtn) {
                stopBtn.addEventListener('click', function() {
                    const containerId = this.getAttribute('data-container');
                    stopChallenge(containerId);
                });
            }
        }
    }

    async function stopChallenge(containerId) {
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
                alert(`Challenge stopped successfully`);
                challengeDetails.classList.add('hidden');
            } else {
                alert('Failed to stop challenge: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Challenge stop error:', error);
            alert('Failed to stop challenge. Please try again.');
        }
    }
});
