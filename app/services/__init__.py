from flask import Flask
from app.config import Config
from app.routes import main_bp  # Import the main blueprint

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register Blueprints
    app.register_blueprint(main_bp)

    return app