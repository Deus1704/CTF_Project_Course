from flask import Flask, request, render_template_string, send_file, redirect, url_for
import os
import io
import tempfile
import subprocess
import random
import string
import time

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')

# Create a temporary directory for storing generated pcap files
TEMP_DIR = tempfile.mkdtemp()

def generate_pcap_with_flag(flag):
    """Generate a PCAP file with the flag hidden in HTTP traffic"""
    # Create a unique filename for this user's pcap
    pcap_path = os.path.join(TEMP_DIR, f"capture_{int(time.time())}.pcap")
    
    # Create a text file with the flag to be transferred via HTTP
    flag_file = os.path.join(TEMP_DIR, "secret.txt")
    with open(flag_file, 'w') as f:
        f.write(f"Congratulations! You found the secret flag: {flag}")
    
    # Use tcpreplay or scapy to generate a pcap file
    # For simplicity, we'll create a basic HTTP traffic simulation
    # In a real scenario, you would use more sophisticated tools
    
    # Create a simple HTTP request/response with the flag
    http_data = f"""
POST /login HTTP/1.1
Host: secretserver.ctf
Content-Type: application/x-www-form-urlencoded
Content-Length: {len(flag) + 10}

username=admin&password={flag}

HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 42

<html><body>Login successful!</body></html>
"""
    
    # Create a text file with the HTTP data
    http_file = os.path.join(TEMP_DIR, "http_data.txt")
    with open(http_file, 'w') as f:
        f.write(http_data)
    
    # Use text2pcap to convert the text representation to a pcap file
    try:
        subprocess.run([
            "text2pcap", 
            "-T", "8080,80", 
            "-D", "10.0.0.1,192.168.1.1",
            http_file, 
            pcap_path
        ], check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        # If text2pcap is not available, create a dummy file with instructions
        with open(pcap_path, 'w') as f:
            f.write(f"This is a simulated PCAP file. In a real environment, this would contain network traffic with the flag: {flag}")
    
    return pcap_path

@app.route('/')
def index():
    # Generate the PCAP file with the flag
    pcap_path = generate_pcap_with_flag(FLAG)
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Network Traffic Analysis Challenge</title>
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
                button, .download-btn { 
                    padding: 8px 16px; 
                    background: #2c3e50; 
                    color: white; 
                    border: none; 
                    cursor: pointer;
                    border-radius: 3px;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 10px;
                }
                button:hover, .download-btn:hover {
                    background: #1a252f;
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
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Network Traffic Analysis Challenge</h1>
                
                <p>Welcome to the network traffic analysis challenge! In this challenge, you need to analyze a packet capture (PCAP) file to find a hidden flag.</p>
                
                <div class="hint">
                    <p><strong>Hint:</strong> Look for HTTP traffic and examine the request parameters carefully.</p>
                </div>
                
                <p>Download the PCAP file and analyze it using tools like Wireshark:</p>
                
                <a href="/download" class="download-btn">Download PCAP File</a>
                
                <p>Once you've found the flag, submit it below:</p>
                
                <form action="/check" method="POST">
                    <input type="text" name="answer" placeholder="Enter the flag you found">
                    <button type="submit">Submit</button>
                </form>
                
                <div class="resources">
                    <h3>Helpful Resources</h3>
                    <ul>
                        <li>Use <a href="https://www.wireshark.org/" target="_blank">Wireshark</a> to analyze the PCAP file</li>
                        <li>Look for HTTP POST requests in the traffic</li>
                        <li>Check for sensitive information in form submissions</li>
                        <li>The flag is hidden in a login request</li>
                    </ul>
                </div>
            </div>
        </body>
    </html>
    ''')

@app.route('/download')
def download_pcap():
    pcap_path = generate_pcap_with_flag(FLAG)
    return send_file(pcap_path, as_attachment=True, download_name="network_capture.pcap")

@app.route('/check', methods=['POST'])
def check():
    answer = request.form.get('answer', '')
    
    if answer == FLAG:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
            <head>
                <title>Success!</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 40px; 
                        line-height: 1.6;
                        color: #333;
                    }
                    h1 { color: #27ae60; }
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                        text-align: center;
                    }
                    .success-message {
                        background-color: #d4edda;
                        color: #155724;
                        padding: 20px;
                        border-radius: 5px;
                        margin: 20px 0;
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
                    <h1>Congratulations!</h1>
                    <div class="success-message">
                        <p>You've successfully solved the network traffic analysis challenge!</p>
                        <p>The flag is: <strong>{{ flag }}</strong></p>
                    </div>
                    <a href="/">Try again</a>
                </div>
            </body>
        </html>
        ''', flag=FLAG)
    else:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
            <head>
                <title>Incorrect</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 40px; 
                        line-height: 1.6;
                        color: #333;
                    }
                    h1 { color: #e74c3c; }
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                        text-align: center;
                    }
                    .error-message {
                        background-color: #f8d7da;
                        color: #721c24;
                        padding: 20px;
                        border-radius: 5px;
                        margin: 20px 0;
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
                    <h1>Incorrect Flag</h1>
                    <div class="error-message">
                        <p>Sorry, that's not the correct flag. Keep analyzing the PCAP file!</p>
                    </div>
                    <a href="/">Try again</a>
                </div>
            </body>
        </html>
        ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
