import requests
import concurrent.futures
import time

# --- [설정 구역] ---
# 프록시(Node.js)를 거치는지, 혹은 실제 도메인인지 주소 지정
TARGET_URL = "http://127.0.0.1:3000/api/apply" 
CATEGORY = "WED_REGULAR"  # 수요일 일반 운동 카테고리 (서버 Enum 값과 동일하게)

# 1단계에서 만든 50개의 토큰을 여기에 붙여넣으세요.
TEST_TOKENS = [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxIiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDEiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.N0ZnsBlESJY77wrhcXdbrrME1a6kAaGfxcBgp5VPUHM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyIiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDIiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.NfBEAcTxPlN9nnCqLZXva4LfwBaovQ2aCJkJ2QxGnAM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzIiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDMiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.iga089huKCMKT3ApwDleVVCAUaFDbGN84c1qHXyboP8",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0IiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDQiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.dtmc5kHUeH9-ms-ihXxs3W9XeLAQAU3sL1viTEf_etY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1IiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDUiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.QCsPHO0KDFu-ofUNmsUMMQrg_TS8jiPFF5ULvCy-nIw",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2IiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDYiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.YEpDPNBHXxzcUL2TMSaKHjgzHOORXRETDckM9_1IH68",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3IiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDciLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.bgkeMKoGdvU_-2-7O4aWKVfU12PAK6gqamsfuqdpD40",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4IiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDgiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.TWLk6GY_qoNt2WHohTiRbZp4-062Wr-xDkdtUcQEmek",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5IiwibmFtZSI6Ilx1ZDE0Y1x1YzJhNFx1ZDEzMDkiLCJyb2xlIjoidXNlciIsInZlciI6MSwiZXhwIjoxNzcyNDM1MDI1fQ.a7d_HZBCtfab6XGUpHrGRnOTXcIVtcvcmPaQe7fOpDs",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxMCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.Xsz-T3W2AKAcYX1m5Ua4XgbJrWiKhl5vkEDg13Lxqds",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxMSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.8i0hH9jxJQH4VwW5gcM4LRkG5tAqIOoOu_rIie5cyd0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxMiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.RMVLvpGJEQC_KhPBea9rTQRfxmjfhz6tSW6cfj1oZu0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxMyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.hxfJDDMLgJ5PbrARAKV8LcIIk1ftKv2Li47h7BCBJLY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxNCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.MCHB6okc4YjH8ATNlb_vG5p82U4Imzy8Y2AxBdOmqr4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxNSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.QOwT0n7xmEDZMV0nQ_Qr7hV6SqnHx2-_Lu9nDrf8wuk",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxNiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.wpuurFJQ5KtD-W2lM7lCpHnBgUcyz0qInPoftnl4hUs",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxNyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.vkww89WVbD34nCUjc3znDZwhnDp98BWRoJchaOqFE2s",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxOCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxOCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.Si374QRd6tr9id9iyJs6oXZBqyAkzKyEhTYg5gsPW7s",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxOSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAxOSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.MplHEG-CPL6DTUmNvq6RBDmGQmhh3NGD2xY0cC832cQ",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyMCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.JWTJbOP6w5bU-RksTncWjm8Gny5HDLhuLKqF4KhYqRA",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyMSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.KMMfE71E9rOhwybsFkkcifDdnTHDHIlOBxXLE-tOnDo",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyMiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.xqpzgwJ_Aqzs12PPZ6KeC5NbLO8KwOJbphBzP36f_Hc",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyMyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.opv0wALhi6IwbFuQaSx5liut6_s_Ak1H9HXvy9vSJxI",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyNCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.UEU1Ty82238J5Jt6G6az1-J1_GR63kvfD-8SoKrmZjo",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyNSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.o61K4djigDOWx2JLr_FXJ7-21ZINDOL9J9Y44CUDzns",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyNiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.MVS07fob6Tk5nVZwpk9U0sK6ir2BG76xMJQWYuE_wDo",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyNyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.F2zOBkgL5NhHoG8VnNRoA5C4Cr5t4B7H33vayFjl37Q",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyOCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyOCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.RNBzNuxYm2Z8Z3hABFTPhbAvCHOnKuwx1EyvhtyQgIk",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyOSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAyOSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.LnyK94dMOi3MULaRdSN0wHHYQ0zK04VsrTmMqoreJxs",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzMCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.zJELuN6GLuepI0Ju4AoHEkwvaxN0EnArEOl423rfBN0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzMSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.G5vfyhMxKHpN2196ZFaSoJlh_O0mYAauY8IlS3Kg1dk",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzMiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.-eG-XB63zA0D1L7l3Iga0FLLhTSJWxUEzhcSZjcffxc",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzMyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.RzE-NKR-rpjfF61AA5xAz9a0WJCJgfNduG_xRlmReqI",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzNCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.dggkbTJ3l3NGp0g4aj68pgGvLv7fYS5-j-C9eqUe4nQ",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzNSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.mpozAm-hnnvmAuHVenBknYeZcyX6IANgB2YIb-4o2QU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzNiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.0VOTlZfjN1NDA8t4rEUkcEtUojuTFikaR2ubvEkQ_pQ",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzNyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.Iylrz2YplM7fJo95Q6663q6cSfa8WeTAh0zszU9rflM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzOCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzOCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.AfIV0_6V_lULWgS5U678G_Ws5fekIUO2z_cYXCxPU3E",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzOSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzAzOSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.FdZYcXkSGK87IK-4l6f-Oqgr4u3_rDoBYiviC1zhsuc",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0MCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.SXBYhsFbFgtcEtTv4H_ne40yKy5LY6dKOQcFimDaUiU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0MSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.INGURoE5YpquOSFAzNWwpuTu08hzXDnAYS3iXCD7I8w",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0MiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.mj2oTEa3XaTbjCKLo-JLeO2ZaX9vggjrEekIkX6UZQ4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0MyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.iEkqx2Hpx4zssIt9SYZJXS4Sm6JbLe6k4WSsLit7UCI",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0NCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.PtqJj7Uw-7xf33VR01hOUnUZuEX8YqdPvTM36HGpOH4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0NSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.aVaOXbMyujRArfzSXalvLk70lXA66kXrEzyz4x8tIYg",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NiIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0NiIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.wahWe4O6tM-wToJQVBB0_bAM8SLcm0cgUFMTWtA-sho",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NyIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0NyIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.DqwAc4QG7jno8_ZSsynyoYVX2z-oaUacobTofn4BQx4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0OCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0OCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.1H7nPpEzKflTS_all13wVTRigYqf5Eq_RTpR6K3QzLw",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0OSIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA0OSIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.1ApF0orgDl17HnJR5sSU2ajHxHOPz4n96tg-dscu3fs",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1MCIsIm5hbWUiOiJcdWQxNGNcdWMyYTRcdWQxMzA1MCIsInJvbGUiOiJ1c2VyIiwidmVyIjoxLCJleHAiOjE3NzI0MzUwMjV9.kTnGq0L6TNwW1K2zCWfULiUASQQWW62CEVV5OoSQmTQ",
]# -----------------

def send_apply_request(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {"category": CATEGORY}
    
    start_time = time.time()
    try:
        # 타임아웃을 짧게 주어 서버가 뻗는지(블로킹되는지) 확인합니다.
        response = requests.post(TARGET_URL, json=payload, headers=headers, timeout=5)
        elapsed = time.time() - start_time
        return {
            "status": response.status_code, 
            "time": elapsed, 
            "text": response.text
        }
    except Exception as e:
        return {"status": "TIMEOUT_OR_ERROR", "time": 0, "text": str(e)}

def run_stress_test():
    total_users = len(TEST_TOKENS)
    print(f"🚀 {total_users}명의 유저가 1차선에서 대기 중...")
    print("💥 3, 2, 1... 발사!\n")
    
    results = {"200": 0, "409": 0, "400": 0, "502": 0, "TIMEOUT_OR_ERROR": 0}
    response_times = []
    
    start_total = time.time()
    
    # max_workers를 유저 수와 동일하게 맞춰 '완벽한 동시 발사'를 구현합니다.
    with concurrent.futures.ThreadPoolExecutor(max_workers=total_users) as executor:
        futures = [executor.submit(send_apply_request, token) for token in TEST_TOKENS]
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            status = str(res["status"])

            if status not in ["200", "409"]:
                print(f"[{status} 에러 원인] {res['text']}")
            
            # 상태 코드 카운팅
            if status in results:
                results[status] += 1
            else:
                results[status] = 1
                
            if res["time"] > 0:
                response_times.append(res["time"])

    end_total = time.time()
    
    # 결과 분석 출력
    avg_time = sum(response_times) / len(response_times) if response_times else 0
    max_time = max(response_times) if response_times else 0
    
    print("=== 📊 스트레스 테스트 결과 ===")
    print(f"⏱️ 전체 소요 시간: {end_total - start_total:.3f}초")
    print(f"⚡ 평균 응답 시간: {avg_time:.3f}초 (최대: {max_time:.3f}초)\n")
    
    print(f"✅ 성공 (200 OK): {results.get('200', 0)}명 (데이터베이스 기록 성공)")
    print(f"🚫 정원 초과 (409): {results.get('409', 0)}명 (정상적으로 커트됨)")
    print(f"🔥 서버 에러 (500/502): {results.get('502', 0) + results.get('500', 0)}명 (서버 죽음)")
    print(f"⚠️ 타임아웃/기타: {results.get('TIMEOUT_OR_ERROR', 0)}명 (대기열 병목)")
    
if __name__ == "__main__":
    if len(TEST_TOKENS) < 2:
        print("⚠️ TEST_TOKENS 리스트에 1단계에서 만든 토큰들을 넣어주세요!")
    else:
        run_stress_test()