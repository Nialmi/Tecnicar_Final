from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash

app = create_app()

with app.app_context():
    users = User.query.all()
    for user in users:
        try:
            # Verifica si el hash de la contraseña es válido
            check_password_hash(user.password, 'Miranda09*')
        except ValueError:
            # Si hay un error, significa que el hash no es válido, así que lo regeneramos
            print(f"Actualizando hash de contraseña para el usuario: {user.username}")
            user.password = generate_password_hash('Miranda09*')
            db.session.add(user)
    db.session.commit()
    print("Actualización completa.")