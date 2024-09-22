import os
import datetime
import shutil
import sqlite3
import tempfile
import zipfile
from flask import current_app
from werkzeug.utils import secure_filename

def create_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(current_app.config['BACKUP_DIR'], timestamp)
    os.makedirs(backup_dir, exist_ok=True)

    # Backup database
    db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    backup_db_path = os.path.join(backup_dir, 'database_backup.sqlite')
    shutil.copy2(db_path, backup_db_path)

    # Backup uploaded content
    upload_dir = current_app.config['UPLOAD_FOLDER']
    backup_upload_dir = os.path.join(backup_dir, 'uploads')
    shutil.copytree(upload_dir, backup_upload_dir)

    # Create a zip file of the backup
    zip_path = os.path.join(current_app.config['BACKUP_DIR'], f'backup_{timestamp}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(backup_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, backup_dir)
                zipf.write(file_path, arcname)

    # Remove the temporary backup directory
    shutil.rmtree(backup_dir)

    return zip_path

def restore_backup(backup_file):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            zipf.extractall(temp_dir)

        # Restore database
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        backup_db_path = os.path.join(temp_dir, 'database_backup.sqlite')
        shutil.copy2(backup_db_path, db_path)

        # Restore uploaded content
        upload_dir = current_app.config['UPLOAD_FOLDER']
        backup_upload_dir = os.path.join(temp_dir, 'uploads')
        shutil.rmtree(upload_dir)
        shutil.copytree(backup_upload_dir, upload_dir)

def list_backups():
    backup_dir = current_app.config['BACKUP_DIR']
    backups = []
    for file in os.listdir(backup_dir):
        if file.endswith('.zip'):
            backups.append({
                'filename': file,
                'timestamp': datetime.datetime.strptime(file[7:-4], "%Y%m%d_%H%M%S"),
                'size': os.path.getsize(os.path.join(backup_dir, file))
            })
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)