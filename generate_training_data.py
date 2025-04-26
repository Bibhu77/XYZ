import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Odisha cities with approximate coordinates
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

BLOOD_TYPES = ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']
PHONE_PREFIX = '+91'

def random_phone():
    """Generate a random 10-digit phone number."""
    return PHONE_PREFIX + ''.join([str(random.randint(0, 9)) for _ in range(10)])

def random_date(start_year=2020, end_year=2025):
    """Generate a random date between start_year and end_year."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 1, 1)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')

def generate_donors(n=100):
    """Generate donor data."""
    donors = []
    for i in range(1, n + 1):
        location = random.choice(list(ODISHA_LOCATIONS.keys()))
        lat, lon = ODISHA_LOCATIONS[location]
        # Add small random offset to coordinates
        lat += random.uniform(-0.05, 0.05)
        lon += random.uniform(-0.05, 0.05)
        donors.append({
            'id': i,
            'blood_type': random.choice(BLOOD_TYPES),
            'latitude': lat,
            'longitude': lon,
            'last_donation': random_date(),
            'phone': random_phone()
        })
    return pd.DataFrame(donors)

def generate_recipients(n=50):
    """Generate recipient data."""
    recipients = []
    for i in range(1, n + 1):
        location = random.choice(list(ODISHA_LOCATIONS.keys()))
        lat, lon = ODISHA_LOCATIONS[location]
        lat += random.uniform(-0.05, 0.05)
        lon += random.uniform(-0.05, 0.05)
        recipients.append({
            'id': i,
            'blood_type': random.choice(BLOOD_TYPES),
            'latitude': lat,
            'longitude': lon,
            'urgency': random.randint(1, 10)
        })
    return pd.DataFrame(recipients)

def generate_hospitals(n=20):
    """Generate hospital data."""
    hospitals = []
    for i in range(1, n + 1):
        location = random.choice(list(ODISHA_LOCATIONS.keys()))
        lat, lon = ODISHA_LOCATIONS[location]
        lat += random.uniform(-0.05, 0.05)
        lon += random.uniform(-0.05, 0.05)
        hospitals.append({
            'id': i,
            'name': f"{location} Hospital",
            'latitude': lat,
            'longitude': lon,
            'blood_type': random.choice(BLOOD_TYPES),
            'stock': random.randint(0, 10)
        })
    return pd.DataFrame(hospitals)

def main():
    """Generate and save datasets."""
    donors = generate_donors(100)
    recipients = generate_recipients(50)
    hospitals = generate_hospitals(20)
    
    donors.to_csv('donors.csv', index=False)
    recipients.to_csv('recipients.csv', index=False)
    hospitals.to_csv('hospitals.csv', index=False)
    
    print("Generated datasets:")
    print(f"- donors.csv: {len(donors)} records")
    print(f"- recipients.csv: {len(recipients)} records")
    print(f"- hospitals.csv: {len(hospitals)} records")

if __name__ == "__main__":
    main()