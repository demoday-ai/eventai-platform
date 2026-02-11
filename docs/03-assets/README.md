# Медиа-ресурсы проекта

Организованное хранилище всех медиа-файлов EventAI.

## Структура

### 📸 screenshots/
Скриншоты веб-интерфейса админки EventAI для демонстрации функционала:
- login-page.png - страница входа
- dashboard-page.png - главная панель
- sidebar-menu.png - боковое меню
- projects-page.png - управление проектами
- clustering-page.png - кластеризация по залам
- experts-page.png - управление экспертами
- schedule-page.png - генерация расписания
- guests-page.png - управление гостями
- coverage-page.png - покрытие залов экспертами
- messaging-page.png - рассылки и уведомления
- settings-page.png - настройки системы
- import-tab1-event.png - импорт данных
- landing-page.png - лендинг проекта

### 🎨 brand/
Логотипы и брендинг:
- ai-talent-hub-logo.svg - логотип AI Talent Hub
- claude-logo.{svg,png} - логотип Claude AI
- compass-01-minimal.{svg,png} - иконка бота (компас)
- botfather-branding.txt - настройки BotFather для Telegram-бота

### 📱 qr-codes/
QR-коды для быстрого доступа:
- bot-qr.png - QR-код Telegram-бота
- landing-qr.png - QR-код лендинга
- qr-screencast-bot.png - QR для видео демо бота
- qr-screencast-admin.png - QR для видео демо админки

### 👥 team/
Фотографии команды "ЯСНОПОНЯТНО":
- dima.jpg - Дмитрий Горбунов (тимлид, продукт)
- ivan.jpg - Иван Александров (разработка)
- nastya.jpg - Анастасия Гапеева (UX/UI, фронтенд)

## Использование

### В README и документации
```markdown
![Screenshot](./docs/03-assets/screenshots/dashboard-page.png)
```

### Во фронтенде
Копии используемых файлов находятся в `frontend/public/`:
- `frontend/public/team/` - фото команды (синхронизированы с docs/03-assets/team/)
- `frontend/public/logo.png` - логотип приложения

## Обновление

При добавлении новых медиа-файлов:
1. Скриншоты → screenshots/
2. Логотипы и брендинг → brand/
3. QR-коды → qr-codes/
4. Фото команды → team/ (+ синхронизировать с frontend/public/team/)

Диаграммы и схемы размещаются в `docs/02-specification/diagrams/`.
