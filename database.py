import sqlite3
from classes import User # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_path='scams.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                type_user TEXT DEFAULT 'noob',
                confidence REAL DEFAULT 1.0,
                age INTEGER DEFAULT 0,
                city TEXT DEFAULT '',
                state TEXT DEFAULT '',
                civil_state TEXT DEFAULT ''
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                scam_type TEXT NOT NULL,
                evidence TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER NOT NULL,
                scam_id INTEGER NOT NULL,
                vote_type INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (scam_id) REFERENCES scams(id) ON DELETE CASCADE,
                UNIQUE(user_id, scam_id)  
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                scam_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (scam_id) REFERENCES scams(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                youtube_link TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutorial_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tutorial_id INTEGER NOT NULL,          
                vote_type INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
                UNIQUE(user_id, tutorial_id)       
            )
        ''')
        self.conn.commit()

    def add_user(self, name, email, password):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
            ''', (name, email, generate_password_hash(password)))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False

    def get_user_by_email(self, email):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0], name=row[1], email=row[2], password_hash=row[3],
                type_user=row[4], confidence=row[5], age=row[6],
                city=row[7], state=row[8], civil_state=row[9]
            )
        return None

    def get_user_by_id(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0], name=row[1], email=row[2], password_hash=row[3],
                type_user=row[4], confidence=row[5], age=row[6],
                city=row[7], state=row[8], civil_state=row[9]
            )
        return None
        
    def get_all_scams(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, title, description, scam_type, evidence, user_id, created_at FROM scams ORDER BY created_at DESC')
        scams_data = cursor.fetchall()
        scams = []
        if scams_data:
            columns = [column[0] for column in cursor.description]
            for row in scams_data:
                scams.append(dict(zip(columns, row)))
        return scams

    def manage_vote(self, user_id, scam_id, new_vote_type):
        cursor = self.conn.cursor()
        cursor.execute("SELECT vote_type FROM votes WHERE user_id = ? AND scam_id = ?", (user_id, scam_id))
        existing_vote_row = cursor.fetchone()

        final_user_vote_status = 0

        try:
            if existing_vote_row:
                current_db_vote_type = existing_vote_row[0]
                if current_db_vote_type == new_vote_type:
                    cursor.execute("DELETE FROM votes WHERE user_id = ? AND scam_id = ?", (user_id, scam_id))
                    final_user_vote_status = 0
                else:
                    cursor.execute("UPDATE votes SET vote_type = ? WHERE user_id = ? AND scam_id = ?", (new_vote_type, user_id, scam_id))
                    final_user_vote_status = new_vote_type
            else:
                cursor.execute("INSERT INTO votes (user_id, scam_id, vote_type) VALUES (?, ?, ?)", (user_id, scam_id, new_vote_type))
                final_user_vote_status = new_vote_type
            self.conn.commit()
            return final_user_vote_status
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_votes(self, scam_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(CASE WHEN vote_type = 1 THEN 1 ELSE 0 END) AS likes, "
                       "SUM(CASE WHEN vote_type = -1 THEN 1 ELSE 0 END) AS dislikes "
                       "FROM votes WHERE scam_id = ?", (scam_id,))
        result = cursor.fetchone()
        likes = result[0] if result[0] else 0
        dislikes = result[1] if result[1] else 0
        return {'likes': likes, 'dislikes': dislikes}

    def get_user_vote(self, scam_id, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT vote_type FROM votes WHERE scam_id = ? AND user_id = ?", (scam_id, user_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    # Métodos para Tutoriais
    def add_tutorial(self, title, content, youtube_link, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO tutorials (title, content, youtube_link, user_id)
                VALUES (?, ?, ?, ?)
            ''', (title, content, youtube_link, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao adicionar tutorial: {e}")
            return False

    def get_all_tutorials(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                t.id, t.title, t.content, t.youtube_link, t.created_at, u.name as author, u.id as author_id
            FROM tutorials t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
        ''')
        rows = cursor.fetchall()
        tutorials = []
        columns = [description[0] for description in cursor.description]
        for row in rows:
            tutorials.append(dict(zip(columns, row)))
        return tutorials

    def get_tutorial_by_id(self, tutorial_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                t.id, t.title, t.content, t.youtube_link, t.created_at, u.name as author, u.id as author_id
            FROM tutorials t
            JOIN users u ON t.user_id = u.id
            WHERE t.id = ?
        ''', (tutorial_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None

    def update_tutorial(self, tutorial_id, title, content, youtube_link):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE tutorials
                SET title = ?, content = ?, youtube_link = ?
                WHERE id = ?
            ''', (title, content, youtube_link, tutorial_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao atualizar tutorial: {e}")
            return False

    def delete_tutorial(self, tutorial_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM tutorials WHERE id = ?', (tutorial_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Erro ao deletar tutorial: {e}")
            return False
        
    def manage_tutorial_vote(self, user_id, tutorial_id, new_vote_type):
        cursor = self.conn.cursor()
        cursor.execute("SELECT vote_type FROM tutorial_votes WHERE user_id = ? AND tutorial_id = ?", (user_id, tutorial_id))
        existing_vote_row = cursor.fetchone()

        final_user_vote_status = 0

        try:
            if existing_vote_row:
                current_db_vote_type = existing_vote_row[0]
                if current_db_vote_type == new_vote_type:
                    # Desfazer o voto se for o mesmo tipo
                    cursor.execute("DELETE FROM tutorial_votes WHERE user_id = ? AND tutorial_id = ?", (user_id, tutorial_id))
                    final_user_vote_status = 0
                else:
                    # Mudar o voto para o novo tipo
                    cursor.execute("UPDATE tutorial_votes SET vote_type = ? WHERE user_id = ? AND tutorial_id = ?", (new_vote_type, user_id, tutorial_id))
                    final_user_vote_status = new_vote_type
            else:
                # Inserir um novo voto
                cursor.execute("INSERT INTO tutorial_votes (user_id, tutorial_id, vote_type) VALUES (?, ?, ?)", (user_id, tutorial_id, new_vote_type))
                final_user_vote_status = new_vote_type
            self.conn.commit()
            return final_user_vote_status
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_tutorial_votes(self, tutorial_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(CASE WHEN vote_type = 1 THEN 1 ELSE 0 END) AS likes, "
                       "SUM(CASE WHEN vote_type = -1 THEN 1 ELSE 0 END) AS dislikes "
                       "FROM tutorial_votes WHERE tutorial_id = ?", (tutorial_id,))
        result = cursor.fetchone()
        likes = result[0] if result[0] else 0
        dislikes = result[1] if result[1] else 0
        return {'likes': likes, 'dislikes': dislikes}

    def get_user_tutorial_vote(self, tutorial_id, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT vote_type FROM tutorial_votes WHERE tutorial_id = ? AND user_id = ?", (tutorial_id, user_id))
        result = cursor.fetchone()
        return result[0] if result else 0


















        