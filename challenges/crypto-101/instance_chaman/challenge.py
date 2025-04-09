from flask import Flask, request, render_template_string, redirect, url_for
import base64
import os

app = Flask(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('CTF_FLAG', 'default_flag_please_set_env_variable')

@app.route('/')
def index():
    return render_template_string('''
    <html>
        <head>
            <title>Crypto 101 Challenge</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .hint { color: #666; font-style: italic; }
                form { margin: 20px 0; }
                input[type="text"] { padding: 8px; width: 300px; }
                button { padding: 8px 16px; background: #4CAF50; color: white; border: none; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>Crypto 101 Challenge</h1>
            <p>I've encoded a secret message. Can you decode it?</p>
            <p class="hint">Hint: It's a common encoding scheme</p>

            <div>
                <p>Encoded message:</p>
                <code>{{ encoded_message }}</code>
            </div>

            <form action="/check" method="POST">
                <input type="text" name="answer" placeholder="Enter the decoded message">
                <button type="submit">Submit</button>
            </form>
        </body>
    </html>
    ''', encoded_message=base64.b64encode(FLAG.encode()).decode())

@app.route('/check', methods=['POST'])
def check():
    answer = request.form.get('answer', '')

    if answer == FLAG:
        return render_template_string('''
        <html>
            <head>
                <title>Success!</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    h1 { color: #4CAF50; }
                </style>
            </head>
            <body>
                <h1>Congratulations!</h1>
                <p>You've successfully solved the challenge!</p>
                <p>The flag is: {{ flag }}</p>
                <a href="/">Try again</a>
            </body>
        </html>
        ''', flag=FLAG)
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
