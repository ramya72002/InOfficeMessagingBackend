'use client'
import email,ssl

from bson import ObjectId
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
messages_collection=db.messages
groups_collection = db.groups
group_messages_collection = db.group_messages

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

@app.route('/create_post', methods=['POST'])
def create_post():
    data = request.json  # Get JSON data from the request
    email = data.get('email')
    phone = data.get('phone')

    # Here you can add logic to save the data, e.g., to a database

    response = {
        "message": "Post created successfully!",
        "data": {
            "email": email,
            "phone": phone
        }
    }
    return jsonify(response), 201
    
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
        
#messages
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()

    # Check if data is received correctly
    if data is None:
        return jsonify({'success': False, 'error': 'No data received'}), 400

    sender = data.get('sender')
    receiver = data.get('receiver')
    message = data.get('message')
    timestamp = data.get('timestamp')

    # Validate required fields
    if not sender or not receiver or not message or not timestamp:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    # Attempt to parse the timestamp
    try:
        # Assuming the timestamp format is 'YYYY-MM-DD hh:mm AM/PM'
        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %I:%M %p")  # Handle the new format
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid timestamp format. Use YYYY-MM-DD hh:mm AM/PM.'}), 400

    # Store the message in the database
    message_data = {
        'sender': sender,
        'receiver': receiver,
        'message': message,
        'timestamp': timestamp,
        'isRead': False  # New field to indicate unread status
    }
    
    try:
        messages_collection.insert_one(message_data)  # Insert the message into the collection
        return jsonify({'success': True, 'message': 'Message sent successfully!'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
          
@app.route('/get_conversation', methods=['GET'])
def get_conversation():
    try:
        sender = request.args.get('sender')
        receiver = request.args.get('receiver')

        if not sender or not receiver:
            return jsonify({'error': 'Sender and receiver are required.'}), 400

        # Fetch messages where the sender and receiver are involved in the conversation
        conversation = list(messages_collection.find({
            '$or': [
                {'sender': sender, 'receiver': receiver},
                {'sender': receiver, 'receiver': sender}
            ]
        }).sort('timestamp', 1))  # Sort messages by timestamp (ascending)

        # Return the conversation
        for msg in conversation:
            msg['_id'] = str(msg['_id'])  # Convert ObjectId to string for JSON serialization

        return jsonify({'success': True, 'conversation': conversation}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark_as_read', methods=['POST'])
def mark_as_read():
    try:
        data = request.get_json()
        current_user = data.get('currentUser')  # Current logged-in user's email
        sender = data.get('sender')  # Sender's email
        receiver = data.get('receiver')  # Receiver's email
        print(current_user,sender,receiver)
        if not current_user or not sender or not receiver:
            return jsonify({'error': 'Sender, receiver, and current user are required.'}), 400

        # Ensure the current user is the receiver
      
        # Find the latest message sent from the sender to the receiver that is not read
        latest_message = messages_collection.find_one(
            {'sender': sender, 'receiver': receiver, 'isRead': False},
            sort=[('timestamp', -1)]  # Sort to get the latest message
        )
        if(current_user==receiver):

            if latest_message:
                # Update the isRead field to true
                messages_collection.update_one(
                    {'_id': latest_message['_id']},
                    {'$set': {'isRead': True}}
                )
                return jsonify({'success': True, 'message': 'Message marked as read.'}), 200
            else:
                return jsonify({'success': True, 'message': 'No unread messages found.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_user_conversations', methods=['GET'])
def get_user_conversations():
    try:
        user_email = request.args.get('email')

        if not user_email:
            return jsonify({'error': 'Email is required.'}), 400

        # Fetch distinct conversation partners
        contacts = messages_collection.distinct('receiver', {'sender': user_email}) + \
                   messages_collection.distinct('sender', {'receiver': user_email})

        return jsonify({'success': True, 'contacts': list(set(contacts))}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 1. Create Group
@app.route('/create_group', methods=['POST'])
def create_group():
    try:
        data = request.get_json()
        group_name = data.get('group_name')
        members = data.get('members', [])  # List of user emails or IDs
        print(group_name,members)
        
        if not group_name or not members:
            return jsonify({'error': 'Group name and members are required.'}), 400
        
        group_data = {
            'group_name': group_name,
            'members': members,
            'created_at': datetime.utcnow()
        }
        
        result = groups_collection.insert_one(group_data)
        return jsonify({'success': True, 'group_id': str(result.inserted_id)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 2. Add Member to Group
@app.route('/add_member', methods=['POST'])
def add_member():
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        new_member = data.get('new_member')
        
        if not group_id or not new_member:
            return jsonify({'error': 'Group ID and new member are required.'}), 400
        
        # Add new member to the group
        result = groups_collection.update_one(
            {'_id': ObjectId(group_id)},
            {'$addToSet': {'members': new_member}}  # Prevent duplicate members
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Group not found.'}), 404
        
        return jsonify({'success': True, 'message': 'Member added to the group.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 3. Send Message to Group
@app.route('/send_group_message', methods=['POST'])
def send_group_message():
    try:
        data = request.get_json()
        sender = data.get('sender')
        group_id = data.get('group_id')
        message = data.get('message')
        timestamp = datetime.utcnow()

        if not sender or not group_id or not message:
            return jsonify({'error': 'Sender, group ID, and message are required.'}), 400
        
        # Check if group exists
        group = groups_collection.find_one({'_id': ObjectId(group_id)})
        if not group:
            return jsonify({'error': 'Group not found.'}), 404
        
        # Insert the message into the group_messages collection
        message_data = {
            'group_id': ObjectId(group_id),
            'sender': sender,
            'message': message,
            'timestamp': timestamp
        }
        
        group_messages_collection.insert_one(message_data)
        return jsonify({'success': True, 'message': 'Message sent to group.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 4. Get Group Messages
@app.route('/get_group_messages', methods=['GET'])
def get_group_messages():
    try:
        group_id = request.args.get('group_id')
        
        if not group_id:
            return jsonify({'error': 'Group ID is required.'}), 400
        
        # Fetch messages for the specified group
        messages = list(group_messages_collection.find({'group_id': ObjectId(group_id)}).sort('timestamp', 1))
        
        # Convert ObjectId to string for JSON serialization
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['group_id'] = str(msg['group_id'])
        
        return jsonify({'success': True, 'messages': messages}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 5. List Groups
@app.route('/list_groups', methods=['GET'])
def list_groups():
    try:
        user_email = request.args.get('email')
        
        if not user_email:
            return jsonify({'error': 'User email is required.'}), 400
        
        # Find all groups the user is part of
        groups = list(groups_collection.find({'members': user_email}, {'_id': 1, 'group_name': 1}))
        
        # Convert ObjectId to string for JSON serialization
        for group in groups:
            group['_id'] = str(group['_id'])
        
        return jsonify({'success': True, 'groups': groups}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
