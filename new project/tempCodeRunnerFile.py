from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Used for session management

# Configure MySQL Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:123456@localhost/parking_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define Admin Model
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# Define Booking Model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    vehicle_number = db.Column(db.String(50), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    slot = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Occupied')

# Create tables if they don’t exist
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/user')
def user():
    return render_template('user.html')

@app.route('/parking')
def parking():
    location = request.args.get('location', 'Unknown Location')

    # Fetch booked slots from MySQL
    booked_cars = {b.slot for b in Booking.query.filter(Booking.slot.like('C%')).all()}  # Cars
    booked_bikes = {b.slot for b in Booking.query.filter(Booking.slot.like('B%')).all()}  # Bikes

    return render_template('parking_layout.html', location=location, booked_cars=booked_cars, booked_bikes=booked_bikes)

@app.route('/booking_form', methods=['GET'])
def booking_form():
    location = request.args.get('location')
    slot = request.args.get('slot')

    existing_booking = Booking.query.filter_by(slot=slot).first()
    if existing_booking:
        return f"<h3>Slot {slot} is already booked! Please choose another.</h3> <a href='/parking?location={location}'>Go Back</a>"

    return render_template('booking_form.html', location=location, slot=slot)

@app.route('/book', methods=['POST'])
def book_slot():
    location = request.form.get('location')
    slot = request.form.get('slot')
    name = request.form.get('name')
    vehicle_number = request.form.get('vehicle_number')
    contact = request.form.get('contact')

    existing_booking = Booking.query.filter_by(slot=slot).first()
    if existing_booking:
        return f"<h3>Slot {slot} is already booked! Please choose another.</h3> <a href='/parking?location={location}'>Go Back</a>"

    # Store booking details in MySQL
    new_booking = Booking(location=location, slot=slot, name=name, vehicle_number=vehicle_number, contact=contact)
    db.session.add(new_booking)
    db.session.commit()

    return redirect(url_for('ticket', booking_id=new_booking.id))

@app.route('/ticket')
def ticket():
    booking_id = request.args.get('booking_id')

    if not booking_id:
        return "<h3>Booking ID is missing!</h3> <a href='/'>Go Back</a>"

    booking = Booking.query.get(booking_id)

    if not booking:
        return "<h3>Booking not found!</h3> <a href='/'>Go Back</a>"

    return render_template('ticket.html', details=booking)

# Admin Routes
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid username or password. <a href='/admin'>Try Again</a>"

    return render_template('admin_login.html')

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the username already exists
        existing_admin = Admin.query.filter_by(username=username).first()
        if existing_admin:
            return "Username already exists! <a href='/admin/signup'>Try Again</a>"

        # Hash the password
        password_hash = generate_password_hash(password)

        # Create a new admin user
        new_admin = Admin(username=username, password_hash=password_hash)
        db.session.add(new_admin)
        db.session.commit()

        return redirect(url_for('admin_login'))  # Redirect to login page after signup

    return render_template('admin_signup.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    total_bookings = Booking.query.count()
    booked_cars = Booking.query.filter(Booking.slot.like('C%')).all()
    booked_bikes = Booking.query.filter(Booking.slot.like('B%')).all()

    available_car_slots = 50 - len(booked_cars)
    available_bike_slots = 500 - len(booked_bikes)

    return render_template('admin_dashboard.html', 
                           username=session['admin'],  # Pass the admin username
                           total_bookings=total_bookings, 
                           booked_cars=booked_cars, 
                           booked_bikes=booked_bikes, 
                           available_car_slots=available_car_slots, 
                           available_bike_slots=available_bike_slots)

@app.route('/admin/car-booking-history')
def car_booking_history():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    booked_cars = Booking.query.filter(Booking.slot.like('C%')).all()
    
    return render_template('car_booking_history.html', booked_cars=booked_cars)

@app.route('/admin/bike-booking-history')
def bike_booking_history():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    booked_bikes = Booking.query.filter(Booking.slot.like('B%')).all()
    
    return render_template('bike_booking_history.html', booked_bikes=booked_bikes)

@app.route('/admin/reports')
def reports():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    total_bookings = Booking.query.count()
    
    return render_template('reports.html', total_bookings=total_bookings)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))



if __name__ == '__main__':
    app.run(debug=True)
