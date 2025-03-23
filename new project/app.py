import os
import io
import base64
import cv2
import numpy as np
import pytesseract
import qrcode
import easyocr
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Used for session management

# Configure MySQL Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:root@localhost/parking_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder to store uploaded images

db = SQLAlchemy(app)

# Load EasyOCR Reader
reader = easyocr.Reader(['en'])

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
    vehicle_number = db.Column(db.String(50), unique=True, nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    slot = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Occupied')  # 'Occupied' or 'Available'

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

# Admin Authentication Routes
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
            return "Username already taken. <a href='/admin/signup'>Try Again</a>"

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Create new admin
        new_admin = Admin(username=username, password_hash=hashed_password)
        db.session.add(new_admin)
        db.session.commit()

        return redirect(url_for('admin_login'))

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
                           username=session['admin'],
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

# Number Plate Recognition & QR Code Generation

@app.route('/detect_plate', methods=['POST'])
def detect_plate():
    if 'plate_image' not in request.files:
        return "No image uploaded!"

    file = request.files['plate_image']

    if file.filename == '':
        return "No selected file"

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Read Image with OpenCV
        image = cv2.imread(filepath)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Preprocessing steps
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)

        # Use Tesseract OCR instead of EasyOCR
        detected_text = pytesseract.image_to_string(gray, config='--psm 7').strip()
        
        print(f"Detected Plate: {detected_text}")  # Debugging print

        if detected_text:
            detected_text = detected_text.replace(" ", "").upper()  # Clean and normalize text
            booking = Booking.query.filter(Booking.vehicle_number.ilike(detected_text)).first()

            if booking:
                if booking.status == "Occupied":
                    booking.status = "Available"
                    db.session.commit()
                    return f"<h3>Vehicle {detected_text} has exited. Slot {booking.slot} is now available!</h3>"

                else:
                    # Generate QR Code
                    qr_data = json.dumps({"Vehicle": detected_text, "Slot": booking.slot, "Status": booking.status})
                    qr = qrcode.make(qr_data)
                    qr_io = io.BytesIO()
                    qr.save(qr_io, format='PNG')
                    qr_io.seek(0)
                    return send_file(qr_io, mimetype='image/png')

            else:
                return f"<h3>Vehicle {detected_text} NOT found in the parking database!</h3>"

        return "No plate detected!"



if __name__ == '__main__':
    app.run(debug=True)
