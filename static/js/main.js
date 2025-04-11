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
            console.log(`Starting challenge ${challengeId}`);
            // Show the modal immediately with a loading message
            const modal = document.getElementById('challenge-modal');
            const challengeDetails = document.getElementById('challenge-details');

            if (challengeDetails && modal) {
                modal.style.display = 'block';
                challengeDetails.innerHTML = `
                    <div class="challenge-content">
                        <h2>Starting Challenge...</h2>
                        <p>Please wait while we set up your challenge environment.</p>
                    </div>
                `;
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
                showChallengeDetails(challengeId, data);
            } else {
                alert('Failed to start challenge: ' + (data.error || 'Unknown error'));
                // Close the modal if there was an error
                if (modal) {
                    modal.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Challenge start error:', error);
            alert('Failed to start challenge. Please try again.');
            // Close the modal if there was an error
            const modal = document.getElementById('challenge-modal');
            if (modal) {
                modal.style.display = 'none';
            }
        }
    }

    function showChallengeDetails(challengeId, data) {
        const modal = document.getElementById('challenge-modal');
        const challengeDetails = document.getElementById('challenge-details');

        if (challengeDetails && modal) {
            // Show the modal immediately
            modal.style.display = 'block';

            challengeDetails.innerHTML = `
                <div id="challenge-content" class="challenge-content">
                    <h2>Challenge Started</h2>
                    <p>Your challenge is running on port: ${data.port}</p>
                    <div class="terminal">
                        <p>Connect to the challenge at: <a href="http://localhost:${data.port}" target="_blank">http://localhost:${data.port}</a></p>
                        <p>Good luck!</p>
                    </div>
                    <div id="timeout-info" class="timeout-info">
                        <p>This challenge will automatically expire in <span id="countdown">10:00</span></p>
                        <div class="progress-bar">
                            <div id="time-remaining" style="width: 100%;"></div>
                        </div>
                    </div>
                    <div class="flag-submission">
                        <h3>Submit Flag</h3>
                        <input type="text" id="flag-input" placeholder="Enter flag here">
                        <button id="submit-flag">Submit</button>
                    </div>
                    <div class="challenge-controls">
                        <button id="stop-challenge" data-container="${data.containerId}">Stop Challenge</button>
                    </div>
                </div>

                <div id="challenge-expired" class="challenge-expired-message">
                    <h3>Challenge Expired</h3>
                    <p>Your challenge session has ended. The container has been automatically stopped.</p>
                    <p>If you'd like to try again, you can start a new challenge session.</p>
                    <div class="challenge-expired-actions">
                        <button class="btn-restart" id="restart-challenge" data-challenge="${challengeId}">Start New Session</button>
                        <button class="btn-close" id="close-expired-challenge">Close</button>
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
                // Update UI elements
                const countdownEl = document.getElementById('countdown');
                const progressBar = document.getElementById('time-remaining');
                const timeoutInfo = document.getElementById('timeout-info');
                const challengeContent = document.getElementById('challenge-content');
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
                }

                alert(`Challenge stopped successfully`);
            } else {
                alert('Failed to stop challenge: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Challenge stop error:', error);
            alert('Failed to stop challenge. Please try again.');
        }
    }
});
