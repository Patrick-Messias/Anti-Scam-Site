from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from werkzeug.exceptions import NotFound
from database import Database
from classes import User, Tutorial
from jinja2 import pass_eval_context
from markupsafe import Markup
# ... (outras importações) ...

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
        user.permissions_set()
    return user

@app.template_filter('youtube_id')
@pass_eval_context
def youtube_id_filter(eval_ctx, url):
    if not url:
        return None
    return Tutorial.extract_youtube_id(url)

@app.template_filter('is_url')
@pass_eval_context
def is_url_filter(eval_ctx, text):
    return text.startswith(('http://', 'https://'))

@app.route('/')
def home():
    tutorials = db.get_all_tutorials()
    return render_template('index.html', tutorials=tutorials)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: # Redireciona se já estiver logado
        return redirect(url_for('dashboard'))

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
    if current_user.is_authenticated: # Redireciona se já estiver logado
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        #confirm_password = request.form.get('confirm_password')

        if not User.is_valid_email(email): # Valida o formato do e-mail
            flash('E-mail inválido. Por favor, insira um e-mail válido.', 'error')
            return render_template('register.html', name=name, email=email)
        
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
            query += ' AND s.scam_type = %s'
            params.append(scam_type_filter)

        if min_date_filter and min_date_filter != '':
            query += ' AND s.created_at::date >= %s'
            params.append(min_date_filter)

        query += ' ORDER BY s.created_at ' + ('DESC' if order == 'newest' else 'ASC')

        cursor = db.conn.cursor()
        cursor.execute(query, params)

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
                VALUES (%s, %s, %s, %s, %s)
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
            WHERE s.id = %s
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
            WHERE c.scam_id = %s
            ORDER BY c.created_at DESC
        ''', (scam_id,))

        comments_columns = [column[0] for column in cursor.description]
        scam_dict['comments'] = [dict(zip(comments_columns, row)) for row in cursor.fetchall()]

        scam = db.get_scam_by_id(scam_id) # ESTE MÉTODO JÁ TRAZ LIKES, DISLIKES, USER_VOTE DENTRO DO DICIONÁRIO 'scam'
        if not scam:
            flash('Denúncia não encontrada', 'error')
            return redirect(url_for('list_scams'))

        # Determina se o usuário logado pode editar/deletar a denúncia
        can_edit_delete_scam = False
        if current_user.is_authenticated:
            if current_user.id == scam_dict['user_id'] or current_user.confidence >= 3.0:
                can_edit_delete_scam = True

        return render_template('scam_details.html',
                            scam=scam, # Passa o dicionário 'scam' completo
                            likes=scam['likes'], # Acessa diretamente do dicionário 'scam'
                            dislikes=scam['dislikes'], # Acessa diretamente do dicionário 'scam'
                            user_vote=scam['user_vote'], # Acessa diretamente do dicionário 'scam'
                            can_edit_delete_scam=can_edit_delete_scam)

    except Exception as e:
        app.logger.error(f"Error loading scam details for {scam_id}: {e}")
        flash(f'Erro ao carregar detalhes da denúncia: {str(e)}', 'error')
        return redirect(url_for('home'))

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
    cursor.execute("SELECT id FROM scams WHERE id = %s", (scam_id,))
    if not cursor.fetchone():
        return jsonify({'status': 'error', 'message': 'Denúncia não encontrada'}), 404

    try:
        action_status = db.add_scam_vote(scam_id, current_user.id, vote_type) # CORRIGIDO
        if action_status is None: # Verificação de erro do DB
            raise Exception("Erro ao processar voto no banco de dados.")

        updated_likes = db.get_scam_likes_count(scam_id) # CORRIGIDO
        updated_dislikes = db.get_scam_dislikes_count(scam_id) # CORRIGIDO
        current_user_vote = db.get_user_scam_vote(scam_id, current_user.id)

        return jsonify({
            'status': 'success',
            'message': 'Voto processado com sucesso!',
            'likes': updated_likes,
            'dislikes': updated_dislikes,
            'user_vote': current_user_vote
        })
    except Exception as e:
        app.logger.error(f"Error processing vote for scam {scam_id} by user {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'Erro interno ao processar o voto.'}), 500

# Adicionar/Modificar essas rotas para a funcionalidade de editar e deletar denúncias
@app.route('/scams/<int:scam_id>/edit', methods=['GET'])
@login_required
def edit_scam(scam_id):
    scam = db.get_scam_by_id(scam_id)
    if not scam:
        flash('Denúncia não encontrada.', 'error')
        return redirect(url_for('list_scams'))

    # Permite edição se for o autor OU um administrador
    if not (current_user.id == scam['user_id'] or current_user.confidence >= 3.0):
        flash('Você não tem permissão para editar esta denúncia.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    return render_template('edit_scam.html', scam=scam)

@app.route('/scams/<int:scam_id>/update', methods=['POST'])
@login_required
def update_scam(scam_id):
    title = request.form.get('title')
    description = request.form.get('description')
    scam_type = request.form.get('scam_type')
    evidence = request.form.get('evidence')

    scam = db.get_scam_by_id(scam_id)
    if not scam:
        flash('Denúncia não encontrada.', 'error')
        return redirect(url_for('list_scams'))

    # Permite atualização se for o autor OU um administrador
    if not (current_user.id == scam['user_id'] or current_user.confidence >= 3.0):
        flash('Você não tem permissão para atualizar esta denúncia.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    if db.update_scam(scam_id, title, description, scam_type, evidence):
        flash('Denúncia atualizada com sucesso!', 'success')
        return redirect(url_for('scam_details', scam_id=scam_id))
    else:
        flash('Erro ao atualizar denúncia. Tente novamente.', 'error')

@app.route('/scams/<int:scam_id>/delete', methods=['POST'])
@login_required
def delete_scam(scam_id):
    scam = db.get_scam_by_id(scam_id)
    if not scam:
        flash('Denúncia não encontrada.', 'error')
        return redirect(url_for('list_scams'))

    # Permite exclusão se for o autor OU um administrador
    if not (current_user.id == scam['user_id'] or current_user.confidence >= 3.0):
        flash('Você não tem permissão para deletar esta denúncia.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    if db.delete_scam(scam_id):
        flash('Denúncia excluída com sucesso!', 'success')
        return redirect(url_for('list_scams')) # Redireciona para a lista de denúncias após deletar
    else:
        flash('Erro ao excluir denúncia. Tente novamente.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))


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
            VALUES (%s, %s, %s)
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
        WHERE comments.scam_id = %s
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
    cursor.execute('SELECT scam_id, user_id FROM comments WHERE id = %s', (comment_id,))
    comment_info = cursor.fetchone()

    if not comment_info:
        flash('Comentário não encontrado.', 'error')
        return redirect(url_for('home'))

    scam_id, comment_user_id = comment_info

    # Permissão para editar comentários: autor ou admin
    if not (current_user.id == comment_user_id or current_user.confidence >= 3.0):
        flash('Você não tem permissão para editar este comentário.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    return redirect(url_for('scam_details', scam_id=scam_id, edit_comment_id=comment_id))

@app.route('/comment/<int:comment_id>/update', methods=['POST'])
@login_required
def update_comment(comment_id):
    new_text = request.form.get('text')

    cursor = db.conn.cursor()
    cursor.execute('SELECT scam_id, user_id FROM comments WHERE id = %s', (comment_id,))
    comment_info = cursor.fetchone()

    if not comment_info:
        flash('Comentário não encontrado.', 'error')
        return redirect(url_for('home'))

    scam_id, comment_user_id = comment_info

    # Permissão para atualizar comentários: autor ou admin
    if not (current_user.id == comment_user_id or current_user.confidence >= 3.0):
        flash('Você não tem permissão para atualizar este comentário.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    if not new_text or not new_text.strip():
        flash('O comentário não pode estar vazio.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    try:
        cursor.execute('UPDATE comments SET text = %s WHERE id = %s', (new_text.strip(), comment_id))
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
    cursor.execute('SELECT scam_id, user_id FROM comments WHERE id = %s', (comment_id,))
    comment_info = cursor.fetchone()

    if not comment_info:
        flash('Comentário não encontrado.', 'error')
        return redirect(url_for('home'))

    scam_id, comment_user_id = comment_info

    # Permissão para deletar comentários: autor ou admin
    if not (current_user.id == comment_user_id or current_user.confidence >= 3.0):
        flash('Você não tem permissão para excluir este comentário.', 'error')
        return redirect(url_for('scam_details', scam_id=scam_id))

    try:
        cursor.execute('DELETE FROM comments WHERE id = %s', (comment_id,))
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
    if not current_user.is_authenticated or not current_user.can_register_scam: # Se can_register_scam é a permissão correta
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
            return redirect(url_for('home'))
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
        if current_user.id == tutorial['user_id'] or current_user.confidence >= 3.0:
            can_edit_delete = True

    tutorial_vote_counts = {
        'likes': db.get_tutorial_likes_count(tutorial_id),
        'dislikes': db.get_tutorial_dislikes_count(tutorial_id)
    }
    user_tutorial_vote = 0
    if current_user.is_authenticated:
        user_tutorial_vote = db.get_user_tutorial_vote(tutorial_id, current_user.id)

    return render_template('tutorial_details.html',
                           tutorial=tutorial,
                           can_edit_delete=can_edit_delete,
                           tutorial_likes=tutorial_vote_counts['likes'],
                           tutorial_dislikes=tutorial_vote_counts['dislikes'],
                           user_tutorial_vote=user_tutorial_vote)


@app.route('/tutorial/<int:tutorial_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tutorial(tutorial_id):
    tutorial = db.get_tutorial_by_id(tutorial_id)
    if not tutorial:
        flash('Tutorial não encontrado.', 'error')
        return redirect(url_for('home'))

    if not (current_user.id == tutorial['user_id'] or current_user.confidence >= 3.0):
        flash('Você não tem permissão para editar este tutorial.', 'error')
        return redirect(url_for('tutorial_details', tutorial_id=tutorial_id))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        youtube_link = request.form.get('youtube_link')

        if not title or not content:
            flash('Título e conteúdo são obrigatórios.', 'error')
            return render_template('create_tutorial.html', tutorial=tutorial)

        if youtube_link and not Tutorial.extract_youtube_id(youtube_link):
            flash('Link do YouTube inválido. Por favor, forneça um link válido.', 'error')
            return render_template('create_tutorial.html', tutorial=tutorial, title=title, content=content, youtube_link=youtube_link)

        if db.update_tutorial(tutorial_id, title, content, youtube_link):
            flash('Tutorial atualizado com sucesso!', 'success')
            return redirect(url_for('tutorial_details', tutorial_id=tutorial_id))
        else:
            flash('Erro ao atualizar tutorial. Tente novamente.', 'error')

    return render_template('create_tutorial.html', tutorial=tutorial)

@app.route('/tutorial/<int:tutorial_id>/delete', methods=['POST'])
@login_required
def delete_tutorial_route(tutorial_id): # Note: a rota é 'delete_tutorial_route'
    tutorial = db.get_tutorial_by_id(tutorial_id)
    if not tutorial:
        flash('Tutorial não encontrado.', 'error')
        return redirect(url_for('home'))

    if not (current_user.id == tutorial['user_id'] or current_user.confidence >= 3.0):
        flash('Você não tem permissão para deletar este tutorial.', 'error')
        return redirect(url_for('tutorial_details', tutorial_id=tutorial_id))

    if db.delete_tutorial(tutorial_id):
        flash('Tutorial excluído com sucesso!', 'success')
        return redirect(url_for('home'))
    else:
        flash('Erro ao excluir tutorial. Tente novamente.', 'error')
        return redirect(url_for('tutorial_details', tutorial_id=tutorial_id))

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
        action_status = db.add_tutorial_vote(current_user.id, tutorial_id, vote_type) # CORRIGIDO
        if action_status is None: # Verificação de erro do DB
            raise Exception("Erro ao processar voto no banco de dados.")

        updated_likes = db.get_tutorial_likes_count(tutorial_id) # CORRIGIDO
        updated_dislikes = db.get_tutorial_dislikes_count(tutorial_id) # CORRIGIDO
        current_user_vote = db.get_user_tutorial_vote(tutorial_id, current_user.id)

        return jsonify({
            'status': 'success',
            'message': 'Voto processado com sucesso!',
            'likes': updated_likes,
            'dislikes': updated_dislikes,
            'user_vote': current_user_vote
        })
    except Exception as e:
        app.logger.error(f"Error processing vote for tutorial {tutorial_id} by user {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'Erro interno ao processar o voto.'}), 500
 # --- Rotas do Dashboard Admin ---

@app.route('/admin')
@login_required
def admin_dashboard():
    # Verifica se o usuário logado é um administrador
    if not current_user.is_authenticated or current_user.confidence < 3.0:
        flash('Você não tem permissão para acessar o dashboard de administração.', 'error')
        return redirect(url_for('dashboard')) # Redireciona para dashboard do usuário se não for admin

    users = db.get_all_users() # Obtém todos os usuários do banco de dados

    # Para cada usuário, obtenha os tutoriais e denúncias
    for user in users:
        # Passar None para user_id em get_user_tutorial_vote/get_user_scam_vote se o current_user não estiver autenticado
        # user['tutorials'] = db.get_tutorials_by_user_id(user['id'])
        # user['scams'] = db.get_scams_by_user_id(user['id'])
        # Comentado, pois essas linhas são para o template e já chamam db.get_scam_by_id
        # ou db.get_tutorial_by_id internamente, que podem estar falhando.
        # As chamadas a get_tutorials_by_user_id e get_scams_by_user_id estão corretas.
        pass # Manter a passagem de dados como dicionário para o template


    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/user/<int:user_id>/update_confidence', methods=['POST'])
@login_required
def admin_update_user_confidence(user_id):
    if not current_user.is_authenticated or current_user.confidence < 3.0:
        flash('Você não tem permissão para realizar esta ação.', 'error')
        return redirect(url_for('dashboard'))

    new_confidence_str = request.form.get('new_confidence')
    if not new_confidence_str:
        flash('Nível de confiança não fornecido.', 'error')
        return redirect(url_for('admin_dashboard'))

    try:
        new_confidence = float(new_confidence_str)
        
        target_user = db.get_user_by_id(user_id)
        if not target_user:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Regras de segurança adicionais para admins
        # 1. Não permitir que um admin rebaixe a si mesmo abaixo de 3.0
        if user_id == current_user.id and new_confidence < 3.0:
            flash('Você não pode rebaixar seu próprio nível de administrador para abaixo de 3.0.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # 2. Não permitir que um admin altere o nível de outro admin com confiança igual ou superior
        if target_user.confidence >= current_user.confidence and user_id != current_user.id:
            flash('Você não pode alterar o nível de confiança de um administrador igual ou superior ao seu.', 'error')
            return redirect(url_for('admin_dashboard'))


        if db.update_user_confidence(user_id, new_confidence):
            flash(f'Nível de confiança do usuário "{target_user.name}" (ID: {user_id}) atualizado para {new_confidence}.', 'success')
        else:
            flash(f'Erro ao atualizar nível de confiança do usuário "{target_user.name}" (ID: {user_id}).', 'error')
    except ValueError:
        flash('Nível de confiança inválido. Use um número (ex: 2.5, 3.0).', 'error')
    except Exception as e:
        flash(f'Ocorreu um erro inesperado: {e}', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_authenticated or current_user.confidence < 3.0:
        flash('Você não tem permissão para realizar esta ação.', 'error')
        return redirect(url_for('dashboard'))
    
    # Não permitir que o admin se delete
    if user_id == current_user.id:
        flash('Você não pode deletar sua própria conta de administrador.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    target_user = db.get_user_by_id(user_id)
    if not target_user:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('admin_dashboard'))

    # Admins não podem deletar outros admins de confiança igual ou superior
    if target_user.confidence >= current_user.confidence:
        flash(f'Você não pode deletar um administrador (ID: {user_id}, Nível: {target_user.confidence}) igual ou superior ao seu nível.', 'error')
        return redirect(url_for('admin_dashboard'))

    if db.delete_user(user_id):
        flash(f'Usuário "{target_user.name}" (ID: {user_id}) deletado com sucesso!', 'success')
    else:
        flash(f'Erro ao deletar usuário "{target_user.name}" (ID: {user_id}).', 'error')

    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    # Cria as tabelas se não existirem (apenas na primeira execução)
    # db._create_tables() # Mantenha comentado, já migrado

    app.run(debug=True)