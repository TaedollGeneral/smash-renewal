#!/bin/bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 백엔드 의존성 설치 (필요할 때만)
npm install --production

# 3. 프론트엔드 빌드 (램 절약을 위해 기존 것 삭제 후 빌드)
cd client
rm -rf dist
npm install --legacy-peer-deps
npm run build

# 4. 서버 재시작
cd ..
pm2 restart all