from app import app
from models import db, Challenge

with app.app_context():
    challenge = Challenge.query.filter_by(challenge_id='web-sqli').first()
    print(f'Challenge exists: {challenge is not None}')
    if challenge:
        print(f'Challenge details: {challenge.name}, {challenge.category}, {challenge.difficulty}, {challenge.points}')
