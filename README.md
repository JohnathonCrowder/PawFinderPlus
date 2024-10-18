# PuppyHorizon Flask Project

## Setup and Installation

1. Navigate to the project directory:

   ```
   cd E:\Github\DogBreederSoftware
   ```

2. Activate the virtual environment:

   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the application:

   ```
   python run.py
   ```

5. Open your web browser and visit: `http://127.0.0.1:5000`

## Project Structure

- `app/`: Contains the Flask application
  - `templates/`: HTML templates
    - `base.html`: Base template with common structure
    - `index.html`: Home page template
  - `__init__.py`: Flask app initialization
- `venv/`: Virtual environment
- `run.py`: Script to run the Flask application
- `requirements.txt`: List of Python dependencies

## Customization

- Update `app/templates/base.html` to change the common structure (navbar, footer, etc.).
- Update `app/templates/index.html` to change the content of the home page.
- The project uses Tailwind CSS via CDN for styling. You can customize the appearance by modifying the Tailwind classes in the HTML.
- Add more routes and views in `app/__init__.py` to create additional pages.
