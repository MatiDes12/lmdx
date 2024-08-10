import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
import os
import logging
from twilio.base.exceptions import TwilioRestException

def send_sms_reminder(phone_number, message):
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    try:
        message = client.messages.create(
            body=message,
            from_='+18669554686',
            to=phone_number
        )
        logging.info(f"SMS sent to {phone_number}: {message.sid}")
    except TwilioRestException as e:
        logging.error(f"Failed to send SMS to {phone_number}: {e}")
        
def send_email(to_email, subject, message):
    from_email = ""
    password = ""
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        server = smtplib.SMTP_SSL('smtp.example.com', 465)
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        logging.info("Email sent successfully")
        return True
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return False

def send_sms(to_phone, message):
    account_sid = ''
    auth_token = ''
    client = Client(account_sid, auth_token)

    try:
        message = client.messages.create(
            body=message,
            from_='+18336862899',  # Your Twilio number
            to=to_phone
        )
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False


# import smtplib
# from email.mime.text import MIMEText

# def send_email(recipient, subject, body):
#     try:
#         msg = MIMEText(body)
#         msg['Subject'] = subject
#         msg['From'] = 'your-email@example.com'
#         msg['To'] = recipient

#         server = smtplib.SMTP('smtp.example.com')
#         server.login('your-email@example.com', 'your-password')
#         server.sendmail('your-email@example.com', [recipient], msg.as_string())
#         server.quit()
#         return True
#     except Exception as e:
#         print(f"Failed to send email: {str(e)}")
#         return False

# def send_sms(phone_number, message):
#     try:
#         # Use your preferred SMS API to send the message
#         # For example, Twilio
#         from twilio.rest import Client
#         account_sid = 'your_account_sid'
#         auth_token = 'your_auth_token'
#         client = Client(account_sid, auth_token)

#         client.messages.create(
#             body=message,
#             from_='+1234567890',
#             to=phone_number
#         )
#         return True
#     except Exception as e:
#         print(f"Failed to send SMS: {str(e)}")
#         return False
