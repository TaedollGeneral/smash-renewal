require('dotenv').config();
const express = require('express');
const http = require('http');
const mysql = require('mysql2');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const FLASK_PORT = process.env.FLASK_PORT || 5000;

// 미들웨어 설정
app.use(cors());
app.use(express.json());

// 정적 파일 경로를 React 빌드 폴더(client/dist)로 설정
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

// ── Flask 리버스 프록시 ────────────────────────────────────────────────────────
// /api/* 와 Flask Blueprint 경로들을 127.0.0.1:5000(Flask)으로 전달한다.
// SPA catch-all보다 반드시 앞에 위치해야 한다.
const FLASK_PREFIXES = ['/api/', '/login', '/apply', '/cancel', '/status'];

app.use((req, res, next) => {
    const isFlask = FLASK_PREFIXES.some(p => req.path === p || req.path.startsWith(p));
    if (!isFlask) return next();

    // GET/HEAD 등 body 없는 요청에서 req.body가 undefined이므로 빈 문자열로 처리
    const bodyStr = req.body ? JSON.stringify(req.body) : '';
    const options = {
        hostname: '127.0.0.1',
        port: FLASK_PORT,
        path: req.url,
        method: req.method,
        headers: {
            ...req.headers,
            host: `127.0.0.1:${FLASK_PORT}`,
            'content-length': Buffer.byteLength(bodyStr),
        },
    };

    const proxy = http.request(options, (flaskRes) => {
        res.status(flaskRes.statusCode);
        Object.entries(flaskRes.headers).forEach(([k, v]) => res.setHeader(k, v));
        flaskRes.pipe(res);
    });

    proxy.on('error', (err) => {
        console.error('[Flask proxy error]', err.message);
        res.status(502).json({ error: 'Flask 서버에 연결할 수 없습니다.' });
    });

    if (bodyStr) proxy.write(bodyStr);
    proxy.end();
});
// ─────────────────────────────────────────────────────────────────────────────

// SPA 라우팅: 위 프록시에서 처리되지 않은 모든 GET 요청에 index.html 반환
// 반드시 프록시 미들웨어보다 아래에 위치해야 한다
app.get('{*splat}', (req, res) => {
    res.sendFile(path.join(__dirname, 'client/dist', 'index.html'));
});

// 서버 시작
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT} (Flask proxy → 127.0.0.1:${FLASK_PORT})`);
});
