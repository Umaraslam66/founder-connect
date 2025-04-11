from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    invitation_code = HiddenField('Invitation Code')
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one.')

class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=80)])
    bio = TextAreaField('Bio (Tell us about yourself)', validators=[Length(max=500)])
    skills = TextAreaField('Skills (Separate with commas)', validators=[Length(max=200)])
    interests = TextAreaField('Interests (What are you working on?)', validators=[Length(max=200)])
    location = StringField('Location', validators=[Length(max=80)])
    linkedin_url = StringField('LinkedIn Profile URL', validators=[Length(max=150)])
    submit = SubmitField('Update Profile')

class InvitationForm(FlaskForm):
    email = StringField('Email to Invite', validators=[DataRequired(), Email()])
    message = TextAreaField('Personal Message (Optional)', validators=[Length(max=300)])
    submit = SubmitField('Send Invitation')

class MessageForm(FlaskForm):
    body = TextAreaField('Message', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Send')