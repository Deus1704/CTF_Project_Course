from flask import Flask, request, jsonify, render_template
import hashlib
import os
import subprocess
import threading
import secrets
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)

# In-memory storage for demo purposes (use DB in production)
users = {}
challenges = {}
active_containers = {}

# Challenge timeout in seconds (1 minute for testing)
CHALLENGE_TIMEOUT = 60

CHALLENGE_BASE = "./challenges"
DOCKER_TEMPLATE = """
FROM python:3.9-slim
WORKDIR /app
RUN pip install flask
COPY . .
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
                with open(src_path, "r") as src_file, open(dst_path, "w") as dst_file:
                    dst_file.write(src_file.read())

        # We no longer need to inject the flag into the challenge file
        # as it will be passed as an environment variable
        print(f"Flag {flag} will be passed as environment variable to the container")

        # Create Dockerfile in the user-specific challenge directory
        dockerfile_path = os.path.join(user_challenge_dir, "Dockerfile")
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
        image_tag = f"ctf_{self.challenge_id}_{user_id}"
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
        # Check if this specific user already has a container for this challenge
        for container_id, info in active_containers.items():
            if info.get('challenge') == self.challenge_id and info.get('user') == user_id:
                try:
                    # Check if container is still running
                    result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                                           capture_output=True, text=True)
                    if "true" in result.stdout.lower():
                        port = info.get('port')
                        print(f"User {user_id} already has challenge {self.challenge_id} running on port {port}")
                        return port, container_id
                    else:
                        # Container exists but is not running, remove it
                        print(f"Container {container_id} exists but is not running, removing it")
                        subprocess.run(["docker", "rm", container_id], capture_output=True, check=False)
                        active_containers.pop(container_id, None)
                except subprocess.CalledProcessError:
                    # Container doesn't exist anymore, remove from active_containers
                    print(f"Container {container_id} no longer exists, removing from active containers")
                    active_containers.pop(container_id, None)

        # Find an available port
        port = self.find_available_port()
        print(f"Starting container for user {user_id}, challenge {self.challenge_id} on port {port}")

        try:
            # Pass the flag as an environment variable to the container
            container_id = subprocess.check_output([
                "docker", "run", "-d", "-p",
                f"{port}:5000", "-e", f"CTF_FLAG={flag}", f"ctf_{self.challenge_id}_{user_id}"
            ]).decode().strip()

            print(f"Container started with ID: {container_id}")
            active_containers[container_id] = {
                "port": port,
                "challenge": self.challenge_id,
                "user": user_id,  # Store which user started this container
                "start_time": datetime.now(),  # Store when the container was started
                "image_tag": f"ctf_{self.challenge_id}_{user_id}"
            }
            return port, container_id
        except subprocess.CalledProcessError as e:
            print(f"Error starting container: {e}")
            print(f"Error output: {e.output.decode() if e.output else 'None'}")
            raise

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user_id = data.get("username")
    password = data.get("password")

    if user_id not in users:
        users[user_id] = {
            "password": generate_password_hash(password),
            "tokens": set()
        }

    if not check_password_hash(users[user_id]["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = secrets.token_urlsafe(32)
    users[user_id]["tokens"].add(token)
    return jsonify({"token": token})

@app.route("/challenge/<challenge_id>/start", methods=["POST"])
def start_challenge(challenge_id):
    user_id = request.json.get("user")
    token = request.headers.get("Authorization")

    if token not in users.get(user_id, {}).get("tokens", set()):
        return jsonify({"error": "Unauthorized"}), 401

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
                    return jsonify({
                        "message": "Challenge already running",
                        "port": port,
                        "containerId": container_id,
                        "flag": flag
                    })
            except Exception as e:
                print(f"Error checking container status: {e}")
                # Continue with starting a new container

    flag = generate_flag(user_id, challenge_id)

    # Process challenge template
    loader = ChallengeLoader(challenge_id)
    loader.build_container(flag, user_id)
    port, container_id = loader.run_container(user_id, flag)

    return jsonify({
        "message": "Challenge started",
        "port": port,
        "containerId": container_id,
        "flag": flag,  # Remove this in production!
        "timeout": CHALLENGE_TIMEOUT,
        "startTime": datetime.now().isoformat()
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
    return render_template('index.html', title="CTF Platform")

@app.route("/challenges")
def get_challenges():
    # Return a list of available challenges
    return jsonify(list(challenges.keys()))

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
            print(f"Container {container_id} has expired (timeout: {CHALLENGE_TIMEOUT}s), stopping and removing...")
            subprocess.run(["docker", "stop", container_id],
                          capture_output=True, check=False)
            subprocess.run(["docker", "rm", container_id],
                          capture_output=True, check=False)

            # Also remove the Docker image to free up space
            image_tag = info.get('image_tag')
            if image_tag:
                try:
                    subprocess.run(["docker", "rmi", image_tag],
                                  capture_output=True, check=False)
                    print(f"Removed Docker image {image_tag}")
                except Exception as e:
                    print(f"Error removing Docker image {image_tag}: {e}")

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

def start_cleanup_thread():
    """Start a background thread to periodically check for expired containers"""
    def cleanup_thread():
        # Sleep first to allow the application to start up
        time.sleep(5)

        while True:
            try:
                print("Running periodic cleanup of expired containers...")
                cleanup_expired_containers()

                # Check more frequently as the timeout gets shorter
                check_interval = min(15, max(5, CHALLENGE_TIMEOUT // 10))
                print(f"Next cleanup check in {check_interval} seconds")
                time.sleep(check_interval)
            except Exception as e:
                print(f"Error in cleanup thread: {e}")
                # Don't crash the thread on error
                time.sleep(10)

    # Start the cleanup thread as a daemon so it doesn't block application shutdown
    thread = threading.Thread(target=cleanup_thread, daemon=True)
    thread.start()
    print(f"Started background cleanup thread (checking every ~{min(15, max(5, CHALLENGE_TIMEOUT // 10))} seconds)")
    return thread

if __name__ == "__main__":
    # Clean up any stale containers from previous runs
    cleanup_stale_containers()

    # Preprocess challenges
    for challenge in os.listdir(CHALLENGE_BASE):
        challenges[challenge] = {
            "dockerfile": DOCKER_TEMPLATE,
            "template": os.path.join(CHALLENGE_BASE, challenge, "challenge.py")
        }
        os.makedirs(os.path.join(CHALLENGE_BASE, challenge), exist_ok=True)

    # Start the cleanup thread
    cleanup_thread = start_cleanup_thread()

    # Start the Flask application
    print(f"Challenge timeout set to {CHALLENGE_TIMEOUT} seconds ({CHALLENGE_TIMEOUT/60} minutes)")
    app.run(host="0.0.0.0", port=5001)
