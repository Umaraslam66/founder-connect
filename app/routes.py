from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User, Invitation, Connection, Message
from app.forms import LoginForm, RegistrationForm, ProfileForm, InvitationForm, MessageForm
from app.utils import create_invitation, validate_invitation, use_invitation, get_invite_url
from werkzeug.urls import url_parse

# Blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
profile_bp = Blueprint('profile', __name__)
connections_bp = Blueprint('connections', __name__)
messages_bp = Blueprint('messages', __name__)

# Main routes
@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        # Get connection counts for dashboard
        connections = current_user.get_connections()
        pending_requests = current_user.get_pending_received_requests()
        unread_messages = current_user.get_unread_messages_count()
        
        return render_template('index.html', 
                              connections=connections,
                              pending_requests=pending_requests,
                              unread_messages=unread_messages)
    else:
        # For non-authenticated users, provide empty values
        return render_template('index.html', 
                              connections=[],
                              pending_requests=[],
                              unread_messages=0)

@main_bp.route('/setup')
def setup():
    # Check if there are no users yet
    if User.query.count() == 0:
        return redirect(url_for('auth.register'))
    else:
        flash('Setup has already been completed', 'info')
        return redirect(url_for('main.index'))

# Auth routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            flash('Invalid email or password', 'danger')
    
    # Pass User model to the template for checking if there are any users
    return render_template('auth/login.html', form=form, User=User)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Check for invitation code
    invitation_code = request.args.get('code')
    
    # Check if this is the first user (allow registration without invitation for first user)
    user_count = User.query.count()
    first_user = user_count == 0
    
    if not first_user and not validate_invitation(invitation_code):
        flash('Invalid or expired invitation code', 'danger')
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if not first_user:
        form.invitation_code.data = invitation_code  # Store the code in the hidden field
    
    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            email=form.email.data,
            location="Stockholm"  # Default location
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        # Mark invitation as used (if not first user)
        if not first_user and invitation_code:
            use_invitation(form.invitation_code.data, user.id)
        
        flash('Your account has been created! You can now log in', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form, first_user=first_user)

@auth_bp.route('/invite', methods=['GET', 'POST'])
@login_required
def invite():
    form = InvitationForm()
    
    # Get user's existing invitations
    invitations = Invitation.query.filter_by(
        sender_id=current_user.id, 
        used=False
    ).all()
    
    max_invites = current_app.config['MAX_INVITES_PER_USER']
    can_invite = current_user.can_create_invitation(max_invites)
    
    if form.validate_on_submit():
        if not can_invite:
            flash('You have reached your maximum number of active invitations', 'warning')
            return redirect(url_for('auth.invite'))
        
        invitation = create_invitation(current_user)
        if invitation:
            invite_url = get_invite_url(invitation.code)
            flash(f'Invitation created! Share this link: {invite_url}', 'success')
            # Note: In a real app, you'd email this to the recipient
            
            return redirect(url_for('auth.invite'))
    
    return render_template('auth/invite.html', 
                          form=form, 
                          invitations=invitations,
                          can_invite=can_invite,
                          max_invites=max_invites)

# Profile routes
@profile_bp.route('/<int:user_id>')
@login_required
def view(user_id):
    user = User.query.get_or_404(user_id)
    
    # Check if users are connected
    is_connected = False
    connection = Connection.query.filter(
        ((Connection.requester_id == current_user.id) & 
         (Connection.requested_id == user.id)) |
        ((Connection.requester_id == user.id) & 
         (Connection.requested_id == current_user.id)),
        Connection.status == 'accepted'
    ).first()
    
    if connection:
        is_connected = True
    
    # Check if there's a pending request
    pending_request = Connection.query.filter(
        ((Connection.requester_id == current_user.id) & 
         (Connection.requested_id == user.id)) |
        ((Connection.requester_id == user.id) & 
         (Connection.requested_id == current_user.id)),
        Connection.status == 'pending'
    ).first()
    
    return render_template('profile/view.html', 
                          user=user, 
                          is_connected=is_connected,
                          pending_request=pending_request)

@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = ProfileForm()
    
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.bio = form.bio.data
        current_user.skills = form.skills.data
        current_user.interests = form.interests.data
        current_user.location = form.location.data
        current_user.linkedin_url = form.linkedin_url.data
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile.view', user_id=current_user.id))
    
    elif request.method == 'GET':
        # Pre-fill the form with current values
        form.name.data = current_user.name
        form.bio.data = current_user.bio
        form.skills.data = current_user.skills
        form.interests.data = current_user.interests
        form.location.data = current_user.location
        form.linkedin_url.data = current_user.linkedin_url
    
    return render_template('profile/edit.html', form=form)

# Connections routes
@connections_bp.route('/')
@login_required
def list():
    connections = current_user.get_connections()
    return render_template('connections/list.html', connections=connections)

@connections_bp.route('/requests')
@login_required
def requests():
    pending_requests = current_user.get_pending_received_requests()
    return render_template('connections/requests.html', pending_requests=pending_requests)

@connections_bp.route('/request/<int:user_id>', methods=['POST'])
@login_required
def request_connection(user_id):
    user = User.query.get_or_404(user_id)
    
    # Check if a connection already exists
    existing = Connection.query.filter(
        ((Connection.requester_id == current_user.id) & 
         (Connection.requested_id == user.id)) |
        ((Connection.requester_id == user.id) & 
         (Connection.requested_id == current_user.id))
    ).first()
    
    if existing:
        flash('A connection request already exists with this user', 'warning')
    else:
        connection = Connection(
            requester_id=current_user.id,
            requested_id=user.id,
            status='pending'
        )
        db.session.add(connection)
        db.session.commit()
        flash(f'Connection request sent to {user.name}', 'success')
    
    return redirect(url_for('profile.view', user_id=user.id))

@connections_bp.route('/accept/<int:request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    connection = Connection.query.get_or_404(request_id)
    
    # Verify this user is the recipient of the request
    if connection.requested_id != current_user.id:
        flash('You are not authorized to accept this request', 'danger')
        return redirect(url_for('connections.requests'))
    
    connection.status = 'accepted'
    db.session.commit()
    
    requester = User.query.get(connection.requester_id)
    flash(f'You are now connected with {requester.name}', 'success')
    return redirect(url_for('connections.requests'))

@connections_bp.route('/reject/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    connection = Connection.query.get_or_404(request_id)
    
    # Verify this user is the recipient of the request
    if connection.requested_id != current_user.id:
        flash('You are not authorized to reject this request', 'danger')
        return redirect(url_for('connections.requests'))
    
    connection.status = 'rejected'
    db.session.commit()
    
    return redirect(url_for('connections.requests'))

# Messages routes
@messages_bp.route('/')
@login_required
def inbox():
    # Get unique conversations
    sent_messages = Message.query.filter_by(sender_id=current_user.id).all()
    received_messages = Message.query.filter_by(recipient_id=current_user.id).all()
    
    # Extract unique conversation partners
    conversation_partners = set()
    for msg in sent_messages:
        conversation_partners.add(msg.recipient_id)
    for msg in received_messages:
        conversation_partners.add(msg.sender_id)
    
    # Get the last message for each conversation
    conversations = []
    for partner_id in conversation_partners:
        partner = User.query.get(partner_id)
        last_message = Message.query.filter(
            ((Message.sender_id == current_user.id) & 
             (Message.recipient_id == partner_id)) |
            ((Message.sender_id == partner_id) & 
             (Message.recipient_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        
        unread_count = Message.query.filter_by(
            sender_id=partner_id,
            recipient_id=current_user.id,
            read=False
        ).count()
        
        conversations.append({
            'partner': partner,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Sort by most recent message
    conversations.sort(key=lambda x: x['last_message'].created_at, reverse=True)
    
    return render_template('messages/inbox.html', conversations=conversations)

@messages_bp.route('/conversation/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    partner = User.query.get_or_404(user_id)
    
    # Check if users are connected
    connection = Connection.query.filter(
        ((Connection.requester_id == current_user.id) & 
         (Connection.requested_id == partner.id)) |
        ((Connection.requester_id == partner.id) & 
         (Connection.requested_id == current_user.id)),
        Connection.status == 'accepted'
    ).first()
    
    if not connection:
        flash('You must be connected with a user to message them', 'warning')
        return redirect(url_for('messages.inbox'))
    
    form = MessageForm()
    
    if form.validate_on_submit():
        message = Message(
            sender_id=current_user.id,
            recipient_id=partner.id,
            body=form.body.data
        )
        db.session.add(message)
        db.session.commit()
        
        # Clear the form
        form.body.data = ''
    
    # Get all messages between these users
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & 
         (Message.recipient_id == partner.id)) |
        ((Message.sender_id == partner.id) & 
         (Message.recipient_id == current_user.id))
    ).order_by(Message.created_at).all()
    
    # Mark unread messages as read
    unread_messages = Message.query.filter_by(
        sender_id=partner.id,
        recipient_id=current_user.id,
        read=False
    ).all()
    
    for msg in unread_messages:
        msg.read = True
    
    db.session.commit()
    
    return render_template('messages/conversation.html', 
                          partner=partner, 
                          messages=messages,
                          form=form)