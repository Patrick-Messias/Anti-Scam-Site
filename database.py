import psycopg2
from psycopg2 import sql # Importe sql para lidar com identificadores
from psycopg2 import IntegrityError
from psycopg2.errors import InFailedSqlTransaction # Importe este erro específico
from classes import User # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self):
        self.db_name = "scams_db"
        self.db_user = "postgres"
        self.db_password = "1911"
        self.db_host = "localhost"
        self.db_port = "5433"
        self.conn = None
        self._connect()
        self._create_tables() # Chamada para criar tabelas na inicialização

    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port
            )
            self.conn.autocommit = True
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            self.conn = None

    def get_cursor(self):
        if self.conn is None or self.conn.closed:
            self._connect()
        if self.conn:
            return self.conn.cursor()
        return None

    def close(self):
        if self.conn:
            self.conn.close()

    def _create_tables(self):
        cursor = self.get_cursor()
        if not cursor:
            return

        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    type_user VARCHAR(50) DEFAULT 'noob',
                    confidence NUMERIC(3,1) DEFAULT 1.0,
                    age INTEGER,
                    city VARCHAR(100),
                    state VARCHAR(100),
                    civil_state VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tutorials (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    youtube_link VARCHAR(255),
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tutorial_votes (
                    id SERIAL PRIMARY KEY,
                    tutorial_id INTEGER NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    vote_type INTEGER NOT NULL, -- 1 for like, -1 for dislike
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tutorial_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS scams (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    scam_type VARCHAR(100) NOT NULL,
                    evidence TEXT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS scam_votes ( -- Tabela adicionada para votos em denúncias
                    id SERIAL PRIMARY KEY,
                    scam_id INTEGER NOT NULL REFERENCES scams(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    vote_type INTEGER NOT NULL, -- 1 for like, -1 for dislike
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(scam_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS comments (
                    id SERIAL PRIMARY KEY,
                    scam_id INTEGER NOT NULL REFERENCES scams(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            self.conn.commit()
            print("Tabelas verificadas/criadas com sucesso!")
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao criar tabelas: {e}")

    # --- Métodos de Usuário ---
    def add_user(self, name, email, password):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash)
            )
            self.conn.commit()
            return True
        except IntegrityError:
            self.conn.rollback()
            return False
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar usuário: {e}")
            return False

    def get_user_by_email(self, email):
        cursor = self.get_cursor()
        if not cursor: return None
        # As colunas são selecionadas na ordem exata para o construtor User
        cursor.execute('''
            SELECT 
                id, name, email, password_hash, type_user, confidence, 
                age, city, state, civil_state
            FROM users 
            WHERE email = %s
        ''', (email,))
        user_data = cursor.fetchone()
        if user_data:
            return User(
                user_data[0], user_data[1], user_data[2], user_data[3],
                user_data[4], # type_user
                user_data[5], # confidence
                user_data[6], user_data[7], user_data[8], user_data[9]
            )
        return None

    def get_user_by_id(self, user_id):
        cursor = self.get_cursor()
        if not cursor: return None
        # As colunas são selecionadas na ordem exata para o construtor User
        cursor.execute('''
            SELECT 
                id, name, email, password_hash, type_user, confidence, 
                age, city, state, civil_state
            FROM users 
            WHERE id = %s
        ''', (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(
                user_data[0], user_data[1], user_data[2], user_data[3],
                user_data[4], # type_user
                user_data[5], # confidence
                user_data[6], user_data[7], user_data[8], user_data[9]
            )
        return None

    def get_all_users(self):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute('''
            SELECT 
                id, name, email, password_hash, type_user, confidence, 
                age, city, state, civil_state
            FROM users
        ''')
        users_data = cursor.fetchall()
        users_list = []
        for user_data in users_data:
            user = {
                'id': user_data[0],
                'name': user_data[1],
                'email': user_data[2],
                'password_hash': user_data[3],
                'type_user': user_data[4],
                'confidence': float(user_data[5]),
                'age': user_data[6],
                'city': user_data[7],
                'state': user_data[8],
                'civil_state': user_data[9],
                'tutorials': self.get_tutorials_by_user_id(user_data[0]),
                'scams': self.get_scams_by_user_id(user_data[0])
            }
            users_list.append(user)
        return users_list

    def update_user_confidence(self, user_id, new_confidence):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute("UPDATE users SET confidence = %s WHERE id = %s", (new_confidence, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao atualizar confiança do usuário: {e}")
            return False

    def delete_user(self, user_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao deletar usuário: {e}")
            return False

    # --- Métodos de Tutorial ---    # --- Métodos para Tutoriais ---
    def get_all_tutorials(self):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute('''
            SELECT t.id, t.title, t.content, t.youtube_link, t.user_id, t.created_at, u.name as author_name
            FROM tutorials t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
        ''')
        tutorials_data = cursor.fetchall()
        tutorials_list = []
        for row in tutorials_data:
            tutorial = {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'youtube_link': row[3],
                'user_id': row[4],
                'created_at': row[5],
                'author_name': row[6],
                'likes': self.get_tutorial_likes_count(row[0]),
                'dislikes': self.get_tutorial_dislikes_count(row[0])
            }
            tutorials_list.append(tutorial)
        return tutorials_list

    def get_tutorials_by_user_id(self, user_id):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute("SELECT id, title FROM tutorials WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return [{'id': row[0], 'title': row[1]} for row in cursor.fetchall()]

    def add_tutorial(self, title, content, youtube_link, user_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute(
                "INSERT INTO tutorials (title, content, youtube_link, user_id) VALUES (%s, %s, %s, %s)",
                (title, content, youtube_link, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar tutorial: {e}")
            return False

    def get_tutorial_by_id(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return None
        cursor.execute('''
            SELECT t.id, t.title, t.content, t.youtube_link, t.user_id, t.created_at, u.name as author_name
            FROM tutorials t
            JOIN users u ON t.user_id = u.id
            WHERE t.id = %s
        ''', (tutorial_id,))
        tutorial_data = cursor.fetchone()
        if tutorial_data:
            tutorial = {
                'id': tutorial_data[0],
                'title': tutorial_data[1],
                'content': tutorial_data[2],
                'youtube_link': tutorial_data[3],
                'user_id': tutorial_data[4],
                'created_at': tutorial_data[5],
                'author_name': tutorial_data[6]
            }
            tutorial['likes'] = self.get_tutorial_likes_count(tutorial_id)
            tutorial['dislikes'] = self.get_tutorial_dislikes_count(tutorial_id)
            
            from flask_login import current_user # Importa aqui para evitar importação circular
            if current_user.is_authenticated:
                tutorial['user_vote'] = self.get_user_tutorial_vote(tutorial_id, current_user.id)
            else:
                tutorial['user_vote'] = 0
            return tutorial
        return None

    def update_tutorial(self, tutorial_id, title, content, youtube_link):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute(
                "UPDATE tutorials SET title = %s, content = %s, youtube_link = %s WHERE id = %s",
                (title, content, youtube_link, tutorial_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao atualizar tutorial: {e}")
            return False

    def delete_tutorial(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute("DELETE FROM tutorial_votes WHERE tutorial_id = %s", (tutorial_id,))
            cursor.execute("DELETE FROM tutorials WHERE id = %s", (tutorial_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao deletar tutorial: {e}")
            return False

    def get_tutorial_likes_count(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT COUNT(*) FROM tutorial_votes WHERE tutorial_id = %s AND vote_type = 1", (tutorial_id,))
        return cursor.fetchone()[0]

    def get_tutorial_dislikes_count(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT COUNT(*) FROM tutorial_votes WHERE tutorial_id = %s AND vote_type = -1", (tutorial_id,))
        return cursor.fetchone()[0]

    def get_user_tutorial_vote(self, tutorial_id, user_id):
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT vote_type FROM tutorial_votes WHERE tutorial_id = %s AND user_id = %s", (tutorial_id, user_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    def add_tutorial_vote(self, tutorial_id, user_id, vote_type):
        cursor = self.get_cursor()
        if not cursor: return None
        self.conn.autocommit = False

        try:
            cursor.execute("SELECT vote_type FROM tutorial_votes WHERE tutorial_id = %s AND user_id = %s", (tutorial_id, user_id))
            existing_vote = cursor.fetchone()

            if existing_vote:
                if existing_vote[0] == vote_type:
                    cursor.execute("DELETE FROM tutorial_votes WHERE tutorial_id = %s AND user_id = %s", (tutorial_id, user_id))
                    self.conn.commit()
                    return "removed"
                else:
                    cursor.execute("UPDATE tutorial_votes SET vote_type = %s WHERE tutorial_id = %s AND user_id = %s", (vote_type, tutorial_id, user_id))
                    self.conn.commit()
                    return "updated"
            else:
                cursor.execute("INSERT INTO tutorial_votes (tutorial_id, user_id, vote_type) VALUES (%s, %s, %s)", (tutorial_id, user_id, vote_type))
                self.conn.commit()
                return "added"
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar voto de tutorial: {e}")
            return None
        finally:
            self.conn.autocommit = True


    # --- Métodos para Tutoriais ---
    def get_all_tutorials(self):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute('''
            SELECT t.id, t.title, t.content, t.youtube_link, t.user_id, t.created_at, u.name as author_name
            FROM tutorials t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
        ''')
        tutorials_data = cursor.fetchall()
        tutorials_list = []
        for row in tutorials_data:
            tutorial = {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'youtube_link': row[3],
                'user_id': row[4],
                'created_at': row[5],
                'author_name': row[6],
                'likes': self.get_tutorial_likes_count(row[0]),
                'dislikes': self.get_tutorial_dislikes_count(row[0])
            }
            tutorials_list.append(tutorial)
        return tutorials_list

    def get_tutorials_by_user_id(self, user_id):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute("SELECT id, title FROM tutorials WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return [{'id': row[0], 'title': row[1]} for row in cursor.fetchall()]

    def add_tutorial(self, title, content, youtube_link, user_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute(
                "INSERT INTO tutorials (title, content, youtube_link, user_id) VALUES (%s, %s, %s, %s)",
                (title, content, youtube_link, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar tutorial: {e}")
            return False

    def get_tutorial_by_id(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return None
        cursor.execute('''
            SELECT t.id, t.title, t.content, t.youtube_link, t.user_id, t.created_at, u.name as author_name
            FROM tutorials t
            JOIN users u ON t.user_id = u.id
            WHERE t.id = %s
        ''', (tutorial_id,))
        tutorial_data = cursor.fetchone()
        if tutorial_data:
            tutorial = {
                'id': tutorial_data[0],
                'title': tutorial_data[1],
                'content': tutorial_data[2],
                'youtube_link': tutorial_data[3],
                'user_id': tutorial_data[4],
                'created_at': tutorial_data[5],
                'author_name': tutorial_data[6]
            }
            tutorial['likes'] = self.get_tutorial_likes_count(tutorial_id)
            tutorial['dislikes'] = self.get_tutorial_dislikes_count(tutorial_id)
            
            from flask_login import current_user # Importa aqui para evitar importação circular
            if current_user.is_authenticated:
                tutorial['user_vote'] = self.get_user_tutorial_vote(tutorial_id, current_user.id)
            else:
                tutorial['user_vote'] = 0
            return tutorial
        return None

    def update_tutorial(self, tutorial_id, title, content, youtube_link):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute(
                "UPDATE tutorials SET title = %s, content = %s, youtube_link = %s WHERE id = %s",
                (title, content, youtube_link, tutorial_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao atualizar tutorial: {e}")
            return False

    def delete_tutorial(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute("DELETE FROM tutorial_votes WHERE tutorial_id = %s", (tutorial_id,))
            cursor.execute("DELETE FROM tutorials WHERE id = %s", (tutorial_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao deletar tutorial: {e}")
            return False

    def get_tutorial_likes_count(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT COUNT(*) FROM tutorial_votes WHERE tutorial_id = %s AND vote_type = 1", (tutorial_id,))
        return cursor.fetchone()[0]

    def get_tutorial_dislikes_count(self, tutorial_id):
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT COUNT(*) FROM tutorial_votes WHERE tutorial_id = %s AND vote_type = -1", (tutorial_id,))
        return cursor.fetchone()[0]

    def get_user_tutorial_vote(self, tutorial_id, user_id):
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT vote_type FROM tutorial_votes WHERE tutorial_id = %s AND user_id = %s", (tutorial_id, user_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    def add_tutorial_vote(self, tutorial_id, user_id, vote_type):
        cursor = self.get_cursor()
        if not cursor: return None
        self.conn.autocommit = False

        try:
            cursor.execute("SELECT vote_type FROM tutorial_votes WHERE tutorial_id = %s AND user_id = %s", (tutorial_id, user_id))
            existing_vote = cursor.fetchone()

            if existing_vote:
                if existing_vote[0] == vote_type:
                    cursor.execute("DELETE FROM tutorial_votes WHERE tutorial_id = %s AND user_id = %s", (tutorial_id, user_id))
                    self.conn.commit()
                    return "removed"
                else:
                    cursor.execute("UPDATE tutorial_votes SET vote_type = %s WHERE tutorial_id = %s AND user_id = %s", (vote_type, tutorial_id, user_id))
                    self.conn.commit()
                    return "updated"
            else:
                cursor.execute("INSERT INTO tutorial_votes (tutorial_id, user_id, vote_type) VALUES (%s, %s, %s)", (tutorial_id, user_id, vote_type))
                self.conn.commit()
                return "added"
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar voto de tutorial: {e}")
            return None
        finally:
            self.conn.autocommit = True

     # --- Métodos para Denúncias (Scams) ---
    def get_all_scams(self):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute('''
            SELECT s.id, s.title, s.description, s.scam_type, s.evidence, 
                   s.user_id, s.created_at, u.name as author_name
            FROM scams s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC
        ''')
        scams_data = cursor.fetchall()
        scams_list = []
        for row in scams_data:
            scam = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'scam_type': row[3],
                'evidence': row[4],
                'user_id': row[5],
                'created_at': row[6],
                'author_name': row[7],
                'likes': self.get_scam_likes_count(row[0]),
                'dislikes': self.get_scam_dislikes_count(row[0])
            }
            scams_list.append(scam)
        return scams_list

    def get_scams_by_user_id(self, user_id):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute("SELECT id, title FROM scams WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return [{'id': row[0], 'title': row[1]} for row in cursor.fetchall()]

    def add_scam(self, title, description, scam_type, evidence, user_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute(
                "INSERT INTO scams (title, description, scam_type, evidence, user_id) VALUES (%s, %s, %s, %s, %s)",
                (title, description, scam_type, evidence, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar denúncia: {e}")
            return False

    def get_scam_by_id(self, scam_id):
        cursor = self.get_cursor()
        if not cursor: return None
        cursor.execute('''
            SELECT 
                s.id, s.title, s.description, s.scam_type, s.evidence, 
                s.user_id, s.created_at, u.name as author_name, u.confidence as author_confidence
            FROM scams s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = %s
        ''', (scam_id,))
        scam_data = cursor.fetchone()
        
        if scam_data:
            scam = {
                'id': scam_data[0],
                'title': scam_data[1],
                'description': scam_data[2],
                'scam_type': scam_data[3],
                'evidence': scam_data[4],
                'user_id': scam_data[5],
                'created_at': scam_data[6],
                'author_name': scam_data[7],
                'author_confidence': scam_data[8],
                'comments': self.get_comments_for_scam(scam_id)
            }
            
            scam['likes'] = self.get_scam_likes_count(scam_id) # Busca e adiciona contagem de likes
            scam['dislikes'] = self.get_scam_dislikes_count(scam_id) # Busca e adiciona contagem de dislikes
            
            from flask_login import current_user # Importa current_user aqui para evitar importação circular
            if current_user.is_authenticated:
                scam['user_vote'] = self.get_user_scam_vote(scam_id, current_user.id) # Busca o voto do usuário logado
            else:
                scam['user_vote'] = 0

            return scam
        return None

    def update_scam(self, scam_id, title, description, scam_type, evidence):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute(
                "UPDATE scams SET title = %s, description = %s, scam_type = %s, evidence = %s WHERE id = %s",
                (title, description, scam_type, evidence, scam_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao atualizar denúncia: {e}")
            return False

    def delete_scam(self, scam_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute("DELETE FROM comments WHERE scam_id = %s", (scam_id,))
            cursor.execute("DELETE FROM scam_votes WHERE scam_id = %s", (scam_id,))
            cursor.execute("DELETE FROM scams WHERE id = %s", (scam_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao deletar denúncia: {e}")
            return False
            
    def get_scam_likes_count(self, scam_id): # Método adicionado para contar likes de denúncias
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT COUNT(*) FROM scam_votes WHERE scam_id = %s AND vote_type = 1", (scam_id,))
        return cursor.fetchone()[0]

    def get_scam_dislikes_count(self, scam_id): # Método adicionado para contar dislikes de denúncias
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT COUNT(*) FROM scam_votes WHERE scam_id = %s AND vote_type = -1", (scam_id,))
        return cursor.fetchone()[0]

    def get_user_scam_vote(self, scam_id, user_id): # Método adicionado para pegar o voto de um usuário em uma denúncia
        cursor = self.get_cursor()
        if not cursor: return 0
        cursor.execute("SELECT vote_type FROM scam_votes WHERE scam_id = %s AND user_id = %s", (scam_id, user_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    def add_scam_vote(self, scam_id, user_id, vote_type): # Método adicionado para registrar voto em denúncia
        cursor = self.get_cursor()
        if not cursor: return None
        self.conn.autocommit = False

        try:
            cursor.execute("SELECT vote_type FROM scam_votes WHERE scam_id = %s AND user_id = %s", (scam_id, user_id))
            existing_vote = cursor.fetchone()

            if existing_vote:
                if existing_vote[0] == vote_type:
                    cursor.execute("DELETE FROM scam_votes WHERE scam_id = %s AND user_id = %s", (scam_id, user_id))
                    self.conn.commit()
                    return "removed"
                else:
                    cursor.execute("UPDATE scam_votes SET vote_type = %s WHERE scam_id = %s AND user_id = %s", (vote_type, scam_id, user_id))
                    self.conn.commit()
                    return "updated"
            else:
                cursor.execute("INSERT INTO scam_votes (scam_id, user_id, vote_type) VALUES (%s, %s, %s)", (scam_id, user_id, vote_type))
                self.conn.commit()
                return "added"
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar voto de denúncia: {e}")
            return None
        finally:
            self.conn.autocommit = True

    # --- Métodos para Comentários ---
    def add_comment(self, scam_id, user_id, text):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute(
                "INSERT INTO comments (scam_id, user_id, text) VALUES (%s, %s, %s)",
                (scam_id, user_id, text)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar comentário: {e}")
            return False

    def get_comments_for_scam(self, scam_id):
        cursor = self.get_cursor()
        if not cursor: return []
        cursor.execute('''
            SELECT c.id, c.user_id, u.name, c.text, c.created_at
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.scam_id = %s
            ORDER BY c.created_at ASC
        ''', (scam_id,))
        comments_data = cursor.fetchall()
        comments_list = []
        for row in comments_data:
            comments_list.append({
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'text': row[3],
                'created_at': row[4]
            })
        return comments_list

    def get_comment_by_id(self, comment_id):
        cursor = self.get_cursor()
        if not cursor: return None
        cursor.execute('''
            SELECT id, scam_id, user_id, text, created_at
            FROM comments
            WHERE id = %s
        ''', (comment_id,))
        comment_data = cursor.fetchone()
        if comment_data:
            return {
                'id': comment_data[0],
                'scam_id': comment_data[1],
                'user_id': comment_data[2],
                'text': comment_data[3],
                'created_at': comment_data[4]
            }
        return None

    def update_comment(self, comment_id, text):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute("UPDATE comments SET text = %s WHERE id = %s", (text, comment_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao atualizar comentário: {e}")
            return False

    def delete_comment(self, comment_id):
        cursor = self.get_cursor()
        if not cursor: return False
        try:
            cursor.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao deletar comentário: {e}")
            return False