from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    bio = db.Column(db.Text)
    skills = db.Column(db.Text)
    interests = db.Column(db.Text)
    location = db.Column(db.String(80), default="Stockholm")
    linkedin_url = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    invitations_sent = db.relationship('Invitation', backref='sender', lazy='dynamic')
    sent_connection_requests = db.relationship('Connection',
                                    foreign_keys='Connection.requester_id',
                                    backref='requester',
                                    lazy='dynamic')
    received_connection_requests = db.relationship('Connection',
                                       foreign_keys='Connection.requested_id',
                                       backref='requested',
                                       lazy='dynamic')
    messages_sent = db.relationship('Message',
                                   foreign_keys='Message.sender_id',
                                   backref='sender',
                                   lazy='dynamic')
    messages_received = db.relationship('Message',
                                      foreign_keys='Message.recipient_id',
                                      backref='recipient',
                                      lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_invitation_count(self):
        """Return the number of unused invitations created by this user"""
        return Invitation.query.filter_by(
            sender_id=self.id, 
            used=False
        ).count()
    
    def can_create_invitation(self, max_invites):
        """Check if user can create more invitations"""
        return self.get_invitation_count() < max_invites
    
    def get_connections(self):
        """Get all confirmed connections"""
        sent = Connection.query.filter_by(
            requester_id=self.id, 
            status='accepted'
        ).all()
        received = Connection.query.filter_by(
            requested_id=self.id, 
            status='accepted'
        ).all()
        
        connections = []
        for conn in sent:
            connections.append(conn.requested)
        for conn in received:
            connections.append(conn.requester)
            
        return connections
    
    def get_pending_received_requests(self):
        """Get pending connection requests received"""
        return Connection.query.filter_by(
            requested_id=self.id, 
            status='pending'
        ).all()
    
    def get_unread_messages_count(self):
        """Count unread messages"""
        return Message.query.filter_by(
            recipient_id=self.id,
            read=False
        ).count()

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    requested_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))