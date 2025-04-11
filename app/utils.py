import random
import string
from flask import current_app
from app.models import Invitation, User
from app import db

def generate_invitation_code(length=10):
    """Generate a unique invitation code"""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        # Make sure code is unique
        existing = Invitation.query.filter_by(code=code).first()
        if not existing:
            return code

def create_invitation(user):
    """Create a new invitation for a user if they are allowed"""
    if user.can_create_invitation(current_app.config['MAX_INVITES_PER_USER']):
        code = generate_invitation_code()
        invitation = Invitation(code=code, sender_id=user.id)
        db.session.add(invitation)
        db.session.commit()
        return invitation
    return None

def get_invite_url(invitation_code):
    """Generate the full invitation URL"""
    from flask import url_for
    return url_for('auth.register', code=invitation_code, _external=True)

def validate_invitation(code):
    """Check if an invitation code is valid and unused"""
    if not code:
        return False
    invitation = Invitation.query.filter_by(code=code, used=False).first()
    return invitation is not None

def use_invitation(code, user_id):
    """Mark an invitation as used and link to the new user"""
    invitation = Invitation.query.filter_by(code=code, used=False).first()
    if invitation:
        invitation.used = True
        inviter = User.query.get(invitation.sender_id)
        new_user = User.query.get(user_id)
        new_user.invited_by_id = inviter.id
        db.session.commit()
        return True
    return False