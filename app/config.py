import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dogbreeder.db'
    SECRET_KEY = 'your_secret_key_here'
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')