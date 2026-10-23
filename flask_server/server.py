from flask import Flask, jsonify
from flask_cors import CORS

from models import db
from routes.users import users_bp
from routes.gifts import gifts_bp
from routes.matches import matches_bp

app = Flask(__name__)
CORS(app, origins="*")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///secret_santa.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
app.register_blueprint(users_bp)
app.register_blueprint(gifts_bp)
app.register_blueprint(matches_bp)

with app.app_context():
    db.create_all()


# Dummy 'About' Route
@app.route("/api/about")
def about():
    return "Delete when you can automate Docker image"

# Members API Route
# @app.route("/members")
# def members():
#     return {"members": ["Member1", "Member2", "Member3"]}

@app.route("/api")
def home():
    return jsonify({"message": "REPS Secret Santa"})

if __name__ == "__main__":
    app.run(port=8000, debug=True)