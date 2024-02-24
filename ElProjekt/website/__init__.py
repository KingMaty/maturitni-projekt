from flask import Flask
from .models import db

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'random string'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'

    db.init_app(app)

    from .auth import auth
    from .routes import routes
    
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(routes.routes)

    return app
