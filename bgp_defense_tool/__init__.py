from flask import Flask
import os
from dotenv import load_dotenv

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Load environment variables
    dotenv_path = os.path.join(app.instance_path, '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register blueprints
    from .blueprints import main
    app.register_blueprint(main.bp)

    # Register custom template filters
    from . import template_filters
    app.add_template_filter(template_filters.strftime)

    return app