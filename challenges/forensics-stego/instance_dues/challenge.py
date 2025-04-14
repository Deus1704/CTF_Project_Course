from flask import Flask, request, render_template_string, send_file, redirect, url_for
import os
import io
from PIL import Image
import numpy as np
import tempfile

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')

# Create a temporary directory for storing generated images
TEMP_DIR = tempfile.mkdtemp()

def hide_flag_in_image(flag):
    """Hide the flag in the least significant bits of an image"""
    # Create a colorful gradient image
    width, height = 600, 400
    image = Image.new('RGB', (width, height))
    pixels = image.load()
    
    # Create a gradient background
    for x in range(width):
        for y in range(height):
            r = int(255 * (x / width))
            g = int(255 * (y / height))
            b = int(255 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)
    
    # Convert flag to binary
    binary_flag = ''.join(format(ord(char), '08b') for char in flag)
    
    # Add a marker to know where the flag ends
    binary_flag += '00000000'  # End marker
    
    # Hide the binary flag in the least significant bit of the red channel
    index = 0
    for y in range(height):
        for x in range(width):
            if index < len(binary_flag):
                r, g, b = pixels[x, y]
                # Set the least significant bit of the red channel
                r = (r & ~1) | int(binary_flag[index])
                pixels[x, y] = (r, g, b)
                index += 1
            else:
                break
    
    # Save the image to a temporary file
    image_path = os.path.join(TEMP_DIR, 'stego_image.png')
    image.save(image_path)
    return image_path

@app.route('/')
def index():
    # Generate the steganography image with the flag
    image_path = hide_flag_in_image(FLAG)
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Steganography Challenge</title>
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
                .challenge-image {
                    margin: 20px 0;
                    border: 1px solid #ddd;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
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
                <h1>Hidden Secrets: Steganography Challenge</h1>
                
                <p>Welcome to the steganography challenge! In this challenge, you need to find a hidden flag in the image below.</p>
                
                <div class="hint">
                    <p><strong>Hint:</strong> The flag is hidden in the least significant bits (LSB) of the image. You might need a steganography tool to extract it.</p>
                </div>
                
                <div class="challenge-image">
                    <img src="/image" alt="Steganography Challenge Image" style="max-width: 100%;">
                </div>
                
                <p>Once you've found the flag, submit it below:</p>
                
                <form action="/check" method="POST">
                    <input type="text" name="answer" placeholder="Enter the flag you found">
                    <button type="submit">Submit</button>
                </form>
                
                <div class="resources">
                    <h3>Helpful Resources</h3>
                    <ul>
                        <li>You can use tools like <a href="https://github.com/zed-0xff/zsteg" target="_blank">zsteg</a>, <a href="https://github.com/DominicBreuker/stego-toolkit" target="_blank">stegsolve</a>, or online steganography tools</li>
                        <li>Learn about <a href="https://en.wikipedia.org/wiki/Steganography" target="_blank">steganography techniques</a></li>
                        <li>The flag is hidden in the least significant bit (LSB) of the red channel</li>
                    </ul>
                </div>
            </div>
        </body>
    </html>
    ''')

@app.route('/image')
def serve_image():
    image_path = hide_flag_in_image(FLAG)
    return send_file(image_path, mimetype='image/png')

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
                        <p>You've successfully solved the steganography challenge!</p>
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
                        <p>Sorry, that's not the correct flag. Keep trying!</p>
                    </div>
                    <a href="/">Try again</a>
                </div>
            </body>
        </html>
        ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
