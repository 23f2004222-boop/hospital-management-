from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)


app.secret_key = "sdfsdfdsfdsfds" 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)









class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    role = db.Column(db.String(50), nullable=False, default="patient")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True
    )
    department = db.relationship("Department", back_populates="users")

    experience = db.Column(db.Integer, nullable=True)       # years
    qualifications = db.Column(db.String(250), nullable=True)

    blacklisted = db.Column(db.Boolean, default=False)

    appointments_as_patient = db.relationship(
        "Appointment",
        back_populates="patient",
        foreign_keys="Appointment.patient_id",
        cascade="all, delete",
        passive_deletes=True
    )

    appointments_as_doctor = db.relationship(
        "Appointment",
        back_populates="doctor",
        foreign_keys="Appointment.doctor_id",
        cascade="all, delete",
        passive_deletes=True
    )

    availabilities = db.relationship(
        "DoctorAvailability",
        back_populates="doctor",
        cascade="all, delete"
    )



class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    users = db.relationship(
        "User",
        back_populates="department",
        cascade="all, delete",
        passive_deletes=True
    )


class Treatment(db.Model):
    __tablename__ = "treatment"

    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    visit_type = db.Column(db.String(100), nullable=True)
    tests_done = db.Column(db.String(200), nullable=True)
    diagnosis = db.Column(db.String(200), nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    medicines = db.Column(db.Text, nullable=True)

    appointment = db.relationship("Appointment", back_populates="treatment")

class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)

    status = db.Column(db.String(20), default="Booked")

    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))

    doctor = db.relationship("User", foreign_keys=[doctor_id], back_populates="appointments_as_doctor")
    patient = db.relationship("User", foreign_keys=[patient_id], back_populates="appointments_as_patient")

    treatment = db.relationship("Treatment", back_populates="appointment", uselist=False, cascade="all, delete")


class DoctorAvailability(db.Model):
    __tablename__ = "doctor_availability"

    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    date = db.Column(db.String(20), nullable=False)
    morning = db.Column(db.Boolean, default=True)
    evening = db.Column(db.Boolean, default=True)

    doctor = db.relationship("User", back_populates="availabilities")



# --------------- ADMIN DASHBOARD ---------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'id' not in session or session.get('role') != 'admin':
        flash("Only admin can view this page", "danger")
        return redirect(url_for('index'))

    doctors = User.query.filter_by(role='doctor').all()
    patients = User.query.filter_by(role='patient').all()
    departments = Department.query.all()
    upcoming = Appointment.query.order_by(Appointment.date, Appointment.time).limit(10).all()

    return render_template(
        "admin_dashboard.html",
        doctors=doctors,
        patients=patients,
        departments=departments,
        upcoming=upcoming
    )

from sqlalchemy import or_

@app.route('/admin/search')
def admin_search():
    if 'id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    q = request.args.get('q', '').strip()

    doctors = []
    patients = []

    if q:
        doctors = User.query.filter(
            User.role == 'doctor',
            or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"))
        ).all()

        patients = User.query.filter(
            User.role == 'patient',
            or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"))
        ).all()

    departments = Department.query.all()

    return render_template(
        "admin_search.html",
        q=q,
        doctors=doctors,
        patients=patients,
        departments=departments
    )

@app.route('/admin/add_department', methods=['GET', 'POST'])
def admin_add_department():
    if 'id' not in session or session.get('role') != 'admin':
        flash("Not allowed", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('department_name')
        desc = request.form.get('description')

        if Department.query.filter_by(department_name=name).first():
            flash("Department already exists", "danger")
            return redirect(url_for('admin_add_department'))

        new_dept = Department(department_name=name, description=desc)
        db.session.add(new_dept)
        db.session.commit()

        flash("Department added", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_add_department.html")
@app.route('/admin/delete_department/<int:dept_id>', methods=['POST'])
def admin_delete_department(dept_id):
    if 'id' not in session or session.get('role') != 'admin':
        flash("Not allowed", "danger")
        return redirect(url_for('index'))

    dept = Department.query.get_or_404(dept_id)

    db.session.delete(dept)
    db.session.commit()

    flash("Department deleted", "info")
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/blacklist/<int:user_id>')
def admin_blacklist_user(user_id):
    if 'id' not in session or session.get('role') != 'admin':
        flash("Not allowed", "danger")
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.blacklisted = True
    db.session.commit()

    flash(f"{user.username} has been blacklisted", "warning")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unblacklist/<int:user_id>')
def admin_unblacklist_user(user_id):
    if 'id' not in session or session.get('role') != 'admin':
        flash("Not allowed", "danger")
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.blacklisted = False
    db.session.commit()

    flash(f"{user.username} has been un-blacklisted", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_patient/<int:patient_id>', methods=['POST'])
def admin_delete_patient(patient_id):
    if 'id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    pat = User.query.get_or_404(patient_id)
    if pat.role != 'patient':
        flash("Not a patient", "danger")
        return redirect(url_for('admin_dashboard'))

    db.session.delete(pat)
    db.session.commit()

    flash("Patient removed", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def admin_edit_doctor(doctor_id):
    if 'id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    doc = User.query.get_or_404(doctor_id)
    depts = Department.query.all()

    if request.method == 'POST':
        doc.username = request.form.get('username')
        doc.email = request.form.get('email')
        doc.experience = request.form.get('experience')
        doc.qualifications = request.form.get('qualifications')
        doc.department_id = request.form.get('department_id')

        db.session.commit()
        flash("Doctor updated", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_edit_doctor.html", doc=doc, departments=depts)


@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def admin_add_doctor():
    if 'id' not in session or session.get('role') != 'admin':
        flash("Only admin can add doctor", "danger")
        return redirect(url_for('index'))

    departments = Department.query.all()

    if request.method == 'POST':
        name = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        dept_id = request.form.get('department_id')
        experience = request.form.get('experience')
        qualifications = request.form.get('qualifications')

        if User.query.filter_by(email=email).first():
            flash("Email already used", "danger")
            return redirect(url_for('admin_add_doctor'))


        doctor = User(
            username=name,
            email=email,
            password=password,
            role='doctor',
            department_id=dept_id if dept_id else None,
            experience=experience if experience else None,
            qualifications=qualifications
        )
        db.session.add(doctor)
        db.session.commit()

        flash("Doctor added", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_add_doctor.html", departments=departments)


@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST'])
def admin_delete_doctor(doctor_id):
    if 'id' not in session or session.get('role') != 'admin':
        flash("Not allowed", "danger")
        return redirect(url_for('index'))

    doctor = User.query.get_or_404(doctor_id)

    if doctor.role != 'doctor':
        flash("This user is not a doctor", "warning")
        return redirect(url_for('admin_dashboard'))

    db.session.delete(doctor)
    db.session.commit()

    flash("Doctor deleted", "info")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/patient/<int:patient_id>/history')
def admin_patient_history(patient_id):
    if 'id' not in session or session.get('role') != 'admin':
        flash("Only admin can view patient history", "danger")
        return redirect(url_for('index'))

    patient = User.query.get_or_404(patient_id)
    appts = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date).all()

    return render_template("patient_history.html", patient=patient, appts=appts, back_url=url_for('admin_dashboard'))



@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Please login as doctor", "danger")
        return redirect(url_for('index'))

    doctor_id = session['id']

    # Only show appointments that are not completed
    upcoming = Appointment.query.filter_by(
        doctor_id=doctor_id,
        status="Booked"
    ).order_by(Appointment.date, Appointment.time).all()

    # List all patients assigned to the doctor
    patients = (
        User.query.join(Appointment, Appointment.patient_id == User.id)
        .filter(Appointment.doctor_id == doctor_id)
        .distinct()
        .all()
    )

    return render_template(
        "doctor_dashboard.html",
        upcoming=upcoming,
        patients=patients
    )


@app.route('/doctor/patient/<int:patient_id>/history')
def doctor_patient_history(patient_id):
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Only doctors can view this", "danger")
        return redirect(url_for('index'))

    patient = User.query.get_or_404(patient_id)
    appts = Appointment.query.filter_by(
        patient_id=patient.id,
        doctor_id=session['id']
    ).order_by(Appointment.date).all()

    return render_template("patient_history.html", patient=patient, appts=appts, back_url=url_for('doctor_dashboard'))


@app.route('/doctor/appointment/<int:appt_id>/update', methods=['GET', 'POST'])
def doctor_update_history(appt_id):
    if 'id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('index'))

    appt = Appointment.query.get_or_404(appt_id)

    # ensure treatment exists
    if not appt.treatment:
        appt.treatment = Treatment(appointment_id=appt.id)

    treatment = appt.treatment

    if request.method == 'POST':

        treatment.visit_type = request.form.get('visit_type')
        treatment.tests_done = request.form.get('tests_done')
        treatment.diagnosis = request.form.get('diagnosis')
        treatment.prescription = request.form.get('prescription')
        treatment.medicines = request.form.get('medicines')

        appt.status = "Completed"

        db.session.commit()

        flash("Appointment updated", "success")
        return redirect(url_for('doctor_dashboard'))

    return render_template(
        "doctor_update_history.html",
        appt=appt,
        treatment=treatment
    )

@app.route('/doctor/appointment/<int:appt_id>/view')
def doctor_view_details(appt_id):
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Login as doctor", "danger")
        return redirect(url_for('index'))

    appt = Appointment.query.get_or_404(appt_id)

    if appt.doctor_id != session['id']:
        flash("Not allowed", "danger")
        return redirect(url_for('doctor_dashboard'))

    return render_template("doctor_view_details.html", appt=appt)

@app.route('/doctor/appointment/<int:appt_id>/complete', methods=['POST'])
def doctor_mark_complete(appt_id):
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Login as doctor", "danger")
        return redirect(url_for('index'))

    appt = Appointment.query.get_or_404(appt_id)

    if appt.doctor_id != session['id']:
        flash("Not allowed", "danger")
        return redirect(url_for('doctor_dashboard'))

    appt.status = "Completed"
    db.session.commit()

    flash("Appointment marked as completed", "success")
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/availability', methods=['GET', 'POST'])
def doctor_availability():
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Only doctors can set availability", "danger")
        return redirect(url_for('index'))

    doctor_id = session['id']

    if request.method == 'POST':
        d = request.form.get('date')
        morning = request.form.get('morning') == 'on'
        evening = request.form.get('evening') == 'on'

        ava = DoctorAvailability(
            doctor_id=doctor_id,
            date=d,
            morning=morning,
            evening=evening
        )
        db.session.add(ava)
        db.session.commit()

        flash("Availability saved", "success")
        return redirect(url_for('doctor_availability'))

    slots = DoctorAvailability.query.filter_by(doctor_id=doctor_id).order_by(DoctorAvailability.date).all()
    return render_template("doctor_add_availability.html", slots=slots)

@app.route('/patient/dashboard')
def patient_dashboard():
    if 'id' not in session or session.get('role') != 'patient':
        flash("Please login as patient", "danger")
        return redirect(url_for('index'))

    patient_id = session['id']

    departments = Department.query.all()

    # Only show active bookings
    upcoming = Appointment.query.filter_by(
        patient_id=patient_id,
        status="Booked"
    ).order_by(Appointment.date, Appointment.time).all()

    # Completed appointment section
    completed = Appointment.query.filter_by(
        patient_id=patient_id,
        status="Completed"
    ).order_by(Appointment.date, Appointment.time).all()

    return render_template(
        "patient_dashboard.html",
        departments=departments,
        upcoming=upcoming,
        completed=completed
    )



@app.route('/patient/department/<int:dept_id>')
def patient_department_detail(dept_id):
    if 'id' not in session or session.get('role') != 'patient':
        flash("Login as patient first", "danger")
        return redirect(url_for('index'))

    dept = Department.query.get_or_404(dept_id)
    doctors = User.query.filter_by(role='doctor', department_id=dept.id).all()

    return render_template("patient_department_detail.html", dept=dept, doctors=doctors)


@app.route('/patient/doctor/<int:doctor_id>/availability')
def patient_check_availability(doctor_id):
    if 'id' not in session or session.get('role') != 'patient':
        flash("Login as patient first", "danger")
        return redirect(url_for('index'))

    doctor = User.query.get_or_404(doctor_id)
    slots = DoctorAvailability.query.filter_by(doctor_id=doctor.id).order_by(DoctorAvailability.date).all()

    return render_template("patient_doctor_availability.html", doctor=doctor, slots=slots)


@app.route('/patient/book/<int:doctor_id>/<date>/<slot>')
def patient_book_specific(doctor_id, date, slot):
    if 'id' not in session or session.get('role') != 'patient':
        flash("Login as patient first", "danger")
        return redirect(url_for('index'))

    # check if this slot already booked by this patient
    exists = Appointment.query.filter_by(
        doctor_id=doctor_id,
        patient_id=session['id'],
        date=date,
        time=slot
    ).first()

    if exists:
        flash("You already booked this slot.", "warning")
        return redirect(url_for('patient_check_availability', doctor_id=doctor_id))

    # create new appointment
    ap = Appointment(
        doctor_id=doctor_id,
        patient_id=session['id'],
        date=date,
        time=slot,
        status="Booked"
    )
    db.session.add(ap)
    db.session.commit()

    flash("Appointment booked successfully!", "success")
    return redirect(url_for('patient_dashboard'))


@app.route('/patient/appointment/<int:appt_id>/cancel', methods=['POST'])
def patient_cancel_appointment(appt_id):
    if 'id' not in session or session.get('role') != 'patient':
        flash("Login as patient first", "danger")
        return redirect(url_for('index'))

    appt = Appointment.query.get_or_404(appt_id)

    if appt.patient_id != session['id']:
        flash("This is not your appointment", "danger")
        return redirect(url_for('patient_dashboard'))

    appt.status = "Cancelled"
    db.session.commit()

    flash("Appointment cancelled", "info")
    return redirect(url_for('patient_dashboard'))


@app.route('/patient/history')
def patient_own_history():
    if 'id' not in session or session.get('role') != 'patient':
        flash("Login as patient first", "danger")
        return redirect(url_for('index'))

    patient = User.query.get_or_404(session['id'])
    appts = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date).all()

    return render_template("patient_history.html", patient=patient, appts=appts, back_url=url_for('patient_dashboard'))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_email = request.form.get('email')
        user_pass = request.form.get('password')
        print(user_email)
        print(user_pass)

        user = User.query.filter_by(email=user_email).first()
        if not user:
            flash("User not found", "danger")
            return redirect(url_for('login'))

        if user.password != user_pass:
            flash("Wrong password", "danger")
            return redirect(url_for('login'))

        session['id'] = user.id
        session['role'] = user.role

        flash("Login successful", "success")

        if user.role == "admin":
            return redirect(url_for('admin_dashboard'))
        elif user.role == "doctor":
            return redirect(url_for('doctor_dashboard'))
        elif user.role == "patient":
            return redirect(url_for('patient_dashboard'))

        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register(): 
    if request.method == 'POST':
        name = request.form.get('username')
        email = request.form.get('email')
        pass1 = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash("Email already used", "danger")
            return redirect(url_for('register'))

        new_user = User(
            username=name,
            email=email,
            password=pass1,
            role="patient"
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created, now login", "success")
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('index'))


@app.route('/doctor/add_availability', methods=['GET', 'POST'])
def add_availability():
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Only doctors can add availability", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        d = request.form.get('date')
        morning = request.form.get('morning') == 'on'
        evening = request.form.get('evening') == 'on'

        ava = DoctorAvailability(
            doctor_id=session['id'],
            date=d,
            morning=morning,
            evening=evening
        )
        db.session.add(ava)
        db.session.commit()

        flash("Availability added", "success")
        return redirect(url_for('add_availability'))

    return render_template("doctor_add_availability.html")


@app.route('/patient/book', methods=['GET', 'POST'])
def book_appt():
    if 'id' not in session or session.get('role') != 'patient':
        flash("Login as patient to book", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        doctor_id = request.form.get('doctor')
        date = request.form.get('date')
        time = request.form.get('time')

        ap = Appointment(
            doctor_id=doctor_id,
            patient_id=session['id'],
            date=date,
            time=time
        )
        db.session.add(ap)
        db.session.commit()

        flash("Appointment booked", "success")
        return redirect(url_for('book_appt'))

    doctors = User.query.filter_by(role='doctor').all()
    return render_template("patient_book.html", doctors=doctors)
from datetime import datetime, timedelta

@app.route('/doctor/add_next7_days')
def doctor_add_next7_days():
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Login as doctor", "danger")
        return redirect(url_for('index'))

    doctor_id = session['id']
    today = datetime.today()

    for i in range(1, 8):
        d = today + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")

        exists = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            date=date_str
        ).first()

        if not exists:
            slot = DoctorAvailability(
                doctor_id=doctor_id,
                date=date_str,
                morning=True,
                evening=True
            )
            db.session.add(slot)

    db.session.commit()
    flash("Added next 7 days availability", "success")
    return redirect(url_for('doctor_availability'))


@app.route('/doctor/delete_slot/<int:slot_id>', methods=['POST'])
def doctor_delete_slot(slot_id):
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Login as doctor", "danger")
        return redirect(url_for('index'))

    slot = DoctorAvailability.query.get_or_404(slot_id)

    appointment_exists = Appointment.query.filter_by(
        doctor_id=session['id'],
        date=slot.date
    ).first()

    if appointment_exists:
        flash("You already have an appointment on this date. Cancel that appointment first.", "warning")
        return redirect(url_for('doctor_availability'))

    db.session.delete(slot)
    db.session.commit()

    flash("Slot removed", "info")
    return redirect(url_for('doctor_availability'))




@app.route('/doctor/update_slot/<int:slot_id>', methods=['POST'])
def doctor_update_slot(slot_id):
    if 'id' not in session or session.get('role') != 'doctor':
        flash("Login as doctor", "danger")
        return redirect(url_for('index'))

    slot = DoctorAvailability.query.get_or_404(slot_id)

    morning_new = 'morning' in request.form
    evening_new = 'evening' in request.form

    if not morning_new and slot.morning:
        appt = Appointment.query.filter_by(
            doctor_id=session['id'],
            date=slot.date,
            time="morning"
        ).first()

        if appt:
            flash("You have a morning appointment on this date. Cancel it first.", "warning")
            return redirect(url_for('doctor_availability'))

    if not evening_new and slot.evening:
        appt = Appointment.query.filter_by(
            doctor_id=session['id'],
            date=slot.date,
            time="evening"
        ).first()

        if appt:
            flash("You have an evening appointment on this date. Cancel it first.", "warning")
            return redirect(url_for('doctor_availability'))

    slot.morning = morning_new
    slot.evening = evening_new

    db.session.commit()

    flash("Availability updated", "success")
    return redirect(url_for('doctor_availability'))





@app.route('/create_db')
def create_db():
    db.create_all()
    return "Database Created"

if __name__ == '__main__':
    with app.app_context(): 

        db.create_all()     
        existing_admin = User.query.filter_by(username="admin").first()
        
        if not existing_admin:
            admin_db = User(
                username="admin",
                password="admin",
                email="11d@gmail.com",
                role="admin"
            )
            db.session.add(admin_db)
            db.session.commit() 
    app.run(debug=True)