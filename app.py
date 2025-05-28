from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from werkzeug.exceptions import NotFound
from database import Database
from classes import User, Tutorial
# Corrigido a importação do Jinja2 e Markupsafe
from jinja2 import pass_eval_context
from markupsafe import Markup 
import re 

app = Flask(__name__)
app.secret_key = '67992084211'  

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = Database()

@login_manager.user_loader
def load_user(user_id):
    user = db.get_user_by_id(int(user_id))
    if user:
        user.permissions_set() # Garante que as permissões sejam carregadas
    return user

# Filtro Jinja2 para extrair ID do YouTube
@app.template_filter('youtube_id')
@pass_eval_context # Alterado de evalcontextfilter
def youtube_id_filter(eval_ctx, url):
    if not url:
        return None
    return Tutorial.extract_youtube_id(url)

# Filtro Jinja2 para verificar se é URL (mantido)
@app.template_filter('is_url')
@pass_eval_context # Alterado de evalcontextfilter
def is_url_filter(eval_ctx, text):
    return text.startswith(('http://', 'https://'))


# Rotas principais
@app.route('/')
def home():
    tutorials = db.get_all_tutorials() # Pega todos os tutoriais para exibir na home
    return render_template('index.html', tutorials=tutorials)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.get_user_by_email(email)
        
        if user and user.check_password(password):
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
def api_scams():
    scams_data = db.get_all_scams()
    return jsonify({
        "status": "success",
        "data": scams_data 
    })

@app.route('/scams')
def list_scams():
    try:
        scam_type_filter = request.args.get('type')
        min_date_filter = request.args.get('min_date')
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
        cursor.execute(query, tuple(params))
        
        columns = [column[0] for column in cursor.description]
        scams_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return render_template('scams.html', scams=scams_list)
        
    except Exception as e:
        app.logger.error(f"Error loading scams: {e}")
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
            db.conn.rollback()
            app.logger.error(f"Error reporting scam: {e}")
            flash(f'Erro ao registrar denúncia: {str(e)}', 'error')
    
    return render_template('report.html')

@app.route('/scams/<int:scam_id>')
def scam_details(scam_id):
    try:
        cursor = db.conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.id, s.title, s.description, s.scam_type, s.evidence, 
                s.created_at, s.user_id,
                u.name as author, u.email as author_email
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (scam_id,))
        
        scam_data_row = cursor.fetchone()
        if not scam_data_row:
            flash('Denúncia não encontrada', 'error')
            return redirect(url_for('list_scams'))
        
        columns = [column[0] for column in cursor.description]
        scam_dict = dict(zip(columns, scam_data_row))
        
        cursor.execute('''
            SELECT 
                c.id, c.text, c.created_at, c.user_id, u.name as author,
                0 as is_editing
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.scam_id = ?
            ORDER BY c.created_at DESC
        ''', (scam_id,))
        
        comments_columns = [column[0] for column in cursor.description]
        scam_dict['comments'] = [dict(zip(comments_columns, row)) for row in cursor.fetchall()]

        vote_counts = db.get_votes(scam_id)
        user_vote = 0
        if current_user.is_authenticated:
            user_vote = db.get_user_vote(scam_id, current_user.id)
        
        return render_template('scam_details.html', 
                                 scam=scam_dict, 
                                 likes=vote_counts['likes'], 
                                 dislikes=vote_counts['dislikes'], 
                                 user_vote=user_vote)
        
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
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT id FROM scams WHERE id = ?", (scam_id,))
    if not cursor.fetchone():
        return jsonify({'status': 'error', 'message': 'Denúncia não encontrada'}), 404

    try:
        new_user_vote_status = db.manage_vote(current_user.id, scam_id, vote_type)
        updated_counts = db.get_votes(scam_id)

        return jsonify({
            'status': 'success',
            'message': 'Voto processado com sucesso!',
            'likes': updated_counts['likes'],
            'dislikes': updated_counts['dislikes'],
            'user_vote': new_user_vote_status
        })
    except Exception as e:
        app.logger.error(f"Error processing vote for scam {scam_id} by user {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'Erro interno ao processar o voto.'}), 500


# Comentários
@app.route('/scams/<int:scam_id>/comment', methods=['POST'])
@login_required
def add_comment(scam_id):
    text = request.form.get('text')
    if not text or not text.strip():
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
    
    comments_data = cursor.fetchall()
    comments_list = []
    if comments_data:
        columns = [column[0] for column in cursor.description]
        for row in comments_data:
            comments_list.append(dict(zip(columns, row)))
    
    return jsonify(comments_list)


@app.route('/comment/<int:comment_id>/edit')
@login_required
def edit_comment(comment_id):
    cursor = db.conn.cursor()
    cursor.execute('SELECT scam_id, user_id FROM comments WHERE id = ?', (comment_id,))
    comment_info = cursor.fetchone()

    if not comment_info:
        flash('Comentário não encontrado.', 'error')
        return redirect(url_for('home'))

    scam_id, comment_user_id = comment_info

    if current_user.id != comment_user_id:
        flash('Você não tem permissão para editar este comentário.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))
    
    # Redireciona para a página de detalhes da denúncia com o comentário em modo de edição
    return redirect(url_for('scam_details', scam_id=scam_id, edit_comment_id=comment_id))

@app.route('/comment/<int:comment_id>/update', methods=['POST'])
@login_required
def update_comment(comment_id):
    new_text = request.form.get('text')
    
    cursor = db.conn.cursor()
    cursor.execute('SELECT scam_id, user_id FROM comments WHERE id = ?', (comment_id,))
    comment_info = cursor.fetchone()

    if not comment_info:
        flash('Comentário não encontrado.', 'error')
        return redirect(url_for('home'))

    scam_id, comment_user_id = comment_info

    if not (current_user.id == comment_user_id or current_user.confidence >= 3.0): # Adicionado permissão para admin
        flash('Você não tem permissão para atualizar este comentário.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    if not new_text or not new_text.strip():
        flash('O comentário não pode estar vazio.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    try:
        cursor.execute('UPDATE comments SET text = ? WHERE id = ?', (new_text.strip(), comment_id))
        db.conn.commit()
        flash('Comentário atualizado com sucesso!', 'success')
    except Exception as e:
        db.conn.rollback()
        app.logger.error(f"Error updating comment {comment_id}: {e}")
        flash(f'Erro ao atualizar comentário: {str(e)}', 'error')

    return redirect(url_for('scam_details', scam_id=scam_id))


@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    cursor = db.conn.cursor()
    cursor.execute('SELECT scam_id, user_id FROM comments WHERE id = ?', (comment_id,))
    comment_info = cursor.fetchone()

    if not comment_info:
        flash('Comentário não encontrado.', 'error')
        return redirect(url_for('home'))

    scam_id, comment_user_id = comment_info

    if not (current_user.id == comment_user_id or current_user.confidence >= 3.0): # Adicionado permissão para admin
        flash('Você não tem permissão para excluir este comentário.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    try:
        cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        db.conn.commit()
        flash('Comentário excluído com sucesso!', 'success')
    except Exception as e:
        db.conn.rollback()
        app.logger.error(f"Error deleting comment {comment_id}: {e}")
        flash(f'Erro ao excluir comentário: {str(e)}', 'error')

    return redirect(url_for('scam_details', scam_id=scam_id))

# Rotas de Tutoriais
@app.route('/create_tutorial', methods=['GET', 'POST'])
@login_required
def create_tutorial():
    if not current_user.is_authenticated or not current_user.can_register_scam: # Ou talvez can_manage_tutorials se for só para admin
        flash('Você não tem permissão para criar tutoriais.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        youtube_link = request.form.get('youtube_link')

        if not title or not content:
            flash('Título e conteúdo são obrigatórios.', 'error')
            return render_template('create_tutorial.html')

        if youtube_link and not Tutorial.extract_youtube_id(youtube_link):
            flash('Link do YouTube inválido. Por favor, forneça um link válido.', 'error')
            return render_template('create_tutorial.html', title=title, content=content, youtube_link=youtube_link)

        if db.add_tutorial(title, content, youtube_link, current_user.id):
            flash('Tutorial criado com sucesso!', 'success')
            return redirect(url_for('home')) # Ou para a lista de tutoriais
        else:
            flash('Erro ao criar tutorial. Tente novamente.', 'error')
    
    return render_template('create_tutorial.html')

@app.route('/tutorial/<int:tutorial_id>')
def tutorial_details(tutorial_id):
    tutorial = db.get_tutorial_by_id(tutorial_id)
    if not tutorial:
        flash('Tutorial não encontrado.', 'error')
        return redirect(url_for('home'))
    
    can_edit_delete = False
    if current_user.is_authenticated:
        # Verifica se é o autor ou se tem permissão de gerenciamento (confidence >= 3.0)
        if current_user.id == tutorial['author_id'] or current_user.confidence >= 3.0:
            can_edit_delete = True

    # NOVAS LINHAS: Obter votos e voto do usuário para o tutorial
    tutorial_vote_counts = db.get_tutorial_votes(tutorial_id)
    user_tutorial_vote = 0
    if current_user.is_authenticated:
        user_tutorial_vote = db.get_user_tutorial_vote(tutorial_id, current_user.id)

    return render_template('tutorial_details.html', 
                           tutorial=tutorial, 
                           can_edit_delete=can_edit_delete,
                           tutorial_likes=tutorial_vote_counts['likes'], # Passa os likes
                           tutorial_dislikes=tutorial_vote_counts['dislikes'], # Passa os dislikes
                           user_tutorial_vote=user_tutorial_vote) # Passa o voto do usuário
    

@app.route('/tutorial/<int:tutorial_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tutorial(tutorial_id):
    tutorial = db.get_tutorial_by_id(tutorial_id)
    if not tutorial:
        flash('Tutorial não encontrado.', 'error')
        return redirect(url_for('home'))

    # Verificação de permissão: autor ou confidence >= 3.0
    if not (current_user.id == tutorial['author_id'] or current_user.confidence >= 3.0):
        flash('Você não tem permissão para editar este tutorial.', 'error')
        return redirect(url_for('tutorial_details', tutorial_id=tutorial_id))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        youtube_link = request.form.get('youtube_link')

        if not title or not content:
            flash('Título e conteúdo são obrigatórios.', 'error')
            return render_template('create_tutorial.html', tutorial=tutorial) # Reusa o template com dados pré-preenchidos

        if youtube_link and not Tutorial.extract_youtube_id(youtube_link):
            flash('Link do YouTube inválido. Por favor, forneça um link válido.', 'error')
            return render_template('create_tutorial.html', tutorial=tutorial, title=title, content=content, youtube_link=youtube_link)

        if db.update_tutorial(tutorial_id, title, content, youtube_link):
            flash('Tutorial atualizado com sucesso!', 'success')
            return redirect(url_for('tutorial_details', tutorial_id=tutorial_id))
        else:
            flash('Erro ao atualizar tutorial. Tente novamente.', 'error')
    
    return render_template('create_tutorial.html', tutorial=tutorial) # Usar o mesmo template para criar e editar

@app.route('/tutorial/<int:tutorial_id>/delete', methods=['POST'])
@login_required
def delete_tutorial(tutorial_id):
    tutorial = db.get_tutorial_by_id(tutorial_id)
    if not tutorial:
        flash('Tutorial não encontrado.', 'error')
        return redirect(url_for('home'))

    # Verificação de permissão: autor ou confidence >= 3.0
    if not (current_user.id == tutorial['author_id'] or current_user.confidence >= 3.0):
        flash('Você não tem permissão para deletar este tutorial.', 'error')
        return redirect(url_for('tutorial_details', tutorial_id=tutorial_id))

    if db.delete_tutorial(tutorial_id):
        flash('Tutorial excluído com sucesso!', 'success')
        return redirect(url_for('home')) # Redireciona para a home ou lista de tutoriais
    else:
        flash('Erro ao excluir tutorial. Tente novamente.', 'error')

# NOVA ROTA: Voto em Tutorial
@app.route('/tutorial/<int:tutorial_id>/vote', methods=['POST'])
@login_required
def vote_tutorial_route(tutorial_id):
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Requisição deve ser JSON'}), 400
    
    data = request.get_json()
    vote_type = data.get('vote_type')
    
    if vote_type not in [1, -1]:
        return jsonify({'status': 'error', 'message': 'Tipo de voto inválido. Use 1 para like, -1 para dislike.'}), 400
    
    tutorial = db.get_tutorial_by_id(tutorial_id)
    if not tutorial:
        return jsonify({'status': 'error', 'message': 'Tutorial não encontrado'}), 404

    try:
        new_user_vote_status = db.manage_tutorial_vote(current_user.id, tutorial_id, vote_type)
        updated_counts = db.get_tutorial_votes(tutorial_id)

        return jsonify({
            'status': 'success',
            'message': 'Voto processado com sucesso!',
            'likes': updated_counts['likes'],
            'dislikes': updated_counts['dislikes'],
            'user_vote': new_user_vote_status
        })
    except Exception as e:
        app.logger.error(f"Error processing vote for tutorial {tutorial_id} by user {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'Erro interno ao processar o voto.'}), 500


if __name__ == '__main__':
    app.run(debug=True)