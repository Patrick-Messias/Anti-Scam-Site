import sqlite3
from classes import User, DigitalScam # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_path='scams.db'):  # Usando banco em memória para testes
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
            return False

    def get_user_by_email(self, email):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0],
                name=row[1],
                email=row[2],
                password_hash=row[3],  # Alterado de 'password' para 'password_hash'
                type_user=row[4],
                confidence=row[5],
                age=row[6],
                city=row[7],
                state=row[8],
                civil_state=row[9]
            )
        return None

    def get_all_scams(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM scams')
        scams = []
        for row in cursor.fetchall():
            scams.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'scam_type': row[3],
                'evidence': row[4],
                'user_id': row[5],
                'created_at': row[6]
            })
        return scams
    
    def get_user_by_id(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0],
                name=row[1],
                email=row[2],
                password_hash=row[3],  # Alterado aqui também
                type_user=row[4],
                confidence=row[5],
                age=row[6],
                city=row[7],
                state=row[8],
                civil_state=row[9]
            )
        return None


if __name__ == '__main__':
    # Teste local do banco de dados (opcional)
    db = Database()
    print("Banco de dados inicializado com sucesso.")

    # TEMP
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA table_info(scams)")

    print("\nEstrutura da tabela scams:")
    for column in cursor.fetchall():
        print(column)
    
    print("\nPrimeiras 5 linhas da tabela scams:")
    cursor.execute("SELECT * FROM scams LIMIT 5")
    for row in cursor.fetchall():
        print(row)



















