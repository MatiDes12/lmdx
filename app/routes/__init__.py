from flask import Flask, Blueprint, render_template, redirect, url_for, session

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'visited' in session:
        # User has visited before, redirect to login page
        return redirect(url_for('main.login'))
    else:
        # First time visit, show index page and set session
        session['visited'] = True
        return render_template('index.html')