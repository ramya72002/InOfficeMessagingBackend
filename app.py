'use client'
import email,ssl
from providers import PROVIDERS
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import pytz
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)
load_dotenv()

# Email settings
EMAIL_ADDRESS = os.getenv('EMAIL_USER')  # Your email from environment variable
EMAIL_PASSWORD = os.getenv('EMAIL_PASS')  # Your email password from environment variable

# Get the MongoDB URI from the environment variable
mongo_uri = os.getenv('MONGO_URI')
# MongoDB setup
client = MongoClient(mongo_uri)
db = client.InOfficeMessaging
users_collection = db.users

def send_sms_via_email(
    number: str,
    message: str,
    provider: str,
    sender_credentials: tuple,
    subject: str = "NVision InOffice Messaging",
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
):
    sender_email, email_password = sender_credentials
    receiver_email = f'{number}@{PROVIDERS.get(provider).get("sms")}'

    email_message = f"Subject:{subject}\nTo:{receiver_email}\n{message}"
     # Send the message via an SSL connection
    try:

        with smtplib.SMTP_SSL(
            smtp_server, smtp_port, context=ssl.create_default_context()
        ) as email:
            email.login(sender_email, email_password)
            email.sendmail(sender_email, receiver_email, email_message)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# Flask route to trigger SMS sending
@app.route('/send_sms', methods=['POST'])
def send_sms():
    data = request.json
    numbers = data.get("numbers", [])
    message = data.get("message", "No message provided")
    provider = data.get("provider", "AT&T")  # Default to AT&T
    sender_credentials = ("nvisionwebsiterequest@gmail.com", "zuek mepr tfel opvg")

    # Send SMS to each number
    for number in numbers:
        success = send_sms_via_email(number, message, provider, sender_credentials)
        if not success:
            return jsonify({"error": f"Failed to send SMS to {number}"}), 500

    return jsonify({"status": "SMS sent successfully"}), 200

def send_otp_email(email, otp):
    try:
        subject = "Your OTP for InOfficeMessaging"
        body = f"Your OTP is {otp} "

        # Set up the MIME
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, email, text)
        server.quit()

        print("OTP sent successfully.")
        return True
    except Exception as e:
        print(f"Failed to send OTP: {e}")
        return False

def generate_otp():
    """Generate a 6-digit OTP code."""
    return random.randint(100000, 999999)

@app.route('/')
def home():
    return "Hello, Flask on Vercel!"

@app.route('/signup', methods=['POST'])
def signup():
    try:
        user_data = request.get_json()
        if user_data:
            # Capture the necessary fields
            name = user_data.get('name')
            email = user_data.get('email')
            company_name = user_data.get('company_name')
            phone = user_data.get('phone')  # Capture phone number
            provider = user_data.get('provider')  # Capture provider

            # Ensure all fields are provided
            if not name or not email or not company_name or not phone or not provider:
                return jsonify({'error': 'Name, email, company name, phone, and provider are required.'}), 400

            # Check if user with the email already exists
            existing_user = users_collection.find_one({'email': email})
            if existing_user:
                return jsonify({'error': 'User with this email already exists.'}), 409

            # Generate OTP and send it via email
            otp_code = generate_otp()
            email_sent = send_otp_email(email, otp_code)

            if not email_sent:
                return jsonify({'error': 'Failed to send OTP email.'}), 500

            # Insert new user (OTP will be stored for validation later)
            result = users_collection.insert_one({
                'name': name,
                'email': email,
                'company_name': company_name,
                'phone': phone,  # Save phone number
                'provider': provider,  # Save provider
                'otp': otp_code,
                'signup_date': datetime.now(pytz.utc),  # Add timestamp for when the user signs up
            })

            # Return success response with the new user's ID
            return jsonify({'success': True, 'user_id': str(result.inserted_id), 'message': 'OTP sent to your email.'}), 201
        else:
            return jsonify({'error': 'Invalid data format.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        # Get the request data
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')

        # Ensure both email and OTP are provided
        if not email or not otp:
            return jsonify({'success': False, 'message': 'Email and OTP are required.'}), 400

        # Check if the user exists with the provided email
        user = users_collection.find_one({'email': email})

        if not user:
            return jsonify({'success': False, 'message': 'User not found.'}), 404

        # Check if the provided OTP matches the one in the database
        if str(user.get('otp')) == str(otp):
            # OTP is correct; remove OTP from the user's record
            users_collection.update_one(
                {'email': email},
                {'$unset': {'otp': ""}}  # Remove OTP field
            )
            return jsonify({'success': True, 'message': 'OTP verified successfully.'}), 200
        else:
            return jsonify({'success': False, 'message': 'Incorrect OTP.'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/signin', methods=['POST'])
def signin():
    user_data = request.get_json()
    if not user_data or 'email' not in user_data:
        return jsonify({'error': 'Email is required.'}), 400
    
    email = user_data.get('email')
    
    # Check if user exists
    existing_user = users_collection.find_one({'email': email})
    if existing_user:
        return jsonify({'success': True, 'message': 'Sign in successful.'}), 200
    else:
        return jsonify({'error': 'Email not registered. Please sign up.'}), 404

@app.route('/postrecord', methods=['POST'])
def post_record():
    try:
        data = request.get_json()
        email = data.get('email')
        title = data.get('title')
        category = data.get('category')
        date = data.get('date')
        time = data.get('time')
        image = data.get('image')  # Base64-encoded image

        # Check for missing fields
        if not email or not title or not category or not date or not time or not image:
            return jsonify({'error': 'All fields are required.'}), 400

        # Define the new record
        new_record = {
            'title': title,
            'category': category,
            'date': date,
            'time': time,
            'image': image,  # Store the image as base64
            'created_at': datetime.now(pytz.utc)  # Timestamp for record creation
        }

        # Check if a user with the given email exists
        user = users_collection.find_one({'email': email})

        if user:
            # If the 'records' field exists, append the new record to it
            if 'records' in user:
                users_collection.update_one(
                    {'email': email},
                    {'$push': {'records': new_record}}
                )
            else:
                # If 'records' field does not exist, create it and add the new record
                users_collection.update_one(
                    {'email': email},
                    {'$set': {'records': [new_record]}}
                )
        else:
            # If the user does not exist, return an error
            return jsonify({'error': 'User not found.'}), 404

        return jsonify({'success': True, 'message': 'Record stored successfully.'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/getrecords', methods=['GET'])
def get_records():
    try:
        email = request.args.get('email')  # Get email from query params
        print(f"Received request for email: {email}")  # Log the received email

        # Fetch the user by email
        user = users_collection.find_one({'email': email}, {'_id': 0})
        print(user)

        if user is None:
            return jsonify({'error': 'User not found.'}), 404  # More specific error for user not found
      
        return jsonify(user), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/getr', methods=['GET'])
def get_r():
    try:
        s=123456 # Get email from query params
 
        return jsonify(s), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    

@app.route('/get_forms_company_name', methods=['GET'])
def get_forms_by_company_name():
    try:
        # Get query parameters from the request
        company_name = request.args.get('company_name')  # Fetch 'group' parameter from the query string

        # Build the filter condition dynamically
        filter_condition = {}
        if company_name:
            filter_condition['company_name'] = company_name

        # Fetch documents matching the dynamic filter condition
        records = list(users_collection.find(filter_condition, {'_id': 0}))  # Exclude the MongoDB ID field

        return jsonify(records), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
