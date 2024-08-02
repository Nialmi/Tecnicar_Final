from flask import render_template, url_for, flash, redirect, request, jsonify, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from .forms import RegistrationForm, LoginForm, CustomerRegistrationForm, UserRegistrationForm, VehicleStatusForm, VehicleUpdateForm
from .models import User, Customer, Vehicle
from . import db, bcrypt
import qrcode
from io import BytesIO
import base64
from sqlalchemy.exc import IntegrityError
from rpa import send_whatsapp_message, build_message  # Importar la función del archivo rpa.py
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def home():
    return render_template('index.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Su Cuenta fue Creada con Exito!, Puede Iniciar Sesion', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            if user.role == 'operator':
                return redirect(url_for('main.register_customer'))
            elif user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            return redirect(url_for('main.home'))
        else:
            flash('Inicio de sesión sin éxito. Por favor revisa el correo electrónico y la contraseña', 'danger')
    return render_template('login.html', title='Login', form=form)

@main.route('/logout')
def logout():
    logout_user()
    flash('Has Cerrado Sesión Correctamente.', 'info')
    return redirect(url_for('main.home'))

def get_customer_by_document(document):
    return Customer.query.filter_by(document=document).first()

@main.route('/verificar_cliente', methods=['POST'])
@login_required
def verificar_cliente():
    data = request.get_json()
    documento = data.get('documento')
    customer = get_customer_by_document(documento)
    if customer:
        response = {
            'existe': True,
            'cliente': {
                'nombre': customer.name,
                'last_name': customer.last_name,
                'phone': customer.phone
            }
        }
    else:
        response = {'existe': False}
    return jsonify(response)

def get_customer_by_document(document):
    return Customer.query.filter_by(document=document).first()

def get_vehicle_by_license_plate(license_plate):
    return Vehicle.query.filter_by(license_plate=license_plate).first()

@main.route('/register_customer', methods=['GET', 'POST'])
@login_required
def register_customer():
    if current_user.role not in ['admin', 'operator']:
        return redirect(url_for('main.home'))

    form = CustomerRegistrationForm()
    qr_img_base64 = None
    customer = None

    if request.method == 'POST' and 'submit' in request.form and form.validate():
        document = form.customer_document.data
        license_plate = form.vehicle_license_plate.data

        customer = get_customer_by_document(document)
        vehicle = get_vehicle_by_license_plate(license_plate)

        if customer:
            flash('Cliente encontrado.', 'info')
            if vehicle:
                flash('Vehículo encontrado. Se registrará una nueva entrada para el vehículo.', 'info')
                # Registrar nuevo vehículo con la misma placa pero nueva fecha
                new_vehicle = Vehicle(
                    model=form.vehicle_model.data,
                    license_plate=form.vehicle_license_plate.data,
                    vehicle_color=form.vehicle_color.data,
                    vehicle_type=form.vehicle_type.data,
                    customer_id=customer.id,
                    aseguradora=form.aseguradora.data,
                    workshop=form.workshop.data,
                    Fecha_Registro=datetime.utcnow()
                )
                db.session.add(new_vehicle)
            else:
                # Registrar nuevo vehículo para el cliente existente
                new_vehicle = Vehicle(
                    model=form.vehicle_model.data,
                    license_plate=form.vehicle_license_plate.data,
                    vehicle_color=form.vehicle_color.data,
                    vehicle_type=form.vehicle_type.data,
                    customer_id=customer.id,
                    aseguradora=form.aseguradora.data,
                    workshop=form.workshop.data,
                    Fecha_Registro=datetime.utcnow()
                )
                db.session.add(new_vehicle)
        else:
            flash('Cliente no encontrado. Registrando nuevo cliente y vehículo.', 'info')
            # Registrar nuevo cliente y vehículo
            customer = Customer(
                document=form.customer_document.data, 
                name=form.customer_name.data, 
                last_name=form.customer_last_name.data, 
                phone=form.customer_phone.data
            )
            db.session.add(customer)
            db.session.commit()

            new_vehicle = Vehicle(
                model=form.vehicle_model.data,
                license_plate=form.vehicle_license_plate.data,
                vehicle_color=form.vehicle_color.data,
                vehicle_type=form.vehicle_type.data,
                customer_id=customer.id,
                aseguradora=form.aseguradora.data,
                workshop=form.workshop.data,
                Fecha_Registro=datetime.utcnow()
            )
            db.session.add(new_vehicle)

        try:
            db.session.commit()
            qr_data = url_for('main.vehicle_info', vehicle_id=new_vehicle.id, _external=True)
            img = qrcode.make(qr_data)
            buf = BytesIO()
            img.save(buf)
            buf.seek(0)

            new_vehicle.qr_image = buf.getvalue()
            db.session.commit()

            qr_img_base64 = base64.b64encode(new_vehicle.qr_image).decode('utf-8')

            flash('¡Cliente y vehículo registrados exitosamente!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Error en el registro. Por favor, intente de nuevo.', 'danger')
    else:
        flash('Por favor corrija los errores en el formulario.', 'danger')

    return render_template('register_customer.html', title='Register Customer', form=form, qr_img=qr_img_base64, customer=customer)

@main.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    return render_template('admin_dashboard.html', title='Admin Dashboard')

@main.route('/admin/reports', methods=['GET', 'POST'])
@login_required
def admin_reports():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))

    # Obtener los estados distintos de la base de datos
    status = Vehicle.query.with_entities(Vehicle.status).distinct().all()
    
    # Verifica si el campo workshop existe en la base de datos
    workshops = []
    if hasattr(Vehicle, 'workshop'):
        workshops = Vehicle.query.with_entities(Vehicle.workshop).distinct().all()

    return render_template('admin_reports.html', title='Vehicle Reports', status=status, workshops=workshops)

@main.route('/get_report_data', methods=['POST'])
@login_required
def get_report_data():
    state_filter = request.json.get('state_filter', '')
    workshop_filter = request.json.get('workshop_filter', '')
    month_filter = request.json.get('month_filter', '')

    query = Vehicle.query
    if state_filter:
        query = query.filter_by(status=state_filter)
    if workshop_filter:
        query = query.filter_by(workshop=workshop_filter)
    if month_filter:
        # Suponiendo que el campo Fecha_Registro es un objeto datetime en SQLAlchemy
        query = query.filter(db.extract('month', Vehicle.Fecha_Registro) == int(month_filter))

    vehicles = query.all()

    data = {}
    for vehicle in vehicles:
        workshop = vehicle.workshop
        status = vehicle.status
        if workshop not in data:
            data[workshop] = {}
        if status in data[workshop]:
            data[workshop][status] += 1
        else:
            data[workshop][status] = 1

    print(data)  # Imprime los datos para depurar
    return jsonify(data)

@main.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    form = UserRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, role=form.role.data)
        db.session.add(user)
        db.session.commit()
        flash('¡Usuario creado exitosamente!', 'success')
        return redirect(url_for('main.admin_dashboard'))
    return render_template('admin_create_user.html', title='Create User', form=form)

@main.route('/admin/view_records', methods=['GET', 'POST'])
@login_required
def admin_view_records():
    if current_user.role not in ['admin', 'operator']:
        return redirect(url_for('main.home'))
    
    form = VehicleUpdateForm()
    vehicle = None
    customer = None
    if request.method == 'POST':
        license_plate = request.form.get('document')
        vehicle = Vehicle.query.filter_by(license_plate=license_plate).first()
        if vehicle:
            customer = Customer.query.get(vehicle.customer_id)
            form = VehicleUpdateForm(obj=vehicle)
            form.customer_document.data = customer.document
            form.customer_name.data = customer.name
            form.customer_last_name.data = customer.last_name
            form.customer_phone.data = customer.phone
    
    return render_template('admin_view_records.html', title='View Records', vehicle=vehicle, customer=customer, base64=base64, form=form)

@main.route('/admin/update_vehicle', methods=['POST'])
@login_required
def update_vehicle():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    
    form = VehicleUpdateForm()
    if form.validate_on_submit():
        vehicle = Vehicle.query.filter_by(license_plate=form.license_plate.data).first()
        customer = Customer.query.filter_by(document=form.customer_document.data).first()
        if vehicle and customer:
            vehicle.model = form.model.data
            vehicle.vehicle_color = form.vehicle_color.data
            vehicle.vehicle_type = form.vehicle_type.data
            vehicle.workshop = form.workshop.data
            vehicle.aseguradora = form.aseguradora.data
            customer.name = form.customer_name.data
            customer.last_name = form.customer_last_name.data
            customer.phone = form.customer_phone.data
            db.session.commit()
            flash('Información del vehículo y cliente actualizada exitosamente', 'success')
        else:
            flash('Vehículo o cliente no encontrado', 'danger')
    else:
        flash('Error en la validación del formulario', 'danger')
    return redirect(url_for('main.admin_view_records'))

@main.route('/admin/delete_vehicle', methods=['POST'])
@login_required
def delete_vehicle():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    
    license_plate = request.form.get('license_plate')
    vehicle = Vehicle.query.filter_by(license_plate=license_plate).first()
    if vehicle:
        db.session.delete(vehicle)
        db.session.commit()
        flash('Vehículo eliminado exitosamente', 'success')
    else:
        flash('Vehículo no encontrado', 'danger')
    return redirect(url_for('main.admin_view_records'))

@main.route('/admin/manage_user', methods=['GET', 'POST'])
@login_required
def manage_user():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    form = UserRegistrationForm()
    user_info = None
    return render_template('admin_manage_user.html', title='Manage User', form=form, user_info=user_info)

@main.route('/admin/search_user', methods=['POST'])
@login_required
def search_user():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    user_info = None
    if user:
        user_info = {
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
        flash(f'User found: {user.username}, {user.email}, {user.role}', 'success')
    else:
        flash('User not found', 'danger')
    return render_template('admin_manage_user.html', title='Manage User', form=UserRegistrationForm(), user_info=user_info)

@main.route('/admin/delete_user', methods=['POST'])
@login_required
def delete_user():
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully', 'success')
    else:
        flash('User not found', 'danger')
    return redirect(url_for('main.manage_user'))
