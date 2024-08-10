from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_bcrypt import Bcrypt

sqlalchemy_db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
bcrypt = Bcrypt()
