#!/usr/bin/env python3
"""
remote_stress.py  (로컬 PC 또는 EC2에서 실행)
==============================================
역할: 서버를 향해 520건의 HTTP 요청을 동시에 폭격하고 결과를 집계한다.

사용법:
  1. EC2 서버에서 `python setup_db_and_tokens.py` 실행
  2. 콘솔에 출력된 VALID_TOKENS, INVALID_TOKENS 배열을 아래 변수에 붙여넣기
  3. 실행:
     - EC2 내부 테스트:  python remote_stress.py --local
     - 외부 도메인 테스트: python remote_stress.py

의존 패키지:
  pip install requests
"""

import sys
import time
import threading
import statistics

import requests as http_client

# ══════════════════════════════════════════════════════════════════════════════
#  [STEP 1] 여기에 EC2에서 출력된 토큰을 붙여넣으세요.
# ══════════════════════════════════════════════════════════════════════════════


VALID_TOKENS = [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxIiwibmFtZSI6InRlc3RlcjEiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.0G_UiGB0pLXFgC0y7AV9s2-Yi2fYXF3qLDlE5KQ6N_s",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyIiwibmFtZSI6InRlc3RlcjIiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.MCtsSh8iJawBLUNvepgYkSsoTmL_orPZkHADEcpvECo",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzIiwibmFtZSI6InRlc3RlcjMiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.PxqcLzolxNzL9b687E85d8NuDa37Hb4QK7WPcODLxyM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0IiwibmFtZSI6InRlc3RlcjQiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.Qhzc34d8NvVowV-B-6Ya4YKBPitWsqaMWzbAGi8Fq8Q",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1IiwibmFtZSI6InRlc3RlcjUiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.j7c3-VGQZeXooo1Q_2Rx-ns8xzlv61LXrXXtn7P1tfU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2IiwibmFtZSI6InRlc3RlcjYiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.W4A9qHB2VVa1D_zv3KYQiGi7iLK7Q4e4fz21fF4szTE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3IiwibmFtZSI6InRlc3RlcjciLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.dqZqYnSHpq1ITSXKXdnKMUN1q02XNrITg0oC0-kicak",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4IiwibmFtZSI6InRlc3RlcjgiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.2aqvTv8U4BHJIWxskIh5DvAKxgpluJ1QL40YTsKJBi8",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5IiwibmFtZSI6InRlc3RlcjkiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.kMq_B8U2NJnLFqSrI8ILn7KvFfd4B79yRbTuLHxNk0o",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMCIsIm5hbWUiOiJ0ZXN0ZXIxMCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.aNfQt0-X4-moRZpdwMRQQL0KtulJB084dGvPaKif0QM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMSIsIm5hbWUiOiJ0ZXN0ZXIxMSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.xGYXe4BdBuFzVReyVTsnSLUw8AvYlifxfUPD2q_zZKA",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMiIsIm5hbWUiOiJ0ZXN0ZXIxMiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.5WWhbcRZBzked4dcmtJCzbU92UCKmI_5gYwKeuMAZ0A",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMyIsIm5hbWUiOiJ0ZXN0ZXIxMyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.ZX87MhbqquELcnDoU9Qu1a_L_NXgCj7j5z4vL7hiH8E",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNCIsIm5hbWUiOiJ0ZXN0ZXIxNCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.lA3x952oce16xUhw991P1PgFwJemwYXxsPkZkgW2GuQ",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNSIsIm5hbWUiOiJ0ZXN0ZXIxNSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.FMr7VQXBtJBw9604ZSx-u-hCQ18qDvpGLXIOdMJQxIU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNiIsIm5hbWUiOiJ0ZXN0ZXIxNiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.unvmgHMs4li163j9ZszUYcQ1iTW_DvQQwJ1F48WhSkE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxNyIsIm5hbWUiOiJ0ZXN0ZXIxNyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.uMvM8fPFO_xjzS3j9KRfn9_JYu-TCn_315zpfAVk0hM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxOCIsIm5hbWUiOiJ0ZXN0ZXIxOCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.5Ha76sHVS2xhJtiepaCHPYg3X0usSolrOrV8ZENOCaU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxOSIsIm5hbWUiOiJ0ZXN0ZXIxOSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.nh9Y0Nb4X7MxkG7cBC4kjEXu_ZOFQp7eQftBhPNHZ7c",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMCIsIm5hbWUiOiJ0ZXN0ZXIyMCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.-i7d0KFVaA6sa1Lz0qCvbTCOozgQ1MtuaZM70DEWOeY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMSIsIm5hbWUiOiJ0ZXN0ZXIyMSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.4mtQ25X81a0knBK1urEHV4x45Vxy6FHOremOQpi-7NM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMiIsIm5hbWUiOiJ0ZXN0ZXIyMiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.BFZfMmeF1CFkqeATEo1NYq7_Vli-7zJ_HMCIZ-j7wZU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyMyIsIm5hbWUiOiJ0ZXN0ZXIyMyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.xgEIxtcJMwrw78YH2aVckh_GTwZDzx1aHt4kBuClU-U",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNCIsIm5hbWUiOiJ0ZXN0ZXIyNCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.voYTHxMnPSBvVP9tn_KKMthWbIrGHGGCJmX7eI6mjjU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNSIsIm5hbWUiOiJ0ZXN0ZXIyNSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.-ihPXDyz_kf9u-O6X_AJDl6G8XaAvVKB4cKF2sFS5PE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNiIsIm5hbWUiOiJ0ZXN0ZXIyNiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.33Mm7902wN6Tm-WAkWKQue3O4ESc_wPRPhUxBb4qxJg",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyNyIsIm5hbWUiOiJ0ZXN0ZXIyNyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.gj-66U6LSyXo87pJ3J2tBrE-Y2hMxszYW2WrH2tiBdo",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyOCIsIm5hbWUiOiJ0ZXN0ZXIyOCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.qjCZPX5fWSJoveUGSTk4mh8BL_gKXFQ0oyrfNZ9--I0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyOSIsIm5hbWUiOiJ0ZXN0ZXIyOSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.fNY89UYkECuSztxKhWSLyOPh1HdlFGRwyDDOGbQqOIY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMCIsIm5hbWUiOiJ0ZXN0ZXIzMCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.0dS1zLJIVwMjZMZbDHPvVEqdwUI8aPGa70YWAfz8fhs",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMSIsIm5hbWUiOiJ0ZXN0ZXIzMSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9._YkqpDAacqrl8MoVj9U__mWkU43gatPpPPko-FMKj5k",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMiIsIm5hbWUiOiJ0ZXN0ZXIzMiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.FP70Mv9tXbS4wvDjT7EevdPR1VGSljIJHevUDqytNx0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzMyIsIm5hbWUiOiJ0ZXN0ZXIzMyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.ompYTklLuTL84tAwQzq6AhLJu2KwjkLCsCfimiPgNkE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNCIsIm5hbWUiOiJ0ZXN0ZXIzNCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.LaT0Gum6uZdKGqugknezCfq1mBm5iwvFMd4mzcvuKbw",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNSIsIm5hbWUiOiJ0ZXN0ZXIzNSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.ECoxDbb-XEO4eQe_CFT-z6nB0c3hwqSG2id2s_-jQw4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNiIsIm5hbWUiOiJ0ZXN0ZXIzNiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.NDyKgSkD7DyBk9o4s3whSBnmAwcWpRSHzEh-_38KUTM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzNyIsIm5hbWUiOiJ0ZXN0ZXIzNyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.ixiXcff-nFP01eS1x3UJJHBaSoOzlmVTqPiG1WQOcpI",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzOCIsIm5hbWUiOiJ0ZXN0ZXIzOCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.d448gWCBQ859NuD_CpWsrQzuTfGTrviaypq0osreCD0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzOSIsIm5hbWUiOiJ0ZXN0ZXIzOSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.2EgC0Ke5Bh4QE4v3u3k8BR-9IIVXgAGFqKvRJ2TlH2A",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MCIsIm5hbWUiOiJ0ZXN0ZXI0MCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.w0WU1szNsfoXnrrj35W8RNjRzzLLcgl9_BWdoeF9rhI",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MSIsIm5hbWUiOiJ0ZXN0ZXI0MSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.5-3dlzY42CRdZiPXxB2A8jl8cDCrdyArrCQizCH-EtA",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MiIsIm5hbWUiOiJ0ZXN0ZXI0MiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.R8Oy30m356NJs6WxoukBzSihXoD87E78BLTQ7s16t1I",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0MyIsIm5hbWUiOiJ0ZXN0ZXI0MyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.li1YzPRyEq0kntdkU2Z7pa72yds_pn9Et9yR9ejFzI4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NCIsIm5hbWUiOiJ0ZXN0ZXI0NCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.SeAJPk2jCx74Zc76g_nq4-M-eiOLEWZZMqFqopcb7Gc",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NSIsIm5hbWUiOiJ0ZXN0ZXI0NSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.dTJ7dAwBbVhWWWBQcyGvgXULWbgl8KtnTcOjRlEM_qU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NiIsIm5hbWUiOiJ0ZXN0ZXI0NiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.cc0_08hCIOWetcrSkkz7XP1QPFXv2Fq0Ma_CRJlBk4c",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0NyIsIm5hbWUiOiJ0ZXN0ZXI0NyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.lbKI6vqDfWhFfIAlJ-U1zwXhuN48W0Z4PznEHGHQgqA",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0OCIsIm5hbWUiOiJ0ZXN0ZXI0OCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.1uyk04MXvT6A-4YiT5-ik_2aSpRlvlRHlLZ2zolMUX4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0OSIsIm5hbWUiOiJ0ZXN0ZXI0OSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.dG57wDUHZlxJVCP_BbmFJmWdXroLD90KbxhA-thdmCM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1MCIsIm5hbWUiOiJ0ZXN0ZXI1MCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.eLPryOHLnA4xnhVsXf8rRyHmZd9tCH4wJEPeLEtY8c8",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1MSIsIm5hbWUiOiJ0ZXN0ZXI1MSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.TtJqGZqR4vBH-vnItb07_1kR1LDZM7ykh8BCwha3DFM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1MiIsIm5hbWUiOiJ0ZXN0ZXI1MiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.0PHMrIvu2yMW_XH51c9tm1cPwGXsLs_5Ij_7rV54Nrs",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1MyIsIm5hbWUiOiJ0ZXN0ZXI1MyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.fA3DlbzrT2KaBYTsoASDnbwoi4T8AxfSsfaK7VpXbi0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1NCIsIm5hbWUiOiJ0ZXN0ZXI1NCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.x-JU6rMORCX-H_jaNXOKCnK1xycFDVX3jNR1XmzFTj8",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1NSIsIm5hbWUiOiJ0ZXN0ZXI1NSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.y6kMgVVK57jHsGgZdp0JTE0aXioSWWuPLwj5pT5sw7E",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1NiIsIm5hbWUiOiJ0ZXN0ZXI1NiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.TFj5RvJVCWFe1BasPMgVMq4lAzo0ElD-JLPq2Tfh_5o",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1NyIsIm5hbWUiOiJ0ZXN0ZXI1NyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.P-Kic8_pbZSunKtSYGD0ZcCRyHCfJqQjq1I8kCdq1_k",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1OCIsIm5hbWUiOiJ0ZXN0ZXI1OCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.whwtS5aYpTgXzGUMgQ2SXDPB61z4eisng2o13rQpVwg",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1OSIsIm5hbWUiOiJ0ZXN0ZXI1OSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.vLc5iATgnY74jvnDLrbv71Qm2mMDF3nFfpD0rPWVwYM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2MCIsIm5hbWUiOiJ0ZXN0ZXI2MCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.k1wQyCEoBxwMei_e0vnwga8Fa55UyNlraX0IapAyfsQ",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2MSIsIm5hbWUiOiJ0ZXN0ZXI2MSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.Lcnu5OvcW97B7KybddNRKSPXVFntqMS3ueKs0BwHgRc",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2MiIsIm5hbWUiOiJ0ZXN0ZXI2MiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.b2uhbDpYbjePR5ib9JA8a6f0ReMs_us8LzwGtLzO3Vw",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2MyIsIm5hbWUiOiJ0ZXN0ZXI2MyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.HDvCB4kMRNv6dFwQjSNKN-Uok4Rn40206CC0eAUpHjE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2NCIsIm5hbWUiOiJ0ZXN0ZXI2NCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.0kxw8xSgeZ_vy-UaZpBluAILgnGTt0ncnKBVrnmBD1U",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2NSIsIm5hbWUiOiJ0ZXN0ZXI2NSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.zvlLd7_fh1IsV4XV1K8bHcXZGm2O1VBoDVAXunDOMWE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2NiIsIm5hbWUiOiJ0ZXN0ZXI2NiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.7pNUXyUjvxRf-fxlB4US3xi6FPQSAmuXLcjvoMXqX8g",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2NyIsIm5hbWUiOiJ0ZXN0ZXI2NyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.Furi8r50z1WGz8G2tC-E3pflkOLuwnNFBk4tlaHSSSg",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2OCIsIm5hbWUiOiJ0ZXN0ZXI2OCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.p0UGyKRFo39XiPwjQcLwjt9QtQiKXJtjWwvVitBULQg",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q2OSIsIm5hbWUiOiJ0ZXN0ZXI2OSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9._qORw_JtqkS-xncGzRihx1z2TRuyr-BmZzgbDfA4EMc",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3MCIsIm5hbWUiOiJ0ZXN0ZXI3MCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.6baWF2k17T4IOBY6ADh_e8_joWHTUSTq-gPWVYJPWRA",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3MSIsIm5hbWUiOiJ0ZXN0ZXI3MSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.r10hf749cGjQ45Fu-8N_-jqNlg_trJhHHsY8gnSHWtE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3MiIsIm5hbWUiOiJ0ZXN0ZXI3MiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.1rxDJ1-tsvEZ_FtGRH-VwLui_cpCgMA7DRjBjjluRHU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3MyIsIm5hbWUiOiJ0ZXN0ZXI3MyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.dU1yDd3f6QEHvrpNMNa3nNRR9hUgIMuDGRnS6pLulhU",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3NCIsIm5hbWUiOiJ0ZXN0ZXI3NCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.wDBfcBB08e8qYvrv3ce8owjm940U53K9i_b459Kewfk",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3NSIsIm5hbWUiOiJ0ZXN0ZXI3NSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.iBS_i4n9GXQHx9CEsfi5EIre33ck6OMqD5lTJAfJSKM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3NiIsIm5hbWUiOiJ0ZXN0ZXI3NiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.ahqTY8qSMB3QoFJA2gZcWpMv6v-k3N95hWpJBpL67uk",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3NyIsIm5hbWUiOiJ0ZXN0ZXI3NyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.1TYLojGdCFs5q-JtU4JTBH8cJTgBFD8OHAe7hS6a85M",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3OCIsIm5hbWUiOiJ0ZXN0ZXI3OCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.OOKDwUxkG_BntW2b6a9f-CnphcIyzCv29Pzez98L2ts",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q3OSIsIm5hbWUiOiJ0ZXN0ZXI3OSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9._p3MIB7oL3BVFriuZs-OgJObKdbLnmaZpzYWzw95Wxw",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4MCIsIm5hbWUiOiJ0ZXN0ZXI4MCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.8fwK4ulUQxugerKzu_mVvEHepxN2Cz-qA-C8yh5lHog",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4MSIsIm5hbWUiOiJ0ZXN0ZXI4MSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.KdzD0jcn5zeVqb75HaY3WZ4c2Vcywj2ncSGGO5cX0Ww",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4MiIsIm5hbWUiOiJ0ZXN0ZXI4MiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.LlQQxUrLbcZyoLGPIkehSytNfjmve3mbFXKQh_pjgtk",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4MyIsIm5hbWUiOiJ0ZXN0ZXI4MyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.bsUHzBWAqcWlqi3s55F0Ci6LuYOBl9-w8CJuetK7h8s",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4NCIsIm5hbWUiOiJ0ZXN0ZXI4NCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.l0Jpa6Sus3GQ5TrM9SGw5SA5nVE6QQqFjOUKdM-GQ00",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4NSIsIm5hbWUiOiJ0ZXN0ZXI4NSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.eMb2Geq0EFBxUmrtBMxhG85BoSktOiMTVs67OngF5Z0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4NiIsIm5hbWUiOiJ0ZXN0ZXI4NiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.UxGg_7X7AI-JVI0r81ml9mC6ljTlM2aKxImSrzvxl64",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4NyIsIm5hbWUiOiJ0ZXN0ZXI4NyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.iwL5gae01y5ZbShUkRhRMa990AlVn3jrBc2--BA4CSA",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4OCIsIm5hbWUiOiJ0ZXN0ZXI4OCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.CP2oDpQtizIxbLnBFLhlT9zSCEhJDBJR0yVUTxDa80U",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q4OSIsIm5hbWUiOiJ0ZXN0ZXI4OSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.K9ZEhyD9tlU7CDejaP6hrY_LBTzSumWuTMbxM682wnM",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5MCIsIm5hbWUiOiJ0ZXN0ZXI5MCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.f1vAGj_c442zuQPxX21cSTCyi4Avu96HvdybFmP8XGI",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5MSIsIm5hbWUiOiJ0ZXN0ZXI5MSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.c5vCD_zi04c4YfM7uf-jFN3Pu1wkHT5ZCMtBWjgO0ts",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5MiIsIm5hbWUiOiJ0ZXN0ZXI5MiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.GUNr9QpoCaGJaQvD2YKR7z_-TTKXCitn7Z8fGMojARw",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5MyIsIm5hbWUiOiJ0ZXN0ZXI5MyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.ywNYXiMLGGSh2OriaZzEcDXb4-beaij5zwY8qoh0AXw",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5NCIsIm5hbWUiOiJ0ZXN0ZXI5NCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.cGSVwUSfdIYsnuOI7wdH7u9x2gPCDWmpbdSP17v711U",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5NSIsIm5hbWUiOiJ0ZXN0ZXI5NSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.5VdoVYTUgBJxVETJioPblUAMGvmo4octtbTiPDixUns",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5NiIsIm5hbWUiOiJ0ZXN0ZXI5NiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.J9t-1W7h1s4KyIByYpAdfgcAFthWJs1hItIQaF60als",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5NyIsIm5hbWUiOiJ0ZXN0ZXI5NyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.8ZGqvfKRLBJaxeWvnEcUfjTWDA1CBPSuykkHhM1OllY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5OCIsIm5hbWUiOiJ0ZXN0ZXI5OCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.-VSd6Zo3vWEzvU1WVJItsuOfiSYOg4EUj9uMZLLcdj0",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q5OSIsIm5hbWUiOiJ0ZXN0ZXI5OSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.6rrD62Dur_71uVj2Ym2bcoXFxOmZ6LS50OEpx3Wdlj4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxMDAiLCJuYW1lIjoidGVzdGVyMTAwIiwicm9sZSI6Im5vbmUiLCJ2ZXIiOjEsImV4cCI6MTc3MjQ0MjQyMH0.yjbqOquNpmeE5qPAz_g3zlmJVx0AkuHJg_ie01pzdrs",
]

INVALID_TOKENS = [
    ("bad_signature", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxIiwibmFtZSI6InRlc3RlcjEiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.pWXExHtU9z3RQBRAVxn8scMvVkjOLXMZdsGMCuOWN1k"),
    ("bad_signature", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyIiwibmFtZSI6InRlc3RlcjIiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.7qmmhFSX5UEV3_O1nvdbZGsoyIJgl939BHuFWFPGU3Y"),
    ("bad_signature", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzIiwibmFtZSI6InRlc3RlcjMiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.Bd-hmGn0K_oOlKTbxURl72QjBaK2UE02tnJR8B9vMfk"),
    ("bad_signature", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0IiwibmFtZSI6InRlc3RlcjQiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.1sAxfXg0bGvjfy8D3fmGSZla3TqYpadx8Bz2d3bv7EQ"),
    ("bad_signature", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1IiwibmFtZSI6InRlc3RlcjUiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyNDQyNDIwfQ.T2CBPalP6ao5n87Z6CY7a4eIi5VLKVRaR8xw0btI0do"),
    ("nonexistent_user", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Imdob3N0XzEiLCJuYW1lIjoiXHVjNzIwXHViODM5MSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.x1HsQjAqXLsIPVtVARNXjWAVvACUcaN_xj9yhCt32XE"),
    ("nonexistent_user", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Imdob3N0XzIiLCJuYW1lIjoiXHVjNzIwXHViODM5MiIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.cw0T03VmQfn80s4cIPar5Ew2qGi325O1pOFFyZzkA78"),
    ("nonexistent_user", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Imdob3N0XzMiLCJuYW1lIjoiXHVjNzIwXHViODM5MyIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.1vrDehwu4be2R1DGnq3ncpqtQdKf6oHR-6nblaCHP54"),
    ("nonexistent_user", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Imdob3N0XzQiLCJuYW1lIjoiXHVjNzIwXHViODM5NCIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.aRAZ4pELakM6o-4wsM_RjPK4kqiWUr1CQGUrGTQgUiA"),
    ("nonexistent_user", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Imdob3N0XzUiLCJuYW1lIjoiXHVjNzIwXHViODM5NSIsInJvbGUiOiJub25lIiwidmVyIjoxLCJleHAiOjE3NzI0NDI0MjB9.mDvidyq7wy6P1AEU5I2VenEz8Xp0zFKq3kbKV7NDcEg"),
    ("version_mismatch", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxIiwibmFtZSI6InRlc3RlcjEiLCJyb2xlIjoibm9uZSIsInZlciI6OTk5LCJleHAiOjE3NzI0NDI0MjB9.fct_vu72i6OI4NHlzt3GDeCZdiLMh48GEbMKqWx3TPY"),
    ("version_mismatch", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyIiwibmFtZSI6InRlc3RlcjIiLCJyb2xlIjoibm9uZSIsInZlciI6OTk5LCJleHAiOjE3NzI0NDI0MjB9.9e5GMWUzf7SE6KYJPFMGwwbRDrbbEvuEDMfnTPbKRHs"),
    ("version_mismatch", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzIiwibmFtZSI6InRlc3RlcjMiLCJyb2xlIjoibm9uZSIsInZlciI6OTk5LCJleHAiOjE3NzI0NDI0MjB9.q--E4PiGkOGOn9gzLiF3eeD-wYyulrT5mgMU45uC8EE"),
    ("version_mismatch", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0IiwibmFtZSI6InRlc3RlcjQiLCJyb2xlIjoibm9uZSIsInZlciI6OTk5LCJleHAiOjE3NzI0NDI0MjB9.ITjYUQCZWf0z0LKLiuoGkHHDJDPFOBGWr86PXFxhmCQ"),
    ("version_mismatch", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1IiwibmFtZSI6InRlc3RlcjUiLCJyb2xlIjoibm9uZSIsInZlciI6OTk5LCJleHAiOjE3NzI0NDI0MjB9.zqVmuEBbRhfDzzgR-cZTqIADDLEywA6skzWLC1OMANk"),
    ("expired_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QxIiwibmFtZSI6InRlc3RlcjEiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyMzUyNDIwfQ.yFVXGvVX4GL45tuxolpraxlxrQCRGAwCf_D_S3iCd5w"),
    ("expired_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QyIiwibmFtZSI6InRlc3RlcjIiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyMzUyNDIwfQ.tiuXscY-9RavOZ0sz6tvjxjYrKdtdreVtPt-w4kO2qI"),
    ("expired_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QzIiwibmFtZSI6InRlc3RlcjMiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyMzUyNDIwfQ.uwSYhePaPFegpnQjUBtfo2ePWO3OtsevTR0DGQuOwgQ"),
    ("expired_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q0IiwibmFtZSI6InRlc3RlcjQiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyMzUyNDIwfQ.vq7zD9NIPD_yI_f3JcP9mGl-Cw-ROFO935tNRwDwpII"),
    ("expired_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3Q1IiwibmFtZSI6InRlc3RlcjUiLCJyb2xlIjoibm9uZSIsInZlciI6MSwiZXhwIjoxNzcyMzUyNDIwfQ.QIzwA6PkPafec6Nh6_Lu_sP8jsZ3sVSa7BigpaocOPM"),
]
# ══════════════════════════════════════════════════════════════════════════════
#  [STEP 2] 타겟 설정
# ══════════════════════════════════════════════════════════════════════════════

# --local 플래그: EC2 내부에서 직접 테스트 (Node.js 프록시 경유)
# --flask 플래그: EC2 내부에서 Flask 직접 테스트 (프록시 완전 우회)
if "--flask" in sys.argv:
    TARGET_HOST = "http://127.0.0.1:5000"
elif "--local" in sys.argv:
    TARGET_HOST = "http://127.0.0.1:3000"
else:
    TARGET_HOST = "https://uos-smash.cloud"
APPLY_URL   = f"{TARGET_HOST}/api/apply"
BOARD_URL   = f"{TARGET_HOST}/api/all-boards"
CATEGORY    = "WED_REGULAR"

GET_REPEAT      = 4    # 유저당 GET 반복 횟수 (100명 x 4 = 400건)
BARRIER_TIMEOUT = 60   # 배리어 대기 최대 시간 (초) — 원격이므로 넉넉하게
REQUEST_TIMEOUT = 20   # 개별 HTTP 요청 타임아웃 (초)

# ══════════════════════════════════════════════════════════════════════════════
#  토큰 유효성 사전 검사
# ══════════════════════════════════════════════════════════════════════════════

if not VALID_TOKENS:
    print("[ERROR] VALID_TOKENS가 비어 있습니다.")
    print("        EC2에서 setup_db_and_tokens.py를 실행하고 출력을 붙여넣으세요.")
    sys.exit(1)

if not INVALID_TOKENS:
    print("[ERROR] INVALID_TOKENS가 비어 있습니다.")
    print("        EC2에서 setup_db_and_tokens.py를 실행하고 출력을 붙여넣으세요.")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
#  태스크 배열 구성
# ══════════════════════════════════════════════════════════════════════════════

# (group, method, url, headers, json_body, label)
tasks = []

# Group A: 유효 토큰으로 POST /api/apply (운동 신청) — 100건
for i, token in enumerate(VALID_TOKENS):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    tasks.append(("A", "POST", APPLY_URL, headers, {"category": CATEGORY}, f"test{i+1}"))

# Group B: 유효 토큰으로 GET /api/all-boards (게시판 조회) — 100 x 4 = 400건
for repeat in range(GET_REPEAT):
    for i, token in enumerate(VALID_TOKENS):
        headers = {"Authorization": f"Bearer {token}"}
        tasks.append(("B", "GET", BOARD_URL, headers, None, f"test{i+1}_r{repeat+1}"))

# Group C: 비정상 토큰으로 POST /api/apply (401 유도) — 20건
for label, token in INVALID_TOKENS:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    tasks.append(("C", "POST", APPLY_URL, headers, {"category": CATEGORY}, label))

TOTAL = len(tasks)

# ══════════════════════════════════════════════════════════════════════════════
#  배리어 + 워커 정의
# ══════════════════════════════════════════════════════════════════════════════

barrier          = threading.Barrier(TOTAL, timeout=BARRIER_TIMEOUT)
results          = [None] * TOTAL
fire_timestamps  = [0.0]  * TOTAL


def worker(index, group, method, url, headers, json_body, label):
    try:
        barrier.wait()
    except threading.BrokenBarrierError:
        results[index] = {
            "group": group, "status": 0, "time": 0,
            "label": label, "error": "BrokenBarrierError",
        }
        return

    fire_timestamps[index] = time.time()

    start = time.time()
    try:
        resp = http_client.request(
            method, url, headers=headers, json=json_body,
            timeout=REQUEST_TIMEOUT,
        )
        elapsed = time.time() - start
        results[index] = {
            "group": group, "status": resp.status_code,
            "time": elapsed, "label": label, "body": resp.text[:200],
        }
    except Exception as e:
        elapsed = time.time() - start
        results[index] = {
            "group": group, "status": 0,
            "time": elapsed, "label": label, "error": str(e)[:200],
        }


# ══════════════════════════════════════════════════════════════════════════════
#  발사
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("  Thundering Herd 원격 폭격 / remote_stress.py")
print("=" * 70)
print(f"\n  타겟  : {TARGET_HOST}")
print(f"  총 요청: {TOTAL}건")
print(f"  구성  : Group A(POST) {len(VALID_TOKENS)}건 | "
      f"Group B(GET) {len(VALID_TOKENS) * GET_REPEAT}건 | "
      f"Group C(401) {len(INVALID_TOKENS)}건")
print(f"\n  {TOTAL}개 스레드 생성 중...")

threads = []
for i, (group, method, url, headers, json_body, label) in enumerate(tasks):
    t = threading.Thread(
        target=worker,
        args=(i, group, method, url, headers, json_body, label),
        name=f"w{i}",
    )
    threads.append(t)

print(f"  스레드 시작 (배리어 대기 진입)...")
wall_start = time.time()

for t in threads:
    t.start()

print(f"  {TOTAL}번째 스레드 도착 대기 중 (timeout={BARRIER_TIMEOUT}s)...")

for t in threads:
    t.join(timeout=90)

wall_elapsed = time.time() - wall_start

# ══════════════════════════════════════════════════════════════════════════════
#  결과 집계
# ══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("  결과 리포트")
print(f"{'=' * 70}")

# 동시 발사 편차
valid_fires = [ts for ts in fire_timestamps if ts > 0]
if valid_fires:
    spread_ms = (max(valid_fires) - min(valid_fires)) * 1000
    print(f"\n[동시성 지표]")
    print(f"  전체 소요 시간    : {wall_elapsed:.3f}s")
    print(f"  발사 편차 (첫~끝) : {spread_ms:.1f}ms")
    print(f"  발사 완료 스레드  : {len(valid_fires)}/{TOTAL}")


def report_group(group_id, title, expected_ok=None):
    group = [r for r in results if r and r["group"] == group_id]
    if not group:
        print(f"\n[{title}] 결과 없음")
        return

    counts = {}
    for r in group:
        s = r["status"]
        counts[s] = counts.get(s, 0) + 1

    times = [r["time"] for r in group if r["time"] > 0]

    print(f"\n[{title}]  ({len(group)}건)")
    print("  상태 코드 분포:")
    for s in sorted(counts):
        note = ""
        if expected_ok and s == expected_ok:
            note = " ✓"
        elif s == 0:
            note = " (연결 실패)"
        print(f"    {s:>4}: {counts[s]}건{note}")

    if times:
        ts = sorted(times)
        n = len(ts)
        p50 = ts[n // 2]
        p95 = ts[min(int(n * 0.95), n - 1)]
        p99 = ts[min(int(n * 0.99), n - 1)]
        avg = statistics.mean(times)
        mx  = max(times)
        print(f"  응답 시간:")
        print(f"    평균 {avg:.3f}s | P50 {p50:.3f}s | P95 {p95:.3f}s | P99 {p99:.3f}s | 최대 {mx:.3f}s")

    if expected_ok:
        unexpected = [r for r in group if r["status"] != expected_ok]
        if unexpected:
            print(f"  예상 외 응답 샘플 (최대 5건):")
            for r in unexpected[:5]:
                detail = r.get("body", r.get("error", ""))[:100]
                print(f"    [{r['status']}] {r['label']}: {detail}")


report_group("A", "Group A — 유효 POST (운동 신청)", expected_ok=200)

# Group A 세부 분석
group_a = [r for r in results if r and r["group"] == "A"]
ok    = sum(1 for r in group_a if r["status"] == 200)
dup   = sum(1 for r in group_a if r["status"] == 409)
auth  = sum(1 for r in group_a if r["status"] == 401)
time_ = sum(1 for r in group_a if r["status"] == 400)
rate  = sum(1 for r in group_a if r["status"] == 429)
err   = sum(1 for r in group_a if r["status"] == 0)

print(f"  세부 분석:")
print(f"    신청 성공    (200): {ok}건")
print(f"    중복 차단    (409): {dup}건" + (" ← 유저당 1회이므로 0이어야 정상" if dup else ""))
print(f"    인증 실패    (401): {auth}건" + (" ← 0이어야 정상" if auth else ""))
print(f"    시간 오류    (400): {time_}건" + (" ← OPEN 시간대 밖에서 실행됨" if time_ else ""))
print(f"    Rate Limit   (429): {rate}건" + (" ← 유저당 1회이므로 0이어야 정상" if rate else ""))
print(f"    연결 실패      (0): {err}건")

report_group("B", "Group B — 유효 GET (게시판 조회)", expected_ok=200)
report_group("C", "Group C — 비정상 POST (401 유도)", expected_ok=401)

# Group C 유형별 분석
group_c = [r for r in results if r and r["group"] == "C"]
if group_c:
    type_map = {}
    for r in group_c:
        ft = r["label"]
        if ft not in type_map:
            type_map[ft] = {"total": 0, "ok": 0}
        type_map[ft]["total"] += 1
        if r["status"] == 401:
            type_map[ft]["ok"] += 1
    print("  유형별 401 달성률:")
    for ft, v in type_map.items():
        note = "정상" if v["ok"] == v["total"] else f"비정상 {v['total'] - v['ok']}건"
        print(f"    {ft:>20}: {v['ok']}/{v['total']}건 401 ({note})")

# 전체 요약
all_times  = [r["time"] for r in results if r and r["time"] > 0]
all_errors = [r for r in results if r and r["status"] == 0]

print(f"\n{'=' * 70}")
print("  전체 요약")
print(f"{'=' * 70}")
print(f"  총 요청: {TOTAL}건 | 완료: {sum(1 for r in results if r)}건 | 연결 실패: {len(all_errors)}건")
if all_times:
    throughput = len(all_times) / wall_elapsed
    print(f"  전체 소요: {wall_elapsed:.3f}s | 처리량: {throughput:.1f} req/s")
    print(f"  응답 시간: 평균 {statistics.mean(all_times):.3f}s | 최대 {max(all_times):.3f}s")

# 병목 진단
print(f"\n[병목 진단 힌트]")
if all_errors:
    print(f"  [!] 연결 실패 {len(all_errors)}건 -> 도메인/방화벽/서버 과부하 확인")
    for r in all_errors[:3]:
        print(f"      {r.get('error', 'unknown')[:100]}")
if time_:
    print(f"  [!] 400 오류 {time_}건 -> OPEN 시간대(토 22:00~일 10:00 KST) 밖에서 실행됨")

group_a_times = [r["time"] for r in group_a if r["time"] > 0]
group_b_times = [r["time"] for r in results if r and r["group"] == "B" and r["time"] > 0]
if group_a_times and group_b_times:
    a_avg = statistics.mean(group_a_times)
    b_avg = statistics.mean(group_b_times)
    if a_avg > b_avg * 2:
        ratio = a_avg / b_avg
        print(f"  [!] POST 평균({a_avg:.3f}s)이 GET 평균({b_avg:.3f}s)의 {ratio:.1f}배 -> board_store Lock 경합 의심")

print(f"\n{'=' * 70}")
print("  테스트 완료")
print(f"{'=' * 70}\n")
