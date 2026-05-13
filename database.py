from models import db, User, ParkingSpot, Staff
import bcrypt
from datetime import datetime

def init_db():
    db.create_all()
    
    # Create Admin user only if not exists
    admin = User.query.filter_by(email='admin@parking.com').first()
    if not admin:
        hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        admin = User(
            name='System Admin',
            email='admin@parking.com',
            phone='1234567890',
            password=hashed_password.decode('utf-8'),
            vehicle_number='ADMIN001',
            role='admin'
        )
        db.session.add(admin)
    
    # Add parking spots
    if ParkingSpot.query.count() == 0:
        spots = [
            ('A1', 'car', 50),
            ('A2', 'car', 50),
            ('A3', 'car', 50),
            ('B1', 'bike', 20),
            ('B2', 'bike', 20),
            ('B3', 'bike', 20),
            ('C1', 'ev', 70),
            ('C2', 'ev', 70),
        ]
        
        for spot_num, spot_type, price in spots:
            spot = ParkingSpot(
                spot_number=spot_num,
                spot_type=spot_type,
                price_per_hour=price,
                status='available'
            )
            db.session.add(spot)
    
    db.session.commit()