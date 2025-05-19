"""
from flask_login import LoginManager
from database import Database # type: ignore
import app

db = Database()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    cursor = db.conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if row: return User(*row)
    return None

if __name__ == '__main__':
    print("Este módulo não deve ser executado diretamente.")
"""












