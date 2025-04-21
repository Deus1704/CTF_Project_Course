print("Starting application...")
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import hashlib
import os
import subprocess
import threading
import secrets
import time
import socket
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Challenge, Submission, Hint, Achievement, Token
print("Imports completed successfully")

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ctf.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# In-memory storage for container management
active_containers = {}

# Challenge timeout in seconds (5 minutes for better user experience)
CHALLENGE_TIMEOUT = 300

# Challenge base directory
CHALLENGE_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "challenges")

# Function to get the host IP address
def get_host_ip():
    try:
        # Create a socket to connect to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to be reachable, just to determine the interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Error getting host IP: {e}")
        return "localhost"

# Get the host IP address
HOST_IP = get_host_ip()
print(f"Host IP address: {HOST_IP}")

# Docker template for challenges
DOCKER_TEMPLATE = """
FROM python:3.9-slim
WORKDIR /app
RUN pip install flask requests
COPY . .
# Use the secure challenge template if challenge.py doesn't exist
RUN if [ ! -f challenge.py ]; then cp /app/challenge_template.py /app/challenge.py; fi
CMD ["python", "challenge.py"]
"""


def generate_flag(user_id, challenge_id):
    secret_seed = "CTF_SECRET_SALT"  # Change in production
    return hashlib.sha256(
        f"{user_id}{challenge_id}{secret_seed}".encode()
    ).hexdigest()

class ChallengeLoader:
    def __init__(self, challenge_id):
        self.challenge_id = challenge_id
        self.path = os.path.join(CHALLENGE_BASE, challenge_id)

    def build_container(self, flag, user_id):
        # Create a user-specific directory for this challenge
        user_challenge_dir = os.path.join(self.path, f"instance_{user_id}")
        os.makedirs(user_challenge_dir, exist_ok=True)

        # Copy all files from the challenge directory to the user-specific directory
        for file_name in os.listdir(self.path):
            if file_name.startswith("instance_"):
                continue  # Skip other user instances

            src_path = os.path.join(self.path, file_name)
            if os.path.isfile(src_path):
                dst_path = os.path.join(user_challenge_dir, file_name)
                try:
                    # Try to open the file as text first
                    with open(src_path, "r") as src_file, open(dst_path, "w") as dst_file:
                        dst_file.write(src_file.read())
                except UnicodeDecodeError:
                    # If it fails, it's probably a binary file
                    with open(src_path, "rb") as src_file, open(dst_path, "wb") as dst_file:
                        dst_file.write(src_file.read())

        # We no longer need to inject the flag into the challenge file
        # as it will be passed as an environment variable
        print(f"Flag {flag} will be passed as environment variable to the container")

        # Create Dockerfile in the user-specific challenge directory if it doesn't exist
        dockerfile_path = os.path.join(user_challenge_dir, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            print(f"Creating Dockerfile at: {dockerfile_path}")
            with open(dockerfile_path, "w") as f:
                f.write(DOCKER_TEMPLATE)

            # Verify Dockerfile was created
            if os.path.exists(dockerfile_path):
                print(f"Dockerfile created successfully at {dockerfile_path}")
                with open(dockerfile_path, "r") as f:
                    print(f"Dockerfile content:\n{f.read()}")
            else:
                print(f"Failed to create Dockerfile at {dockerfile_path}")

        # Build Docker image with a user-specific tag
        image_tag = f"ctf_{self.challenge_id}_{user_id}".lower()
        print(f"Building Docker image {image_tag}")
        result = subprocess.run([
            "docker", "build", "-t",
            image_tag, "."
        ], cwd=user_challenge_dir, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Docker build failed with error:\n{result.stderr}")
            raise Exception(f"Docker build failed: {result.stderr}")
        else:
            print(f"Docker build succeeded for {image_tag}")

        return user_challenge_dir, image_tag

    def find_available_port(self, start_port=10000, max_attempts=100):
        """Find an available port starting from start_port"""
        import socket
        import random

        # Also check if any active containers are already using ports
        used_ports = set()
        for container_info in active_containers.values():
            used_ports.add(container_info.get('port', 0))

        # Check Docker to see if any ports are already bound
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Ports}}"],
                capture_output=True, text=True, check=True
            )
            # Parse port mappings from Docker output
            for line in result.stdout.strip().split('\n'):
                if line and '->5000/tcp' in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        port_part = parts[1].split('->', 1)[0]
                        try:
                            used_ports.add(int(port_part))
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Warning: Could not check Docker ports: {e}")

        # Try ports in a randomized order to reduce collision chance in multi-user scenarios
        port_range = list(range(start_port, start_port + max_attempts))
        random.shuffle(port_range)

        for port in port_range:
            if port in used_ports:
                continue

            # Check if port is available using socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", port))
                    print(f"Found available port: {port}")
                    return port
                except OSError:
                    print(f"Port {port} is not available, trying next port")
                    continue

        raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

    def run_container(self, user_id, flag):
        print(f"[DEBUG] Running container for user {user_id}, challenge {self.challenge_id}")
        # Check if this specific user already has a container for this challenge
        for container_id, info in active_containers.items():
            if info.get('challenge') == self.challenge_id and info.get('user') == user_id:
                try:
                    # Check if container is still running
                    print(f"[DEBUG] Checking if container {container_id} is running")
                    result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                                           capture_output=True, text=True)
                    print(f"[DEBUG] Docker inspect result: {result.stdout}")
                    if "true" in result.stdout.lower():
                        port = info.get('port')
                        print(f"User {user_id} already has challenge {self.challenge_id} running on port {port}")
                        return port, container_id
                    else:
                        # Container exists but is not running, remove it
                        print(f"Container {container_id} exists but is not running, removing it")
                        subprocess.run(["docker", "rm", container_id], capture_output=True, check=False)
                        active_containers.pop(container_id, None)
                except subprocess.CalledProcessError as e:
                    # Container doesn't exist anymore, remove from active_containers
                    print(f"Container {container_id} no longer exists, error: {e}")
                    active_containers.pop(container_id, None)

        # Find an available port
        port = self.find_available_port()
        print(f"Starting container for user {user_id}, challenge {self.challenge_id} on port {port}")

        try:
            # Check if the image exists
            image_tag = f"ctf_{self.challenge_id}_{user_id}"
            image_check = subprocess.run(["docker", "images", image_tag, "--format", "{{.ID}}"],
                                        capture_output=True, text=True)
            print(f"[DEBUG] Image check result: {image_check.stdout}")

            if not image_check.stdout.strip():
                print(f"[DEBUG] Image {image_tag} not found, rebuilding...")
                self.build_container(flag, user_id)

            # Pass the flag as an environment variable to the container
            print(f"[DEBUG] Running Docker container with command: docker run -d -p {port}:5000 -e CTF_FLAG={flag} {image_tag}")

            # Get the host URL using the actual host IP instead of localhost
            host_port = request.host.split(':')[-1] if ':' in request.host else "5002"
            host_url = f"http://{HOST_IP}:{host_port}/"

            # Get user token if available
            user_token = ''
            if hasattr(request, 'headers') and request.headers.get('Authorization'):
                user_token = request.headers.get('Authorization')

            # Run the container first
            container_id = subprocess.check_output([
                "docker", "run",
                "-d",  # Detached mode
                "--restart", "unless-stopped",  # Restart policy
                "-p", f"{port}:5000",  # Port mapping
                "-e", f"CTF_FLAG={flag}",  # Flag environment variable
                "-e", f"MAIN_SITE={host_url}",  # Main site URL for redirect
                "-e", f"CHALLENGE_ID={self.challenge_id}",  # Challenge ID
                "-e", f"USER_TOKEN={user_token}",  # User token for authentication
                "-e", f"USER_ID={user_id}",  # User ID for verification
                "--memory", "256m",  # Memory limit
                "--cpus", "0.5",  # CPU limit
                image_tag
            ]).decode().strip()

            # Now that we have the container ID, update it with the ID as an environment variable
            try:
                subprocess.run([
                    "docker", "exec", container_id,
                    "sh", "-c", f"echo 'export CONTAINER_ID={container_id}' >> /etc/environment"
                ], check=True)
            except Exception as e:
                print(f"Warning: Failed to set CONTAINER_ID in container: {e}")

            print(f"Container started with ID: {container_id}")

            # Wait a moment for the container to start
            time.sleep(1)

            # Verify container is running
            verify_result = subprocess.run(["docker", "ps", "--filter", f"id={container_id}", "--format", "{{.ID}}"],
                                          capture_output=True, text=True)
            print(f"[DEBUG] Verify container running: {verify_result.stdout}")

            if not verify_result.stdout.strip():
                # Container failed to start, check logs
                logs = subprocess.run(["docker", "logs", container_id], capture_output=True, text=True)
                print(f"[DEBUG] Container logs: {logs.stdout}\nErrors: {logs.stderr}")
                raise Exception(f"Container failed to start: {logs.stderr}")

            active_containers[container_id] = {
                "port": port,
                "challenge": self.challenge_id,
                "user": user_id,  # Store which user started this container
                "start_time": datetime.now(),  # Store when the container was started
                "image_tag": image_tag
            }
            return port, container_id
        except subprocess.CalledProcessError as e:
            print(f"Error starting container: {e}")
            print(f"Error output: {e.output.decode() if e.output else 'None'}")
            # Try to rebuild the image and try again
            try:
                print(f"[DEBUG] Attempting to rebuild image and retry...")
                self.build_container(flag, user_id)

                # Try running the container again with basic options
                container_id = subprocess.check_output([
                    "docker", "run", "-d", "-p",
                    f"{port}:5000", "-e", f"CTF_FLAG={flag}", f"ctf_{self.challenge_id}_{user_id}"
                ]).decode().strip()

                print(f"Container started with ID (retry): {container_id}")

                active_containers[container_id] = {
                    "port": port,
                    "challenge": self.challenge_id,
                    "user": user_id,
                    "start_time": datetime.now(),
                    "image_tag": f"ctf_{self.challenge_id}_{user_id}"
                }
                return port, container_id
            except Exception as retry_error:
                print(f"Retry failed: {retry_error}")
                raise

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Check if user exists
    user = User.query.filter_by(username=username).first()

    # If user doesn't exist, create a new one
    if not user:
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    elif not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Update last login time
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Create a new token
    token_value = secrets.token_urlsafe(32)
    token = Token(user_id=user.id, token=token_value)
    db.session.add(token)
    db.session.commit()

    # Create response with token in JSON
    response = jsonify({"token": token_value, "user_id": user.id, "username": user.username, "points": user.points, "is_admin": user.is_admin})

    # Set a cookie with the token for use with redirects from challenge containers
    response.set_cookie('ctf_token', token_value, httponly=True, max_age=86400)  # 24 hours

    return response

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Check if user exists and is an admin
    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_admin:
        return jsonify({"error": "Unauthorized: Not an admin user"}), 403

    # Update last login time
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Create a new token
    token_value = secrets.token_urlsafe(32)
    token = Token(user_id=user.id, token=token_value)
    db.session.add(token)
    db.session.commit()

    # Create response with token in JSON
    response = jsonify({"token": token_value, "user_id": user.id, "username": user.username, "is_admin": True})

    # Set a cookie with the token for use with redirects
    response.set_cookie('ctf_admin_token', token_value, httponly=True, max_age=86400)  # 24 hours

    return response

def verify_token(token_value):
    """Verify if a token is valid and return the associated user"""
    if not token_value:
        return None

    token = Token.query.filter_by(token=token_value, is_active=True).first()
    if not token:
        return None

    # Check if token is expired
    if token.expires_at and token.expires_at < datetime.now():
        token.is_active = False
        db.session.commit()
        return None

    return token.user

@app.route("/challenge/<challenge_id>/start", methods=["POST"])
def start_challenge(challenge_id):
    print(f"Starting challenge {challenge_id}")
    token_value = request.headers.get("Authorization")
    user = verify_token(token_value)

    if not user:
        print(f"Unauthorized: invalid or expired token")
        return jsonify({"error": "Unauthorized"}), 401

    user_id = user.username  # Use username for backward compatibility with Docker

    # Check if user already has this challenge running
    for container_id, info in active_containers.items():
        if info.get('challenge') == challenge_id and info.get('user') == user_id:
            try:
                # Check if container is still running
                result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                                        capture_output=True, text=True)
                if "true" in result.stdout.lower():
                    print(f"User {user_id} already has challenge {challenge_id} running on container {container_id}")
                    port = info.get('port')
                    flag = generate_flag(user_id, challenge_id)  # Regenerate the flag for consistency

                    # Check if user has already solved this challenge
                    challenge = Challenge.query.filter_by(challenge_id=challenge_id).first()
                    if challenge:
                        previous_correct = Submission.query.filter_by(
                            user_id=user.id,
                            challenge_id=challenge.id,
                            is_correct=True
                        ).first()

                        # Get the main site URL for redirection using the actual host IP
                        host_port = request.host.split(':')[-1] if ':' in request.host else "5002"
                        main_site = f"http://{HOST_IP}:{host_port}/"

                        # Include solved status in response
                        return jsonify({
                            "message": "Challenge already running",
                            "port": port,
                            "containerId": container_id,
                            "flag": flag,
                            "already_solved": previous_correct is not None,
                            "timeout": CHALLENGE_TIMEOUT,
                            "startTime": info.get('start_time').isoformat() if info.get('start_time') else datetime.now().isoformat(),
                            "main_site": main_site
                        })
                    else:
                        # Get the main site URL for redirection using the actual host IP
                        host_port = request.host.split(':')[-1] if ':' in request.host else "5002"
                        main_site = f"http://{HOST_IP}:{host_port}/"

                        return jsonify({
                            "message": "Challenge already running",
                            "port": port,
                            "containerId": container_id,
                            "flag": flag,
                            "already_solved": False,
                            "timeout": CHALLENGE_TIMEOUT,
                            "startTime": info.get('start_time').isoformat() if info.get('start_time') else datetime.now().isoformat(),
                            "main_site": main_site
                        })
            except Exception as e:
                print(f"Error checking container status: {e}")
                # Continue with starting a new container

    flag = generate_flag(user_id, challenge_id)

    # Process challenge template
    print(f"Processing challenge template for {challenge_id}")
    loader = ChallengeLoader(challenge_id)
    print(f"Building container for user {user_id} with flag {flag}")
    loader.build_container(flag, user_id)
    print(f"Running container for user {user_id}")
    port, container_id = loader.run_container(user_id, flag)
    print(f"Container started on port {port} with ID {container_id}")

    # Get the main site URL for redirection using the actual host IP
    host_port = request.host.split(':')[-1] if ':' in request.host else "5002"
    main_site = f"http://{HOST_IP}:{host_port}/"

    return jsonify({
        "message": "Challenge started",
        "port": port,
        "containerId": container_id,
        "flag": flag,  # Remove this in production!
        "timeout": CHALLENGE_TIMEOUT,
        "startTime": datetime.now().isoformat(),
        "main_site": main_site
    })

@app.route("/containers", methods=["GET"])
def list_containers():
    return jsonify(active_containers)

@app.route("/challenge/<container_id>/status", methods=["GET"])
def check_container_status(container_id):
    # Check if container exists in our records
    if container_id not in active_containers:
        return jsonify({"status": "not_found", "message": "Container not found"}), 404

    container_info = active_containers[container_id]
    start_time = container_info.get('start_time')

    if not start_time:
        return jsonify({"status": "unknown", "message": "Container start time unknown"}), 400

    # Calculate remaining time
    now = datetime.now()
    elapsed_seconds = (now - start_time).total_seconds()
    remaining_seconds = max(0, CHALLENGE_TIMEOUT - elapsed_seconds)

    # Check if container is still running in Docker
    try:
        result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                              capture_output=True, text=True)

        if result.returncode != 0 or "true" not in result.stdout.lower():
            # Container is not running
            return jsonify({
                "status": "stopped",
                "message": "Container is not running",
                "elapsed": elapsed_seconds,
                "remaining": 0
            })
    except Exception as e:
        print(f"Error checking container status: {e}")
        # Continue with time calculation even if Docker check fails

    # Return status with timing information
    return jsonify({
        "status": "running" if remaining_seconds > 0 else "expired",
        "elapsed": elapsed_seconds,
        "remaining": remaining_seconds,
        "timeout": CHALLENGE_TIMEOUT,
        "user": container_info.get('user'),
        "challenge": container_info.get('challenge'),
        "port": container_info.get('port')
    })

@app.route("/challenge/<container_id>/stop", methods=["POST"])
def stop_challenge(container_id):
    # Check if container exists in our records
    if container_id not in active_containers:
        # Check if it exists in Docker anyway and try to remove it
        try:
            result = subprocess.run(["docker", "inspect", container_id],
                                   capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Container {container_id} exists in Docker but not in our records, stopping it")
                subprocess.run(["docker", "stop", container_id], check=True)
                subprocess.run(["docker", "rm", container_id], check=True)
                return jsonify({"message": "Container stopped and removed"})
        except Exception as e:
            print(f"Error checking container: {e}")

        return jsonify({"error": "Container not found"}), 404

    try:
        print(f"Stopping container {container_id}")
        # Use capture_output to suppress Docker output
        subprocess.run(["docker", "stop", container_id],
                      capture_output=True, check=True)
        subprocess.run(["docker", "rm", container_id],
                      capture_output=True, check=True)

        challenge_info = active_containers.pop(container_id)
        print(f"Container {container_id} stopped and removed")
        return jsonify({
            "message": "Challenge stopped",
            "challenge": challenge_info["challenge"]
        })
    except subprocess.CalledProcessError as e:
        print(f"Error stopping container: {e}")
        # If the container doesn't exist anymore, remove it from our records
        if "No such container" in str(e.stderr):
            active_containers.pop(container_id, None)
            return jsonify({"message": "Container was already removed"})
        return jsonify({"error": "Failed to stop container"}), 500

@app.route("/")
def index():
    # Check if there's a flag success parameter
    flag_success = request.args.get('flag_success') == 'true'
    challenge_id = request.args.get('challenge')
    container_id = request.args.get('container_id')
    auto_show = request.args.get('auto_show') == 'true'

    # Prepare context for template
    context = {
        'title': "CTF Platform",
        'flag_success': flag_success,
        'challenge_id': challenge_id,
        'container_id': container_id,
        'auto_show': auto_show,
        'points_earned': 0,
        'challenge_name': '',
        'host_ip': HOST_IP  # Pass the host IP to the template
    }

    # If flag was successfully submitted from a challenge container
    if flag_success and challenge_id:
        # Get the user from the session cookie if available
        session_token = request.cookies.get('ctf_token')
        auth_header = request.headers.get('Authorization')

        # Try to get token from cookie or header
        token = session_token or auth_header

        # If no token, redirect to login page
        if not token:
            return redirect('/login.html')

        # Verify the token
        user = verify_token(token)
        if not user:
            # Invalid token, redirect to login
            return redirect('/login.html')

        # Verify that this user is the one who started the challenge
        if container_id and container_id in active_containers:
            container_info = active_containers.get(container_id)
            if container_info.get('user') != user.username:
                # This user didn't start this challenge
                flash("You cannot claim points for a challenge started by another user.", "error")
                return render_template('index.html', title="CTF Platform", host_ip=HOST_IP)

        # User is authenticated and verified
        # Get the challenge
        challenge = Challenge.query.filter_by(challenge_id=challenge_id).first()
        if challenge:
            context['challenge_name'] = challenge.name

            # Check if this is the first correct submission for this challenge
            previous_correct = Submission.query.filter_by(
                user_id=user.id,
                challenge_id=challenge.id,
                is_correct=True
            ).first()

            if not previous_correct:
                # Record the submission
                submission = Submission(
                    user_id=user.id,
                    challenge_id=challenge.id,
                    flag=generate_flag(user.username, challenge_id),  # We don't have the actual flag, but we can regenerate it
                    is_correct=True,
                    points_awarded=challenge.points
                )
                db.session.add(submission)

                # Award points to the user
                user.points += challenge.points
                db.session.commit()

                # Add points to context
                context['points_earned'] = challenge.points

                # Set a flash message
                flash(f"Congratulations! You earned {challenge.points} points for solving {challenge.name}!", "success")
            else:
                # Even if already solved, we need to show the points that were earned
                previous_submission = Submission.query.filter_by(
                    user_id=user.id,
                    challenge_id=challenge.id,
                    is_correct=True
                ).first()

                if previous_submission:
                    context['points_earned'] = previous_submission.points_awarded
                else:
                    context['points_earned'] = challenge.points

                flash("You've already solved this challenge!", "info")

            # Try to stop the container for this challenge
            try:
                # If container_id is provided in the URL, use it
                if container_id:
                    # Stop and remove the container - use check_call for synchronous execution
                    print(f"Stopping container {container_id} after successful flag submission")
                    try:
                        # Force stop and remove the container
                        subprocess.check_call(["docker", "stop", container_id])
                        subprocess.check_call(["docker", "rm", "-f", container_id])
                        print(f"Container {container_id} has been stopped and removed")

                        # Remove from active containers
                        if container_id in active_containers:
                            active_containers.pop(container_id, None)
                            print(f"Removed container {container_id} from active containers")
                    except subprocess.CalledProcessError as e:
                        print(f"Error stopping container: {e}")
                        # Try to find the container by name/ID pattern
                        try:
                            # Get all containers for this challenge and user
                            result = subprocess.check_output(["docker", "ps", "-q", "--filter", f"name={challenge_id}-{user.username}"], text=True)
                            container_ids = result.strip().split('\n')
                            for c_id in container_ids:
                                if c_id:
                                    print(f"Found container {c_id} for challenge {challenge_id}, stopping it")
                                    subprocess.call(["docker", "stop", c_id])
                                    subprocess.call(["docker", "rm", "-f", c_id])
                        except Exception as inner_e:
                            print(f"Error finding containers by pattern: {inner_e}")
                else:
                    # Find the container for this user and challenge
                    found = False
                    for c_id, info in list(active_containers.items()):
                        if info.get('challenge') == challenge_id and info.get('user') == user.username:
                            container_id = c_id
                            context['container_id'] = container_id
                            found = True

                            # Stop and remove the container
                            print(f"Stopping container {container_id} after successful flag submission")
                            try:
                                subprocess.check_call(["docker", "stop", container_id])
                                subprocess.check_call(["docker", "rm", "-f", container_id])
                                print(f"Container {container_id} has been stopped and removed")
                            except subprocess.CalledProcessError as e:
                                print(f"Error stopping container: {e}")

                            # Remove from active containers
                            active_containers.pop(container_id, None)
                            print(f"Removed container {container_id} from active containers")
                            break

                    # If not found in active_containers, try to find by pattern
                    if not found:
                        try:
                            # Get all containers for this challenge and user
                            result = subprocess.check_output(["docker", "ps", "-q", "--filter", f"name={challenge_id}-{user.username}"], text=True)
                            container_ids = result.strip().split('\n')
                            for c_id in container_ids:
                                if c_id:
                                    print(f"Found container {c_id} for challenge {challenge_id}, stopping it")
                                    subprocess.call(["docker", "stop", c_id])
                                    subprocess.call(["docker", "rm", "-f", c_id])
                        except Exception as inner_e:
                            print(f"Error finding containers by pattern: {inner_e}")
            except Exception as e:
                print(f"Error stopping container: {e}")

            # Set a flag to show the celebration effect
            context['show_celebration'] = True
            context['challenge_solved'] = True

    return render_template('index.html', **context)

@app.route("/admin")
def admin_panel():
    return render_template('admin.html', title="CTF Platform - Admin Panel")

@app.route("/leaderboard")
def leaderboard():
    """Get the leaderboard of top users by points"""
    # Use a more efficient query with a subquery to count solved challenges
    from sqlalchemy import func, distinct

    # Get the count of distinct challenges solved by each user
    solved_challenges_subquery = db.session.query(
        Submission.user_id,
        func.count(distinct(Submission.challenge_id)).label('solved_count')
    ).filter(Submission.is_correct == True).group_by(Submission.user_id).subquery()

    # Join with the User table and order by points
    leaderboard_query = db.session.query(
        User,
        solved_challenges_subquery.c.solved_count
    ).outerjoin(
        solved_challenges_subquery,
        User.id == solved_challenges_subquery.c.user_id
    ).order_by(User.points.desc(), solved_challenges_subquery.c.solved_count.desc())

    # Get top 10 users
    top_users = leaderboard_query.limit(10).all()

    # Format the response
    leaderboard_data = [{
        'username': user.username,
        'points': user.points,
        'solved_challenges': solved_count if solved_count is not None else 0,
        'rank': index + 1  # Add rank based on position
    } for index, (user, solved_count) in enumerate(top_users)]

    return jsonify(leaderboard_data)

@app.route("/user/profile")
def user_profile():
    """Get the profile of the current user"""
    token_value = request.headers.get("Authorization")
    user = verify_token(token_value)

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # Get solved challenges
    solved_submissions = Submission.query.filter_by(user_id=user.id, is_correct=True).all()
    solved_challenge_ids = [sub.challenge_id for sub in solved_submissions]

    # Get challenges the user has solved
    solved_challenges = Challenge.query.filter(Challenge.id.in_(solved_challenge_ids)).all() if solved_challenge_ids else []

    # Get user achievements
    achievements = [{
        'name': achievement.name,
        'description': achievement.description,
        'badge_image': achievement.badge_image,
        'points': achievement.points
    } for achievement in user.achievements]

    # Get recent submissions
    recent_submissions = Submission.query.filter_by(user_id=user.id).order_by(Submission.submitted_at.desc()).limit(5).all()

    # Get user's rank
    from sqlalchemy import func, distinct

    # Count users with more points than the current user
    rank_query = db.session.query(func.count(User.id) + 1).filter(User.points > user.points)
    user_rank = rank_query.scalar()

    # If there are users with the same points, use solved challenges as a tiebreaker
    if user_rank == 1:
        # Check if there are other users with the same points
        same_points_users = User.query.filter(User.points == user.points, User.id != user.id).all()
        if same_points_users:
            # Count solved challenges for current user
            user_solved_count = Submission.query.filter_by(user_id=user.id, is_correct=True).distinct(Submission.challenge_id).count()

            # Count users with same points but more solved challenges
            for other_user in same_points_users:
                other_solved_count = Submission.query.filter_by(user_id=other_user.id, is_correct=True).distinct(Submission.challenge_id).count()
                if other_solved_count > user_solved_count:
                    user_rank += 1

    return jsonify({
        'username': user.username,
        'points': user.points,
        'rank': user_rank,
        'solved_challenges': [{
            'id': challenge.challenge_id,
            'name': challenge.name,
            'category': challenge.category,
            'difficulty': challenge.difficulty,
            'points': challenge.points
        } for challenge in solved_challenges],
        'achievements': achievements,
        'recent_submissions': [{
            'challenge_name': Challenge.query.get(sub.challenge_id).name if Challenge.query.get(sub.challenge_id) else 'Unknown',
            'is_correct': sub.is_correct,
            'points_awarded': sub.points_awarded,
            'submitted_at': sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
        } for sub in recent_submissions]
    })

@app.route("/admin/users")
def admin_users():
    """Get all users for admin panel"""
    token_value = request.headers.get("Authorization")
    user = verify_token(token_value)

    if not user or not user.is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    # Use a more efficient query with a subquery to count solved challenges
    from sqlalchemy import func, distinct

    # Get the count of distinct challenges solved by each user
    solved_challenges_subquery = db.session.query(
        Submission.user_id,
        func.count(distinct(Submission.challenge_id)).label('solved_count')
    ).filter(Submission.is_correct == True).group_by(Submission.user_id).subquery()

    # Join with the User table and order by points
    users_query = db.session.query(
        User,
        solved_challenges_subquery.c.solved_count
    ).outerjoin(
        solved_challenges_subquery,
        User.id == solved_challenges_subquery.c.user_id
    ).order_by(User.points.desc(), solved_challenges_subquery.c.solved_count.desc())

    # Get all users
    users_with_counts = users_query.all()

    # Format the response with ranks
    user_data = [{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'points': u.points,
        'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'last_login': u.last_login.strftime('%Y-%m-%d %H:%M:%S') if u.last_login else None,
        'is_admin': u.is_admin,
        'solved_challenges': solved_count if solved_count is not None else 0,
        'rank': index + 1  # Add rank based on position
    } for index, (u, solved_count) in enumerate(users_with_counts)]

    return jsonify(user_data)

@app.route("/admin/challenges")
def admin_challenges():
    """Get all challenges for admin panel"""
    token_value = request.headers.get("Authorization")
    user = verify_token(token_value)

    if not user or not user.is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    challenges = Challenge.query.all()

    challenge_data = [{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'category': c.category,
        'difficulty': c.difficulty,
        'points': c.points,
        'challenge_id': c.challenge_id,
        'is_active': c.is_active,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'solve_count': Submission.query.filter_by(challenge_id=c.id, is_correct=True).count()
    } for c in challenges]

    return jsonify(challenge_data)

@app.route("/admin/submissions")
def admin_submissions():
    """Get recent submissions for admin panel"""
    token_value = request.headers.get("Authorization")
    user = verify_token(token_value)

    if not user or not user.is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    submissions = Submission.query.order_by(Submission.submitted_at.desc()).limit(100).all()

    submission_data = [{
        'id': s.id,
        'username': User.query.get(s.user_id).username if User.query.get(s.user_id) else 'Unknown',
        'challenge_name': Challenge.query.get(s.challenge_id).name if Challenge.query.get(s.challenge_id) else 'Unknown',
        'is_correct': s.is_correct,
        'points_awarded': s.points_awarded,
        'submitted_at': s.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
    } for s in submissions]

    return jsonify(submission_data)

@app.route("/admin/toggle-challenge/<int:challenge_id>", methods=["POST"])
def toggle_challenge(challenge_id):
    """Toggle a challenge's active status"""
    token_value = request.headers.get("Authorization")
    user = verify_token(token_value)

    if not user or not user.is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    challenge.is_active = not challenge.is_active
    db.session.commit()

    return jsonify({
        'id': challenge.id,
        'name': challenge.name,
        'is_active': challenge.is_active
    })

@app.route("/admin/make-admin/<int:user_id>", methods=["POST"])
def make_admin(user_id):
    """Make a user an admin"""
    token_value = request.headers.get("Authorization")
    admin_user = verify_token(token_value)

    if not admin_user or not admin_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_admin = True
    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'is_admin': user.is_admin
    })

@app.route("/admin/add-challenge", methods=["POST"])
def add_challenge():
    """Add a new challenge"""
    token_value = request.headers.get("Authorization")
    admin_user = verify_token(token_value)

    if not admin_user or not admin_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    # Validate required fields
    required_fields = ['name', 'description', 'category', 'difficulty', 'points', 'challenge_id']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Check if challenge_id already exists
    existing_challenge = Challenge.query.filter_by(challenge_id=data['challenge_id']).first()
    if existing_challenge:
        return jsonify({"error": f"Challenge ID '{data['challenge_id']}' already exists"}), 400

    # Create challenge directory if it doesn't exist
    challenge_dir = os.path.join(CHALLENGE_BASE, data['challenge_id'])
    os.makedirs(challenge_dir, exist_ok=True)

    # Create a basic challenge.py file if it doesn't exist
    challenge_file = os.path.join(challenge_dir, 'challenge.py')
    if not os.path.exists(challenge_file):
        challenge_content = f'''
# Basic challenge template
from flask import Flask, request, render_template_string, jsonify, redirect
import os
import requests

app = Flask(__name__)

# Get flag from environment variable
FLAG = os.environ.get('FLAG', 'flag{{placeholder}}')
# Get main site URL (default to localhost if not provided)
MAIN_SITE = os.environ.get('MAIN_SITE', 'http://localhost:5002')
# Get challenge ID and container ID
CHALLENGE_ID = os.environ.get('CHALLENGE_ID', '')
CONTAINER_ID = os.environ.get('CONTAINER_ID', '')

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ challenge_name }}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .flag-form {{ margin-top: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        .flag-input {{ width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }}
        .submit-btn {{ background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }}
        .submit-btn:hover {{ background-color: #45a049; }}
        .message {{ margin-top: 20px; padding: 10px; border-radius: 4px; }}
        .success {{ background-color: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }}
        .error {{ background-color: #f2dede; color: #a94442; border: 1px solid #ebccd1; }}
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
                <input type="text" id="flag" name="flag" class="flag-input" placeholder="Enter flag here (e.g., flag{{...}})" required>
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
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </div>

    <script>
        // Make variables available to JavaScript
        const FLAG = "{{FLAG}}";
        const MAIN_SITE = "{{MAIN_SITE}}";
        const CHALLENGE_ID = "{{CHALLENGE_ID}}";
        const CONTAINER_ID = "{{CONTAINER_ID}}";

        // Handle form submission
        document.getElementById('flag-form').addEventListener('submit', function(e) {{
            // Always prevent default form submission
            e.preventDefault();

            // Get the flag value
            const flag = document.getElementById('flag').value.trim();

            // If flag is correct, show success overlay before redirecting
            if (flag === FLAG) {{
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
                fetch('/submit-flag', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        flag: flag
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        console.log('Flag submission successful, redirecting to:', data.redirect_url);
                        // Redirect to the URL provided by the server
                        setTimeout(() => {{
                            window.location.href = data.redirect_url;
                        }}, 2000);
                    }}
                }})
                .catch(error => {{
                    console.error('Error submitting flag:', error);
                    // Fallback redirect if the AJAX call fails
                    setTimeout(() => {{
                        const redirectUrl = `${MAIN_SITE}?flag_success=true&challenge=${CHALLENGE_ID}&container_id=${CONTAINER_ID}&auto_show=true`;
                        console.log('Fallback redirect to:', redirectUrl);
                        window.location.href = redirectUrl;
                    }}, 2000);
                }});
            }} else {{
                // If flag is incorrect, submit via AJAX
                fetch('/submit-flag', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        flag: flag
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (!data.success) {{
                        // Show error message
                        const messageDiv = document.getElementById('message');
                        if (messageDiv) {{
                            messageDiv.className = 'message error';
                            messageDiv.style.display = 'block';
                            messageDiv.textContent = data.message || 'Incorrect flag. Try again!';

                            // Hide the message after 3 seconds
                            setTimeout(() => {{
                                messageDiv.style.display = 'none';
                            }}, 3000);
                        }}
                    }}
                }})
                .catch(error => {{
                    console.error('Error submitting flag:', error);
                }});
            }}
        }});
    </script>
</body>
</html>
""", challenge_name="{data['name']}", challenge_description="{data['description']}")

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
                    return jsonify({{
                        'success': True,
                        'message': 'Congratulations! Flag is correct! Redirecting to main site...',
                        'redirect_url': f"{{MAIN_SITE}}?flag_success=true&challenge={{challenge_id}}&container_id={{container_id}}&auto_show=true"
                    }})
                # For form submissions, redirect directly
                else:
                    redirect_url = f"{{MAIN_SITE}}?flag_success=true&challenge={{challenge_id}}&container_id={{container_id}}&auto_show=true"
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
                    return jsonify({{
                        'success': False,
                        'message': 'Incorrect flag. Try again!'
                    }})
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
            return jsonify({{
                'success': False,
                'message': f'Error processing submission: {{str(e)}}'
            }})
        else:
            # Flag is incorrect
            return jsonify({{
                'success': False,
                'message': 'Incorrect flag. Try again!'
            }})
    except Exception as e:
        return jsonify({{
            'success': False,
            'message': f'Error processing submission: {{str(e)}}'
        }})

@app.route('/flag')
def get_flag():
    # This is just a placeholder - you should implement your own challenge logic
    return jsonify({{'message': 'Not that easy! Solve the challenge to get the flag.'}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
'''

        with open(challenge_file, 'w') as f:
            f.write(challenge_content)

    # Create new challenge in database
    challenge = Challenge(
        name=data['name'],
        description=data['description'],
        category=data['category'],
        difficulty=data['difficulty'],
        points=data['points'],
        challenge_id=data['challenge_id'],
        is_active=True
    )

    db.session.add(challenge)
    db.session.commit()

    return jsonify({
        'id': challenge.id,
        'name': challenge.name,
        'description': challenge.description,
        'category': challenge.category,
        'difficulty': challenge.difficulty,
        'points': challenge.points,
        'challenge_id': challenge.challenge_id,
        'is_active': challenge.is_active
    })

@app.route("/test")
def test():
    return jsonify({"status": "ok", "message": "Server is running"})

@app.route("/host-info")
def host_info():
    """Return host information for network access"""
    host_port = request.host.split(':')[-1] if ':' in request.host else "5002"
    return jsonify({
        "host_ip": HOST_IP,
        "host_port": host_port,
        "host_url": f"http://{HOST_IP}:{host_port}/"
    })

@app.route("/verify-token")
def verify_token_endpoint():
    """Verify a token and return user information"""
    token_value = request.headers.get("Authorization")
    user = verify_token(token_value)

    if not user:
        return jsonify({"error": "Invalid or expired token"}), 401

    return jsonify({
        "valid": True,
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin
    })

@app.route("/submit-flag-main", methods=["POST"])
def submit_flag_main():
    """Submit a flag for a challenge from the main site"""
    data = request.json
    flag = data.get("flag")
    challenge_id = data.get("challenge_id")
    container_id = data.get("container_id")
    token_value = request.headers.get("Authorization")

    if not flag or not challenge_id:
        return jsonify({"error": "Flag and challenge ID are required"}), 400

    # Verify user token
    user = verify_token(token_value)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # Get the challenge
    challenge = Challenge.query.filter_by(challenge_id=challenge_id).first()
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    # Verify that this user is the one who started the challenge
    if container_id and container_id in active_containers:
        container_info = active_containers.get(container_id)
        if container_info.get('user') != user.username:
            return jsonify({
                "success": False,
                "message": "You cannot submit a flag for a challenge started by another user."
            }), 403

    # Generate the expected flag
    expected_flag = generate_flag(user.username, challenge_id)

    # Check if the flag is correct
    is_correct = (flag == expected_flag)

    # Record the submission
    submission = Submission(
        user_id=user.id,
        challenge_id=challenge.id,
        flag=flag,
        is_correct=is_correct,
        points_awarded=challenge.points if is_correct else 0
    )
    db.session.add(submission)

    # If correct, award points to the user
    if is_correct:
        # Check if this is the first correct submission for this challenge
        previous_correct = Submission.query.filter_by(
            user_id=user.id,
            challenge_id=challenge.id,
            is_correct=True
        ).first()

        if not previous_correct:
            user.points += challenge.points
            db.session.commit()
            return jsonify({
                "success": True,
                "message": f"Congratulations! You earned {challenge.points} points!",
                "points_earned": challenge.points,
                "total_points": user.points
            })
        else:
            return jsonify({
                "success": True,
                "message": "Correct flag! You've already solved this challenge.",
                "points_earned": 0,
                "total_points": user.points
            })
    else:
        db.session.commit()
        return jsonify({
            "success": False,
            "message": "Incorrect flag. Try again!"
        })

@app.route("/challenges")
def get_challenges():
    # Get challenges from the database
    db_challenges = Challenge.query.filter_by(is_active=True).all()

    # If no challenges in DB, return directory-based challenges
    if not db_challenges:
        # Get challenges from directory
        challenge_dirs = []
        for challenge in os.listdir(CHALLENGE_BASE):
            if os.path.isdir(os.path.join(CHALLENGE_BASE, challenge)) and not challenge.startswith('.'):
                challenge_dirs.append(challenge)
        return jsonify(challenge_dirs)

    # Return challenges from database
    challenge_list = [{
        'id': c.challenge_id,
        'name': c.name,
        'description': c.description,
        'category': c.category,
        'difficulty': c.difficulty,
        'points': c.points
    } for c in db_challenges]

    return jsonify(challenge_list)

def cleanup_expired_containers():
    """Clean up containers that have exceeded their timeout"""
    now = datetime.now()
    expired_containers = []

    # Find expired containers
    for container_id, info in list(active_containers.items()):
        start_time = info.get('start_time')
        if start_time:
            elapsed_seconds = (now - start_time).total_seconds()
            print(f"Container {container_id} for user {info.get('user')} has been running for {elapsed_seconds:.1f} seconds (timeout: {CHALLENGE_TIMEOUT}s)")

            if elapsed_seconds > CHALLENGE_TIMEOUT:
                expired_containers.append((container_id, info))

    # Clean up expired containers
    for container_id, info in expired_containers:
        try:
            # First check if the container is still running
            check_result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                                         capture_output=True, text=True, check=False)

            if check_result.returncode != 0 or "true" not in check_result.stdout.lower():
                print(f"Container {container_id} is not running, just removing from active list")
                active_containers.pop(container_id, None)
                continue

            print(f"Container {container_id} has expired (timeout: {CHALLENGE_TIMEOUT}s), stopping and removing...")

            # Gracefully stop the container
            stop_result = subprocess.run(["docker", "stop", "--time=10", container_id],
                                       capture_output=True, text=True, check=False)

            if stop_result.returncode != 0:
                print(f"Warning: Failed to stop container {container_id}: {stop_result.stderr}")

            # Only try to remove if stop was successful
            if stop_result.returncode == 0:
                rm_result = subprocess.run(["docker", "rm", container_id],
                                         capture_output=True, text=True, check=False)

                if rm_result.returncode != 0:
                    print(f"Warning: Failed to remove container {container_id}: {rm_result.stderr}")

                # Don't remove images immediately to avoid issues with other containers
                # We'll do image cleanup separately

            # Remove from active_containers but preserve user session data
            active_containers.pop(container_id, None)

            print(f"Successfully cleaned up expired container {container_id} for user {info.get('user')}")
        except Exception as e:
            print(f"Error cleaning up expired container {container_id}: {e}")

def cleanup_stale_containers():
    """Clean up any stale containers from previous runs"""
    try:
        # Get all containers with our CTF prefix
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=ctf_", "--format", "{{.ID}}"],
            capture_output=True, text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            container_ids = result.stdout.strip().split('\n')
            print(f"Found {len(container_ids)} stale containers, cleaning up...")

            for container_id in container_ids:
                try:
                    print(f"Stopping and removing container {container_id}")
                    subprocess.run(["docker", "stop", container_id],
                                  capture_output=True, check=False)
                    subprocess.run(["docker", "rm", container_id],
                                  capture_output=True, check=False)
                except Exception as e:
                    print(f"Error cleaning up container {container_id}: {e}")
    except Exception as e:
        print(f"Error during container cleanup: {e}")

def cleanup_unused_images():
    """Clean up unused Docker images to free up space"""
    try:
        # Get a list of all images
        result = subprocess.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}} {{.ID}}"],
                              capture_output=True, text=True, check=False)

        if result.returncode != 0:
            print(f"Warning: Failed to list Docker images: {result.stderr}")
            return

        # Find CTF images that aren't being used by active containers
        active_images = set()
        for info in active_containers.values():
            if 'image_tag' in info:
                active_images.add(info['image_tag'])

        # Parse the image list
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split(' ')
            if len(parts) != 2:
                continue

            image_tag, image_id = parts

            # Only clean up CTF images
            if image_tag.startswith('ctf_') and image_tag not in active_images:
                print(f"Removing unused image {image_tag} ({image_id})")
                subprocess.run(["docker", "rmi", image_id],
                              capture_output=True, check=False)
    except Exception as e:
        print(f"Error cleaning up unused images: {e}")

def start_cleanup_thread():
    """Start a background thread to periodically check for expired containers"""
    def cleanup_thread():
        # Sleep first to allow the application to start up
        time.sleep(5)

        # Counter for image cleanup (do it less frequently)
        image_cleanup_counter = 0

        while True:
            try:
                print("Running periodic cleanup of expired containers...")
                cleanup_expired_containers()

                # Increment counter and check if we should clean up images
                image_cleanup_counter += 1
                if image_cleanup_counter >= 10:  # Clean up images every ~5 minutes
                    print("Running cleanup of unused images...")
                    cleanup_unused_images()
                    image_cleanup_counter = 0

                # Use a longer check interval to reduce server load
                # This won't affect user experience since UI handles expiration
                check_interval = 30
                print(f"Next cleanup check in {check_interval} seconds")
                time.sleep(check_interval)
            except Exception as e:
                print(f"Error in cleanup thread: {e}")
                # Don't crash the thread on error
                time.sleep(10)

    # Start the cleanup thread as a daemon so it doesn't block application shutdown
    thread = threading.Thread(target=cleanup_thread, daemon=True)
    thread.start()
    print(f"Started background cleanup thread (checking every 30 seconds)")
    return thread

def init_challenges():
    """Initialize challenges from the challenges directory"""
    print(f"Challenge base directory: {CHALLENGE_BASE}")

    # Copy the challenge template to the challenges directory
    template_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "challenge_template.py")
    if os.path.exists(template_src):
        print(f"Copying challenge template to challenges directory")
        for challenge_dir in os.listdir(CHALLENGE_BASE):
            challenge_path = os.path.join(CHALLENGE_BASE, challenge_dir)
            if os.path.isdir(challenge_path) and not challenge_dir.startswith('.'):
                template_dst = os.path.join(challenge_path, "challenge_template.py")
                try:
                    with open(template_src, "r") as src_file, open(template_dst, "w") as dst_file:
                        dst_file.write(src_file.read())
                    print(f"Copied template to {challenge_dir}")
                except Exception as e:
                    print(f"Error copying template to {challenge_dir}: {e}")
    else:
        print(f"Warning: Challenge template not found at {template_src}")

    # Check if we need to initialize the database with challenges
    with app.app_context():
        if Challenge.query.count() == 0:
            print("Initializing challenges in the database...")
            # Define challenge categories and difficulties
            categories = {
                'web': ['web-basic', 'web-sqli'],
                'crypto': ['crypto-101'],
                'forensics': ['forensics-pcap', 'forensics-stego', 'forensics-carving'],
                'reverse': ['reverse-engineering']
            }

            difficulties = {
                'web-basic': 'easy',
                'web-sqli': 'medium',
                'crypto-101': 'easy',
                'forensics-pcap': 'medium',
                'forensics-stego': 'hard',
                'forensics-carving': 'hard',
                'reverse-engineering': 'medium'
            }

            points = {
                'easy': 100,
                'medium': 250,
                'hard': 500
            }

            # Add challenges to the database
            for challenge_dir in os.listdir(CHALLENGE_BASE):
                if os.path.isdir(os.path.join(CHALLENGE_BASE, challenge_dir)) and not challenge_dir.startswith('.'):
                    # Determine category
                    category = None
                    for cat, challenges in categories.items():
                        if challenge_dir in challenges:
                            category = cat
                            break
                    if not category:
                        category = challenge_dir.split('-')[0] if '-' in challenge_dir else 'misc'

                    # Determine difficulty
                    difficulty = difficulties.get(challenge_dir, 'medium')

                    # Create challenge name
                    name = ' '.join(word.capitalize() for word in challenge_dir.split('-'))

                    # Create challenge
                    challenge = Challenge(
                        name=name,
                        description=f"A {difficulty} {category} challenge",
                        category=category,
                        difficulty=difficulty,
                        points=points.get(difficulty, 200),
                        challenge_id=challenge_dir,
                        is_active=True
                    )
                    db.session.add(challenge)

            db.session.commit()
            print("Challenges initialized in the database.")

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='CTF Platform')
    parser.add_argument('--port', type=int, default=5002, help='Port to run the server on')
    args = parser.parse_args()

    # Clean up any stale containers from previous runs
    cleanup_stale_containers()

    # Create database tables
    with app.app_context():
        db.create_all()
        print("Database tables created.")

        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            print("Creating admin user...")
            admin_user = User(username="admin", email="admin@ctf.local", is_admin=True)
            admin_user.set_password("adminctf2023")
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully.")
        elif not admin_user.is_admin:
            print("Updating existing admin user to have admin privileges...")
            admin_user.is_admin = True
            db.session.commit()
            print("Admin user updated successfully.")

    # Initialize challenges
    init_challenges()

    # Start the cleanup thread
    cleanup_thread = start_cleanup_thread()

    # Start the Flask application
    print(f"Challenge timeout set to {CHALLENGE_TIMEOUT} seconds ({CHALLENGE_TIMEOUT/60} minutes)")
    # Use the port from command line arguments or default
    port = args.port
    print(f"Starting server on port {port}")
    print(f"\n===================================================")
    print(f"CTF Platform is now running!")
    print(f"Access the platform at: http://{HOST_IP}:{port}")
    print(f"Share this URL with other users on your network")
    print(f"===================================================\n")
    app.run(host="0.0.0.0", port=port)
