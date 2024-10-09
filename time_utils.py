from flask import jsonify
from datetime import datetime

def time_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def serve_time():
    return jsonify({"time": time_now()})
#twiliofrom flask import Flask, jsonify, request
# from flask_cors import CORS
# from datetime import datetime, timedelta
# from twilio.rest import Client
# from pymongo import MongoClient
# from dotenv import load_dotenv
# import os
# import pytz
# import random
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart



# app = Flask(__name__)
# CORS(app)
# load_dotenv()

# # Email settings
# EMAIL_ADDRESS = os.getenv('EMAIL_USER')  # Your email from environment variable
# EMAIL_PASSWORD = os.getenv('EMAIL_PASS')  # Your email password from environment variable


# # Twilio setup
# account_sid = 'AC7c35bf431ea5ed73d11935c105948fa8'
# auth_token = '3b536236a9d097d6a100716e86d08c6d'  # Replace with your actual auth token
# client1 = Client(account_sid, auth_token)
# messaging_service_sid = 'MG01feed8fa5bf48e707f010bd05926e44'  # Replace with your Twilio Messaging Service SID

# # MongoDB setup (if needed)
# mongo_uri = os.getenv('MONGO_URI')
# # MongoDB setup
# client = MongoClient(mongo_uri)
# db = client.InOfficeMessaging
# users_collection = db.users

# @app.route('/send-sms', methods=['POST'])
# def send_sms():
#     try:
#         data = request.json
#         phone_numbers = data.get('to')  # List of recipient phone numbers
#         message_body = data.get('message')  # Message content
        
#         # Ensure 'to' contains a list
#         if not isinstance(phone_numbers, list):
#             return jsonify({'status': 'error', 'message': 'Phone numbers should be a list.'}), 400

#         sent_messages = []  # To store the status of sent messages

#         # Loop through each number and send SMS
#         for number in phone_numbers:
#             message = client1.messages.create(
#                 messaging_service_sid=messaging_service_sid,
#                 body=message_body,
#                 to=number
#             )
#             sent_messages.append({
#                 'phone_number': number,
#                 'message_sid': message.sid,
#                 'status': 'sent'
#             })

#         return jsonify({
#             'status': 'success',
#             'sent_messages': sent_messages,
#             'message': 'SMS sent successfully to all numbers.'
#         }), 200
#     except Exception as e:
#         return jsonify({'status': 'error', 'message': str(e)}), 500
