# sbc-vpc

Инструментарий для Orange Pi (или другого SBC), который подключается к Delta DVP (PLC) по USB/Modbus и работает в режиме slave. Репозиторий содержит базовые утилиты для запуска модбас-слейва, который фиксирует запросы контроллера Delta и позволит в дальнейшем строить веб-интерфейс для управления.

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

### Примеры запуска

**Стандартный RTU (8N1):**

```bash
python -m sbc_vpc --port /dev/ttyUSB0 --baudrate 9600 --bytesize 8 --parity N --stopbits 1 --unit-id 1
```

**Если «тихо» — часто у Delta DVP встречается режим 7E1:**

```bash
python -m sbc_vpc --port /dev/ttyUSB0 --baudrate 9600 --bytesize 7 --parity E --stopbits 1 --unit-id 1
```

> `--unit-id` — адрес слейва Modbus (1..247), должен совпадать с тем, на который DVP шлёт запросы.

Пример systemd-юнита с настройками по умолчанию лежит в `examples/sbc-vpc.service`.

## Тесты

```bash
pip install pytest
pytest
```

## Дальнейшие шаги

- Реализовать обмен пользовательскими данными между Orange Pi и Delta DVP.
- Добавить веб-интерфейс для визуализации и управления параметрами.
