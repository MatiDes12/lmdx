from flask import Blueprint, render_template, request, redirect, url_for, flash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

bp = Blueprint('contact', __name__, url_prefix='/contact')

# Load environment variables from .env file
load_dotenv()

@bp.route('/', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        message = request.form['message']
        
        if not full_name or not email or not message:
            flash('Please fill out all fields', 'error')
            return redirect(url_for('contact.contact'))
        
        # Send email
        try:
            send_email(full_name, email, message)
            flash('Your message has been sent!', 'success')
            return redirect(url_for('contact.contact', success=True))
        except Exception as e:
            print(e)
            flash('An error occurred while sending your message.', 'error')
            return redirect(url_for('contact.contact'))
    
    success = request.args.get('success', False)
    return render_template('contact/contact.html', success=success)

def send_email(full_name, email, message):
    sender_email = os.getenv('MAIL_USERNAME')
    sender_password = os.getenv('MAIL_PASSWORD')
    receiver_email = 'luminamedix@gmail.com'
    sender_default = os.getenv('MAIL_DEFAULT_SENDER')

    msg = MIMEMultipart()
    msg['From'] = sender_default
    msg['To'] = receiver_email
    msg['Subject'] = 'New Contact Form Submission'

    body = f"Full Name: {full_name}\nEmail: {email}\n\nMessage:\n{message}"
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

# from flask import Blueprint, render_template, request, redirect, url_for, flash
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from dotenv import load_dotenv
# import os

# bp = Blueprint('contact', __name__, url_prefix='/contact')

# # Load environment variables from .env file
# load_dotenv()

# @bp.route('/', methods=['GET', 'POST'])
# def contact():
#     if request.method == 'POST':
#         full_name = request.form['full_name']
#         email = request.form['email']
#         message = request.form['message']
        
#         if not full_name or not email or not message:
#             flash('Please fill out all fields', 'error')
#             return redirect(url_for('contact.contact'))
        
#         # Send email
#         try:
#             send_email(full_name, email, message)
#             flash('Your message has been sent!', 'success')
#         except Exception as e:
#             print(e)
#             flash('An error occurred while sending your message.', 'error')
        
#         return redirect(url_for('contact.contact'))
    
#     return render_template('contact/contact.html')

# def send_email(full_name, email, message):
#     sender_email = os.getenv('MAIL_USERNAME')
#     sender_password = os.getenv('MAIL_PASSWORD')
#     receiver_email = 'luminamedix@gmail.com'
#     sender_default = os.getenv('MAIL_DEFAULT_SENDER')

#     msg = MIMEMultipart()
#     msg['From'] = sender_default
#     msg['To'] = receiver_email
#     msg['Subject'] = 'New Contact Form Submission'

#     body = f"Full Name: {full_name}\nEmail: {email}\n\nMessage:\n{message}"
#     msg.attach(MIMEText(body, 'plain'))

#     with smtplib.SMTP('smtp.gmail.com', 587) as server:
#         server.starttls()
#         server.login(sender_email, sender_password)
#         server.send_message(msg)
