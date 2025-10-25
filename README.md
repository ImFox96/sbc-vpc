# sbc-vpc

Инструментарий для Orange Pi (или другого SBC), который подключается к Delta DVP по USB/Modbus и работает в режиме slave. Репозиторий содержит базовые утилиты для запуска модбас-слейва, который фиксирует запросы контроллера Delta и позволит в дальнейшем строить веб-интерфейс для управления.

## Возможности

- Конфигурируемый запуск Modbus RTU slave через `pymodbus`.
- Логирование всех операций чтения/записи, инициированных Delta DVP.
- Простая структура, которую можно расширять для обмена пользовательскими данными и построения UI.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск сканера запросов Delta

```bash
python -m sbc_vpc --port /dev/ttyUSB0 --baudrate 9600 --unit-id 1
```

Параметры подключения (`--port`, `--baudrate`, `--parity` и т.д.) можно менять под своё оборудование. После запуска в консоли появятся логи, отражающие чтения и записи со стороны Delta DVP.

> 💡 Если по умолчанию линия «молчит», попробуйте режим `7E1`:
>
> ```bash
> python -m sbc_vpc --bytesize 7 --parity E --stopbits 1
> ```

Для продакшена полезно добавить JSON-формат логов и писать их в journald:

```bash
python -m sbc_vpc --json-logs | systemd-cat -t sbc-vpc
```

Пример `systemd`-юнита с ротацией журналов через `journald`:

```ini
[Unit]
Description=Orange Pi Modbus slave for Delta DVP
After=network-online.target

[Service]
Type=simple
User=orangepi
Group=orangepi
ExecStart=/usr/bin/python -m sbc_vpc --port /dev/ttyUSB0 --baudrate 9600 --unit-id 1 --json-logs
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sbc-vpc

[Install]
WantedBy=multi-user.target
```

Журналы будут доступны через `journalctl -u sbc-vpc.service` и автоматически ротироваться `systemd`.

## Тесты

```bash
pip install pytest
pytest
```

## Дальнейшие шаги

- Реализовать обмен пользовательскими данными между Orange Pi и Delta DVP.
- Добавить веб-интерфейс для визуализации и управления параметрами.
