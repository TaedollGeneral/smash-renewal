require('dotenv').config();
const express = require('express');
const http = require('http');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT           = process.env.PORT       || 3000;
const FLASK_PORT     = process.env.FLASK_PORT || 5000;
// VIP 포트: VIP_ENABLED=true (c6i.xlarge 피크타임)일 때 POST /api/apply를 별도 Gunicorn으로 분기
const VIP_ENABLED    = process.env.VIP_ENABLED    === 'true';
const FLASK_VIP_PORT = process.env.FLASK_VIP_PORT || 5001;

// [보안] CORS — 허용 출처를 운영 도메인으로 제한
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || '').split(',').filter(Boolean);
app.use(cors({
    origin: ALLOWED_ORIGINS.length > 0
        ? (origin, cb) => {
            // 동일 출처(origin === undefined) 또는 허용 목록에 포함된 출처만 허용
            if (!origin || ALLOWED_ORIGINS.includes(origin)) {
                cb(null, true);
            } else {
                cb(new Error('CORS 정책에 의해 차단되었습니다.'));
            }
        }
        : false,  // ALLOWED_ORIGINS 미설정 시 동일 출처만 허용
    credentials: true,
}));
// express.json()을 전역 미들웨어로 등록하지 않음.
// Flask 프록시는 req를 raw 스트림 그대로 전달하므로, body를 미리 파싱하면
// 스트림이 소비되어 Flask로 재전송이 불가능해지고 서버 크래시의 원인이 됨.

// [보안] HTTP 보안 헤더 — XSS, 클릭재킹, MIME 스니핑 방지
app.use((req, res, next) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('X-XSS-Protection', '1; mode=block');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
    // HSTS는 Nginx/로드밸런서에서 설정 권장 (HTTPS 종단점)
    if (process.env.NODE_ENV === 'production') {
        res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
    }
    next();
});

// 정적 파일 경로를 React 빌드 폴더(client/dist)로 설정
app.use(express.static(path.join(__dirname, 'client/dist')));

// ── /api/category-states 응답 캐시 (2초 TTL) ─────────────────────────────────
// 200명 동시 접속 × 2초 폴링 = 최대 초당 100건 요청을 캐시가 흡수한다.
// TTL 2초: 실제 상태 변경(신청 오픈/마감)보다 훨씬 짧아 UX 영향 없음.
let _statesCache = { body: null, headers: null, ts: 0 };
const STATES_CACHE_TTL_MS = 2000;

// ── Flask 리버스 프록시 ────────────────────────────────────────────────────────
// /api/* 와 Flask Blueprint 경로들을 127.0.0.1:5000(Flask)으로 전달한다.
// SPA catch-all보다 반드시 앞에 위치해야 한다.
const FLASK_PREFIXES = ['/api/', '/login', '/apply', '/cancel', '/status'];

app.use((req, res, next) => {
    const isFlask = FLASK_PREFIXES.some(p => req.path === p || req.path.startsWith(p));
    if (!isFlask) return next();

    // ── /api/category-states 캐시 처리 ───────────────────────────────────────
    // 2초 TTL 내 재요청은 캐시에서 즉시 반환하여 Flask 도달 차단.
    // serverTime 필드는 캐시 저장 시각이 아닌 현재 시각으로 교체하여
    // 클라이언트 시계 동기화 정확도를 유지한다.
    if (req.method === 'GET' && req.path === '/api/category-states') {
        if (_statesCache.body && (Date.now() - _statesCache.ts) < STATES_CACHE_TTL_MS) {
            try {
                const parsed = JSON.parse(_statesCache.body.toString());
                parsed.serverTime = Date.now();
                const freshBody = Buffer.from(JSON.stringify(parsed));
                const headers = { ..._statesCache.headers, 'content-length': freshBody.length };
                res.writeHead(200, headers);
                return res.end(freshBody);
            } catch {
                // JSON 파싱 실패 시 원본 캐시 그대로 반환
                res.writeHead(200, _statesCache.headers);
                return res.end(_statesCache.body);
            }
        }
    }

    // req 스트림을 파싱 없이 Flask로 직접 파이프한다.
    // - body 재직렬화를 하지 않으므로 Buffer.byteLength 관련 크래시가 원천 차단됨
    // - Content-Type(JSON, form-data 등)에 관계없이 모든 요청을 원본 그대로 전달함
    // - Content-Length 등 원본 헤더가 변조 없이 Flask에 그대로 전달됨
    // 실제 클라이언트 IP를 Flask에 전달 (Rate Limiter가 IP를 정확히 식별하기 위함)
    const clientIp = req.ip || req.socket.remoteAddress || '0.0.0.0';

    // [보안] 클라이언트가 보낸 프록시 관련 헤더를 제거하고 신뢰할 수 있는 값만 설정
    const sanitizedHeaders = { ...req.headers };
    delete sanitizedHeaders['x-forwarded-for'];
    delete sanitizedHeaders['x-forwarded-host'];
    delete sanitizedHeaders['x-forwarded-proto'];
    delete sanitizedHeaders['x-real-ip'];

    // ── VIP 포트 분기 ─────────────────────────────────────────────────────────
    // VIP_ENABLED=true (c6i.xlarge 피크타임)이고 POST /api/apply인 경우에만
    // 전용 Gunicorn VIP 인스턴스(port 5001)로 라우팅한다.
    // 그 외 모든 요청(로그인, GET, 취소 등)은 GEN 인스턴스(port 5000)로 전달.
    const isVipApply = VIP_ENABLED && req.path === '/api/apply' && req.method === 'POST';
    const targetPort = isVipApply ? FLASK_VIP_PORT : FLASK_PORT;

    const options = {
        hostname: '127.0.0.1',
        port: targetPort,
        path: req.url,
        method: req.method,
        headers: {
            ...sanitizedHeaders,
            host: `127.0.0.1:${targetPort}`,
            'x-forwarded-for': clientIp,
            'x-forwarded-proto': req.protocol,
        },
    };

    const proxy = http.request(options, (flaskRes) => {
        // ── category-states 캐시 갱신 ────────────────────────────────────────
        // 성공 응답(200)일 때만 캐시에 저장한다.
        const isCacheTarget = req.method === 'GET'
            && req.path === '/api/category-states'
            && flaskRes.statusCode === 200;

        if (isCacheTarget) {
            const chunks = [];
            flaskRes.on('data', chunk => chunks.push(chunk));
            flaskRes.on('end', () => {
                const body = Buffer.concat(chunks);
                _statesCache = { body, headers: flaskRes.headers, ts: Date.now() };
                res.writeHead(200, flaskRes.headers);
                res.end(body);
            });
            flaskRes.on('error', (err) => {
                console.error('[Flask response stream error]', err.message);
                if (!res.writableEnded) res.end();
            });
            return; // 아래 pipe 처리를 건너뜀
        }

        res.writeHead(flaskRes.statusCode, flaskRes.headers);
        flaskRes.pipe(res);

        // Flask 응답 스트림 에러 (전송 도중 Flask 크래시 등)
        flaskRes.on('error', (err) => {
            console.error('[Flask response stream error]', err.message);
            if (!res.writableEnded) res.end();
        });
    });

    // Flask 연결 30초 타임아웃 — 무한 대기(hang) 방지
    proxy.setTimeout(30_000, () => {
        proxy.destroy();
        if (!res.headersSent) {
            res.writeHead(504, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: '서버 응답 시간 초과' }));
        }
    });

    proxy.on('error', (err) => {
        console.error('[Flask proxy error]', err.message);
        if (!res.headersSent) {
            res.writeHead(502, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: '서버에 연결할 수 없습니다.' }));
        }
    });

    // 클라이언트가 먼저 연결을 끊으면 Flask 요청도 중단 (리소스 누수 방지)
    res.on('close', () => {
        if (!proxy.destroyed) proxy.destroy();
    });

    req.pipe(proxy);
});
// ─────────────────────────────────────────────────────────────────────────────

// SPA 라우팅: 위 프록시에서 처리되지 않은 모든 GET 요청에 index.html 반환
// 반드시 프록시 미들웨어보다 아래에 위치해야 한다
app.get('{*splat}', (req, res) => {
    res.sendFile(path.join(__dirname, 'client/dist', 'index.html'));
});

// [보안] URIError 전용 에러 핸들러 — 잘못된 URI 인코딩(%c0 등) 요청 처리
// path-to-regexp가 {*splat} 패턴 매칭 시 decodeURIComponent를 호출하여 발생.
// 핸들러가 없으면 Express 기본 500 응답이 반환되므로 400으로 명시적 차단한다.
app.use((err, req, res, next) => {
    if (err instanceof URIError) {
        if (!res.headersSent) res.status(400).end();
        return;
    }
    next(err);
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
