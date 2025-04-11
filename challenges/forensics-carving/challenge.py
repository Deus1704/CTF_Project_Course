from flask import Flask, request, render_template_string, send_file, redirect, url_for
import os
import io
import tempfile
import random
import string
import time

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')

# Create a temporary directory for storing generated files
TEMP_DIR = tempfile.mkdtemp()

def create_file_with_hidden_data(flag):
    """Create a file with hidden data (flag) inside"""
    # Create a unique filename
    file_path = os.path.join(TEMP_DIR, f"forensic_challenge_{int(time.time())}.dat")
    
    # Create some random data
    random_data = ''.join(random.choices(string.ascii_letters + string.digits, k=1024)).encode()
    
    # Create a JPEG-like header
    jpeg_header = bytes.fromhex("FFD8FFE000104A4649460001")
    
    # Create a PDF-like header
    pdf_header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"
    
    # Create a ZIP-like header
    zip_header = bytes.fromhex("504B0304")
    
    # Combine everything with the flag hidden in the middle
    with open(file_path, 'wb') as f:
        f.write(jpeg_header)
        f.write(random_data[:256])
        f.write(pdf_header)
        f.write(random_data[256:512])
        f.write(f"FLAG: {flag}".encode())
        f.write(random_data[512:768])
        f.write(zip_header)
        f.write(random_data[768:])
    
    return file_path

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
        <head>
            <title>File Carving Challenge</title>
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
                <h1>File Carving Challenge</h1>
                
                <p>Welcome to the file carving challenge! In this challenge, you need to analyze a binary file to find a hidden flag.</p>
                
                <div class="hint">
                    <p><strong>Hint:</strong> The file contains multiple file signatures and hidden data. Look for text patterns that might indicate the flag.</p>
                </div>
                
                <p>Download the file and analyze it using forensic tools:</p>
                
                <a href="/download" class="download-btn">Download Challenge File</a>
                
                <p>Once you've found the flag, submit it below:</p>
                
                <form action="/check" method="POST">
                    <input type="text" name="answer" placeholder="Enter the flag you found">
                    <button type="submit">Submit</button>
                </form>
                
                <div class="resources">
                    <h3>Helpful Resources</h3>
                    <ul>
                        <li>Use a hex editor like <a href="https://hexed.it/" target="_blank">hexed.it</a> to examine the file</li>
                        <li>Look for file signatures (magic numbers) that might indicate embedded files</li>
                        <li>Search for text strings like "FLAG" in the binary data</li>
                        <li>Try tools like <a href="https://github.com/sleuthkit/sleuthkit" target="_blank">The Sleuth Kit</a> or <a href="https://github.com/ReFirmLabs/binwalk" target="_blank">Binwalk</a> for file carving</li>
                    </ul>
                </div>
            </div>
        </body>
    </html>
    ''')

@app.route('/download')
def download_file():
    file_path = create_file_with_hidden_data(FLAG)
    return send_file(file_path, as_attachment=True, download_name="forensic_challenge.dat")

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
                        <p>You've successfully solved the file carving challenge!</p>
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
                        <p>Sorry, that's not the correct flag. Keep analyzing the file!</p>
                    </div>
                    <a href="/">Try again</a>
                </div>
            </body>
        </html>
        ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
