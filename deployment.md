# 🚀 Развертывание бота на сервер

## Вариант 1: Локальный запуск (разработка)

```bash
python pit.py
```

Подходит для:
- Тестирования
- Разработки
- Малых нагрузок

## Вариант 2: Windows Service (постоянный запуск)

### Шаг 1: Установка NSSM
```bash
choco install nssm
```

### Шаг 2: Регистрация сервиса
```bash
nssm install YouTubeBot "C:\Python\python.exe" "c:\Users\Leader\Desktop\pit.py\pit.py"
nssm set YouTubeBot AppDirectory "c:\Users\Leader\Desktop\pit.py"
```

### Шаг 3: Запуск сервиса
```bash
nssm start YouTubeBot
```

### Проверка статуса
```bash
nssm status YouTubeBot
```

### Остановка сервиса
```bash
nssm stop YouTubeBot
```

## Вариант 3: Linux Systemd (VPS)

### Шаг 1: Создание unit файла
```bash
sudo nano /etc/systemd/system/youtube-bot.service
```

### Шаг 2: Содержимое файла
```ini
[Unit]
Description=YouTube Downloader Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/pit.py
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 /home/ubuntu/pit.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Шаг 3: Активация сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable youtube-bot
sudo systemctl start youtube-bot
```

### Проверка статуса
```bash
sudo systemctl status youtube-bot
```

### Логи
```bash
sudo journalctl -u youtube-bot -f
```

## Вариант 4: Docker контейнер

### Шаг 1: Создание Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Установка FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Копирование файлов
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pit.py .
COPY .env .

# Запуск бота
CMD ["python", "pit.py"]
```

### Шаг 2: Построение образа
```bash
docker build -t youtube-bot .
```

### Шаг 3: Запуск контейнера
```bash
docker run -d --name youtube-bot youtube-bot
```

### Шаг 4: Проверка логов
```bash
docker logs youtube-bot
docker logs -f youtube-bot  # Follow mode
```

## Вариант 5: Docker Compose

### Создание docker-compose.yml
```yaml
version: '3.8'

services:
  youtube-bot:
    build: .
    container_name: youtube-downloader-bot
    restart: always
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - MAX_FILESIZE_MB=50
    volumes:
      - ./temp_downloads:/app/temp_downloads
    networks:
      - bot-network

networks:
  bot-network:
    driver: bridge
```

### Запуск
```bash
docker-compose up -d
```

## Вариант 6: Cloud сервисы

### Heroku (устаревший, но еще доступен)

```bash
# Установка Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Логин
heroku login

# Создание приложения
heroku create your-app-name

# Добавление buildpacks
heroku buildpacks:add heroku/python
heroku buildpacks:add https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest

# Установка переменных окружения
heroku config:set TELEGRAM_BOT_TOKEN=your_token

# Deploy
git push heroku main
```

### AWS EC2

1. Создайте EC2 инстанс (Ubuntu 20.04)
2. SSH подключение:
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```
3. Установка:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-venv ffmpeg
   git clone your-repo
   cd pit.py
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Запуск с systemd (см. Вариант 3)

### Google Cloud Run

```bash
# Требуется Dockerfile

# Authenticate
gcloud auth login

# Deploy
gcloud run deploy youtube-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --set-env-vars TELEGRAM_BOT_TOKEN=your_token
```

### DigitalOcean App Platform

1. Создайте DigitalOcean аккаунт
2. Загрузите репозиторий на GitHub
3. Создайте новое приложение
4. Подключите GitHub репозиторий
5. Добавьте переменные окружения
6. Deploy!

## Рекомендации по выбору

| Вариант | Цена | Сложность | Производительность | Рекомендуется |
|---------|------|-----------|-------------------|--------------|
| Локальный | Бесплатно | Низкая | Средняя | Разработка |
| Windows Service | Бесплатно | Средняя | Хорошая | Windows сервер |
| Linux Systemd | ~$5/мес | Средняя | Отличная | Linux VPS |
| Docker | Зависит | Средняя | Отличная | Масштабируемость |
| Heroku | ~$7/мес | Низкая | Хорошая | Простая выгрузка |
| AWS | Зависит | Высокая | Отличная | Высокие требования |
| Google Cloud | Зависит | Высокая | Отличная | Google экосистема |
| DigitalOcean | ~$5-20/мес | Средняя | Отличная | Баланс цены/качества |

## Мониторинг и логирование

### Системные логи

#### Linux:
```bash
tail -f /var/log/syslog | grep youtube-bot
```

#### Windows:
```bash
eventvwr.msc  # Event Viewer
```

### Логи приложения

Добавьте логирование в файл:
```python
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Мониторинг здоровья бота

```python
# Добавьте периодическую проверку
async def health_check():
    while True:
        await asyncio.sleep(3600)  # Каждый час
        # Проверка подключения к Telegram
        try:
            await bot.get_me()
            logger.info("Bot health check: OK")
        except Exception as e:
            logger.error(f"Bot health check failed: {e}")
```

## Автоматическая перезагрузка при ошибке

### Linux скрипт (bot_runner.sh)
```bash
#!/bin/bash

while true; do
    python3 pit.py
    echo "Bot crashed. Restarting in 10 seconds..."
    sleep 10
done
```

Запуск:
```bash
chmod +x bot_runner.sh
nohup ./bot_runner.sh > bot_runner.log 2>&1 &
```

## Обновление бота в продакшене

### Безопасное обновление

1. Остановите бота
2. Создайте резервную копию
3. Обновите код
4. Запустите тесты
5. Запустите бота снова

```bash
# Пример для Linux
systemctl stop youtube-bot
cp -r pit.py pit.py.backup
git pull origin main
python3 -m pytest tests/
systemctl start youtube-bot
```

## Резервные копии

### Важные файлы для резервной копии
- `pit.py` - основной код
- `.env` - конфигурация
- Логи (если нужны)

### Автоматическая резервная копия (cron)
```bash
# Каждый день в 3:00
0 3 * * * tar -czf /backups/bot_$(date +\%Y\%m\%d).tar.gz /home/ubuntu/pit.py
```

## Вопросы и ответы

**Q: Какой вариант выбрать для начинающих?**
A: Docker + Docker Compose - гарантированная совместимость и простота.

**Q: Какой вариант дешевле?**
A: Linux VPS (~$3-5/мес) с Systemd.

**Q: Как масштабировать бот?**
A: Используйте Docker Swarm или Kubernetes для множественных инстансов.

**Q: Где хранить файлы?**
A: На локальном диске сервера (не забывайте про очистку).

---

Выберите подходящий вариант развертывания и наслаждайтесь вашим YouTube Downloader Telegram Bot!
