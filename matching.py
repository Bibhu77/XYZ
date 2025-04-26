import pandas as pd
from haversine import haversine
from datetime import datetime, timedelta
import joblib
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Blood type compatibility rules
compatibility = {
    'O-': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
    'O+': ['O+', 'A+', 'B+', 'AB+'],
    'A-': ['A-', 'A+', 'AB-', 'AB+'],
    'A+': ['A+', 'AB+'],
    'B-': ['B-', 'B+', 'AB-', 'AB+'],
    'B+': ['B+', 'AB+'],
    'AB-': ['AB-', 'AB+'],
    'AB+': ['AB+']
}

# Donor compatibility (which blood types a donor can supply)
donor_compatibility = {
    'O-': ['O-'],
    'O+': ['O-', 'O+'],
    'A-': ['O-', 'A-'],
    'A+': ['O-', 'O+', 'A-', 'A+'],
    'B-': ['O-', 'B-'],
    'B+': ['O-', 'O+', 'B-', 'B+'],
    'AB-': ['O-', 'A-', 'B-', 'AB-'],
    'AB+': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']
}

# Load AI model and scaler
try:
    model = joblib.load('donor_match_model.pkl')
    scaler = joblib.load('scaler.pkl')
except Exception as e:
    logging.error(f"Error loading model or scaler: {str(e)}")
    model = None
    scaler = None

def load_data():
    """Load donor, recipient, and hospital data from CSV files."""
    try:
        # Specify dtype to ensure phone is loaded as string
        donors = pd.read_csv('donors.csv', dtype={'phone': str})
        recipients = pd.read_csv('recipients.csv')
        hospitals = pd.read_csv('hospitals.csv')
        # Ensure phone column is string
        donors['phone'] = donors['phone'].astype(str)
        logging.debug(f"Loaded data: {len(donors)} donors, {len(recipients)} recipients, {len(hospitals)} hospitals")
        return donors, recipients, hospitals
    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")
        raise

def calculate_distance(donor_loc, recipient_loc):
    """Calculate distance between two locations using Haversine formula."""
    try:
        return haversine(donor_loc, recipient_loc)  # Returns distance in km
    except Exception as e:
        logging.error(f"Error calculating distance: {str(e)}")
        return float('inf')

def calculate_reliability(last_donation):
    """Calculate reliability score (0-1) based on days since last donation."""
    try:
        if pd.isna(last_donation):
            return 0.5
        days_ago = (datetime.now() - pd.to_datetime(last_donation)).days
        return max(0, min(1, 1 - (days_ago / 365)))
    except Exception as e:
        logging.error(f"Error calculating reliability for {last_donation}: {str(e)}")
        return 0.5

def match_donor(recipient, donors, hospitals, max_distance=50):
    """Match donors to a recipient using AI model, prioritizing match quality."""
    matches = []
    recipient_loc = (recipient['latitude'], recipient['longitude'])
    
    # Find hospitals with low stock for compatible blood types
    compatible_blood_types = donor_compatibility.get(recipient['blood_type'], [recipient['blood_type']])
    low_stock_hospitals = hospitals[
        (hospitals['blood_type'].isin(compatible_blood_types)) & 
        (hospitals['stock'] < 5)
    ]
    logging.debug(f"Found {len(low_stock_hospitals)} low-stock hospitals for blood types: {compatible_blood_types}")
    
    for _, donor in donors.iterrows():
        # Validate donor data
        if pd.isna(donor['latitude']) or pd.isna(donor['longitude']) or pd.isna(donor['blood_type']) or pd.isna(donor['phone']):
            logging.warning(f"Skipping donor {donor['id']} due to missing data")
            continue
        
        # Check blood type compatibility
        if recipient['blood_type'] in compatibility.get(donor['blood_type'], []):
            donor_loc = (donor['latitude'], donor['longitude'])
            distance = calculate_distance(donor_loc, recipient_loc)
            if distance <= max_distance:
                # Calculate minimum distance to a low-stock hospital
                min_hospital_distance = float('inf')
                if not low_stock_hospitals.empty:
                    for _, hospital in low_stock_hospitals.iterrows():
                        hospital_loc = (hospital['latitude'], hospital['longitude'])
                        hospital_distance = calculate_distance(donor_loc, hospital_loc)
                        min_hospital_distance = min(min_hospital_distance, hospital_distance)
                else:
                    # Fallback: find the closest hospital (any blood type or stock)
                    for _, hospital in hospitals.iterrows():
                        hospital_loc = (hospital['latitude'], hospital['longitude'])
                        hospital_distance = calculate_distance(donor_loc, hospital_loc)
                        min_hospital_distance = min(min_hospital_distance, hospital_distance)
                
                reliability = calculate_reliability(donor['last_donation'])
                
                # Prepare features for AI model
                features = [
                    1,  # is_compatible
                    distance,
                    min_hospital_distance if min_hospital_distance != float('inf') else 1000,
                    recipient['urgency'],
                    reliability
                ]
                
                logging.debug(f"Donor {donor['id']} features: {features}")
                
                # Validate features
                if any(pd.isna(f) or np.isinf(f) for f in features):
                    logging.warning(f"Invalid features for donor {donor['id']}: {features}")
                    match_quality = 0.0
                elif model is None or scaler is None:
                    logging.error(f"Model or scaler not loaded for donor {donor['id']}")
                    match_quality = 0.0
                else:
                    try:
                        features_array = np.array([features])
                        # Scale distance-based features (indices 1 and 2)
                        features_array[:, [1, 2]] = scaler.transform(features_array[:, [1, 2]])
                        match_quality = model.predict(features_array)[0]
                        if np.isnan(match_quality) or np.isinf(match_quality):
                            logging.warning(f"Invalid prediction for donor {donor['id']}: {match_quality}")
                            match_quality = 0.0
                    except Exception as e:
                        logging.error(f"Prediction error for donor {donor['id']}: {str(e)}")
                        match_quality = 0.0
                
                matches.append({
                    'donor_id': donor['id'],
                    'blood_type': donor['blood_type'],
                    'distance': distance,
                    'urgency_score': recipient['urgency'],
                    'donor_latitude': donor['latitude'],
                    'donor_longitude': donor['longitude'],
                    'hospital_distance': min_hospital_distance,
                    'match_quality': float(max(0, min(match_quality, 1))),
                    'phone': str(donor['phone'])  # Ensure phone is string
                })
    
    # Sort matches by match quality
    sorted_matches = sorted(matches, key=lambda x: x['match_quality'], reverse=True)[:10]  # Top 10 matches
    logging.debug(f"Found {len(sorted_matches)} matches")
    return sorted_matches

def main():
    """Test the AI matching logic."""
    donors, recipients, hospitals = load_data()
    recipient = recipients.iloc[0]
    logging.info(f"Matching for recipient: {recipient['blood_type']} at ({recipient['latitude']}, {recipient['longitude']})")
    
    matches = match_donor(recipient, donors, hospitals)
    
    if matches:
        logging.info("Found matches:")
        for match in matches:
            hospital_distance = match['hospital_distance'] if match['hospital_distance'] != float('inf') else 'No hospitals found'
            logging.info(f"Donor ID: {match['donor_id']}, Blood Type: {match['blood_type']}, Distance: {match['distance']:.2f} km, Hospital Distance: {hospital_distance}, Urgency: {match['urgency_score']}, Match Quality: {match['match_quality']:.4f}, Phone: {match['phone']}")
    else:
        logging.info("No matches found.")

if __name__ == "__main__":
    main()