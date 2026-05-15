# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(30), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='user', lazy=True)
    manager_application = db.relationship('ManagerApplication', backref='user', uselist=False)

class ManagerApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience = db.Column(db.String(500), nullable=False)
    qualification = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='pending')
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_date = db.Column(db.DateTime)
    review_notes = db.Column(db.String(500))

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_number = db.Column(db.String(10), unique=True, nullable=False)
    spot_type = db.Column(db.String(20), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='available')
    
    bookings = db.relationship('Booking', backref='parking_spot', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, cancelled, completed
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Cancellation fields
    cancellation_reason = db.Column(db.String(500), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    refund_amount = db.Column(db.Float, nullable=True)
    cancelled_by = db.Column(db.String(50), default='user')  # user, admin, system
    
    payments = db.relationship('Payment', backref='booking', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    transaction_id = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Refund details
    refund_transaction_id = db.Column(db.String(100), nullable=True)
    refunded_at = db.Column(db.DateTime, nullable=True)

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    shift = db.Column(db.String(20), nullable=False)
    salary = db.Column(db.Float, nullable=False)
    joining_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    issue_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    spot = db.relationship('ParkingSpot', backref='maintenances')

class CancellationLog(db.Model):
    """Track all cancellation activities for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cancelled_by_role = db.Column(db.String(20), nullable=False)
    cancellation_reason = db.Column(db.String(500), nullable=False)
    original_amount = db.Column(db.Float, nullable=False)
    refund_amount = db.Column(db.Float, nullable=False)
    refund_percentage = db.Column(db.Float, nullable=False)
    cancelled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    booking = db.relationship('Booking', backref='cancellation_logs')
    user = db.relationship('User', backref='cancellations')