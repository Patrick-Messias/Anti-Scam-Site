from database import Database
from werkzeug.security import generate_password_hash
import sys

# Inicializa o banco de dados
db = Database()

# Dados do novo usuário administrador
admin_name = input("Digite o nome do admin: ")
admin_email = input("Digite o e-mail do admin: ")
admin_password = input("Digite a senha do admin: ")

try:
    cursor = db.conn.cursor()

    # Verifica se o e-mail já existe
    cursor.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
    if cursor.fetchone():
        print(f"Erro: O e-mail {admin_email} já está em uso.")
        sys.exit(1) # Sai com erro

    # Insere o novo usuário com confidence 3.0 e type_user 'admin'
    cursor.execute('''
        INSERT INTO users (name, email, password_hash, type_user, confidence)
        VALUES (%s, %s, %s, %s, %s)
    ''', (admin_name, admin_email, generate_password_hash(admin_password), 'admin', 3.0))

    db.conn.commit()
    print(f"Usuário administrador '{admin_name}' criado com sucesso!")

except Exception as e:
    db.conn.rollback()
    print(f"Ocorreu um erro: {e}")
finally:
    db.conn.close()