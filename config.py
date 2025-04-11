import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-replace-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'founder_network.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_INVITES_PER_USER = 3
    BASE_URL = os.environ.get('BASE_URL') or 'http://web-production-df2a1.up.railway.app'