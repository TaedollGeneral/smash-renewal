#!/usr/bin/env python3
# reset_users_from_csv.py — CSV 파일로 users 테이블 초기화
#
# 사용: python reset_users_from_csv.py [csv_file_path]
# 기본값: smash_db/smash_members_utf8.csv

import sqlite3
import csv
import bcrypt
import os
import sys
from pathlib import Path

_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_DIR, 'smash_db', 'users.db')

def reset_users_from_csv(csv_file: str) -> None:
    """CSV 파일로 users 테이블을 초기화한다.

    주의: 기존 users 테이블의 모든 데이터가 삭제됩니다!

    Args:
        csv_file: CSV 파일 경로 (헤더 필수)
                  포맷: student_id, name, password, role
    """
    if not os.path.exists(csv_file):
        print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_file}")
        return False

    print(f"📄 CSV 파일: {csv_file}")
    print(f"📚 DB 경로: {_DB_PATH}")

    # 확인 메시지
    response = input("\n⚠️  users 테이블의 모든 데이터가 삭제됩니다. 계속하시겠습니까? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ 취소되었습니다.")
        return False

    conn = sqlite3.connect(_DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. users 테이블 DROP (안전하게 존재 여부 확인)
        cursor.execute("DROP TABLE IF EXISTS users")
        print("🔄 기존 users 테이블 삭제 완료")

        # 2. users 테이블 생성
        cursor.execute('''
            CREATE TABLE users (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        print("✅ users 테이블 생성 완료")

        # 3. CSV 데이터 로드
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 헤더 건너뛰기

            count = 0
            errors = 0

            for row_num, row in enumerate(reader, start=2):
                if not row:
                    continue

                try:
                    s_id = row[0].strip()
                    name = row[1].strip()
                    raw_pw = row[2].strip()
                    role = row[3].strip()

                    # 비밀번호 암호화
                    hashed_pw = bcrypt.hashpw(raw_pw.encode('utf-8'), bcrypt.gensalt())

                    cursor.execute(
                        'INSERT INTO users VALUES (?, ?, ?, ?)',
                        (s_id, name, hashed_pw.decode('utf-8'), role)
                    )
                    count += 1

                except (IndexError, ValueError) as e:
                    print(f"⚠️  행 {row_num} 오류: {e}")
                    errors += 1
                    continue
                except sqlite3.IntegrityError:
                    print(f"⚠️  행 {row_num}: 중복된 student_id ({row[0]})")
                    errors += 1
                    continue

        conn.commit()

        # 4. 결과 출력
        print(f"\n✅ 데이터 로드 완료")
        print(f"   - 추가된 회원: {count}명")
        if errors > 0:
            print(f"   - 오류/스킵: {errors}건")

        # 5. 검증
        total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        print(f"   - 현재 총 회원: {total}명")

        return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    # CSV 파일 경로 결정
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = os.path.join(_DIR, 'smash_db', 'smash_members_utf8.csv')

    success = reset_users_from_csv(csv_file)
    sys.exit(0 if success else 1)
