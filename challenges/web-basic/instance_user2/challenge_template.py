# Basic challenge template with token verification
from flask import Flask, request, render_template_string, jsonify, redirect, abort
import os
import requests
import json

app = Flask(__name__)

# Get flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'flag{placeholder}')
# Get main site URL (default to localhost if not provided)
MAIN_SITE = os.environ.get('MAIN_SITE', 'http://localhost:5002')
# Get challenge ID and container ID
CHALLENGE_ID = os.environ.get('CHALLENGE_ID', '')
CONTAINER_ID = os.environ.get('CONTAINER_ID', '')
# Get user token and ID for verification
USER_TOKEN = os.environ.get('USER_TOKEN', '')
USER_ID = os.environ.get('USER_ID', '')

def verify_access():
    """Verify that the user has permission to access this challenge"""
    # Get token from cookie or Authorization header
    token = None
    if request.cookies.get('ctf_token'):
        token = request.cookies.get('ctf_token')
    elif request.headers.get('Authorization'):
        token = request.headers.get('Authorization')
    
    # If no token is provided, check if this is the user who started the challenge
    if not token and USER_TOKEN:
        # For direct access, we'll use the token that was used to start the challenge
        token = USER_TOKEN
    
    # If still no token, deny access
    if not token:
        return False
    
    # Verify token with main site
    try:
        # Make a request to the main site to verify the token
        response = requests.get(
            f"{MAIN_SITE}verify-token",
            headers={"Authorization": token}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check if this is the user who started the challenge
            if data.get('username') == USER_ID:
                return True
        
        return False
    except Exception as e:
        print(f"Error verifying token: {e}")
        # If verification fails, fall back to comparing with the stored token
        return token == USER_TOKEN

@app.before_request
def check_auth():
    """Check authentication before processing any request"""
    # Skip auth check for the verification endpoint itself
    if request.path == '/verify-access':
        return
    
    # Verify access for all other routes
    if not verify_access():
        # Return a JSON response for API requests
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return jsonify({"error": "Unauthorized access. This challenge was started by another user."}), 403
        
        # Return an HTML error page for regular requests
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Access Denied</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
                h1 { color: #d9534f; }
                .container { max-width: 600px; margin: 0 auto; }
                .btn { display: inline-block; padding: 10px 15px; background-color: #007bff; 
                       color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Access Denied</h1>
                <p>You are not authorized to access this challenge.</p>
                <p>This challenge was started by another user or your session has expired.</p>
                <a href="{{ main_site }}" class="btn">Return to Main Site</a>
            </div>
        </body>
        </html>
        """, main_site=MAIN_SITE), 403

@app.route('/verify-access')
def verify_access_endpoint():
    """Endpoint to verify if the user has access to this challenge"""
    has_access = verify_access()
    return jsonify({"has_access": has_access})

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ challenge_name }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1 { color: #333; }
            .container { max-width: 800px; margin: 0 auto; }
            .flag-form { margin-top: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .flag-input { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
            .submit-btn { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
            .submit-btn:hover { background-color: #45a049; }
            .message { margin-top: 20px; padding: 10px; border-radius: 4px; }
            .success { background-color: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }
            .error { background-color: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{{ challenge_name }}</h1>
            <p>{{ challenge_description }}</p>
            <p>Can you find the flag?</p>

            <div class="flag-form">
                <h3>Submit Flag</h3>
                <form id="flag-form" action="/submit-flag" method="post">
                    <input type="text" id="flag" name="flag" class="flag-input" placeholder="Enter flag here (e.g., flag{...})" required>
                    <button type="submit" class="submit-btn">Submit Flag</button>
                </form>
                <div id="message" class="message" style="display: none;"></div>
            </div>

            <!-- Success message that shows briefly before redirect -->
            <div id="success-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.8); z-index: 1000;">
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: white; padding: 30px; border-radius: 10px; text-align: center;">
                    <div style="color: #28a745; font-size: 48px; margin-bottom: 20px;">✓</div>
                    <h2 style="color: #28a745; margin-bottom: 15px;">Flag Correct!</h2>
                    <p>Congratulations! You've solved the challenge.</p>
                    <p style="margin-bottom: 20px;">Closing challenge and redirecting to main site...</p>
                    <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 15px;">
                        <div style="width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #28a745; border-radius: 50%; animation: spin 1s linear infinite; margin-right: 10px;"></div>
                        <span>Stopping container...</span>
                    </div>
                    <div style="width: 100%; height: 4px; background-color: #f3f3f3; margin-top: 20px; border-radius: 2px; overflow: hidden;">
                        <div id="progress-bar" style="height: 100%; width: 0%; background-color: #28a745; transition: width 2s linear;"></div>
                    </div>
                </div>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        </div>

        <script>
            // Make variables available to JavaScript
            const FLAG = "{{FLAG}}";
            const MAIN_SITE = "{{MAIN_SITE}}";
            const CHALLENGE_ID = "{{CHALLENGE_ID}}";
            const CONTAINER_ID = "{{CONTAINER_ID}}";

            // Handle form submission
            document.getElementById('flag-form').addEventListener('submit', function(e) {
                // Always prevent default form submission
                e.preventDefault();

                // Get the flag value
                const flag = document.getElementById('flag').value.trim();

                // If flag is correct, show success overlay before redirecting
                if (flag === FLAG) {
                    document.getElementById('success-overlay').style.display = 'block';
                    document.getElementById('progress-bar').style.width = '100%';

                    // Add a message that the challenge is being closed
                    const message = document.createElement('div');
                    message.style.position = 'fixed';
                    message.style.top = '10px';
                    message.style.left = '50%';
                    message.style.transform = 'translateX(-50%)';
                    message.style.backgroundColor = '#28a745';
                    message.style.color = 'white';
                    message.style.padding = '10px 20px';
                    message.style.borderRadius = '5px';
                    message.style.zIndex = '2000';
                    message.textContent = 'Challenge completed! Redirecting to main site...';
                    document.body.appendChild(message);

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
                            const messageDiv = document.getElementById('message');
                            if (messageDiv) {
                                messageDiv.className = 'message error';
                                messageDiv.style.display = 'block';
                                messageDiv.textContent = data.message || 'Incorrect flag. Try again!';

                                // Hide the message after 3 seconds
                                setTimeout(() => {
                                    messageDiv.style.display = 'none';
                                }, 3000);
                            }
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
    """, challenge_name="Challenge", challenge_description="Find the flag in this challenge.", FLAG=FLAG, MAIN_SITE=MAIN_SITE, CHALLENGE_ID=CHALLENGE_ID, CONTAINER_ID=CONTAINER_ID)

@app.route('/submit-flag', methods=['POST', 'GET'])
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
                challenge_id = os.environ.get('CHALLENGE_ID', '')
                main_site = os.environ.get('MAIN_SITE', 'http://localhost:5002')

                # Try to stop the container
                try:
                    import subprocess
                    if container_id:
                        # Execute the command to stop the container - use check_call for synchronous execution
                        print(f"Stopping container {container_id} after successful flag submission")
                        # Use Popen with a timeout to avoid blocking the redirect
                        stop_process = subprocess.Popen(['docker', 'stop', container_id])
                        # Don't wait for completion - we want to redirect quickly
                        # The main site will handle cleanup if needed
                except Exception as e:
                    print(f"Error stopping container: {e}")

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
    return jsonify({
        'success': False,
        'message': 'Invalid request method'
    })

@app.route('/flag')
def get_flag():
    # This is just a placeholder - you should implement your own challenge logic
    return jsonify({'message': 'Not that easy! Solve the challenge to get the flag.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
