import json
from datetime import datetime, timedelta
from flask import current_app
from werkzeug.utils import secure_filename

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    """
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_json_data(filename):
    """
    Load and sort data from a JSON file.
    """
    with open(filename) as f:
        data = json.load(f)
    return sorted(data['breeds'] if 'breeds' in data else data['colors'])

def format_url(url):
    """
    Ensure URL starts with http:// or https://
    """
    if url and not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url

def get_week_range():
    """
    Get the date range for the current week.
    """
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

def get_month_range():
    """
    Get the date range for the current month.
    """
    now = datetime.utcnow()
    month_start = now.replace(day=1)
    next_month = month_start.replace(day=28) + timedelta(days=4)
    month_end = next_month - timedelta(days=next_month.day)
    return month_start, month_end

def save_image(image_file):
    """
    Save an uploaded image file and return the filename.
    """
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        image_file.save(current_app.config['UPLOAD_FOLDER'] / filename)
        return filename
    return None

def delete_file(filename):
    """
    Delete a file from the upload folder.
    """
    file_path = current_app.config['UPLOAD_FOLDER'] / filename
    if file_path.exists():
        file_path.unlink()

def generate_unique_filename(original_filename):
    """
    Generate a unique filename by appending a timestamp.
    """
    name, ext = original_filename.rsplit('.', 1)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{name}_{timestamp}.{ext}"

def is_valid_date(date_string, date_format="%Y-%m-%d"):
    """
    Check if a given string is a valid date.
    """
    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False

def calculate_age(birth_date):
    """
    Calculate age based on a given birth date.
    """
    today = datetime.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def format_currency(amount):
    """
    Format a number as currency (USD).
    """
    return f"${amount:,.2f}"

def truncate_string(string, length, suffix='...'):
    """
    Truncate a string to a specified length and append a suffix if truncated.
    """
    if len(string) <= length:
        return string
    else:
        return string[:length].rsplit(' ', 1)[0] + suffix