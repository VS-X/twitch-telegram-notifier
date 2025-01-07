# Twitch Telegram Notifier

This script sends notifications via Telegram if certain Twitch streams goes live or changes category. It uses polling mechanism (instead of EventSub) to avoid the need to have a domain and expose it to public.

### Requirements
   * You need to create a new Twitch app in the developer dashboard
   * You need to create a bot in Telegram
   * Docker & Docker Compose (optional)

## Getting started

1. Clone the repo
2. Copy `config.ini.template` to `config.ini`
3. Fill in the information in the config file
4. Run `docker compose up` or install python dependencies and run the `twitch.py`

