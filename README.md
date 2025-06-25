# SyntheticEdge AI

This repository contains utilities for connecting to the Deriv WebSocket API and detecting live trading patterns. Credentials are loaded from environment variables for security:

- `DERIV_API_TOKEN` – Deriv API token
- `DERIV_APP_ID` – Deriv application ID
- `TELEGRAM_BOT_TOKEN` – Telegram bot token for alerts
- `TELEGRAM_CHAT_ID` – Telegram chat ID

## Running pattern detector

```
export DERIV_API_TOKEN=your_token
export DERIV_APP_ID=your_app_id
export TELEGRAM_BOT_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
python analytics/pattern_detector.py
```

The script connects directly to the Deriv WebSocket, processes real-time ticks, detects candlestick patterns, support/resistance breaks, and trend line breaks. Alerts are sent immediately to the Telegram chat.
