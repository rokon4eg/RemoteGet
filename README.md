# RemoteGet

**Выполняет асинхронное выполнение команд сразу на нескольких удаленных устройствах на базе RouterOS (MikroTik).**

Список устройств для подключения подгружается из xlsx файла с обязательными столбцами: (ID,	Город,	NAME_DEVICE,	IP_DEVICE,	LOGIN, PASSWORD). 
Набор и имена полей можно изменить в методе Devices.load_from_excel() модуля devicecontrol.py

В настоящее время уже реализовано выполнение следующих команд:
1. main.devices_get_sysname(): получение системного имени, модели, версии прошивки, серийного номера, аптайма.
2. main.devices_get_config(): получение конфигурации командой "/export compact"
3. devicecontrol.Devices.save_export_compact_to_files(): сохранение конфигураций из п.2 в отдельных файлах с созданием отдельной папки для каждого нового дня
4. main.devices_get_ppp_active_and_counting(): получение активных сессий PPP и подсчет количества активных/отключенных интерфейсов

**Анализирует конфигурацию микротика на предмет наличия "разорванных" связей - мусора.** - модуль "parse_config"

За мусор принято считать:
1. "Bridge empty" - пустые бриджы без портов
2. "Bridge single"	- бриджы только с одним портом внутри
3. "int single"	- порты входящие в одиночные бриджы из п.2, на которых нет IP
4. "vlans free"	- вланы, не используемые ни в бриджах, ни в бондингах, ни в IP адресах
5. "EOIP free"	- ЕОИП туннели, не используемые ни во вланах, ни в бриджах, ни в бондингах, ни в IP адресах
6. "PPP free" - ppp secrets, не используемые для построения eoip туннелей

**Выключает и удаляет мусорные сущности из пункта выше**

**Формирует списки IP адресов, проверяя наличие IP в "Техническом учете"(ТУ) биллинга, и доступность IP по ICMP c анализируемого устройства**

Список IP формируется из RemoteIP в EOIPах и из RemoteIP в PPP secrets. IP в ТУ были предварительно выгружены из биллинга и разделены по городам на файлы, например: "\tu\Хабаровск_tu.txt". Структура файла не критична, IP выбираются регулярным выражением.
Получаем два списка: "IP free" и "IP in TU". Информация о доступности по ICMP сохраняется в отдельный файл для каждого города, с накопительным эффектом для последующего анализа динамики доступности узла.  


**Сохраняет полученную информацию в сводную таблицу**
![image](https://user-images.githubusercontent.com/32700236/160656191-163df122-10f3-4eb9-b7f4-0a0642fc85da.png)


devicecontrol.Devices.save_parse_result_to_files
