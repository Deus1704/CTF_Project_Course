from flask import Flask, request, render_template_string, jsonify, redirect
import os
import json

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')
# Get main site URL (default to localhost if not provided)
MAIN_SITE = os.environ.get('MAIN_SITE', 'http://localhost:5002')
# Get challenge ID and container ID
CHALLENGE_ID = os.environ.get('CHALLENGE_ID', 'web-basic')
CONTAINER_ID = os.environ.get('CONTAINER_ID', '')

@app.route('/')
def index():
    return render_template_string('''
    <html>
        <head>
            <title>Web Basic Challenge</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .hint { color: #666; font-style: italic; }
                .note { margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff; }
                .flag-form { margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 5px; }
                .flag-input { padding: 8px; width: 300px; margin-right: 10px; }
                .submit-btn { padding: 8px 15px; background-color: #28a745; color: white; border: none; cursor: pointer; }
                .message { margin-top: 10px; padding: 10px; border-radius: 5px; }
                .success { background-color: #dff0d8; color: #3c763d; }
                .error { background-color: #f2dede; color: #a94442; }
            </style>
        </head>
        <body>
            <h1>Welcome to the Web Basic Challenge</h1>
            <p>Can you find the hidden flag?</p>
            <p class="hint">Hint: Check the page source and HTTP headers</p>
            <!-- Flag hint: The flag is not in the HTML comments -->

            <div class="note">
                <p><strong>Important:</strong> Once you find the flag, submit it using the form below to earn points:</p>
            </div>

            <div class="flag-form">
                <h3>Submit Flag</h3>
                <form id="flag-form" action="/submit-flag" method="post">
                    <input type="text" id="flag" name="flag" class="flag-input" placeholder="Enter flag here" required>
                    <button type="submit" class="submit-btn">Submit Flag</button>
                </form>
                <div id="message" class="message" style="display: none;"></div>
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
                                // Show success message
                                const messageDiv = document.getElementById('message');
                                if (messageDiv) {
                                    messageDiv.className = 'message success';
                                    messageDiv.style.display = 'block';
                                    messageDiv.textContent = data.message || 'Congratulations! Flag is correct! Redirecting to main site...';
                                }
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
    ''', FLAG=FLAG, MAIN_SITE=MAIN_SITE, CHALLENGE_ID=CHALLENGE_ID, CONTAINER_ID=CONTAINER_ID)

@app.route('/check')
def check():
    # The flag is hidden in the HTTP headers
    response = app.make_response("Nothing to see here in the body...")
    response.headers['X-Secret-Flag'] = FLAG
    return response

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
                challenge_id = os.environ.get('CHALLENGE_ID', 'web-basic')
                main_site = os.environ.get('MAIN_SITE', 'http://localhost:5002')

                # For AJAX requests, return JSON
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'Congratulations! Flag is correct! Redirecting to main site...',
                        'redirect_url': f"{main_site}?flag_success=true&challenge={challenge_id}&container_id={container_id}&auto_show=true"
                    })
                # For form submissions, redirect directly
                else:
                    redirect_url = f"{main_site}?flag_success=true&challenge={challenge_id}&container_id={container_id}&auto_show=true"
                    return render_template_string("""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Correct Flag</title>
                        <meta http-equiv="refresh" content="2;url={{{{ redirect_url }}}}" />
                        <style>
                            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background-color: #f8f9fa; }
                            .success { color: #28a745; }
                            .container { max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                            .redirect-info { margin-top: 20px; color: #6c757d; font-size: 14px; }
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
                            setTimeout(function() {
                                window.location.href = "{{{{ redirect_url }}}}";
                            }, 2000);
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
    app.run(host='0.0.0.0', port=5000)
