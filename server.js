require('dotenv').config();
const express = require('express');
const mysql = require('mysql2');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// 미들웨어 설정
app.use(cors());
app.use(express.json()); // 프론트에서 보내는 JSON 데이터 받기

// [수정 1] 정적 파일 경로를 React 빌드 폴더(client/dist)로 변경
app.use(express.static(path.join(__dirname, 'client/dist')));

// DB 연결 풀 생성
const pool = mysql.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    database: process.env.DB_NAME,
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

const promisePool = pool.promise();

// DB 연결 테스트 API (이건 유지)
app.get('/test-db', async (req, res) => {
    try {
        const [rows] = await promisePool.query('SELECT 1 + 1 AS solution');
        res.json({ message: 'DB 연결 성공!', solution: rows[0].solution });
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: 'DB 연결 실패', error: err.message });
    }
});

// [수정 2] 모든 요청(*)에 대해 React의 index.html 반환 (SPA 라우팅)
// 주의: 이 코드는 항상 API 라우트보다 아래에 있어야 합니다.
app.get('/*', (req, res) => {
    res.sendFile(path.join(__dirname, 'client/dist', 'index.html'));
});

// 서버 시작
app.listen(PORT, () => {
    console.log(`🚀 Server is running on port ${PORT}`);
});