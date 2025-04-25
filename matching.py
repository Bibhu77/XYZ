import pandas as pd
from haversine import haversine

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

def load_data():
    """Load donor, recipient, and hospital data from CSV files."""
    donors = pd.read_csv('donors.csv')
    recipients = pd.read_csv('recipients.csv')
    hospitals = pd.read_csv('hospitals.csv')
    return donors, recipients, hospitals

def calculate_distance(donor_loc, recipient_loc):
    """Calculate distance between two locations using Haversine formula."""
    return haversine(donor_loc, recipient_loc)  # Returns distance in km

def match_donor(recipient, donors, hospitals, max_distance=50):
    """Match donors to a recipient, prioritizing hospitals with low stock."""
    matches = []
    
    # Convert recipient location to tuple (latitude, longitude)
    recipient_loc = (recipient['latitude'], recipient['longitude'])
    
    # Find hospitals with low stock for the recipient's blood type
    low_stock_hospitals = hospitals[
        (hospitals['blood_type'] == recipient['blood_type']) & 
        (hospitals['stock'] < 5)
    ]
    
    for _, donor in donors.iterrows():
        # Check blood type compatibility
        if recipient['blood_type'] in compatibility[donor['blood_type']]:
            # Convert donor location to tuple
            donor_loc = (donor['latitude'], donor['longitude'])
            # Calculate distance to recipient
            distance = calculate_distance(donor_loc, recipient_loc)
            # Filter donors within max_distance
            if distance <= max_distance:
                # Calculate minimum distance to a low-stock hospital
                min_hospital_distance = float('inf')
                if not low_stock_hospitals.empty:
                    for _, hospital in low_stock_hospitals.iterrows():
                        hospital_loc = (hospital['latitude'], hospital['longitude'])
                        hospital_distance = calculate_distance(donor_loc, hospital_loc)
                        min_hospital_distance = min(min_hospital_distance, hospital_distance)
                
                matches.append({
                    'donor_id': donor['id'],
                    'blood_type': donor['blood_type'],
                    'distance': distance,
                    'urgency_score': recipient['urgency'],
                    'donor_latitude': donor['latitude'],
                    'donor_longitude': donor['longitude'],
                    'hospital_distance': min_hospital_distance
                })
    
    # Sort matches by hospital distance (if applicable), then recipient distance, then urgency
    sorted_matches = sorted(
        matches, 
        key=lambda x: (x['hospital_distance'] if x['hospital_distance'] != float('inf') else float('inf'), x['distance'], -x['urgency_score'])
    )
    
    return sorted_matches

def main():
    """Test the matching logic."""
    donors, recipients, hospitals = load_data()
    
    # Test with the first recipient
    recipient = recipients.iloc[0]  # Example: First recipient
    print(f"Matching for recipient: {recipient['blood_type']} at ({recipient['latitude']}, {recipient['longitude']})")
    
    matches = match_donor(recipient, donors, hospitals)
    
    if matches:
        print("Found matches:")
        for match in matches:
            print(f"Donor ID: {match['donor_id']}, Blood Type: {match['blood_type']}, Distance: {match['distance']:.2f} km, Hospital Distance: {match['hospital_distance']:.2f} km, Urgency: {match['urgency_score']}")
    else:
        print("No matches found.")

if __name__ == "__main__":
    main()