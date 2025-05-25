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

# Denúncias
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
        # Obter parâmetros de filtro
        scam_type = request.args.get('type')
        min_date = request.args.get('min_date')
        order = request.args.get('order', 'newest')
        
        # Query base
        query = '''
            SELECT 
                s.id,
                s.title,
                s.description,
                s.scam_type,
                s.evidence,
                s.created_at,
                u.name as author
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE 1=1
        '''
        params = []
        
        # Aplicar filtros
        if scam_type and scam_type != '':
            query += ' AND s.scam_type = ?'
            params.append(scam_type)
        
        if min_date and min_date != '':
            query += ' AND DATE(s.created_at) >= ?'
            params.append(min_date)
        
        # Ordenação
        query += ' ORDER BY s.created_at ' + ('DESC' if order == 'newest' else 'ASC')
        
        # DEBUG - Mostrar a query gerada
        print(f"Executando query: {query}")
        print(f"Com parâmetros: {params}")
        
        # Executar query
        cursor = db.conn.cursor()
        cursor.execute(query, params)
        
        columns = [column[0] for column in cursor.description]
        scams = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # DEBUG - Mostrar resultados
        print(f"Encontrados {len(scams)} denúncias")
        
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
        
        # Busca a denúncia
        cursor.execute('''
            SELECT 
                s.*,
                u.name as author,
                u.email as author_email
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (scam_id,))
        
        scam_data = cursor.fetchone()
        if not scam_data:
            flash('Denúncia não encontrada', 'error')
            return redirect(url_for('list_scams'))
        
        columns = [column[0] for column in cursor.description]
        scam = dict(zip(columns, scam_data))
        
        # Busca os comentários (todos com is_editing=0)
        cursor.execute('''
            SELECT 
                c.id,
                c.text,
                c.created_at,
                c.user_id,
                u.name as author,
                0 as is_editing
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.scam_id = ?
            ORDER BY c.created_at DESC
        ''', (scam_id,))
        
        comments_columns = [column[0] for column in cursor.description]
        scam['comments'] = [dict(zip(comments_columns, row)) for row in cursor.fetchall()]
        
        return render_template('scam_details.html', scam=scam)
        
    except Exception as e:
        flash(f'Erro ao carregar denúncia: {str(e)}', 'error')
        return redirect(url_for('list_scams'))
      
# Commentários
@app.route('/scams/<int:scam_id>/comment', methods=['POST'])
@login_required
def add_comment(scam_id):
    if request.method == 'POST':
        text = request.form.get('text')
        
        if not text:
            flash('Comentário não pode estar vazio!', 'error')
            return redirect(url_for('scam_details', scam_id=scam_id))
        
        try:
            cursor = db.conn.cursor()
            cursor.execute('''
                INSERT INTO comments (text, user_id, scam_id)
                VALUES (?, ?, ?)
            ''', (text, current_user.id, scam_id))
            db.conn.commit()
            flash('Comentário adicionado!', 'success')
        except Exception as e:
            flash(f'Erro ao comentar: {str(e)}', 'error')
        
        return redirect(url_for('scam_details', scam_id=scam_id))

@app.route('/scams/<int:scam_id>/comments')
def get_comments(scam_id):
    cursor = db.conn.cursor()
    cursor.execute('''
        SELECT 
            comments.text, 
            comments.created_at,
            users.name as author
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.scam_id = ?
        ORDER BY comments.created_at DESC
    ''', (scam_id,))
    
    columns = [column[0] for column in cursor.description]
    comments = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return jsonify(comments)

@app.route('/comments/<int:comment_id>/edit')
@login_required
def edit_comment(comment_id):
    try:
        cursor = db.conn.cursor()
        
        # 1. Busca o comentário com verificação de usuário
        cursor.execute('''
            SELECT c.id, c.text, c.user_id, c.scam_id, c.created_at
            FROM comments c
            WHERE c.id = ? AND c.user_id = ?
        ''', (comment_id, current_user.id))
        
        comment_data = cursor.fetchone()
        
        if not comment_data:
            flash('Comentário não encontrado ou não autorizado', 'error')
            return redirect(url_for('list_scams'))
        
        scam_id = comment_data[3]  # scam_id está na posição 3 (4ª coluna)

        # 2. Busca todos os comentários marcando o atual para edição
        cursor.execute('''
            SELECT c.id, c.text, c.created_at, c.user_id, u.name as author,
                   (c.id = ?) as is_editing
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.scam_id = ?
            ORDER BY c.created_at DESC
        ''', (comment_id, scam_id))
        
        columns = [column[0] for column in cursor.description]
        comments = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # 3. Busca a denúncia principal
        cursor.execute('''
            SELECT s.*, u.name as author, u.email as author_email
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (scam_id,))
        
        scam_data = cursor.fetchone()
        
        if not scam_data:
            flash('Denúncia associada não encontrada', 'error')
            return redirect(url_for('list_scams'))
        
        scam_columns = [column[0] for column in cursor.description]
        scam = dict(zip(scam_columns, scam_data))
        scam['comments'] = comments
        
        return render_template('scam_details.html', scam=scam)
        
    except Exception as e:
        flash(f'Erro ao editar comentário: {str(e)}', 'error')
        return redirect(url_for('list_scams'))
        
@app.route('/comments/<int:comment_id>/update', methods=['POST'])
@login_required
def update_comment(comment_id):
    try:
        new_text = request.form.get('text')
        if not new_text or not new_text.strip():
            flash('O comentário não pode estar vazio', 'error')
            return redirect(url_for('edit_comment', comment_id=comment_id))
        
        cursor = db.conn.cursor()
        
        # Primeiro verifica se o comentário existe e pertence ao usuário
        cursor.execute('''
            SELECT scam_id FROM comments 
            WHERE id = ? AND user_id = ?
        ''', (comment_id, current_user.id))
        
        result = cursor.fetchone()
        if not result:
            flash('Comentário não encontrado ou não autorizado', 'error')
            return redirect(url_for('list_scams'))
        
        scam_id = result[0]
        
        # Atualiza o comentário
        cursor.execute('''
            UPDATE comments 
            SET text = ? 
            WHERE id = ? AND user_id = ?
        ''', (new_text.strip(), comment_id, current_user.id))
        db.conn.commit()
        
        flash('Comentário atualizado com sucesso!', 'success')
        return redirect(url_for('scam_details', scam_id=scam_id))
        
    except Exception as e:
        flash(f'Erro ao atualizar comentário: {str(e)}', 'error')
        return redirect(url_for('list_scams'))
    
@app.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    try:
        cursor = db.conn.cursor()
        
        # Verifica o dono e obtém o scam_id antes de deletar
        cursor.execute('SELECT user_id, scam_id FROM comments WHERE id = ?', (comment_id,))
        result = cursor.fetchone()
        
        if not result:
            flash('Comentário não encontrado', 'error')
        elif result[0] != current_user.id:
            flash('Você não tem permissão para excluir este comentário', 'error')
        else:
            cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
            db.conn.commit()
            flash('Comentário excluído com sucesso!', 'success')
            return redirect(url_for('scam_details', scam_id=result[1]))
        
        return redirect(url_for('list_scams'))
        
    except Exception as e:
        flash(f'Erro ao excluir comentário: {str(e)}', 'error')
        return redirect(url_for('list_scams'))
    

@app.route('/scams/<int:scam_id>/vote/<int:vote_type>', methods=['POST'])
@login_required
def vote_scam(scam_id, vote_type):
    try:
        cursor = db.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO votes (user_id, scam_id, vote_type)
            VALUES (?, ?, ?)
        ''', (current_user.id, scam_id, vote_type))
        db.conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/scams/filter')
def filter_scams():
    scam_type = request.args.get('type')
    min_date = request.args.get('min_date')
    # ... outros filtros
    
    query = 'SELECT * FROM scams WHERE 1=1'
    params = []
    
    if scam_type:
        query += ' AND scam_type = ?'
        params.append(scam_type)
    # ... adicione outros filtros
    
    cursor = db.conn.cursor()
    cursor.execute(query, params)
    scams = [dict(zip([col[0] for col in cursor.description], row)) 
             for row in cursor.fetchall()]
    
    return render_template('scams.html', scams=scams)

@app.template_filter('is_url')
def is_url(text):
    import re
    url_pattern = re.compile(r'https?://\S+')
    return bool(url_pattern.match(text)) if text else False

if __name__ == '__main__':
    app.run(debug=True)