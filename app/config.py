import os

class Config:
    SECRET_KEY = 'your_secret_key_here'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, '..', 'instance')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'uploads')
    MAX_CONTENT_LENGTH = 1024 * 1024 * 100  # 100 MB limit
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    BACKUP_DIR = os.path.join(BASE_DIR, '..', 'backups')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'dogbreeder.db')
    POSTS_PER_PAGE = 10
    
    @classmethod
    def init_app(cls, app):
        # Create backup directory if it doesn't exist
        os.makedirs(cls.BACKUP_DIR, exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.INSTANCE_DIR, exist_ok=True)