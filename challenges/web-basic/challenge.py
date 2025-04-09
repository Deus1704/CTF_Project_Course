from flask import Flask, request, render_template_string
import os

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')

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
            </style>
        </head>
        <body>
            <h1>Welcome to the Web Basic Challenge</h1>
            <p>Can you find the hidden flag?</p>
            <p class="hint">Hint: Check the page source and HTTP headers</p>
            <!-- Flag hint: The flag is not in the HTML comments -->
        </body>
    </html>
    ''')

@app.route('/check')
def check():
    # The flag is hidden in the HTTP headers
    response = app.make_response("Nothing to see here in the body...")
    response.headers['X-Secret-Flag'] = FLAG
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
