from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
# werkzeug.security items are already imported in database.py, not strictly needed here if not used directly
# from werkzeug.security import generate_password_hash, check_password_hash 
from werkzeug.exceptions import NotFound
from database import Database #
from classes import User #
#from jinja2 import evalcontextfilter, Markup # Not used in current scope

app = Flask(__name__)
app.secret_key = '67992084211'  

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# These SQLAlchemy configs are not used if we are directly using sqlite3 via Database class
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scams.db'

db = Database() #

@login_manager.user_loader
def load_user(user_id):
    return db.get_user_by_id(int(user_id)) #

# Rotas principais
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.get_user_by_email(email) #
        
        if user and user.check_password(password):  #
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('E-mail ou senha incorretos', 'error')
    
    return render_template('login.html') #

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
        elif db.get_user_by_email(email): #
            flash('E-mail já cadastrado!', 'error')
        else:
            if db.add_user(name, email, password): #
                flash('Conta criada com sucesso! Faça login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Erro ao criar conta. Tente novamente.', 'error')
    
    return render_template('register.html')

# Denúncias
@app.route('/api/v1/scams', methods=['GET'])
def api_scams():
    scams_data = db.get_all_scams() #
    # Assuming DigitalScam objects are not directly returned by get_all_scams based on its current implementation
    # If they were, it would be: [scam.__dict__ for scam in scams_data]
    return jsonify({
        "status": "success",
        "data": scams_data 
    })

@app.route('/scams')
def list_scams():
    try:
        scam_type_filter = request.args.get('type') # Renamed to avoid conflict
        min_date_filter = request.args.get('min_date') # Renamed
        order = request.args.get('order', 'newest')
        
        query = '''
            SELECT 
                s.id, s.title, s.description, s.scam_type, s.evidence,
                s.created_at, u.name as author
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE 1=1
        '''
        params = []
        
        if scam_type_filter and scam_type_filter != '':
            query += ' AND s.scam_type = ?'
            params.append(scam_type_filter)
        
        if min_date_filter and min_date_filter != '':
            query += ' AND DATE(s.created_at) >= ?'
            params.append(min_date_filter)
        
        query += ' ORDER BY s.created_at ' + ('DESC' if order == 'newest' else 'ASC')
        
        cursor = db.conn.cursor()
        cursor.execute(query, tuple(params)) # Use tuple for params
        
        columns = [column[0] for column in cursor.description]
        scams_list = [dict(zip(columns, row)) for row in cursor.fetchall()] # Renamed
        
        return render_template('scams.html', scams=scams_list) #
        
    except Exception as e:
        app.logger.error(f"Error loading scams: {e}") # Log the error
        flash(f'Erro ao carregar denúncias: {str(e)}', 'error')
        return redirect(url_for('home'))
    
@app.route('/report', methods=['GET', 'POST'])
@login_required
def report_scam():
    if request.method == 'POST':
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
            db.conn.rollback() # Rollback on error
            app.logger.error(f"Error reporting scam: {e}")
            flash(f'Erro ao registrar denúncia: {str(e)}', 'error')
    
    return render_template('report.html')

@app.route('/scams/<int:scam_id>')
def scam_details(scam_id):
    try:
        cursor = db.conn.cursor()
        
        # Busca a denúncia
        cursor.execute('''
            SELECT 
                s.id, s.title, s.description, s.scam_type, s.evidence, 
                s.created_at, s.user_id,
                u.name as author, u.email as author_email
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (scam_id,))
        
        scam_data_row = cursor.fetchone() # Renamed
        if not scam_data_row:
            flash('Denúncia não encontrada', 'error')
            return redirect(url_for('list_scams'))
        
        columns = [column[0] for column in cursor.description]
        scam_dict = dict(zip(columns, scam_data_row)) # Renamed
        
        # Busca os comentários
        cursor.execute('''
            SELECT 
                c.id, c.text, c.created_at, c.user_id, u.name as author,
                0 as is_editing -- Default to not editing
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.scam_id = ?
            ORDER BY c.created_at DESC
        ''', (scam_id,))
        
        comments_columns = [column[0] for column in cursor.description]
        scam_dict['comments'] = [dict(zip(comments_columns, row)) for row in cursor.fetchall()]

        # Fetch votes
        vote_counts = db.get_votes(scam_id) #
        user_vote = 0
        if current_user.is_authenticated:
            user_vote = db.get_user_vote(scam_id, current_user.id) #
        
        return render_template('scam_details.html', 
                                 scam=scam_dict, 
                                 likes=vote_counts['likes'], 
                                 dislikes=vote_counts['dislikes'], 
                                 user_vote=user_vote) #
        
    except Exception as e:
        app.logger.error(f"Error loading scam details for {scam_id}: {e}")
        flash(f'Erro ao carregar detalhes da denúncia: {str(e)}', 'error')
        return redirect(url_for('list_scams'))

@app.route('/scams/<int:scam_id>/vote', methods=['POST'])
@login_required
def vote_scam_route(scam_id):
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Requisição deve ser JSON'}), 400
    
    data = request.get_json()
    vote_type = data.get('vote_type')
    
    if vote_type not in [1, -1]:
        return jsonify({'status': 'error', 'message': 'Tipo de voto inválido. Use 1 para like, -1 para dislike.'}), 400
    
    # Verificar se a denúncia existe
    cursor = db.conn.cursor()
    cursor.execute("SELECT id FROM scams WHERE id = ?", (scam_id,))
    if not cursor.fetchone():
        return jsonify({'status': 'error', 'message': 'Denúncia não encontrada'}), 404

    try:
        new_user_vote_status = db.manage_vote(current_user.id, scam_id, vote_type) #
        updated_counts = db.get_votes(scam_id) #

        return jsonify({
            'status': 'success',
            'message': 'Voto processado com sucesso!',
            'likes': updated_counts['likes'],
            'dislikes': updated_counts['dislikes'],
            'user_vote': new_user_vote_status # 1 for like, -1 for dislike, 0 for no vote
        })
    except Exception as e:
        app.logger.error(f"Error processing vote for scam {scam_id} by user {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'Erro interno ao processar o voto.'}), 500


# Comentários - (Mantendo as rotas de comentários como estavam, verificar se precisam de ajustes)
@app.route('/scams/<int:scam_id>/comment', methods=['POST'])
@login_required
def add_comment(scam_id):
    text = request.form.get('text')
    if not text or not text.strip(): # Added strip()
        flash('Comentário não pode estar vazio!', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))
    
    try:
        cursor = db.conn.cursor()
        cursor.execute('''
            INSERT INTO comments (text, user_id, scam_id)
            VALUES (?, ?, ?)
        ''', (text.strip(), current_user.id, scam_id))
        db.conn.commit()
        flash('Comentário adicionado!', 'success')
    except Exception as e:
        db.conn.rollback()
        app.logger.error(f"Error adding comment for scam {scam_id}: {e}")
        flash(f'Erro ao adicionar comentário: {str(e)}', 'error')
    
    return redirect(url_for('scam_details', scam_id=scam_id))

# ... (manter as outras rotas de comentários: get_comments, edit_comment, update_comment, delete_comment)
# ... (manter filter_scams e is_url filter)

@app.route('/scams/<int:scam_id>/comments') # From original file
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
    comments_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return jsonify(comments_list)

@app.route('/comments/<int:comment_id>/edit') # From original file
@login_required
def edit_comment(comment_id):
    try:
        cursor = db.conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.text, c.user_id, c.scam_id, c.created_at
            FROM comments c
            WHERE c.id = ? AND c.user_id = ?
        ''', (comment_id, current_user.id))
        comment_data_row = cursor.fetchone()
        
        if not comment_data_row:
            flash('Comentário não encontrado ou não autorizado para edição.', 'error')
            return redirect(request.referrer or url_for('list_scams')) # Redirect back or to list
        
        scam_id = comment_data_row[3]

        # Fetch the main scam details
        cursor.execute('''
            SELECT s.*, u.name as author, u.email as author_email
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (scam_id,))
        scam_main_data = cursor.fetchone()
        if not scam_main_data:
            flash('Denúncia associada não encontrada.', 'error')
            return redirect(url_for('list_scams'))
        
        scam_columns = [col[0] for col in cursor.description]
        scam_dict_for_render = dict(zip(scam_columns, scam_main_data))

        # Fetch all comments for this scam, marking the one being edited
        cursor.execute('''
            SELECT c.id, c.text, c.created_at, c.user_id, u.name as author,
                   (c.id = ?) as is_editing
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.scam_id = ?
            ORDER BY c.created_at DESC
        ''', (comment_id, scam_id))
        
        comments_columns = [col[0] for col in cursor.description]
        scam_dict_for_render['comments'] = [dict(zip(comments_columns, row)) for row in cursor.fetchall()]
        
        # Fetch votes for scam_details template
        vote_counts = db.get_votes(scam_id)
        user_vote = 0
        if current_user.is_authenticated:
            user_vote = db.get_user_vote(scam_id, current_user.id)

        return render_template('scam_details.html', 
                                scam=scam_dict_for_render,
                                likes=vote_counts['likes'],
                                dislikes=vote_counts['dislikes'],
                                user_vote=user_vote)
        
    except Exception as e:
        app.logger.error(f"Error loading edit comment form for comment {comment_id}: {e}")
        flash(f'Erro ao preparar edição do comentário: {str(e)}', 'error')
        return redirect(request.referrer or url_for('list_scams'))

@app.route('/comments/<int:comment_id>/update', methods=['POST']) # From original file
@login_required
def update_comment(comment_id):
    new_text = request.form.get('text')
    if not new_text or not new_text.strip():
        flash('O comentário não pode estar vazio.', 'error')
        # To redirect back to the edit state, we need scam_id.
        # This requires fetching it or passing it. For simplicity, redirect to scam details.
        # A better UX would involve passing scam_id or fetching it before redirecting to edit_comment.
        cursor = db.conn.cursor()
        cursor.execute('SELECT scam_id FROM comments WHERE id = ?', (comment_id,))
        res = cursor.fetchone()
        if res:
            return redirect(url_for('edit_comment', comment_id=comment_id)) # Or scam_details
        return redirect(url_for('list_scams'))

    try:
        cursor = db.conn.cursor()
        cursor.execute('SELECT user_id, scam_id FROM comments WHERE id = ?', (comment_id,))
        comment_owner_scam = cursor.fetchone()

        if not comment_owner_scam:
            flash('Comentário não encontrado.', 'error')
            return redirect(url_for('list_scams'))
        
        if comment_owner_scam[0] != current_user.id:
            flash('Não autorizado a atualizar este comentário.', 'error')
            return redirect(url_for('scam_details', scam_id=comment_owner_scam[1]))

        cursor.execute('UPDATE comments SET text = ? WHERE id = ?', (new_text.strip(), comment_id))
        db.conn.commit()
        flash('Comentário atualizado com sucesso!', 'success')
        return redirect(url_for('scam_details', scam_id=comment_owner_scam[1]))

    except Exception as e:
        db.conn.rollback()
        app.logger.error(f"Error updating comment {comment_id}: {e}")
        flash(f'Erro ao atualizar comentário: {str(e)}', 'error')
        # Try to redirect to the scam_details page of the comment if possible
        cursor = db.conn.cursor()
        cursor.execute('SELECT scam_id FROM comments WHERE id = ?', (comment_id,))
        res = cursor.fetchone()
        if res:
            return redirect(url_for('scam_details', scam_id=res[0]))
        return redirect(url_for('list_scams'))


@app.route('/comments/<int:comment_id>/delete', methods=['POST']) # From original file
@login_required
def delete_comment(comment_id):
    try:
        cursor = db.conn.cursor()
        cursor.execute('SELECT user_id, scam_id FROM comments WHERE id = ?', (comment_id,))
        comment_info = cursor.fetchone()
        
        if not comment_info:
            flash('Comentário não encontrado.', 'error')
        elif comment_info[0] != current_user.id:
            flash('Você não tem permissão para excluir este comentário.', 'error')
        else:
            cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
            db.conn.commit()
            flash('Comentário excluído com sucesso!', 'success')
            return redirect(url_for('scam_details', scam_id=comment_info[1]))
        
        # If redirection inside else didn't happen, redirect to list_scams or previous page
        return redirect(request.referrer or url_for('list_scams'))
        
    except Exception as e:
        db.conn.rollback()
        app.logger.error(f"Error deleting comment {comment_id}: {e}")
        flash(f'Erro ao excluir comentário: {str(e)}', 'error')
        return redirect(request.referrer or url_for('list_scams'))


@app.template_filter('is_url') # From original file
def is_url(text):
    import re
    url_pattern = re.compile(r'https?://\S+')
    return bool(url_pattern.match(str(text))) if text else False # Added str() for safety

if __name__ == '__main__':
    app.run(debug=True)