import os

import firebase_admin
from firebase_admin import firestore
from flask import Flask, jsonify
from flask_cors import CORS

from routes.admin import admin_bp
from routes.dev_storage import dev_storage_bp
from routes.gifts import gifts_bp
from routes.matches import matches_bp
from routes.photos import photos_bp
from routes.questions import questions_bp
from routes.users import me_bp, users_bp


def _env_list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def create_app(test_config=None):
    """Builds the app from env vars. Tests pass test_config to override settings, and with
    TESTING set, Firebase isn't initialized (tests replace the repository instead)."""
    app = Flask(__name__)

    app.config["GOOGLE_CLOUD_PROJECT"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "secret-santa-511801")
    app.config["FIRESTORE_DATABASE"] = os.environ.get("FIRESTORE_DATABASE", "secret-santa-database")
    app.config["PHOTOS_BUCKET"] = os.environ.get("PHOTOS_BUCKET", "secret-santa-photos")
    app.config["PROFILE_PICTURES_BUCKET"] = os.environ.get("PROFILE_PICTURES_BUCKET", "secret-santa-profile-photos")
    app.config["ADMIN_EMAILS"] = {email.lower() for email in _env_list("ADMIN_EMAILS")}
    # "gcs" uses the real buckets with signed URLs. "local" keeps files on disk for development.
    app.config["STORAGE_MODE"] = os.environ.get("STORAGE_MODE", "gcs")
    # Only needed in local dev, where React runs on another port. In production Hosting
    # serves the client and the API from one origin, so ALLOWED_ORIGINS stays unset.
    app.config["ALLOWED_ORIGINS"] = _env_list("ALLOWED_ORIGINS")
    if test_config:
        app.config.update(test_config)

    if app.config["ALLOWED_ORIGINS"]:
        CORS(app, origins=app.config["ALLOWED_ORIGINS"])

    if not app.testing:
        # Uses Application Default Credentials: the service account on Cloud Run, and
        # `gcloud auth application-default login` locally (or the emulators, when their env vars are set)
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(options={"projectId": app.config["GOOGLE_CLOUD_PROJECT"]})
        app.extensions["firestore"] = firestore.client(database_id=app.config["FIRESTORE_DATABASE"])

    app.register_blueprint(me_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(gifts_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(admin_bp)
    if app.config["STORAGE_MODE"] == "local":
        app.register_blueprint(dev_storage_bp)

    @app.route("/api/about")
    def about():
        return "Add your wish list before November 25th. That's when you'll find out who you're getting a gift for."

    @app.route("/api")
    def home():
        return jsonify({"message": "REPS Secret Santa"})

    return app


if __name__ == "__main__":
    create_app().run(port=8000, debug=True)
