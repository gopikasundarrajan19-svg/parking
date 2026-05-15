# database.py
from models import db, User, ParkingSpot, Booking, Payment, Staff, Maintenance, ManagerApplication, CancellationLog
from sqlalchemy import inspect, text
import bcrypt

def init_db():
    """Create all database tables"""
    db.create_all()
    print("✅ All tables created successfully!")
    
    # Add missing columns if they don't exist (for existing databases)
    add_missing_columns()
    
    # Print all table names
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Tables:", tables)
    
    # Check if admin exists
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        admin_user = User(
            name='Admin',
            email='admin@parking.com',
            phone='9999999999',
            password=hashed_password.decode('utf-8'),
            vehicle_number='ADMIN',
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Admin user created!")
    
    # Add sample parking spots if empty
    if ParkingSpot.query.count() == 0:
        sample_spots = [
            ParkingSpot(spot_number='A1', spot_type='Car', price_per_hour=50.0),
            ParkingSpot(spot_number='A2', spot_type='Car', price_per_hour=50.0),
            ParkingSpot(spot_number='B1', spot_type='Bike', price_per_hour=20.0),
            ParkingSpot(spot_number='B2', spot_type='Bike', price_per_hour=20.0),
            ParkingSpot(spot_number='C1', spot_type='Car', price_per_hour=60.0),
            ParkingSpot(spot_number='C2', spot_type='Car', price_per_hour=60.0),
            ParkingSpot(spot_number='D1', spot_type='EV', price_per_hour=80.0),
            ParkingSpot(spot_number='D2', spot_type='EV', price_per_hour=80.0),
        ]
        db.session.add_all(sample_spots)
        db.session.commit()
        print(f"✅ {len(sample_spots)} sample parking spots added!")
    
    # Add sample staff if empty
    if Staff.query.count() == 0:
        sample_staff = [
            Staff(name='John Doe', email='john@staff.com', phone='1111111111', 
                  position='Security Guard', shift='Morning', salary=25000),
            Staff(name='Jane Smith', email='jane@staff.com', phone='2222222222', 
                  position='Supervisor', shift='Evening', salary=35000),
            Staff(name='Bob Wilson', email='bob@staff.com', phone='3333333333', 
                  position='Cleaner', shift='Night', salary=20000),
        ]
        db.session.add_all(sample_staff)
        db.session.commit()
        print(f"✅ {len(sample_staff)} sample staff added!")
    
    # Print summary
    print("\n📊 Database Summary:")
    print(f"  - Users: {User.query.count()}")
    print(f"  - Parking Spots: {ParkingSpot.query.count()}")
    print(f"  - Bookings: {Booking.query.count()}")
    print(f"  - Staff: {Staff.query.count()}")
    print(f"  - Maintenance: {Maintenance.query.count()}")
    print(f"  - Cancellation Logs: {CancellationLog.query.count()}")
    
    # Show cancellation fields info
    print("\n✅ Cancellation Features Ready:")
    print("  - Users can cancel bookings with reason")
    print("  - Smart refund calculation (100%/50%/0%)")
    print("  - Cancellation logs tracking")
    print("  - Refund transaction records")

def add_missing_columns():
    """Add missing cancellation columns to existing tables"""
    try:
        with db.engine.connect() as conn:
            # Check Booking table columns
            result = conn.execute(text("PRAGMA table_info(booking)"))
            columns = [row[1] for row in result]
            
            # Add missing columns to Booking table
            if 'cancellation_reason' not in columns:
                print("📝 Adding cancellation_reason column...")
                conn.execute(text("ALTER TABLE booking ADD COLUMN cancellation_reason VARCHAR(500)"))
            
            if 'cancelled_at' not in columns:
                print("📝 Adding cancelled_at column...")
                conn.execute(text("ALTER TABLE booking ADD COLUMN cancelled_at DATETIME"))
            
            if 'refund_amount' not in columns:
                print("📝 Adding refund_amount column...")
                conn.execute(text("ALTER TABLE booking ADD COLUMN refund_amount FLOAT"))
            
            if 'cancelled_by' not in columns:
                print("📝 Adding cancelled_by column...")
                conn.execute(text("ALTER TABLE booking ADD COLUMN cancelled_by VARCHAR(50) DEFAULT 'user'"))
            
            # Check Payment table columns
            result = conn.execute(text("PRAGMA table_info(payment)"))
            payment_columns = [row[1] for row in result]
            
            if 'transaction_id' not in payment_columns:
                print("📝 Adding transaction_id to payment...")
                conn.execute(text("ALTER TABLE payment ADD COLUMN transaction_id VARCHAR(100)"))
            
            if 'refund_transaction_id' not in payment_columns:
                print("📝 Adding refund_transaction_id to payment...")
                conn.execute(text("ALTER TABLE payment ADD COLUMN refund_transaction_id VARCHAR(100)"))
            
            if 'refunded_at' not in payment_columns:
                print("📝 Adding refunded_at to payment...")
                conn.execute(text("ALTER TABLE payment ADD COLUMN refunded_at DATETIME"))
            
            conn.commit()
            print("✅ All missing columns added successfully!")
            
    except Exception as e:
        print(f"⚠️ Note: Some columns may already exist: {e}")

def reset_database():
    """WARNING: This will delete all data!"""
    confirm = input("⚠️ WARNING: This will delete ALL data! Type 'DELETE' to confirm: ")
    if confirm == 'DELETE':
        db.drop_all()
        db.create_all()
        print("✅ Database reset successfully!")
        init_db()
    else:
        print("❌ Reset cancelled.")

def show_database_info():
    """Display detailed database information"""
    with db.engine.connect() as conn:
        print("\n📋 DATABASE SCHEMA INFO")
        print("=" * 40)
        
        # Show Booking table structure
        result = conn.execute(text("PRAGMA table_info(booking)"))
        print("\n📌 Booking Table Columns:")
        for row in result:
            print(f"   - {row[1]} ({row[2]})")
        
        # Show Payment table structure  
        result = conn.execute(text("PRAGMA table_info(payment)"))
        print("\n💰 Payment Table Columns:")
        for row in result:
            print(f"   - {row[1]} ({row[2]})")
        
        # Show CancellationLog table
        result = conn.execute(text("PRAGMA table_info(cancellation_log)"))
        print("\n🚫 CancellationLog Table Columns:")
        for row in result:
            print(f"   - {row[1]} ({row[2]})")

if __name__ == '__main__':
    print("🔧 DATABASE MANAGEMENT TOOL")
    print("=" * 40)
    print("1. Initialize/Create database")
    print("2. Reset database (DELETE ALL DATA)")
    print("3. Show database info")
    
    choice = input("\nEnter choice (1-3): ")
    
    if choice == '1':
        with app.app_context():
            init_db()
    elif choice == '2':
        with app.app_context():
            reset_database()
    elif choice == '3':
        with app.app_context():
            show_database_info()
    else:
        print("Invalid choice")