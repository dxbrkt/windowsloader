# ⚡ WinFlash Pro

Приложение с графическим интерфейсом для автоматического создания загрузочной USB-флешки с Windows. Разработано на Python + PyQt6.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green?style=flat-square)
![Windows](https://img.shields.io/badge/Target-Windows%2010%2F11-0078d4?style=flat-square&logo=windows)

---

## Что умеет

- Автоматически находит подключённые USB-накопители
- Скачивает Windows ISO напрямую с серверов Microsoft через [UUP Dump](https://uupdump.net)
- Поддержка Windows 10 / 11 (Home, Pro, LTSC)
- Обход проверок TPM 2.0, Secure Boot, RAM при установке Windows 11
- Записывает загрузочную флешку (diskpart + robocopy на Windows)
- Генерирует `autounattend.xml` для автоматической установки
- Пошаговый визард с красивым glassmorphism интерфейсом

## Запуск

```bash
pip install -r requirements.txt
python main.py
```

> На Windows приложение автоматически запрашивает права администратора (нужны для форматирования диска)

## Сборка в .exe

```bat
build_exe.bat
```

Готовый `WinFlashPro.exe` появится в папке `dist/`.

## Структура проекта

```
├── main.py               # Точка входа
├── app/
│   ├── window.py         # Главное окно (glassmorphism)
│   ├── pages.py          # Страницы визарда
│   └── widgets.py        # UI-компоненты
└── core/
    ├── downloader.py     # Загрузка ISO через UUP Dump
    ├── installer.py      # Запись ISO на USB
    ├── usb.py            # Определение USB-накопителей
    └── windows_db.py     # База версий Windows
```

## Как работает загрузка ISO

Приложение использует [UUP Dump](https://uupdump.net) — сервис, который скачивает файлы обновлений Windows напрямую с CDN Microsoft и собирает из них ISO с помощью встроенного `DISM.exe`. Это тот же способ, который использует [Rufus](https://rufus.ie).

1. Поиск актуальной сборки через UUP Dump API
2. Скачивание `.cab` / `.esd` файлов с `microsoft.com`
3. Сборка ISO через `DISM` + `oscdimg`

## Обход требований Windows 11

При установке Windows 11 на старые ПК (без TPM 2.0 или Secure Boot) приложение добавляет в корень флешки файл `autounattend.xml` с ключами реестра:

```xml
HKLM\SYSTEM\Setup\LabConfig\BypassTPMCheck = 1
HKLM\SYSTEM\Setup\LabConfig\BypassSecureBootCheck = 1
```

Это официально задокументированный метод, описанный в [документации Microsoft](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-setup-automation-overview).

## Зависимости

| Библиотека | Назначение |
|------------|-----------|
| `PyQt6` | GUI-фреймворк |
| `psutil` | Информация о дисках и системе |
| `requests` | HTTP-запросы к UUP Dump API |

## Источники и документация

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [UUP Dump JSON API](https://git.uupdump.net/uup-dump/json-api)
- [Microsoft — Windows Setup Automation](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-setup-automation-overview)
- [Microsoft — DISM Overview](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism---deployment-image-servicing-and-management-technical-reference-for-windows)
- [Rufus source code (MIT)](https://github.com/pbatard/rufus)
- [Ventoy — multiboot USB](https://github.com/ventoy/Ventoy)
- [psutil docs](https://psutil.readthedocs.io/)

## Лицензия

MIT
