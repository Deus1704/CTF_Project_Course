# CTF Platform Quick Start Guide

This guide will help you get the CTF Platform up and running quickly.

## Prerequisites

Ensure you have the following installed:
- Python 3.8+
- Docker
- Git

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/ctf-platform.git
cd ctf-platform
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize the database:

```bash
python init_db.py
```

4. Start the application:

```bash
python app.py
```

5. Access the platform at http://localhost:5002

## Default Credentials

- **Admin User**: admin / adminctf2023
- **Test User**: user@example.com / user123

## Creating Your First Challenge

1. Navigate to the Admin Panel at http://localhost:5002/admin
2. Log in with the admin credentials
3. Click "Add Challenge"
4. Fill in the challenge details:
   - Name: My First Challenge
   - Description: This is a test challenge
   - Category: web
   - Difficulty: easy
   - Points: 100
   - Challenge ID: web-test-1
5. Click "Create Challenge"
6. The system will create a basic challenge template in the challenges directory

## Testing the Challenge

1. Log out of the admin account
2. Log in with the test user credentials
3. Find your challenge in the challenge list
4. Click "Start Challenge"
5. The challenge will open in a new tab
6. Submit the flag (visible in the challenge for testing purposes)
7. You should be redirected back to the main site with points awarded

## Next Steps

- Customize the challenge by editing the files in `challenges/web-test-1/`
- Create more challenges with different categories and difficulties
- Explore the admin panel to manage users and view submissions
- Check out the [documentation](docs/) for more detailed information

## Troubleshooting

- If Docker containers aren't starting, check Docker service is running
- If challenges aren't appearing, check the challenge directory permissions
- For database issues, try deleting the `ctf.db` file and running `init_db.py` again
- Check the console output for error messages

For more detailed information, refer to the [full documentation](docs/).
