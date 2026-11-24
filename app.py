import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from services.ia_service import analizar_imagen_ia

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_super_segura_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///basuracero.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 # Max 5MB per image

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELOS DE BASE DE DATOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Denuncia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    lat = db.Column(db.String(50), nullable=False)
    lng = db.Column(db.String(50), nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(50), default='Pendiente')
    
    ia_tipo = db.Column(db.String(200))
    ia_nivel = db.Column(db.String(100))
    ia_similitud = db.Column(db.String(200))

    user = db.relationship('User', backref=db.backref('denuncias', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        denuncias = Denuncia.query.all()
    else:
        denuncias = Denuncia.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', denuncias=denuncias)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe.', 'danger')
            return redirect(url_for('register'))
            
        is_admin = True if User.query.count() == 0 else False
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registro exitoso. Inicia sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/denunciar', methods=['POST'])
@login_required
def denunciar():
    imagen = request.files.get('imagen')
    direccion = request.form.get('direccion')
    
    if imagen and direccion:
        # --- DETECCIÓN DE DUPLICADOS ---
        # Buscamos si ya hay una denuncia activa en esta misma dirección
        denuncia_existente = Denuncia.query.filter(
            Denuncia.direccion == direccion,
            Denuncia.estado.in_(['Pendiente', 'Proceso'])
        ).first()

        if denuncia_existente:
            # Si existe, mostramos el mensaje de error y cortamos el proceso para no duplicar
            flash('¡Atención! Ya existe una denuncia activa en esta ubicación. Se ha registrado tu aviso como reiteración para evitar duplicados.', 'warning')
            return redirect(url_for('dashboard'))
        # -------------------------------

        filename = secure_filename(imagen.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen.save(filepath)
        
        resultado_ia = analizar_imagen_ia(filepath)
        
        nueva_denuncia = Denuncia(
            user_id=current_user.id,
            direccion=direccion,
            lat=request.form.get('lat'),
            lng=request.form.get('lng'),
            imagen=filename,
            ia_tipo=resultado_ia['tipo'],
            ia_nivel=resultado_ia['nivel'],
            ia_similitud=resultado_ia['similitud']
        )
        db.session.add(nueva_denuncia)
        db.session.commit()
        flash('Denuncia registrada con éxito.', 'success')
        
    return redirect(url_for('dashboard'))

# --- RUTAS DE ADMIN ---
@app.route('/actualizar_estado/<int:id>', methods=['POST'])
@login_required
def actualizar_estado(id):
    if current_user.is_admin:
        denuncia = Denuncia.query.get(id)
        if denuncia:
            denuncia.estado = request.form.get('estado')
            db.session.commit()
            flash('Estado actualizado.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/eliminar_denuncia/<int:id>', methods=['POST'])
@login_required
def eliminar_denuncia(id):
    if current_user.is_admin:
        denuncia = Denuncia.query.get(id)
        if denuncia:
            db.session.delete(denuncia)
            db.session.commit()
            flash('Denuncia eliminada.', 'success')
    return redirect(url_for('dashboard'))

with app.app_context():
    os.makedirs('static/uploads', exist_ok=True)
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
