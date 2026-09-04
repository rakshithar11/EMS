from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from pathlib import Path

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    base = Path(app.root_path).parent

    app.config.update(
        SECRET_KEY="change-this-secret-key",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{base / 'ems.db'}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=str(base / "uploads"),
        DATA_FOLDER=str(base / "data"),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )

    Path(app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True)
    Path(app.config["DATA_FOLDER"]).mkdir(exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .auth import auth_bp
    from .main import main_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/head")

    with app.app_context():
        db.create_all()

        from .seed import seed
        seed()

        from .sync import sync_data_files
        sync_data_files()

    @app.before_request
    def refresh_file_data():
        if not app.config.get("_sync_running", False):
            from .sync import sync_data_files
            sync_data_files()

    return app