from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from matching import match_donor, load_data
from twilio.rest import Client
import math
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Twilio credentials (use environment variables in production)
TWILIO_SID = 'ACe550a7d3d9a84f08982c094145a4ed39'
TWILIO_AUTH_TOKEN = '942b5e84f5ad3b2a0e0695e2050e1ca4'
TWILIO_PHONE = '+19786506413'

# Initialize Twilio client
try:
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
except Exception as e:
    logging.error(f"Failed to initialize Twilio client: {str(e)}")
    twilio_client = None

# Load data once when the server starts
donors, _, hospitals = load_data()

# Odisha location mapping
ODISHA_LOCATIONS = {
    'Bhubaneswar': (20.2961, 85.8245),
    'Cuttack': (20.4625, 85.8828),
    'Rourkela': (22.2604, 84.8536),
    'Berhampur': (19.3140, 84.7941),
    'Sambalpur': (21.4669, 83.9757),
    'Puri': (19.8134, 85.8315),
    'Balasore': (21.4940, 86.9427),
    'Bargarh': (21.3353, 83.6161),
    'Angul': (20.8442, 85.1511),
    'Jharsuguda': (21.8553, 84.0062),
    'Dhenkanal': (20.6587, 85.5980),
    'Kendrapara': (20.5002, 86.4166),
    'Jagatsinghpur': (20.2548, 86.1706),
    'Koraput': (18.8110, 82.7105),
    'Rayagada': (19.1711, 83.4160),
    'Bolangir': (20.7074, 83.4843),
    'Sundargarh': (22.1167, 84.0333),
    'Nayagarh': (20.1281, 85.0985),
    'Malkangiri': (18.3650, 82.1367),
    'Khordha': (20.1883, 85.6214)
}

@app.route('/match', methods=['POST'])
def match():
    """API endpoint to match donors to a recipient using AI."""
    try:
        # Get recipient data from the request
        data = request.json
        location = data.get('location')
        if location not in ODISHA_LOCATIONS:
            return jsonify({
                'status': 'error',
                'message': 'Invalid location. Please select a valid city in Odisha.'
            }), 400
        
        latitude, longitude = ODISHA_LOCATIONS[location]
        recipient = {
            'blood_type': data['blood_type'],
            'latitude': latitude,
            'longitude': longitude,
            'urgency': int(data['urgency'])
        }
        
        logging.debug(f"Recipient data: {recipient}")
        
        # Find matches using AI model
        matches = match_donor(recipient, donors, hospitals)
        
        # Process matches to handle Infinity
        for match in matches:
            if math.isinf(match['hospital_distance']) or match['hospital_distance'] > 1000:
                match['hospital_distance'] = None  # or "No low-stock hospitals"
        
        # Send SMS to the closest donor (if any)
        sms_status = "not_attempted"
        if matches and twilio_client:
            closest_donor_id = matches[0]['donor_id']
            donor = donors[donors['id'] == closest_donor_id].iloc[0]
            to_phone = donor['phone']
            if to_phone == TWILIO_PHONE:
                sms_status = "failed: To and From numbers cannot be the same"
                logging.error(sms_status)
            else:
                message = f"Urgent: {recipient['blood_type']} blood needed in {location}. Please contact the hospital."
                try:
                    twilio_client.messages.create(
                        body=message,
                        from_=TWILIO_PHONE,
                        to=to_phone
                    )
                    sms_status = "sent"
                except Exception as sms_error:
                    sms_status = f"failed: {str(sms_error)}"
                    logging.error(f"Failed to send SMS: {sms_status}")
        
        # Return matches as JSON
        return jsonify({
            'status': 'success',
            'matches': matches,
            'sms_status': sms_status
        })
    
    except Exception as e:
        logging.error(f"Error in /match endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)