from flask import Flask, request, render_template_string, send_file, redirect, url_for
import os
import io
import tempfile
import subprocess
import random
import string
import time
import base64

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')

# Create a temporary directory for storing generated files
TEMP_DIR = tempfile.mkdtemp()

def create_simple_pcap_file(flag):
    """Create a simple PCAP file with the flag embedded in it"""
    # Create a unique filename
    pcap_path = os.path.join(TEMP_DIR, f"capture_{int(time.time())}.pcap")
    
    # Since we might not have tcpdump/tshark available in all environments,
    # we'll create a simple binary file that looks like a PCAP
    # In a real environment, you would use proper tools to create a valid PCAP
    
    # PCAP Global Header (simplified)
    pcap_header = bytes.fromhex(
        "d4c3b2a1" +  # Magic Number
        "0200" +      # Major Version
        "0400" +      # Minor Version
        "00000000" +  # GMT to local correction
        "00000000" +  # Accuracy of timestamps
        "ffff0000" +  # Snaplen
        "01000000"    # Data Link Type (1 = Ethernet)
    )
    
    # Create a packet with the flag in it
    packet_data = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>Secret flag: {flag}</body></html>".encode()
    
    # Packet header
    packet_header = bytes.fromhex(
        "00000000" +  # Timestamp seconds
        "00000000" +  # Timestamp microseconds
        f"{len(packet_data):08x}" +  # Captured Length
        f"{len(packet_data):08x}"    # Actual Length
    )
    
    # Write the PCAP file
    with open(pcap_path, 'wb') as f:
        f.write(pcap_header)
        f.write(packet_header)
        f.write(packet_data)
    
    return pcap_path

@app.route('/')
def index():
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
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Network Traffic Analysis Challenge</h1>
                
                <p>Welcome to the network traffic analysis challenge! In this challenge, you need to analyze a packet capture (PCAP) file to find a hidden flag.</p>
                
                <div class="hint">
                    <p><strong>Hint:</strong> Look for HTTP traffic and examine the response content carefully.</p>
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
                        <li>Look for HTTP traffic in the capture</li>
                        <li>Check the content of HTTP responses</li>
                        <li>The flag is hidden in plain text within the traffic</li>
                    </ul>
                </div>
            </div>
        </body>
    </html>
    ''')

@app.route('/download')
def download_pcap():
    pcap_path = create_simple_pcap_file(FLAG)
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
    app.run(host='0.0.0.0', port=5000, debug=False)
