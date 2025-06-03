BEGIN TRANSACTION;
CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                type_user TEXT DEFAULT 'noob',
                confidence REAL DEFAULT 1.0,
                age INTEGER DEFAULT 0,
                city TEXT DEFAULT '',
                state TEXT DEFAULT '',
                civil_state TEXT DEFAULT ''
            );
CREATE TABLE scams (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                scam_type TEXT NOT NULL,
                evidence TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
CREATE TABLE votes (
                id SERIAL PRIMARY KEY, 
                user_id INTEGER NOT NULL,
                scam_id INTEGER NOT NULL,
                vote_type INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (scam_id) REFERENCES scams(id) ON DELETE CASCADE,
                UNIQUE(user_id, scam_id)  
            );
CREATE TABLE comments (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                scam_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (scam_id) REFERENCES scams(id) ON DELETE CASCADE
            );
CREATE TABLE tutorials (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                youtube_link TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
CREATE TABLE tutorial_votes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                tutorial_id INTEGER NOT NULL,          
                vote_type INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
                UNIQUE(user_id, tutorial_id)       
            );
COMMIT;
