from flask import Flask, request, render_template_string, jsonify, redirect, g
import os
import sqlite3
import json

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')
# Get main site URL (default to localhost if not provided)
MAIN_SITE = os.environ.get('MAIN_SITE', 'http://localhost:5002')
# Get challenge ID and container ID
CHALLENGE_ID = os.environ.get('CHALLENGE_ID', 'web-sqli')
CONTAINER_ID = os.environ.get('CONTAINER_ID', '')

# Database setup
DATABASE = 'users.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
        ''')
        
        # Create secrets table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            secret_data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Insert sample data
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM secrets")
        
        # Insert admin user with the flag
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                      ('admin', 'super_secure_password', 'admin'))
        
        # Insert regular users
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                      ('john', 'password123', 'user'))
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                      ('alice', 'alice123', 'user'))
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                      ('bob', 'bob456', 'user'))
        
        # Insert secrets
        cursor.execute("INSERT INTO secrets (user_id, secret_data) VALUES (?, ?)", 
                      (1, f"Admin secret: {FLAG}"))
        cursor.execute("INSERT INTO secrets (user_id, secret_data) VALUES (?, ?)", 
                      (2, "John's personal data: SSN 123-45-6789"))
        cursor.execute("INSERT INTO secrets (user_id, secret_data) VALUES (?, ?)", 
                      (3, "Alice's personal data: Credit card 1234-5678-9012-3456"))
        cursor.execute("INSERT INTO secrets (user_id, secret_data) VALUES (?, ?)", 
                      (4, "Bob's personal data: Password hint - favorite pet name"))
        
        db.commit()

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Secure Login System</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    line-height: 1.6;
                    color: #333;
                    background-color: #f5f5f5;
                }
                h1, h2 { color: #2c3e50; }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .hint { 
                    color: #666; 
                    font-style: italic; 
                    background-color: #f9f9f9;
                    padding: 10px;
                    border-left: 3px solid #2c3e50;
                    margin: 20px 0;
                }
                form { 
                    margin: 20px 0;
                    background-color: #f9f9f9;
                    padding: 20px;
                    border-radius: 5px;
                }
                input[type="text"], input[type="password"] { 
                    padding: 8px; 
                    width: 70%; 
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    margin-bottom: 10px;
                }
                button { 
                    padding: 8px 16px; 
                    background: #2c3e50; 
                    color: white; 
                    border: none; 
                    cursor: pointer;
                    border-radius: 3px;
                }
                button:hover {
                    background: #1a252f;
                }
                .error {
                    color: #a94442;
                    background-color: #f2dede;
                    padding: 10px;
                    border-radius: 3px;
                    margin: 10px 0;
                }
                .success {
                    color: #3c763d;
                    background-color: #dff0d8;
                    padding: 10px;
                    border-radius: 3px;
                    margin: 10px 0;
                }
                .flag-form {
                    margin-top: 30px;
                    border-top: 1px solid #eee;
                    padding-top: 20px;
                }
                .user-info {
                    background-color: #e8f4f8;
                    padding: 15px;
                    border-radius: 5px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Secure User Portal</h1>
                <p>Welcome to our super secure user portal. Only authorized users can access their data.</p>
                
                <div class="hint">
                    <p><strong>Hint:</strong> This login system might have some SQL injection vulnerabilities. Can you find a way to access the admin's secrets?</p>
                </div>
                
                <h2>Login</h2>
                <form id="login-form" action="/login" method="post">
                    <div>
                        <label for="username">Username:</label><br>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div>
                        <label for="password">Password:</label><br>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">Login</button>
                </form>
                
                <div id="error-message" class="error" style="display: none;"></div>
                
                <div class="flag-form">
                    <h3>Submit Flag</h3>
                    <form id="flag-form" action="/submit-flag" method="post">
                        <input type="text" id="flag" name="flag" placeholder="Enter flag here" required>
                        <button type="submit">Submit Flag</button>
                    </form>
                    <div id="flag-message" class="message" style="display: none;"></div>
                </div>
            </div>

            <script>
                // Make variables available to JavaScript
                const FLAG = "{{FLAG}}";
                const MAIN_SITE = "{{MAIN_SITE}}";
                const CHALLENGE_ID = "{{CHALLENGE_ID}}";
                const CONTAINER_ID = "{{CONTAINER_ID}}";

                // Handle login form submission
                document.getElementById('login-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const username = document.getElementById('username').value.trim();
                    const password = document.getElementById('password').value.trim();
                    
                    fetch('/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            username: username,
                            password: password
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Redirect to user page
                            window.location.href = '/user?id=' + data.user_id;
                        } else {
                            // Show error message
                            const errorDiv = document.getElementById('error-message');
                            errorDiv.textContent = data.message || 'Login failed. Please try again.';
                            errorDiv.style.display = 'block';
                            
                            // Hide the message after 3 seconds
                            setTimeout(() => {
                                errorDiv.style.display = 'none';
                            }, 3000);
                        }
                    })
                    .catch(error => {
                        console.error('Error during login:', error);
                    });
                });

                // Handle flag form submission
                document.getElementById('flag-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const flag = document.getElementById('flag').value.trim();
                    
                    // If flag is correct, show success overlay before redirecting
                    if (flag === FLAG) {
                        // Submit the flag via AJAX
                        fetch('/submit-flag', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                flag: flag
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                console.log('Flag submission successful, redirecting to:', data.redirect_url);
                                // Redirect to the URL provided by the server
                                setTimeout(() => {
                                    window.location.href = data.redirect_url;
                                }, 2000);
                            }
                        })
                        .catch(error => {
                            console.error('Error submitting flag:', error);
                            // Fallback redirect if the AJAX call fails
                            setTimeout(() => {
                                const redirectUrl = `${MAIN_SITE}?flag_success=true&challenge=${CHALLENGE_ID}&container_id=${CONTAINER_ID}&auto_show=true`;
                                console.log('Fallback redirect to:', redirectUrl);
                                window.location.href = redirectUrl;
                            }, 2000);
                        });
                    } else {
                        // If flag is incorrect, submit via AJAX
                        fetch('/submit-flag', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                flag: flag
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (!data.success) {
                                // Show error message
                                const messageDiv = document.getElementById('flag-message');
                                messageDiv.className = 'error';
                                messageDiv.style.display = 'block';
                                messageDiv.textContent = data.message || 'Incorrect flag. Try again!';

                                // Hide the message after 3 seconds
                                setTimeout(() => {
                                    messageDiv.style.display = 'none';
                                }, 3000);
                            }
                        })
                        .catch(error => {
                            console.error('Error submitting flag:', error);
                        });
                    }
                });
            </script>
        </body>
    </html>
    ''', FLAG=FLAG, MAIN_SITE=MAIN_SITE, CHALLENGE_ID=CHALLENGE_ID, CONTAINER_ID=CONTAINER_ID)

@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
    else:
        username = request.form.get('username', '')
        password = request.form.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'})
    
    # Vulnerable SQL query - intentional SQL injection vulnerability
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(query)
        user = cursor.fetchone()
        
        if user:
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user_id': user['id']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/user')
def user_page():
    user_id = request.args.get('id')
    
    if not user_id:
        return redirect('/')
    
    try:
        # Another vulnerable query - intentional SQL injection
        query = f"SELECT * FROM users WHERE id = {user_id}"
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute(query)
        user = cursor.fetchone()
        
        if not user:
            return "User not found", 404
        
        # Get user's secrets
        cursor.execute(f"SELECT * FROM secrets WHERE user_id = {user_id}")
        secrets = cursor.fetchall()
        
        # Convert to list of dicts for easier template rendering
        secrets_list = [dict(secret) for secret in secrets]
        user_dict = dict(user)
        
        return render_template_string('''
        <!DOCTYPE html>
        <html>
            <head>
                <title>User Profile</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 40px; 
                        line-height: 1.6;
                        color: #333;
                        background-color: #f5f5f5;
                    }
                    h1, h2 { color: #2c3e50; }
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 20px;
                        border-radius: 5px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }
                    .user-info {
                        background-color: #e8f4f8;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }
                    .secret-item {
                        background-color: #fff9e6;
                        padding: 10px;
                        border-left: 3px solid #f0ad4e;
                        margin-bottom: 10px;
                    }
                    .back-link {
                        display: inline-block;
                        margin-top: 20px;
                        color: #2c3e50;
                        text-decoration: none;
                    }
                    .back-link:hover {
                        text-decoration: underline;
                    }
                    .flag-form {
                        margin-top: 30px;
                        border-top: 1px solid #eee;
                        padding-top: 20px;
                    }
                    input[type="text"] { 
                        padding: 8px; 
                        width: 70%; 
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        margin-bottom: 10px;
                    }
                    button { 
                        padding: 8px 16px; 
                        background: #2c3e50; 
                        color: white; 
                        border: none; 
                        cursor: pointer;
                        border-radius: 3px;
                    }
                    button:hover {
                        background: #1a252f;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>User Profile</h1>
                    
                    <div class="user-info">
                        <h2>{{ user.username }}</h2>
                        <p><strong>Role:</strong> {{ user.role }}</p>
                        <p><strong>User ID:</strong> {{ user.id }}</p>
                    </div>
                    
                    <h2>User Secrets</h2>
                    {% if secrets %}
                        {% for secret in secrets %}
                            <div class="secret-item">
                                <p>{{ secret.secret_data }}</p>
                            </div>
                        {% endfor %}
                    {% else %}
                        <p>No secrets found for this user.</p>
                    {% endif %}
                    
                    <a href="/" class="back-link">← Back to Login</a>
                    
                    <div class="flag-form">
                        <h3>Submit Flag</h3>
                        <form id="flag-form" action="/submit-flag" method="post">
                            <input type="text" id="flag" name="flag" placeholder="Enter flag here" required>
                            <button type="submit">Submit Flag</button>
                        </form>
                        <div id="flag-message" class="message" style="display: none;"></div>
                    </div>
                </div>
                
                <script>
                    // Make variables available to JavaScript
                    const FLAG = "{{FLAG}}";
                    const MAIN_SITE = "{{MAIN_SITE}}";
                    const CHALLENGE_ID = "{{CHALLENGE_ID}}";
                    const CONTAINER_ID = "{{CONTAINER_ID}}";

                    // Handle flag form submission
                    document.getElementById('flag-form').addEventListener('submit', function(e) {
                        e.preventDefault();
                        
                        const flag = document.getElementById('flag').value.trim();
                        
                        // If flag is correct, show success overlay before redirecting
                        if (flag === FLAG) {
                            // Submit the flag via AJAX
                            fetch('/submit-flag', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    flag: flag
                                })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    console.log('Flag submission successful, redirecting to:', data.redirect_url);
                                    // Redirect to the URL provided by the server
                                    setTimeout(() => {
                                        window.location.href = data.redirect_url;
                                    }, 2000);
                                }
                            })
                            .catch(error => {
                                console.error('Error submitting flag:', error);
                                // Fallback redirect if the AJAX call fails
                                setTimeout(() => {
                                    const redirectUrl = `${MAIN_SITE}?flag_success=true&challenge=${CHALLENGE_ID}&container_id=${CONTAINER_ID}&auto_show=true`;
                                    console.log('Fallback redirect to:', redirectUrl);
                                    window.location.href = redirectUrl;
                                }, 2000);
                            });
                        } else {
                            // If flag is incorrect, submit via AJAX
                            fetch('/submit-flag', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    flag: flag
                                })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (!data.success) {
                                    // Show error message
                                    const messageDiv = document.getElementById('flag-message');
                                    messageDiv.className = 'error';
                                    messageDiv.style.display = 'block';
                                    messageDiv.textContent = data.message || 'Incorrect flag. Try again!';

                                    // Hide the message after 3 seconds
                                    setTimeout(() => {
                                        messageDiv.style.display = 'none';
                                    }, 3000);
                                }
                            })
                            .catch(error => {
                                console.error('Error submitting flag:', error);
                            });
                        }
                    });
                </script>
            </body>
        </html>
        ''', user=user_dict, secrets=secrets_list, FLAG=FLAG, MAIN_SITE=MAIN_SITE, CHALLENGE_ID=CHALLENGE_ID, CONTAINER_ID=CONTAINER_ID)
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/submit-flag', methods=['POST'])
def submit_flag():
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
                submitted_flag = data.get('flag', '')
            else:
                submitted_flag = request.form.get('flag', '')

            if submitted_flag == FLAG:
                # Flag is correct
                # Get container ID and challenge ID from environment variables
                container_id = os.environ.get('CONTAINER_ID', '')
                challenge_id = os.environ.get('CHALLENGE_ID', 'web-sqli')
                main_site = os.environ.get('MAIN_SITE', 'http://localhost:5002')

                # For AJAX requests, return JSON
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'Congratulations! Flag is correct! Redirecting to main site...',
                        'redirect_url': f"{MAIN_SITE}?flag_success=true&challenge={challenge_id}&container_id={container_id}&auto_show=true"
                    })
                # For form submissions, redirect directly
                else:
                    redirect_url = f"{MAIN_SITE}?flag_success=true&challenge={challenge_id}&container_id={container_id}&auto_show=true"
                    return render_template_string("""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Correct Flag</title>
                        <meta http-equiv="refresh" content="2;url={{{{ redirect_url }}}}" />
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background-color: #f8f9fa; }}
                            .success {{ color: #28a745; }}
                            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                            .redirect-info {{ margin-top: 20px; color: #6c757d; font-size: 14px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h2 class="success">Flag Correct!</h2>
                            <p>Congratulations! You've solved the challenge.</p>
                            <p>Redirecting to main site in 2 seconds...</p>
                            <div class="redirect-info">If you are not redirected automatically, <a href="{{{{ redirect_url }}}}">click here</a>.</div>
                        </div>
                        <script>
                            // Ensure we redirect even if meta refresh fails
                            setTimeout(function() {{
                                window.location.href = "{{{{ redirect_url }}}}";
                            }}, 2000);
                        </script>
                    </body>
                    </html>
                    """, redirect_url=redirect_url)
            else:
                # Flag is incorrect
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'message': 'Incorrect flag. Try again!'
                    })
                else:
                    return render_template_string("""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Incorrect Flag</title>
                        <meta http-equiv="refresh" content="2;url=/" />
                        <style>
                            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
                            .error { color: #dc3545; }
                        </style>
                    </head>
                    <body>
                        <h2 class="error">Incorrect Flag</h2>
                        <p>Please try again. Redirecting back to challenge...</p>
                    </body>
                    </html>
                    """)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error processing submission: {str(e)}'
            })
    else:
        # Flag is incorrect
        return jsonify({
            'success': False,
            'message': 'Incorrect flag. Try again!'
        })

if __name__ == '__main__':
    # Initialize the database
    init_db()
    app.run(host='0.0.0.0', port=5000)
