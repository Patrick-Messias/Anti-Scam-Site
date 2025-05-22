from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from database import Database
from classes import User
#from jinja2 import evalcontextfilter, Markup

app = Flask(__name__)
app.secret_key = '67992084211'  

# Configuração do LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scams.db'

# # Database (versão funcional mínima)
# class Database:
#     def __init__(self):
#         self.users = {
#             "admin@test.com": {
#                 "id": 1,
#                 "password": generate_password_hash("senha123"),
#                 "name": "Admin"
#             }
#         }

#     def get_user_by_id(self, user_id):
#         for email, user in self.users.items():
#             if user["id"] == user_id:
#                 return User(user["id"], email, user["name"], user["password"])
#         return None

#     def get_user_by_email(self, email):
#         user_data = self.users.get(email)
#         if user_data:
#             return User(user_data["id"], email, user_data["name"], user_data["password"])
#         return None

# # Classe User obrigatória para o Flask-Login
# class User(UserMixin):
#     def __init__(self, id, email, name, password_hash):
#         self.id = id
#         self.email = email
#         self.name = name
#         self.password_hash = password_hash

#     def check_password(self, password):
#         return check_password_hash(self.password_hash, password)

db = Database()

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
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.get_user_by_email(email)
        
        if user and user.check_password(password):  # Isso está correto
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('E-mail ou senha incorretos', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.name)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([name, email, password, confirm_password]):
            flash('Preencha todos os campos!', 'error')
        elif password != confirm_password:
            flash('As senhas não coincidem!', 'error')
        elif db.get_user_by_email(email):
            flash('E-mail já cadastrado!', 'error')
        else:
            if db.add_user(name, email, password):
                flash('Conta criada com sucesso! Faça login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Erro ao criar conta. Tente novamente.', 'error')
    
    return render_template('register.html')

@app.route('/api/v1/scams', methods=['GET'])
def api_scams():  # Nome alterado
    scams = db.get_all_scams()
    return jsonify({
        "status": "success",
        "data": [scam.__dict__ for scam in scams]
    })

@app.route('/scams')
def list_scams():
    try:
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT 
                scams.id,
                scams.title,
                scams.description,
                scams.scam_type,
                scams.evidence,
                scams.created_at,
                users.name as author
            FROM scams 
            JOIN users ON scams.user_id = users.id
            ORDER BY scams.created_at DESC
        ''')
        columns = [column[0] for column in cursor.description]  # Pega os nomes das colunas
        scams = []
        
        for row in cursor.fetchall():
            # Converte a tupla para dicionário com nomes de colunas
            scam = dict(zip(columns, row))
            scams.append(scam)
            
        return render_template('scams.html', scams=scams)
        
    except Exception as e:
        flash(f'Erro ao carregar denúncias: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report_scam():
    if request.method == 'POST':
        # Certifique-se que esses names batem com seu formulário
        title = request.form.get('title')
        description = request.form.get('description')
        scam_type = request.form.get('scam_type')
        evidence = request.form.get('evidence')
        
        try:
            cursor = db.conn.cursor()
            cursor.execute('''
                INSERT INTO scams (title, description, scam_type, evidence, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, description, scam_type, evidence, current_user.id))
            db.conn.commit()
            flash('Denúncia registrada com sucesso!', 'success')
            return redirect(url_for('list_scams'))
        except Exception as e:
            flash(f'Erro ao registrar: {str(e)}', 'error')
    
    return render_template('report.html')

@app.route('/scams/<int:scam_id>')
def scam_details(scam_id):
    try:
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT 
                scams.*,
                users.name as author,
                users.email as author_email
            FROM scams 
            JOIN users ON scams.user_id = users.id
            WHERE scams.id = ?
        ''', (scam_id,))
        
        columns = [column[0] for column in cursor.description]
        scam = dict(zip(columns, cursor.fetchone()))
        
        return render_template('scam_details.html', scam=scam)
        
    except Exception as e:
        flash(f'Erro ao carregar denúncia: {str(e)}', 'error')
        return redirect(url_for('list_scams'))

@app.template_filter('is_url')
def is_url(text):
    import re
    url_pattern = re.compile(r'https?://\S+')
    return bool(url_pattern.match(text)) if text else False

if __name__ == '__main__':
    app.run(debug=True)