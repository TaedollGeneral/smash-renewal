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
// express.json()을 전역 미들웨어로 등록하지 않음.
// Flask 프록시는 req를 raw 스트림 그대로 전달하므로, body를 미리 파싱하면
// 스트림이 소비되어 Flask로 재전송이 불가능해지고 서버 크래시의 원인이 됨.

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

    // req 스트림을 파싱 없이 Flask로 직접 파이프한다.
    // - body 재직렬화를 하지 않으므로 Buffer.byteLength 관련 크래시가 원천 차단됨
    // - Content-Type(JSON, form-data 등)에 관계없이 모든 요청을 원본 그대로 전달함
    // - Content-Length 등 원본 헤더가 변조 없이 Flask에 그대로 전달됨
    const options = {
        hostname: '127.0.0.1',
        port: FLASK_PORT,
        path: req.url,
        method: req.method,
        headers: {
            ...req.headers,
            host: `127.0.0.1:${FLASK_PORT}`,
        },
    };

    const proxy = http.request(options, (flaskRes) => {
        res.writeHead(flaskRes.statusCode, flaskRes.headers);
        flaskRes.pipe(res);
    });

    proxy.on('error', (err) => {
        console.error('[Flask proxy error]', err.message);
        if (!res.headersSent) {
            res.status(502).json({ error: 'Flask 서버에 연결할 수 없습니다.' });
        }
    });

    req.pipe(proxy);
});
// ─────────────────────────────────────────────────────────────────────────────

// SPA 라우팅: 위 프록시에서 처리되지 않은 모든 GET 요청에 index.html 반환
// 반드시 프록시 미들웨어보다 아래에 위치해야 한다
app.get('{*splat}', (req, res) => {
    res.sendFile(path.join(__dirname, 'client/dist', 'index.html'));
});

// 예상치 못한 예외가 발생해도 프로세스 전체가 죽지 않도록 최후 안전망 등록
// (req.pipe 등 스트림 레이어에서 발생하는 미처리 에러 대비)
process.on('uncaughtException', (err) => {
    console.error('[uncaughtException]', err);
});
process.on('unhandledRejection', (reason) => {
    console.error('[unhandledRejection]', reason);
});

// 서버 시작
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT} (Flask proxy → 127.0.0.1:${FLASK_PORT})`);
});
