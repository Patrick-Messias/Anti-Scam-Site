import sqlite3
from classes import User, DigitalScam # type: ignore

class Database:
    def __init__(self, db_path=':memory:'):  # Usando banco em memória para testes
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                type_user TEXT NOT NULL,
                confidence REAL NOT NULL,
                age INTEGER NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                civil_state TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type_scam TEXT NOT NULL,
                danger_level REAL NOT NULL,
                damage_level REAL NOT NULL,
                evidence TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()

    def add_user(self, user):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (user.name, user.email, user.password_hash, user.is_admin))
        self.conn.commit()

    def get_user_by_email(self, email):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row: return User(*row)
        return None

    def get_all_scams(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM scams')
        return [DigitalScam(*row) for row in cursor.fetchall()]
    
    def get_user_by_id(self, user_id):
        # Exemplo básico - adapte para seu banco de dados
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(*user_data)  # Seu construtor de User deve aceitar esses parâmetros
        return None


if __name__ == '__main__':
    # Teste local do banco de dados (opcional)
    db = Database()
    print("Banco de dados inicializado com sucesso.")



















