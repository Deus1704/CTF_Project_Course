import hashlib
import random
from flask import Flask, session, request, jsonify

app = Flask(__name__)

app.secret_key = "your_super_secret_key"


CTF_SECRET_PREFIX = "ctf_challenge_"  # This need to be different for each challenge. Customly set for a challenge
HASH_ALGORITHM = hashlib.sha256


## Main flag generation code;
def generate_ctf_flag(user_unique_id):
    """Generate unique non-guessable flag for a user"""
    challenge_secret = f"{CTF_SECRET_PREFIX}{user_unique_id}"
    return f"CTF{{{HASH_ALGORITHM(challenge_secret.encode()).hexdigest()}}}"

## Code to verify the hash
def verify_ctf_flag(user_input, user_unique_id):
    """Validate user-submitted flag against generated value"""
    expected_flag = generate_ctf_flag(user_unique_id)
    return user_input.strip() == expected_flag

@app.route('/generate_flag')
def generate_flag():
    # Check if the user is authenticated; here we use session as an example.
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # Generate a unique ID for this session/user. In a real-world scenario,
    # you might fetch/store this in a database.
    user_unique_id = ''.join(random.choices('0123456789', k=10))
    # Store the unique id in session for later verification
    session['user_unique_id'] = user_unique_id

    flag = generate_ctf_flag(user_unique_id)
    return jsonify({"flag": flag})

@app.route('/submit_flag', methods=['POST'])
def submit_flag():
    if 'user_id' not in session or 'user_unique_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # Get flag from form data (or JSON if preferred)
    user_input = request.form.get('flag', '')
    is_valid = verify_ctf_flag(user_input, session['user_unique_id'])

    return jsonify({
        "correct": is_valid,
        "message": "Correct flag!" if is_valid else "Invalid flag"
    })

# For testing purposes, we simulate a login route.
@app.route('/login')
def login():
    # In a real challenge, you would implement proper authentication.
    session['user_id'] = "example_user"
    return f"Logged in! Now you can access /generate_flag \n the user_id that is never shown to the user={session['user_id']}"

if __name__ == '__main__':
    app.run(debug=True)
