# drivingschool
- 教習所予約システムから技能教習の空き状況を自動的に取得し、Slackへ通知

## 環境・言語、使用しているサービス
- Python 3.6.0
- AWS
  - lambda
  - CloudWatch Events
- Slack API

## 主な実装箇所
- lambda_function.py
  - 本実装を記述

## 注意点
- 教習所予約システムのサーバの負荷を考慮し、CloudWatch Eventsは高頻度のアクセスとならないように配慮する
