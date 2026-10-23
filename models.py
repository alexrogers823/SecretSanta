from flask import url_for
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    # Nullable only so older rows created before the name split still load
    last_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    address = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    gifts = db.relationship(
        "Gift",
        backref="user",
        cascade="all, delete-orphan",
        order_by="Gift.position",
        lazy=True,
    )
    assigned_to = db.relationship(
        "User",
        remote_side=[id],
        foreign_keys=[assigned_to_id],
    )

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "address": self.address,
            "profile_picture_url": self.profile_picture_url(),
        }

    def profile_picture_url(self):
        if not self.profile_picture:
            return None
        # The filename changes on every upload, so it doubles as a cache buster
        return url_for("users.get_profile_picture", user_id=self.id, v=self.profile_picture, _external=True)


class Gift(db.Model):
    __tablename__ = "gifts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    position = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "url": self.url,
            "notes": self.notes,
            "position": self.position,
        }
