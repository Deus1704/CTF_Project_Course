from flask import Flask, request, render_template_string, send_file, jsonify, redirect
import os
import io
import tempfile
import random
import string
import time
import base64

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')
# Get main site URL (default to localhost if not provided)
MAIN_SITE = os.environ.get('MAIN_SITE', 'http://localhost:5010')
# Get challenge ID and container ID
CHALLENGE_ID = os.environ.get('CHALLENGE_ID', 'reverse-engineering')
CONTAINER_ID = os.environ.get('CONTAINER_ID', '')

# Create a temporary directory for storing generated files
TEMP_DIR = tempfile.mkdtemp()

def create_binary_file():
    """Create a simple binary file that needs to be reverse engineered"""
    # Create a unique filename
    binary_path = os.path.join(TEMP_DIR, f"secret_binary_{int(time.time())}")
    
    # Create a simple C-like binary structure
    # This is a simplified version - in a real challenge, you'd create a more complex binary
    
    # Magic header
    header = b"REVENG"
    
    # Version
    version = b"\x01\x00"
    
    # Encode the flag with a simple XOR
    xor_key = 42
    encoded_flag = bytes([b ^ xor_key for b in FLAG.encode()])
    
    # Add length of encoded flag
    flag_length = len(encoded_flag).to_bytes(2, byteorder='little')
    
    # Add some random data to make it look more complex
    random_data = bytes([random.randint(0, 255) for _ in range(20)])
    
    # Create a checksum (simple sum of all bytes in the encoded flag)
    checksum = sum(encoded_flag) % 256
    checksum_bytes = checksum.to_bytes(1, byteorder='little')
    
    # Assemble the binary
    binary_content = header + version + flag_length + random_data + encoded_flag + checksum_bytes
    
    # Write the binary file
    with open(binary_path, 'wb') as f:
        f.write(binary_content)
    
    return binary_path

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Reverse Engineering Challenge</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    line-height: 1.6;
                    color: #333;
                }
                h1 { color: #2c3e50; }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                }
                .hint { 
                    color: #666; 
                    font-style: italic; 
                    background-color: #f9f9f9;
                    padding: 10px;
                    border-left: 3px solid #2c3e50;
                }
                form { 
                    margin: 20px 0;
                    background-color: #f9f9f9;
                    padding: 20px;
                    border-radius: 5px;
                }
                input[type="text"] { 
                    padding: 8px; 
                    width: 70%; 
                    border: 1px solid #ddd;
                    border-radius: 3px;
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
                .download-btn {
                    display: inline-block;
                    margin: 20px 0;
                    padding: 10px 20px;
                    background-color: #3498db;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }
                .download-btn:hover {
                    background-color: #2980b9;
                }
                .resources {
                    margin-top: 30px;
                    padding: 15px;
                    background-color: #f5f5f5;
                    border-radius: 5px;
                }
                .resources h3 {
                    margin-top: 0;
                }
                .resources ul {
                    padding-left: 20px;
                }
                pre {
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }
                code {
                    font-family: monospace;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Reverse Engineering Challenge</h1>
                
                <p>Welcome to the reverse engineering challenge! In this challenge, you need to analyze a binary file to find a hidden flag.</p>
                
                <div class="hint">
                    <p><strong>Hint:</strong> The flag is encoded with a simple XOR operation. Look for patterns in the binary structure.</p>
                </div>
                
                <p>Download the binary file and analyze it:</p>
                
                <a href="/download" class="download-btn">Download Binary File</a>
                
                <p>Here's a hexdump preview of the file structure:</p>
                
                <pre><code>
00000000: 5245 5645 4e47 0100 1a00 7b3d 2a5f 9c7e  REVENG......{=*_.~
00000010: 4c8d 3e2f 6a12 5b9a 3c4d 5e7f 2e3f 4a5b  L.>/j.[.<M^..?J[
00000020: 6c7d 8e9f a0b1 c2d3 e4f5 0617 2839 4a5b  l}...........(9J[
...
                </code></pre>
                
                <p>Once you've found the flag, submit it below:</p>
                
                <form id="flag-form" action="/submit-flag" method="post">
                    <input type="text" id="flag" name="flag" placeholder="Enter the flag you found">
                    <button type="submit">Submit Flag</button>
                </form>
                <div id="message" class="message" style="display: none;"></div>
                
                <div class="resources">
                    <h3>Helpful Resources</h3>
                    <ul>
                        <li>Use a hex editor like <a href="https://hexed.it/" target="_blank">hexed.it</a> to examine the binary</li>
                        <li>Look for patterns in the file structure</li>
                        <li>The file starts with a magic header "REVENG"</li>
                        <li>The flag is encoded with a simple XOR operation (key = 42)</li>
                        <li>Try writing a simple script to decode the flag</li>
                    </ul>
                </div>
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

@app.route('/download')
def download_binary():
    binary_path = create_binary_file()
    return send_file(binary_path, as_attachment=True, download_name="secret_binary")

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
                challenge_id = os.environ.get('CHALLENGE_ID', 'reverse-engineering')
                main_site = os.environ.get('MAIN_SITE', 'http://localhost:5010')

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

@app.route('/hint')
def hint():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Reverse Engineering Hint</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    line-height: 1.6;
                    color: #333;
                }
                h1 { color: #2c3e50; }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                }
                .hint { 
                    color: #666; 
                    background-color: #f9f9f9;
                    padding: 20px;
                    border-left: 3px solid #2c3e50;
                    margin-bottom: 20px;
                }
                pre {
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }
                code {
                    font-family: monospace;
                }
                a {
                    display: inline-block;
                    margin-top: 20px;
                    padding: 10px 20px;
                    background-color: #2c3e50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }
                a:hover {
                    background-color: #1a252f;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Reverse Engineering Hint</h1>
                
                <div class="hint">
                    <h3>File Structure</h3>
                    <p>The binary file has the following structure:</p>
                    <ul>
                        <li>Magic header: "REVENG" (6 bytes)</li>
                        <li>Version: 2 bytes (little-endian)</li>
                        <li>Flag length: 2 bytes (little-endian)</li>
                        <li>Random data: 20 bytes (ignore this)</li>
                        <li>Encoded flag: [flag_length] bytes</li>
                        <li>Checksum: 1 byte (sum of encoded flag bytes mod 256)</li>
                    </ul>
                </div>
                
                <div class="hint">
                    <h3>Decoding Algorithm</h3>
                    <p>The flag is encoded with a simple XOR operation using the key 42 (decimal).</p>
                    <p>Here's a Python snippet to help you decode it:</p>
                    <pre><code>
# Assuming you've extracted the encoded flag bytes into 'encoded_flag'
xor_key = 42
decoded_flag = ''.join([chr(b ^ xor_key) for b in encoded_flag])
print(decoded_flag)
                    </code></pre>
                </div>
                
                <a href="/">Back to Challenge</a>
            </div>
        </body>
    </html>
    ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
