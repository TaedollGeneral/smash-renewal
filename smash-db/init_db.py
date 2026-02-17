import sqlite3
import csv
import bcrypt
import os

# 파일명 설정
CSV_FILE = 'smash_members_utf8.csv'
DB_FILE = 'users.db'

def init_database():
    # 1. DB 연결 (없으면 생성)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 2. 테이블 생성 (학번을 PK로 설정)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # 3. 데이터 이관
    if os.path.exists(CSV_FILE):
        print(f"Reading {CSV_FILE}...")
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader) # 헤더 건너뛰기

            count = 0
            for row in reader:
                if not row: continue

                # CSV 순서: student_id, name, password, role
                s_id = row[0].strip()
                nm = row[1].strip()
                raw_pw = row[2].strip()
                rl = row[3].strip()

                # [핵심] 비밀번호 암호화 (Hashing)
                hashed_pw = bcrypt.hashpw(raw_pw.encode('utf-8'), bcrypt.gensalt())

                try:
                    cursor.execute('INSERT INTO users VALUES (?, ?, ?, ?)', 
                                   (s_id, nm, hashed_pw.decode('utf-8'), rl))
                    count += 1
                except sqlite3.IntegrityError:
                    pass # 중복 데이터는 무시

        conn.commit()
        print(f"✅ DB 구축 완료! 총 {count}명 저장됨.")
    else:
        print("❌ CSV 파일을 찾을 수 없습니다.")

    conn.close()

if __name__ == '__main__':
    init_database()
