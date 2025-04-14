from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association table for user achievements
user_achievements = db.Table('user_achievements',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('achievement_id', db.Integer, db.ForeignKey('achievement.id'), primary_key=True),
    db.Column('earned_at', db.DateTime, default=datetime.utcnow)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    submissions = db.relationship('Submission', backref='user', lazy=True)
    achievements = db.relationship('Achievement', secondary=user_achievements, 
                                  backref=db.backref('users', lazy='dynamic'))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def add_points(self, points):
        self.points += points
        db.session.commit()
        
    def __repr__(self):
        return f'<User {self.username}>'

class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # easy, medium, hard
    points = db.Column(db.Integer, nullable=False)
    challenge_id = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'web-basic'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('Submission', backref='challenge', lazy=True)
    hints = db.relationship('Hint', backref='challenge', lazy=True)
    
    def __repr__(self):
        return f'<Challenge {self.name}>'

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)
    flag = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    points_awarded = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Submission {self.id} by User {self.user_id}>'

class Hint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    points_penalty = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Hint {self.id} for Challenge {self.challenge_id}>'

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    badge_image = db.Column(db.String(200), nullable=True)  # Path to badge image
    points = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('tokens', lazy=True))
    
    def __repr__(self):
        return f'<Token {self.token[:10]}... for User {self.user_id}>'
