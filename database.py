import sqlite3
from classes import User, DigitalScam # type: ignore
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
            self.conn.rollback() # Rollback on error
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
        
    def get_all_scams(self): # Kept for other functionalities if needed
        cursor = self.conn.cursor()
        # Fetching limited data for overview, adjust as needed
        cursor.execute('SELECT id, title, description, scam_type, evidence, user_id, created_at FROM scams ORDER BY created_at DESC')
        scams_data = cursor.fetchall()
        scams = []
        if scams_data:
            columns = [column[0] for column in cursor.description]
            for row in scams_data:
                scams.append(dict(zip(columns, row)))
        return scams

    def manage_vote(self, user_id, scam_id, new_vote_type):
        """
        Manages a user's vote on a scam.
        - If the user votes with the same type again, the vote is removed.
        - If the user votes with a different type, the vote is updated.
        - If the user has no vote, a new vote is inserted.
        Returns the final vote status of the user for this scam (1, -1, or 0 for no vote).
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT vote_type FROM votes WHERE user_id = ? AND scam_id = ?", (user_id, scam_id))
        existing_vote_row = cursor.fetchone()

        final_user_vote_status = 0  # 0 means no vote

        if existing_vote_row:
            current_db_vote_type = existing_vote_row[0]
            if current_db_vote_type == new_vote_type:
                # User is un-voting (e.g., clicking 'like' when it's already liked)
                cursor.execute("DELETE FROM votes WHERE user_id = ? AND scam_id = ?", (user_id, scam_id))
                final_user_vote_status = 0
            else:
                # User is changing their vote (e.g., from 'like' to 'dislike')
                cursor.execute("UPDATE votes SET vote_type = ? WHERE user_id = ? AND scam_id = ?", (new_vote_type, user_id, scam_id))
                final_user_vote_status = new_vote_type
        else:
            # User is casting a new vote
            cursor.execute("INSERT INTO votes (user_id, scam_id, vote_type) VALUES (?, ?, ?)", (user_id, scam_id, new_vote_type))
            final_user_vote_status = new_vote_type
        
        self.conn.commit()
        return final_user_vote_status

    def get_votes(self, scam_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN vote_type = 1 THEN 1 ELSE 0 END) as likes,
                SUM(CASE WHEN vote_type = -1 THEN 1 ELSE 0 END) as dislikes
            FROM votes
            WHERE scam_id = ?
        ''', (scam_id,))
        result = cursor.fetchone()
        return {'likes': result[0] if result[0] is not None else 0, 'dislikes': result[1] if result[1] is not None else 0}

    def get_user_vote(self, scam_id, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT vote_type FROM votes
            WHERE scam_id = ? AND user_id = ?
        ''', (scam_id, user_id))
        result = cursor.fetchone()
        return result[0] if result else 0

if __name__ == '__main__':
    db = Database(db_path=':memory:') # Use in-memory for isolated testing
    print("Banco de dados (em memória) inicializado com sucesso.")
    # Example Usage:
    # db.add_user("Test User", "test@example.com", "password123")
    # user = db.get_user_by_email("test@example.com")
    # if user:
    #     print(f"User created: {user.name}")
    #     # Assume a scam with id 1 exists for testing votes
    #     # db.conn.execute("INSERT INTO scams (id, title, description, scam_type, user_id) VALUES (1, 'Test Scam', 'Desc', 'Phishing', ?)",(user.id,))
    #     # db.conn.commit()
        
    #     # vote_status = db.manage_vote(user.id, 1, 1) # Like
    #     # print(f"Vote status after like: {vote_status}") # Expected: 1
    #     # counts = db.get_votes(1)
    #     # print(f"Counts: {counts}") # Expected: {'likes': 1, 'dislikes': 0}

    #     # vote_status = db.manage_vote(user.id, 1, -1) # Change to dislike
    #     # print(f"Vote status after dislike: {vote_status}") # Expected: -1
    #     # counts = db.get_votes(1)
    #     # print(f"Counts: {counts}") # Expected: {'likes': 0, 'dislikes': 1}
        
    #     # vote_status = db.manage_vote(user.id, 1, -1) # Un-dislike
    #     # print(f"Vote status after un-dislike: {vote_status}") # Expected: 0
    #     # counts = db.get_votes(1)
    #     # print(f"Counts: {counts}") # Expected: {'likes': 0, 'dislikes': 0}
    # else:
    #     print("Failed to create user.")