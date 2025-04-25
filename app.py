from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from matching import match_donor, load_data
from twilio.rest import Client
import math

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Twilio credentials 
TWILIO_SID = 'ACe550a7d3d9a84f08982c094145a4ed39'  # Account SID
TWILIO_AUTH_TOKEN = '942b5e84f5ad3b2a0e0695e2050e1ca4'  # Auth Token
TWILIO_PHONE = '+19786506413'  # Twilio phone number

# Initialize Twilio client
try:
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
except Exception as e:
    print(f"Failed to initialize Twilio client: {str(e)}")
    twilio_client = None

# Load data once when the server starts
donors, _, hospitals = load_data()

@app.route('/match', methods=['POST'])
def match():
    """API endpoint to match donors to a recipient."""
    try:
        # Get recipient data from the request
        data = request.json
        recipient = {
            'blood_type': data['blood_type'],
            'latitude': float(data['latitude']),
            'longitude': float(data['longitude']),
            'urgency': int(data['urgency'])
        }
        
        # Find matches
        matches = match_donor(recipient, donors, hospitals)
        
        # Process matches to handle Infinity
        for match in matches:
            if math.isinf(match['hospital_distance']):
                match['hospital_distance'] = None  # or "No low-stock hospitals"

        # Send SMS to the closest donor (if any)
        sms_status = "not_attempted"
        if matches and twilio_client:
            closest_donor_id = matches[0]['donor_id']
            donor = donors[donors['id'] == closest_donor_id].iloc[0]
            to_phone = donor['phone']
            # Check if To and From numbers are different
            if to_phone == TWILIO_PHONE:
                sms_status = "failed: To and From numbers cannot be the same"
                print(sms_status)
            else:
                message = f"Urgent: {recipient['blood_type']} blood needed at ({recipient['latitude']}, {recipient['longitude']}). Please contact the hospital."
                try:
                    twilio_client.messages.create(
                        body=message,
                        from_=TWILIO_PHONE,
                        to=to_phone
                    )
                    sms_status = "sent"
                except Exception as sms_error:
                    sms_status = f"failed: {str(sms_error)}"
                    print(f"Failed to send SMS: {sms_status}")
        
        # Return matches as JSON
        return jsonify({
            'status': 'success',
            'matches': matches,
            'sms_status': sms_status
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)