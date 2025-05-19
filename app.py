from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, login_user, current_user, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '1911'  # Chave secreta para sessões

# Configuração do LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database (versão funcional mínima)
class Database:
    def __init__(self):
        self.users = {
            "admin@test.com": {
                "id": 1,
                "password": generate_password_hash("senha123"),
                "name": "Admin"
            }
        }

    def get_user_by_id(self, user_id):
        for email, user in self.users.items():
            if user["id"] == user_id:
                return User(user["id"], email, user["name"], user["password"])
        return None

    def get_user_by_email(self, email):
        user_data = self.users.get(email)
        if user_data:
            return User(user_data["id"], email, user_data["name"], user_data["password"])
        return None

# Classe User obrigatória para o Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name, password_hash):
        self.id = id
        self.email = email
        self.name = name
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

db = Database()

# Configuração OBRIGATÓRIA do user_loader
@login_manager.user_loader
def load_user(user_id):
    return db.get_user_by_id(int(user_id))

# Rotas principais
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.get_user_by_email(email)

        if not user:
            flash('Email não cadastrado!', 'error')
        elif not user.check_password(password):
            flash('Senha incorreta!', 'error')
        
        print(f"Senha digitada: {password}")  # Debug
        if user:
            print(f"Hash armazenado: {user.password_hash}")  # Debug
            
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return f"Bem-vindo, {current_user.name}! <a href='/logout'>Sair</a>"

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()  # Novo

            if not all([email, password, confirm_password]):
                flash('Preencha todos os campos!', 'error')
                return redirect(url_for('register'))

            if password != confirm_password:
                flash('As senhas não coincidem!', 'error')
                return redirect(url_for('register'))

            if not db.get_user_by_email(email):
                new_id = len(db.users) + 1
                db.users[email] = {
                    "id": new_id,
                    "name": email.split('@')[0],
                    "password": generate_password_hash(password)
                }
                flash('Cadastro realizado! Faça login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Email já cadastrado!', 'error')

        except Exception as e:
            flash(f'Erro no registro: {str(e)}', 'error')

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)