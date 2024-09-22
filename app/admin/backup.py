import os
import datetime
import shutil
import sqlite3
import tempfile
import zipfile
from flask import current_app
from werkzeug.utils import secure_filename
from app.extensions import db


def create_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(current_app.config['BACKUP_DIR'], timestamp)
    os.makedirs(backup_dir, exist_ok=True)

    try:
        # Backup database
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
        backup_db_path = os.path.join(backup_dir, 'database_backup.sqlite')
        shutil.copy2(db_path, backup_db_path)

        # Backup uploaded content
        upload_dir = current_app.config['UPLOAD_FOLDER']
        backup_upload_dir = os.path.join(backup_dir, 'uploads')
        if os.path.exists(upload_dir):
            shutil.copytree(upload_dir, backup_upload_dir)
        else:
            current_app.logger.warning(f"Upload directory not found: {upload_dir}")

        # Create a zip file of the backup
        zip_filename = f'backup_{timestamp}.zip'
        zip_path = os.path.join(current_app.config['BACKUP_DIR'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_dir)
                    zipf.write(file_path, arcname)

        # Remove the temporary backup directory
        shutil.rmtree(backup_dir)

        current_app.logger.info(f"Backup created successfully: {zip_filename}")
        return zip_path
    except Exception as e:
        current_app.logger.error(f"Error creating backup: {str(e)}")
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        raise

def restore_backup(backup_file):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            zipf.extractall(temp_dir)

        # Restore database
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        backup_db_path = os.path.join(temp_dir, 'database_backup.sqlite')
        if not os.path.exists(backup_db_path):
            raise FileNotFoundError("Database backup file not found in the archive")

        # Close all database connections
        db.session.remove()
        db.engine.dispose()

        # Replace the current database with the backup
        shutil.copy2(backup_db_path, db_path)

        # Restore uploaded content
        upload_dir = current_app.config['UPLOAD_FOLDER']
        backup_upload_dir = os.path.join(temp_dir, 'uploads')
        if os.path.exists(backup_upload_dir):
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
            shutil.copytree(backup_upload_dir, upload_dir)

    current_app.logger.info("Backup restored successfully")

    # Reconnect to the database
    db.engine.dispose()
    db.session.remove()
    db.create_all()

def list_backups():
    backup_dir = current_app.config['BACKUP_DIR']
    backups = []
    try:
        for file in os.listdir(backup_dir):
            if file.endswith('.zip'):
                file_path = os.path.join(backup_dir, file)
                backups.append({
                    'filename': file,
                    'timestamp': datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
                    'size': os.path.getsize(file_path)
                })
    except FileNotFoundError:
        current_app.logger.error(f"Backup directory not found: {backup_dir}")
    except Exception as e:
        current_app.logger.error(f"Error listing backups: {str(e)}")
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)