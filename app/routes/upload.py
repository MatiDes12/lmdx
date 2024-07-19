import os
from flask import Blueprint, current_app, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename
from app.services.image_analysis_service import analyze_image

bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'dcm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Analyze the image using Google Gemini API
            analysis_result = analyze_image(filepath)
            return render_template('upload_result.html', result=analysis_result)
    return render_template('upload.html')