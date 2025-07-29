import os

# Get the absolute path of the directory where this file is located.
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class. Contains common settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secret-key-that-you-should-change'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'dev-wordbook.db')

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Note: This points to the database inside the 'instance' folder, which is a best practice.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'wordbook.db')

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
