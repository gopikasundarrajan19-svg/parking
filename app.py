from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, ParkingSpot, Booking, Payment, Staff, Maintenance, ManagerApplication, CancellationLog
from database import init_db
from datetime import datetime, timedelta
import bcrypt
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def utility_processor():
    return {'now': datetime.now}

# ==================== HOME & AUTH ROUTES ====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = User.query.filter_by(email=email).first()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        if user.role == 'manager_pending':
            flash('Your manager application is pending admin approval!', 'warning')
            return redirect(url_for('index'))
        
        login_user(user)
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'manager':
            return redirect(url_for('manager_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    else:
        flash('Invalid email or password', 'danger')
        return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']
    vehicle_number = request.form['vehicle_number']
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        flash('Email already registered!', 'danger')
        return redirect(url_for('index'))
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    new_user = User(
        name=name,
        email=email,
        phone=phone,
        password=hashed_password.decode('utf-8'),
        vehicle_number=vehicle_number,
        role='user'
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    flash('Registration successful! Please login.', 'success')
    return redirect(url_for('index'))

@app.route('/manager/register', methods=['POST'])
def manager_register():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']
    experience = request.form['experience']
    qualification = request.form['qualification']
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        flash('Email already registered!', 'danger')
        return redirect(url_for('index'))
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    new_manager = User(
        name=name,
        email=email,
        phone=phone,
        password=hashed_password.decode('utf-8'),
        vehicle_number='N/A',
        role='manager_pending'
    )
    
    db.session.add(new_manager)
    db.session.flush()
    
    application = ManagerApplication(
        user_id=new_manager.id,
        experience=experience,
        qualification=qualification,
        status='pending'
    )
    
    db.session.add(application)
    db.session.commit()
    
    flash('Manager registration submitted! Waiting for admin approval.', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

# ==================== ADMIN ROUTES ====================
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    total_spots = ParkingSpot.query.count()
    available_spots = ParkingSpot.query.filter_by(status='available').count()
    occupied_spots = ParkingSpot.query.filter_by(status='occupied').count()
    total_bookings = Booking.query.count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    total_users = User.query.filter_by(role='user').count()
    pending_managers = User.query.filter_by(role='manager_pending').count()
    cancelled_bookings = Booking.query.filter_by(status='cancelled').count()
    
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_spots=total_spots,
                         available_spots=available_spots,
                         occupied_spots=occupied_spots,
                         total_bookings=total_bookings,
                         total_revenue=total_revenue,
                         total_users=total_users,
                         pending_managers=pending_managers,
                         cancelled_bookings=cancelled_bookings,
                         recent_bookings=recent_bookings)

@app.route('/admin/approve_managers')
@login_required
def approve_managers():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    pending_managers = db.session.query(User, ManagerApplication).join(
        ManagerApplication, User.id == ManagerApplication.user_id
    ).filter(User.role == 'manager_pending').all()
    
    return render_template('admin/approve_managers.html', pending_managers=pending_managers)

@app.route('/admin/approve_manager/<int:user_id>')
@login_required
def approve_manager(user_id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.role = 'manager'
    
    application = ManagerApplication.query.filter_by(user_id=user_id).first()
    application.status = 'approved'
    application.reviewed_date = datetime.now()
    
    db.session.commit()
    flash(f'Manager {user.name} approved successfully!', 'success')
    return redirect(url_for('approve_managers'))

@app.route('/admin/reject_manager/<int:user_id>')
@login_required
def reject_manager(user_id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    user = User.query.get_or_404(user_id)
    application = ManagerApplication.query.filter_by(user_id=user_id).first()
    application.status = 'rejected'
    application.reviewed_date = datetime.now()
    
    db.session.commit()
    flash(f'Manager {user.name} rejected!', 'warning')
    return redirect(url_for('approve_managers'))

@app.route('/admin/manage_spots')
@login_required
def manage_spots():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spots = ParkingSpot.query.all()
    return render_template('admin/manage_spots.html', spots=spots)

@app.route('/admin/add_spot', methods=['POST'])
@login_required
def add_spot():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spot_number = request.form['spot_number']
    spot_type = request.form['spot_type']
    price_per_hour = float(request.form['price_per_hour'])
    
    new_spot = ParkingSpot(
        spot_number=spot_number,
        spot_type=spot_type,
        price_per_hour=price_per_hour,
        status='available'
    )
    
    db.session.add(new_spot)
    db.session.commit()
    flash('Parking spot added successfully!', 'success')
    return redirect(url_for('manage_spots'))

@app.route('/admin/delete_spot/<int:spot_id>')
@login_required
def delete_spot(spot_id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spot = ParkingSpot.query.get_or_404(spot_id)
    db.session.delete(spot)
    db.session.commit()
    flash('Parking spot deleted!', 'success')
    return redirect(url_for('manage_spots'))

# ==================== IMPORTANT: UPDATED EDIT SPOT ROUTE ====================
@app.route('/admin/edit_spot/<int:spot_id>', methods=['GET', 'POST'])
@login_required
def edit_spot(spot_id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    if request.method == 'POST':
        spot.spot_number = request.form['spot_number']
        spot.spot_type = request.form['spot_type']
        spot.price_per_hour = float(request.form['price_per_hour'])
        spot.status = request.form['status']
        
        db.session.commit()
        flash(f'Spot {spot.spot_number} updated successfully!', 'success')
        return redirect(url_for('manage_spots'))
    
    return render_template('admin/edit_spot.html', spot=spot)

@app.route('/admin/view_bookings')
@login_required
def admin_view_bookings():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/view_bookings.html', bookings=bookings)

@app.route('/admin/cancelled_bookings')
@login_required
def admin_cancelled_bookings():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    cancelled_bookings = Booking.query.filter_by(status='cancelled').order_by(Booking.cancelled_at.desc()).all()
    total_refund = db.session.query(db.func.sum(Booking.refund_amount)).filter_by(status='cancelled').scalar() or 0
    
    return render_template('admin/cancelled_bookings.html', 
                         cancelled_bookings=cancelled_bookings,
                         total_refund=total_refund)

# ==================== MANAGER ROUTES ====================
@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    total_spots = ParkingSpot.query.count()
    available_spots = ParkingSpot.query.filter_by(status='available').count()
    occupied_spots = ParkingSpot.query.filter_by(status='occupied').count()
    maintenance_spots = ParkingSpot.query.filter_by(status='maintenance').count()
    
    today = datetime.now().date()
    today_bookings = Booking.query.filter(db.func.date(Booking.created_at) == today).count()
    today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        db.func.date(Payment.created_at) == today
    ).scalar() or 0
    
    staff_count = Staff.query.filter_by(status='active').count()
    maintenance_count = Maintenance.query.filter_by(status='pending').count()
    cancelled_count = Booking.query.filter_by(status='cancelled').count()
    
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    spots = ParkingSpot.query.all()
    
    return render_template('manager/dashboard.html',
                         total_spots=total_spots,
                         available_spots=available_spots,
                         occupied_spots=occupied_spots,
                         maintenance_spots=maintenance_spots,
                         today_bookings=today_bookings,
                         today_revenue=today_revenue,
                         staff_count=staff_count,
                         maintenance_count=maintenance_count,
                         cancelled_count=cancelled_count,
                         recent_bookings=recent_bookings,
                         spots=spots)

@app.route('/manager/manage_staff')
@login_required
def manage_staff():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    staff_members = Staff.query.all()
    return render_template('manager/manage_staff.html', staff_members=staff_members)

@app.route('/manager/add_staff', methods=['POST'])
@login_required
def add_staff():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    position = request.form['position']
    shift = request.form['shift']
    salary = float(request.form['salary'])
    
    new_staff = Staff(
        name=name, email=email, phone=phone,
        position=position, shift=shift, salary=salary, status='active'
    )
    
    db.session.add(new_staff)
    db.session.commit()
    flash('Staff member added!', 'success')
    return redirect(url_for('manage_staff'))

@app.route('/manager/edit_staff/<int:staff_id>')
@login_required
def edit_staff(staff_id):
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    staff = Staff.query.get_or_404(staff_id)
    return render_template('manager/edit_staff.html', staff=staff)

@app.route('/manager/update_staff/<int:staff_id>', methods=['POST'])
@login_required
def update_staff(staff_id):
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    staff = Staff.query.get_or_404(staff_id)
    
    staff.name = request.form['name']
    staff.email = request.form['email']
    staff.phone = request.form['phone']
    staff.position = request.form['position']
    staff.shift = request.form['shift']
    staff.salary = float(request.form['salary'])
    
    db.session.commit()
    flash('Staff member updated successfully!', 'success')
    return redirect(url_for('manage_staff'))

@app.route('/manager/delete_staff/<int:staff_id>')
@login_required
def delete_staff(staff_id):
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    staff = Staff.query.get_or_404(staff_id)
    db.session.delete(staff)
    db.session.commit()
    flash('Staff deleted!', 'success')
    return redirect(url_for('manage_staff'))

@app.route('/manager/reports')
@login_required
def manager_reports():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    today = datetime.now().date()
    daily_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        db.func.date(Payment.created_at) == today
    ).scalar() or 0
    daily_bookings = Booking.query.filter(db.func.date(Booking.created_at) == today).count()
    
    week_ago = datetime.now() - timedelta(days=7)
    weekly_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.created_at >= week_ago
    ).scalar() or 0
    weekly_bookings = Booking.query.filter(Booking.created_at >= week_ago).count()
    
    month_ago = datetime.now() - timedelta(days=30)
    monthly_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.created_at >= month_ago
    ).scalar() or 0
    monthly_bookings = Booking.query.filter(Booking.created_at >= month_ago).count()
    
    cancelled_bookings = Booking.query.filter_by(status='cancelled').count()
    total_refund = db.session.query(db.func.sum(Booking.refund_amount)).filter_by(status='cancelled').scalar() or 0
    
    popular_spots = db.session.query(
        ParkingSpot.spot_number,
        db.func.count(Booking.id).label('count')
    ).join(Booking).group_by(ParkingSpot.id).order_by(db.desc('count')).limit(5).all()
    
    return render_template('manager/reports.html',
                         daily_revenue=daily_revenue, daily_bookings=daily_bookings,
                         weekly_revenue=weekly_revenue, weekly_bookings=weekly_bookings,
                         monthly_revenue=monthly_revenue, monthly_bookings=monthly_bookings,
                         cancelled_bookings=cancelled_bookings, total_refund=total_refund,
                         popular_spots=popular_spots)

@app.route('/manager/maintenance')
@login_required
def manager_maintenance():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spots = ParkingSpot.query.all()
    maintenance_requests = Maintenance.query.order_by(Maintenance.created_at.desc()).all()
    return render_template('manager/maintenance.html', spots=spots, maintenance_requests=maintenance_requests)

@app.route('/manager/add_maintenance', methods=['POST'])
@login_required
def add_maintenance():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spot_id = request.form['spot_id']
    issue_type = request.form['issue_type']
    description = request.form['description']
    
    spot = ParkingSpot.query.get(spot_id)
    spot.status = 'maintenance'
    
    maintenance = Maintenance(spot_id=spot_id, issue_type=issue_type, description=description, status='pending')
    db.session.add(maintenance)
    db.session.commit()
    flash('Maintenance request submitted!', 'success')
    return redirect(url_for('manager_maintenance'))

@app.route('/manager/complete_maintenance/<int:maintenance_id>')
@login_required
def complete_maintenance(maintenance_id):
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    maintenance = Maintenance.query.get_or_404(maintenance_id)
    maintenance.status = 'completed'
    maintenance.completed_at = datetime.now()
    
    spot = ParkingSpot.query.get(maintenance.spot_id)
    spot.status = 'available'
    
    db.session.commit()
    flash('Maintenance completed!', 'success')
    return redirect(url_for('manager_maintenance'))

@app.route('/manager/pricing')
@login_required
def manager_pricing():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spots = ParkingSpot.query.all()
    return render_template('manager/pricing.html', spots=spots)

@app.route('/manager/update_price', methods=['POST'])
@login_required
def update_price():
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spot_id = request.form['spot_id']
    new_price = float(request.form['price_per_hour'])
    
    spot = ParkingSpot.query.get(spot_id)
    spot.price_per_hour = new_price
    db.session.commit()
    flash('Price updated!', 'success')
    return redirect(url_for('manager_pricing'))

@app.route('/manager/view_cancellations')
@login_required
def manager_view_cancellations():
    """Manager can view all cancelled bookings (Read Only)"""
    if current_user.role != 'manager':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    cancelled_bookings = Booking.query.filter_by(status='cancelled').order_by(Booking.cancelled_at.desc()).all()
    total_refund_amount = db.session.query(db.func.sum(Booking.refund_amount)).filter_by(status='cancelled').scalar() or 0
    total_original_amount = db.session.query(db.func.sum(Booking.total_amount)).filter_by(status='cancelled').scalar() or 0
    total_cancelled = len(cancelled_bookings)
    
    today = datetime.now().date()
    today_cancellations = Booking.query.filter(
        db.func.date(Booking.cancelled_at) == today,
        Booking.status == 'cancelled'
    ).count()
    
    week_ago = datetime.now() - timedelta(days=7)
    weekly_cancellations = Booking.query.filter(
        Booking.cancelled_at >= week_ago,
        Booking.status == 'cancelled'
    ).count()
    
    month_ago = datetime.now() - timedelta(days=30)
    monthly_cancellations = Booking.query.filter(
        Booking.cancelled_at >= month_ago,
        Booking.status == 'cancelled'
    ).count()
    
    total_bookings = Booking.query.count()
    if total_bookings > 0:
        cancellation_rate = round((total_cancelled / total_bookings) * 100, 1)
    else:
        cancellation_rate = 0
    
    if total_cancelled > 0:
        avg_refund = round(total_refund_amount / total_cancelled, 2)
    else:
        avg_refund = 0
    
    return render_template('manager/view_cancellations.html',
                         cancelled_bookings=cancelled_bookings,
                         total_refund_amount=total_refund_amount,
                         total_original_amount=total_original_amount,
                         total_cancelled=total_cancelled,
                         today_cancellations=today_cancellations,
                         weekly_cancellations=weekly_cancellations,
                         monthly_cancellations=monthly_cancellations,
                         cancellation_rate=cancellation_rate,
                         avg_refund=avg_refund)

# ==================== USER ROUTES WITH CANCELLATION ====================
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'manager':
            return redirect(url_for('manager_dashboard'))
    
    available_spots = ParkingSpot.query.filter_by(status='available').all()
    active_booking = Booking.query.filter_by(user_id=current_user.id, status='active').first()
    cancelled_count = Booking.query.filter_by(user_id=current_user.id, status='cancelled').count()
    
    return render_template('user/dashboard.html', 
                         available_spots=available_spots, 
                         active_booking=active_booking,
                         cancelled_count=cancelled_count)

@app.route('/user/book_slot/<int:spot_id>', methods=['GET', 'POST'])
@login_required
def book_slot(spot_id):
    if current_user.role != 'user':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    if request.method == 'POST':
        duration = int(request.form['duration'])
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration)
        total_amount = spot.price_per_hour * duration
        
        active_booking = Booking.query.filter_by(user_id=current_user.id, status='active').first()
        if active_booking:
            flash('You already have an active booking!', 'danger')
            return redirect(url_for('user_dashboard'))
        
        spot.status = 'occupied'
        
        booking = Booking(
            user_id=current_user.id, spot_id=spot.id,
            start_time=start_time, end_time=end_time,
            total_amount=total_amount, status='active', payment_status='pending'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        return redirect(url_for('payment', booking_id=booking.id))
    
    return render_template('user/book_slot.html', spot=spot)

@app.route('/user/payment/<int:booking_id>')
@login_required
def payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    return render_template('user/payment.html', booking=booking)

@app.route('/user/process_payment/<int:booking_id>', methods=['POST'])
@login_required
def process_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    payment_method = request.form['payment_method']
    
    payment = Payment(
        booking_id=booking.id, 
        amount=booking.total_amount, 
        payment_method=payment_method, 
        status='completed',
        transaction_id=f'TXN_{booking.id}_{datetime.now().timestamp()}'
    )
    booking.payment_status = 'paid'
    
    db.session.add(payment)
    db.session.commit()
    
    flash('Payment successful! Your parking spot is booked.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/my_bookings')
@login_required
def my_bookings():
    if current_user.role != 'user':
        return redirect(url_for('user_dashboard'))
    
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('user/my_bookings.html', bookings=bookings)

@app.route('/user/cancel_booking/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def cancel_booking(booking_id):
    """User cancels their booking"""
    if current_user.role != 'user':
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('You can only cancel your own bookings!', 'danger')
        return redirect(url_for('my_bookings'))
    
    if booking.status == 'completed':
        flash('Cannot cancel a completed booking!', 'warning')
        return redirect(url_for('my_bookings'))
    
    if booking.status == 'cancelled':
        flash('This booking is already cancelled!', 'info')
        return redirect(url_for('my_bookings'))
    
    if request.method == 'POST':
        cancellation_reason = request.form.get('cancellation_reason')
        additional_comments = request.form.get('additional_comments', '')
        
        full_reason = cancellation_reason
        if additional_comments:
            full_reason += f" - {additional_comments}"
        
        now = datetime.now()
        if now < booking.start_time:
            refund_amount = booking.total_amount
            refund_percentage = 100
            flash(f'Booking cancelled! Full refund of ₹{refund_amount} will be processed.', 'success')
        elif now < booking.end_time:
            refund_amount = booking.total_amount * 0.5
            refund_percentage = 50
            flash(f'Booking cancelled! Partial refund of ₹{refund_amount} will be processed.', 'warning')
        else:
            refund_amount = 0
            refund_percentage = 0
            flash('Booking cancelled but no refund available as time has passed.', 'info')
        
        booking.status = 'cancelled'
        booking.cancellation_reason = full_reason
        booking.cancelled_at = datetime.now()
        booking.refund_amount = refund_amount
        booking.cancelled_by = 'user'
        
        if refund_amount > 0 and booking.payment_status == 'paid':
            booking.payment_status = 'refunded'
            
            refund_payment = Payment(
                booking_id=booking.id,
                amount=-refund_amount,
                payment_method='refund',
                status='completed',
                transaction_id=f'REF_{booking.id}_{datetime.now().timestamp()}',
                refunded_at=datetime.now()
            )
            db.session.add(refund_payment)
        
        spot = ParkingSpot.query.get(booking.spot_id)
        spot.status = 'available'
        
        cancellation_log = CancellationLog(
            booking_id=booking.id,
            user_id=current_user.id,
            cancelled_by_role='user',
            cancellation_reason=full_reason,
            original_amount=booking.total_amount,
            refund_amount=refund_amount,
            refund_percentage=refund_percentage
        )
        db.session.add(cancellation_log)
        
        db.session.commit()
        
        return redirect(url_for('my_bookings'))
    
    return render_template('user/cancel_booking.html', booking=booking)

@app.route('/user/release_spot/<int:booking_id>')
@login_required
def release_spot(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    booking.status = 'completed'
    booking.end_time = datetime.now()
    
    spot = ParkingSpot.query.get(booking.spot_id)
    spot.status = 'available'
    
    db.session.commit()
    flash('Parking spot released!', 'success')
    return redirect(url_for('user_dashboard'))

# ==================== API ROUTES FOR AJAX CANCELLATION ====================
@app.route('/api/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def api_cancel_booking(booking_id):
    """AJAX endpoint for cancellation"""
    if current_user.role != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if booking.status != 'active':
        return jsonify({'error': 'Booking cannot be cancelled'}), 400
    
    data = request.get_json()
    reason = data.get('reason', 'No reason provided')
    
    now = datetime.now()
    if now < booking.start_time:
        refund_amount = booking.total_amount
        refund_percentage = 100
        message = f'Full refund of ₹{refund_amount}'
    elif now < booking.end_time:
        refund_amount = booking.total_amount * 0.5
        refund_percentage = 50
        message = f'Partial refund of ₹{refund_amount}'
    else:
        refund_amount = 0
        refund_percentage = 0
        message = 'No refund available'
    
    booking.status = 'cancelled'
    booking.cancellation_reason = reason
    booking.cancelled_at = now
    booking.refund_amount = refund_amount
    booking.cancelled_by = 'user'
    
    if refund_amount > 0 and booking.payment_status == 'paid':
        booking.payment_status = 'refunded'
    
    spot = ParkingSpot.query.get(booking.spot_id)
    spot.status = 'available'
    
    cancellation_log = CancellationLog(
        booking_id=booking.id,
        user_id=current_user.id,
        cancelled_by_role='user',
        cancellation_reason=reason,
        original_amount=booking.total_amount,
        refund_amount=refund_amount,
        refund_percentage=refund_percentage
    )
    db.session.add(cancellation_log)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Booking cancelled successfully. {message}',
        'refund_amount': refund_amount,
        'refund_percentage': refund_percentage
    })

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)