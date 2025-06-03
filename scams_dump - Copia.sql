PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE users (
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
            );
INSERT INTO users VALUES(1,'Patrick Messias Barbosa','pat@gmail.com','scrypt:32768:8:1$kkVCP7unwVYlIOkC$3bc09b0e121bd00a6cb172bae54fc7c17634ee15f3915a4faa3c6163086dd511111c94b1f129cf9c6dd72f91b134f4747f459a8679c1308a3e07ab67b865acd1','noob',1.0,0,'','','');
CREATE TABLE scams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                scam_type TEXT NOT NULL,
                evidence TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
INSERT INTO scams VALUES(1,'INSS','FRAUDUDENTO!','Fraude','inss@gmail.com',1,'2025-05-28 13:21:24');
INSERT INTO scams VALUES(2,'LULA MORRE','MORREU!','Fake News','pat2@gmail.com',1,'2025-05-28 13:21:38');
INSERT INTO scams VALUES(3,'Golpe Phishing GitHub','Tentaram roubar!','Phishing','pat@gmail.com',1,'2025-05-28 13:22:02');
CREATE TABLE votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER NOT NULL,
                scam_id INTEGER NOT NULL,
                vote_type INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (scam_id) REFERENCES scams(id) ON DELETE CASCADE,
                UNIQUE(user_id, scam_id)  
            );
INSERT INTO votes VALUES(1,1,3,-1,'2025-05-28 13:22:05');
INSERT INTO votes VALUES(2,1,2,1,'2025-05-28 13:22:10');
CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                scam_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (scam_id) REFERENCES scams(id) ON DELETE CASCADE
            );
CREATE TABLE tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                youtube_link TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
INSERT INTO tutorials VALUES(1,'Como não cair em bait','Não clicar em links estranhos!','https://www.youtube.com/watch?v=dQw4w9WgXcQ',1,'2025-05-28 13:23:03');
INSERT INTO tutorials VALUES(2,'AAAAAAA','TEST','',1,'2025-05-28 13:23:20');
CREATE TABLE tutorial_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tutorial_id INTEGER NOT NULL,          
                vote_type INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
                UNIQUE(user_id, tutorial_id)       
            );
INSERT INTO tutorial_votes VALUES(1,1,2,1,'2025-05-28 13:23:27');
INSERT INTO tutorial_votes VALUES(2,1,1,-1,'2025-05-28 13:23:33');
INSERT INTO sqlite_sequence VALUES('users',1);
INSERT INTO sqlite_sequence VALUES('scams',3);
INSERT INTO sqlite_sequence VALUES('votes',2);
INSERT INTO sqlite_sequence VALUES('tutorials',2);
INSERT INTO sqlite_sequence VALUES('tutorial_votes',2);
COMMIT;
