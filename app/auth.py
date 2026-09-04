from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from .models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("main.dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
