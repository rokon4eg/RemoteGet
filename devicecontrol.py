import os, re, logging, asyncio, json, yaml

from datetime import date, datetime
from threading import Lock
from typing import List, Coroutine

import pandas
from scrapli.exceptions import ScrapliException
from scrapli import AsyncScrapli

import tools
from parse_config.parse_config import MikrotikConfig, GeneralParam

SLEEP = 0.1


class SingletonMeta(type):
    """
    Это потокобезопасная реализация класса Singleton.
    """

    _instances = {}

    _lock: Lock = Lock()
    """
    У нас теперь есть объект-блокировка для синхронизации потоков во время
    первого доступа к Одиночке.
    """

    def __call__(cls, *args, **kwargs):
        """
        Данная реализация не учитывает возможное изменение передаваемых
        аргументов в `__init__`.
        """
        # Теперь представьте, что программа была только-только запущена.
        # Объекта-одиночки ещё никто не создавал, поэтому несколько потоков
        # вполне могли одновременно пройти через предыдущее условие и достигнуть
        # блокировки. Самый быстрый поток поставит блокировку и двинется внутрь
        # секции, пока другие будут здесь его ожидать.
        with cls._lock:
            # Первый поток достигает этого условия и проходит внутрь, создавая
            # объект-одиночку. Как только этот поток покинет секцию и освободит
            # блокировку, следующий поток может снова установить блокировку и
            # зайти внутрь. Однако теперь экземпляр одиночки уже будет создан и
            # поток не сможет пройти через это условие, а значит новый объект не
            # будет создан.
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class Logger(metaclass=SingletonMeta):
    # instance = None
    #
    # def __new__(cls):
    #     if cls.instance is None:
    #         cls.instance = super().__new__(cls)
    #     return cls.instance

    def __init__(self):
        # logging.basicConfig(filename="devices.log",
        #                     format='%(asctime)s: %(name)s - %(levelname)s - %(message)s',
        #                     filemode='w')
        # self.root = logging.getLogger()
        self.dir = os.path.join('log', datetime.today().strftime("%Y-%m-%d %H.%M.%S"))
        if not os.path.exists(self.dir):
            os.mkdir(self.dir)
        self.log_format = '%(asctime)s: %(name)s - %(levelname)s - %(message)s'
        self.root = self.set_logger('main', 'main.log')
        self.export_compact = self.set_logger('export_compact', 'export_compact.log')
        self.output_parse = self.set_logger('output_parse', 'output_parse.log')
        self.output_icmp = self.set_logger('output_icmp', 'output_icmp.log')
        self.device_com = self.set_logger('device_com', 'device_com.log')
        self.connections = self.set_logger('connections', 'connections.log')
        self.command_put = self.set_logger('command_put', 'command_put.log')
        self.tu = self.set_logger('tu', 'tu.log')

    def set_logger(self, logger_name, file_out, log_format=''):
        if not log_format:
            log_format = self.log_format
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(os.path.join(self.dir, file_out))
        handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(handler)
        return logger


class Devices:
    config_example = dict()
    config_example['host'] = ''
    config_example['auth_username'] = ''
    config_example['auth_password'] = ''
    config_example['auth_strict_key'] = False
    config_example['platform'] = 'mikrotik_routeros'
    config_example['transport'] = 'asyncssh'
    config_example['timeout_socket'] = 30
    config_example['timeout_transport'] = 30

    def __init__(self):
        self.device_list: List[Device] = []
        self.dir_export_compact = 'export_compact'
        self.dir_tu = 'tu'
        self.dir_output_parse = 'output_parse'
        self.dir_output_icmp_ip_free = 'output_icmp_ip_free'
        self.dir_output_icmp_ip_in_tu = 'output_icmp_ip_in_tu'
        self.logger = Logger()

    def load_from_yaml(self, filename):
        """
        Заполняет device_list на основе данных в YAML файле"""
        config_yaml = []
        with open(filename, 'rt') as file_yaml:
            config_yaml += yaml.safe_load(file_yaml.read())
        for config in config_yaml:
            dev = Device(config)
            dev.ip = config['host']
            self.device_list.append(dev)
            # self.logger.root.setLevel(logging.INFO)
            self.logger.tu.info(f'load_from_yaml: ip={dev.ip}, transport={config["transport"]}')

    def load_from_excel(self, filename):
        """
        Заполняет device_list на основе данных в Excel файле
        """
        data = pandas.read_excel(filename, index_col=0)
        for node in data.iloc:
            config = self.config_example.copy()
            config['host'] = node['IP_DEVICE']
            config['auth_username'] = node['LOGIN']
            config['auth_password'] = node['PASSWORD']
            dev = Device(config.copy())
            dev.city = node['Город']
            dev.name = node['NAME_DEVICE']
            self.device_list.append(dev)
            # self.logger.root.setLevel(logging.INFO)
            self.logger.tu.info(f'load_from_excel: {dev.city} {dev.ip} ({node["NAME_DEVICE"]}) ,'
                                f' transport={config["transport"]}')

    def load_export_compact_from_files(self, dir_='', date_=''):
        """
        DONE Метод загружает конфигурацию каждого устройства из отдельного файла в выделенном каталоге dir
        """
        self.logger.root.info(f'Load "export compact" from files...')
        if not dir_:
            dir_ = self.dir_export_compact
        if date_:
            dir_ = os.path.join(dir_, date_)
        if os.path.exists(dir_):
            for dev in self.device_list:
                filename = tools.get_file_name(dev.city + '_' + dev.name, suffix=self.dir_export_compact, dir=dir_)
                if os.path.exists(filename):
                    with open(filename, 'rt') as file:
                        dev.export_compact = file.read()
                    if dev.export_compact:
                        self.logger.export_compact.info(f'device with ip:{dev.ip} load config from {filename}')
                    else:
                        self.logger.export_compact.warning(f'device with ip:{dev.ip} don''t have config')
        else:
            self.logger.export_compact.error(f'! Dir "{dir_}" does not exist.')
        self.logger.root.info(f'Load "export compact" success.')

    def save_export_compact2files(self, dir=''):
        """
        Метод сохраняет конфигурации каждого устройства в отдельный файл в выделенном каталоге dir
        """
        self.logger.root.info(f'Save "export compact" to files...')
        if not dir:
            dir = os.path.join(self.dir_export_compact, str(date.today()))
        if not os.path.exists(dir):
            os.mkdir(dir)
        for dev in self.device_list:
            if dev.export_compact:
                filename = tools.get_file_name(dev.city + '_' + dev.name, suffix=self.dir_export_compact, dir=dir)
                with open(filename, 'wt') as file:
                    file.write(dev.export_compact)
                self.logger.export_compact.info(f'device with ip:{dev.ip} save config to {filename}')
            else:
                self.logger.export_compact.warning(f'device with ip:{dev.ip} don''t have config')
        self.logger.root.info(f'Save "export compact" success.')

    def save_parse_result2files(self, dir=''):
        """
        Метод сохраняет результат парсинга конфигураций каждого устройства в отдельный файл в выделенном каталоге dir
        + file_summary
        """
        self.logger.root.info(f'Save parse config to files...')
        if not dir:
            dir = os.path.join(self.dir_output_parse, str(date.today()))
        if not os.path.exists(dir):
            os.mkdir(dir)
        summary = []
        for dev in self.device_list:
            if not (dev.mikroconfig is None):
                general_param = GeneralParam(dev.mikroconfig)
                output_msg, text_for_output_in_file = general_param.get_output_info()
                dev.result_parsing = output_msg % (dev.name, dev.ip, dev.city) + text_for_output_in_file

                if dev.result_parsing:
                    filename = tools.get_file_name(dev.city + '_' + dev.name, suffix=self.dir_output_parse, dir=dir)
                    with open(filename, 'wt') as file:
                        file.write(dev.result_parsing)
                    self.logger.output_parse.info(f'device with ip:{dev.ip} save result parse config to {filename}')
                    summary.append(dev.get_summary_parse_result())
                else:
                    self.logger.output_parse.warning(f'device with ip:{dev.ip} don''t have result parse')
        file_name = 'summary_' + str(date.today())
        file_summary = tools.get_file_name(file_name, suffix=self.dir_output_parse, dir=dir, ext='xlsx')
        ind = 0
        while os.path.exists(file_summary):
            ind += 1
            file_name_new = file_name + f'({str(ind)})'
            file_summary = tools.get_file_name(file_name_new, suffix=self.dir_output_parse, dir=dir, ext='xlsx')

        try:
            pandas.read_json(json.dumps(summary)).sort_values('City').to_excel(file_summary)
        except Exception as err:
            msg = f'! Error save file {file_summary} with parse result.\n' \
                  f'{err}'
            print(msg)
            self.logger.root.warning(msg)
        self.logger.root.info(f'Save parse config success.')

    def parse_config(self):
        self.logger.root.info(f'Parse config...')
        for dev in self.device_list:
            if dev.export_compact:
                file_tu = tools.get_file_name(dev.city, suffix=self.dir_tu, dir=self.dir_tu)
                if not os.path.exists(file_tu):
                    self.logger.tu.warning(f'! File with IP from TU {file_tu} not exists')
                    file_tu = ''
                dev.mikroconfig = MikrotikConfig(dev.export_compact, file_tu, dev.ip_ppp_active)
                # general_param = GeneralParam(dev.mikroconfig)
                #
                # output_msg, text_for_output_in_file = general_param.get_output_info()
                # dev.result_parsing = output_msg % (dev.name, dev.ip, dev.city) + text_for_output_in_file
        self.logger.root.info(f'Parse config success.')

    def save_icmp_result2files(self, type_ip_list):
        self.logger.root.info(f'Save ICMP result to files...')
        if not os.path.exists(self.dir_output_icmp_ip_free):
            os.mkdir(self.dir_output_icmp_ip_free)
        if not os.path.exists(self.dir_output_icmp_ip_in_tu):
            os.mkdir(self.dir_output_icmp_ip_in_tu)
        for device in self.device_list:
            ip_result = ''
            dir_output = ''
            if type_ip_list == 'ip_free':
                ip_result = device.icmp_ip_free_result
                dir_output = self.dir_output_icmp_ip_free
            elif type_ip_list == 'ip_in_tu':
                ip_result = device.icmp_ip_in_tu_result
                dir_output = self.dir_output_icmp_ip_in_tu
            if ip_result and dir_output:
                file_icmp = tools.get_file_name(device.city + '_' + device.name, suffix=dir_output,
                                                dir=dir_output, ext='xlsx')
                res_json = json.dumps({str(date.today()): ip_result})
                new_data = pandas.read_json(res_json)
                if os.path.exists(file_icmp):
                    old_data = pandas.read_excel(file_icmp, index_col=0)
                    data = old_data.merge(new_data, left_index=True, right_index=True, how='outer')
                else:
                    data = new_data
                try:
                    data.to_excel(file_icmp)
                except Exception as err:
                    msg = f'! Error save file {file_icmp} with icmp result.\n' \
                          f'{err}'
                    print(msg)
                    self.logger.root.warning(msg)
        self.logger.root.info(f'Save ICMP result success.')


class Device:
    count = -1

    def __new__(cls, *args, **kwargs):
        cls.count += 1
        return super().__new__(cls)

    def __init__(self, connect_param):
        self.false_icmp_list = []
        self.id = self.count
        self.enabled = False
        self.connect_param = connect_param
        self.ip = connect_param['host']
        self.name = ''
        self.city = ''
        self.result_parsing = ''
        self.icmp_ip_free_result = dict()
        self.icmp_ip_in_tu_result = dict()
        self.export_compact = ''
        self.ip_ppp_active = set()
        self.mikroconfig: MikrotikConfig = None
        self.logger = Logger()

    def get_summary_parse_result(self):
        res = dict()
        if self.mikroconfig is not None:
            res['City'] = self.city
            res['sys name'] = self.name
            res['MikroTik IP'] = self.ip
            res['Bridge empty'] = len(self.mikroconfig.br_empty)
            res['Bridge single'] = len(self.mikroconfig.br_single)
            res['int single'] = len(self.mikroconfig.int_single_dict)
            res['vlans free'] = len(self.mikroconfig.vlans_free)
            res['EOIP free'] = len(self.mikroconfig.eoip_free)
            res['IP free'] = len(self.mikroconfig.ip_free)
            res['False ICMP IP free'] = len(self.mikroconfig.icmp_false)
            res['True ICMP IP free'] = len(self.mikroconfig.icmp_true)
            res['IP in TU'] = len(self.mikroconfig.ip_in_tu)
            res['False ICMP IP in TU'] = len(self.mikroconfig.icmp_ip_in_tu_false)
            res['True ICMP IP in TU'] = len(self.mikroconfig.icmp_ip_in_tu_true)
        return res


class DeviceManagement:
    """
    Класс отвечает за асинхронное выполнение команд на одном устройстве
    """

    def __init__(self, device: Device):
        self.device = device
        self.session = None  # self.open_session()

    async def open_session(self):
        try:
            if self.session is None:
                self.session = AsyncScrapli(**self.device.connect_param)
            elif not self.session.isalive():
                self.session = AsyncScrapli(**self.device.connect_param)
        except AttributeError:
            self.session = AsyncScrapli(**self.device.connect_param)
        await asyncio.sleep(SLEEP)
        try:
            id = self.device.id
            msg = f'[{id}]: Connecting to {self.session.host} via {self.session.transport_name}:{self.session.port}...'
            print(msg)
            self.device.logger.connections.info(msg)
            await self.session.open()
            if self.session.isalive():
                msg = f'[{id}]: Connected to {self.session.host} via {self.session.transport_name}:{self.session.port}'
                print(msg)
                self.device.logger.connections.info(msg)
        except Exception as err:
            msg = f'[{id}]: ! Open error {self.session.host} via {self.session.transport_name}:{self.session.port}' \
                  f'\n{err}'
            print(msg)
            self.device.logger.connections.warning(msg)
        return self.session

    async def close_session(self):
        try:
            id = self.device.id
            await self.session.close()
            msg = f'[{id}]: Host {self.session.host} disconnected' \
                  f' via {self.session.transport_name}:{self.session.port}'
            print(msg)
            self.device.logger.connections.info(msg)
        except ScrapliException or OSError as err:
            msg = f'[{id}]: ! Close error from {self.session.host}' \
                  f' via {self.session.transport_name}:{self.session.port}\n' \
                  f'{err}'
            print(msg)
            self.device.logger.connections.warning(msg)
        return None

    async def send_command(self, command, print_result=True, is_need_open=True):
        if is_need_open:
            self.session = await self.open_session()
        response = None
        if self.session.isalive():
            try:
                pr = await self.session.get_prompt()
                await asyncio.sleep(SLEEP)
                response = await self.session.send_command(command)
                id = self.device.id
                msg = f'{"-" * 50}\n[{id}]: Result from {self.session.host}' \
                      f' via {self.session.transport_name}:{self.session.port}'
                print(msg)
                self.device.logger.connections.info(msg)
                print(pr, response.channel_input)
                self.device.logger.connections.info(pr + ' ' + response.channel_input)
                if print_result:
                    print(response.result)
                    self.device.logger.connections.info(response.result)
                else:
                    # msg = f'--- No output. Variable "print_result" set is {print_result}'
                    # print(msg)
                    self.device.logger.connections.info(msg)
                msg = 'elapsed time = ' + str(response.elapsed_time)
                print(msg)
                self.device.logger.connections.info(msg)
            except ScrapliException as err:
                msg = f'[{id}]: ! Send command {command} error on {self.session.host}' \
                      f' via {self.session.transport_name}:{self.session.port}\n' \
                      f'{err}'
                print(msg)
                self.device.logger.connections.error(msg)
            finally:
                if is_need_open:
                    await self.close_session()
        return response

    async def send_commands(self, commands, print_result=True):
        response_list = []
        self.session = await self.open_session()
        if self.session.isalive():
            try:
                if type(commands) != list:
                    commands = [commands]
                for command in commands:
                    response = await self.send_command(command, print_result=print_result, is_need_open=False)
                    response_list.append(response)
            finally:
                await self.close_session()
        else:
            return None
        return response_list


class CommandRunner_Get(DeviceManagement):
    """
    Класс реализует расширенное выполнение команд чтения на одном устройстве
    """
    GET_IP = '/ip address print'
    SEND_PING = '/ping %s count=5'
    GET_CONFIG = '/export compact'
    GET_PPP_ACTIVE = '/ppp active pr detail'
    GET_NAME = '/system identity print'

    def __init__(self, device):
        super().__init__(device)
        self.logger = Logger()

    async def check_icmp(self, ip_list, type_ip_list, print_result=True, check_enabled=False):
        """type_ip_list = [ 'ip_free' | 'ip_in_tu' ]"""
        if (not check_enabled) or self.device.enabled:
            regx = r'sent=(\d)+.*received=(\d)+.*packet-loss=(\d+%)'
            result = dict()
            count = 0
            true_icmp = set()
            false_icmp = set()
            if not (type(ip_list) == list or type(ip_list) == set):
                ip_list = [ip_list]
            try:
                await self.open_session()
                if self.session.isalive():
                    for ip in ip_list:
                        count += 1
                        msg = f'Check {count}/{len(ip_list)} ICMP from {self.device.ip} to host {ip} - %s'
                        response = await self.send_command(self.SEND_PING % ip, print_result=print_result,
                                                           is_need_open=False)
                        ping_count = re.findall(regx, response.result)
                        # TODO IndexError: list index out of range
                        try:
                            if int(ping_count[0][1]) >= 3:
                                date.today()
                                result.update({ip: 'Успешно {1} из {0}. Потерь - {2}'.format(*ping_count[0])})
                                true_icmp.add(ip)
                                print(msg % 'TRUE')
                                self.logger.output_icmp.info(msg % 'TRUE')
                            else:
                                result.update({ip: 'FALSE'})
                                false_icmp.add(ip)
                                self.device.false_icmp_list.append(ip)
                                print(msg % 'FALSE')
                                self.logger.output_icmp.info(msg % 'FALSE')
                        except Exception as err:
                            msg = msg % 'Error' + str(ping_count)
                            self.logger.output_icmp.error(msg)
                            self.logger.root.error(msg)
                            print(msg)
            finally:
                message = f'Check ICMP {type_ip_list} for {len(ip_list)} host from {self.device.ip} ({self.device.name}) complete!' \
                          f'\n ICMP is True - {len(true_icmp)}. ICMP is False - {len(false_icmp)}.'
                print(message)
                self.logger.root.info(message)
                await self.close_session()
            if type_ip_list == 'ip_free':
                self.device.icmp_ip_free_result.update(result)
                self.device.mikroconfig.icmp_false.update(false_icmp)
                self.device.mikroconfig.icmp_true.update(true_icmp)
            elif type_ip_list == 'ip_in_tu':
                self.device.icmp_ip_in_tu_result.update(result)
                self.device.mikroconfig.icmp_ip_in_tu_false.update(false_icmp)
                self.device.mikroconfig.icmp_ip_in_tu_true.update(true_icmp)

    async def get_config(self, print_result=False, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            response = await self.send_command(self.GET_CONFIG, print_result=print_result)
            if not (response is None):
                self.device.export_compact = response.result
                self.logger.device_com.info(f'Host with IP {self.device.ip} ({self.device.name}) return config')
            else:
                self.logger.device_com.warning(f'Host with IP {self.device.ip} ({self.device.name})'
                                               f' don`t return config')

    async def get_ppp_active(self, print_result=False, check_enabled=False):
        regx = r'address=((?:\d+\.){3}\d+)'
        if (not check_enabled) or self.device.enabled:
            response = await self.send_command(self.GET_PPP_ACTIVE, print_result=print_result)
            if not (response is None):
                res = re.findall(regx, response.result)
                self.device.ip_ppp_active = set(res)
                self.logger.device_com.info(f'Host with IP {self.device.ip} ({self.device.name})'
                                            f' return ppp active')
            else:
                self.logger.device_com.warning(f'Host with IP {self.device.ip} ({self.device.name})'
                                               f' don`t return ppp active')

    async def get_sysname(self):
        """
        Метод проверяет каждое устройство из device_list на доступность
        и устанавливает признак в self.device_list[i].enabled
        + заполняет name
        """
        response = await self.send_command(self.GET_NAME)
        if not (response is None):
            self.device.enabled = True
            self.device.name = response.result.strip().lstrip('name:').strip()
            self.logger.device_com.info(f'Host with IP {self.device.ip} return sysname - {self.device.name}')
        else:
            self.device.enabled = False
            self.logger.device_com.warning(f'Host with IP {self.device.ip} ({self.device.name}) not response!')

    async def get_any_commands(self, commands, print_result=True):
        return await self.send_commands(commands, print_result)

    # async def manual_send_command(device):
    #     try:
    #         async with AsyncScrapli(**device) as session:
    #             sleep(0.25)
    #             while True:
    #                 # session.send_command('\n', strip_prompt=False)
    #                 # print('1')
    #                 # prompt = session.get_prompt()
    #                 # async for prompt in session.get_prompt():
    #                 command = input()
    #                 if command.lower() == ('q' or 'exit'):
    #                     break
    #                 resp = await session.send_command(command, strip_prompt=False)
    #                 # print(session.get_prompt())
    #                 print(resp.result)
    #                 # print(resp.genie_parse_output())
    #     except ScrapliException as err:
    #         print(err)
    #     except asyncio.exceptions.TimeoutError:
    #         print("asyncio.exceptions.TimeoutError", device["host"])


class CommandRunner_Put(DeviceManagement):
    """
    Класс реализует выполнение команд записи на одном устройстве
    """
    PUT_DISABLE_INTERFACE_BY_NAME = '/interface {0} disable [find where name="{1}"]'  # {0} = [bridge|vlan|eoip]
    PUT_ENABLE_INTERFACE_BY_NAME = '/interface {0} enable [find where name="{1}"]'  # {0} = [bridge|vlan|eoip]
    PRINT_INTERFACE_BY_NAME = '/interface {0} print where name="{1}"'  # {0} = [bridge|vlan|eoip]

    PUT_DISABLE_EOIP_BY_REMOTE_IP = '/interface eoip disable [find where remote-address={0}]'
    PUT_ENABLE_EOIP_BY_REMOTE_IP = '/interface eoip enable [find where remote-address={0}]'

    def __init__(self, device):
        super().__init__(device)
        self.logger = Logger()

    async def set_status_interfaces(self, action, print_result):
        if self.device.mikroconfig:
            bridges = self.device.mikroconfig.br_empty | self.device.mikroconfig.br_single
            await self.set_status_interfaces_by_name(action, 'bridge', bridges, print_result)  # set_status bridge empty and single

            eoip_single = [int for int, type in self.device.mikroconfig.int_single_dict.items() if type == 'eoip']
            await self.set_status_interfaces_by_name(action, 'eoip', eoip_single, print_result)  # set_status eoip single

            vlan_single = [int for int, type in self.device.mikroconfig.int_single_dict.items() if type == 'vlan']
            await self.set_status_interfaces_by_name(action, 'vlan', vlan_single, print_result)  # set_status vlan single

            eoips = self.device.mikroconfig.eoip_free
            await self.set_status_interfaces_by_name(action, 'eoip', eoips, print_result)  # set_status eoip free

            vlans = self.device.mikroconfig.vlans_free
            await self.set_status_interfaces_by_name(action, 'vlan', vlans, print_result)  # set_status vlan free

    async def set_status_interfaces_by_name(self, action, type_int, int_list, print_result=True, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            if type(int_list) is set:
                int_list = list(int_list)
            set_status_command = ''
            if action == 'disable':
                set_status_command = self.PUT_DISABLE_INTERFACE_BY_NAME
            elif action == 'enable':
                set_status_command = self.PUT_ENABLE_INTERFACE_BY_NAME
            elif action == 'print':
                set_status_command = self.PRINT_INTERFACE_BY_NAME
            if set_status_command:
                count = 0
                try:
                    await self.open_session()
                    if self.session.isalive():
                        for int in int_list:
                            count += 1
                            msg = f'{count}/{len(int_list)} {action}_interfaces_by_name in {self.device.city}: ' \
                                  f'{self.device.ip}({self.device.name}) ' \
                                  f'{set_status_command.format(type_int, int)}'
                            self.logger.command_put.info(msg)
                            response = await self.send_command(set_status_command.format(type_int, int),
                                                               print_result=print_result,
                                                               is_need_open=False)
                            # if print_result:
                            #     self.logger.command_put.info(response)
                finally:
                    msg = f'Сomplete {action}_interfaces_by_name in {self.device.city}: ' \
                          f'{self.device.ip}({self.device.name}) for {len(int_list)} interfaces.'
                    print(msg)
                    self.logger.command_put.info(msg)
                    await self.close_session()
                    # DONE отправка команды на ЦМ - set_status_command
        # await asyncio.sleep(SLEEP)

    async def disable_eoip_by_remote_ip(self, ip_list):
        if type(ip_list) is set:
            ip_list = list(ip_list)
        for ip in ip_list:
            self.logger.command_put.info(f'disable_eoip_by_remote_ip: - {ip}')
        await asyncio.sleep(SLEEP)

    async def enable_eoip_by_remote_ip(self, ip_list):
        if type(ip_list) is set:
            ip_list = list(ip_list)
        for ip in ip_list:
            self.logger.command_put.info(f'enable_eoip_by_remote_ip: - {ip}')
        await asyncio.sleep(SLEEP)


class DevicesCommander:
    """
    Класс реализует асинхронное выполнение команд сразу на нескольких устройствах
    """

    def __init__(self, devices: Devices, coroutines: List[Coroutine] = None):
        self.devices = devices
        self._coroutines = []
        if not (coroutines is None):
            self.set_coroutines(coroutines)

    def append_coroutine(self, coroutine: Coroutine):
        self._coroutines.append(coroutine)

    def add_coroutines(self, coroutines: List[Coroutine]):
        self._coroutines += coroutines

    def set_coroutines(self, coroutines: List[Coroutine]):
        self._coroutines = coroutines

    def clear_coroutines(self):
        self._coroutines = []

    async def get_coroutines_for_run(self):
        return await asyncio.gather(*self._coroutines)

    def run(self):
        run_coroutines = self.get_coroutines_for_run()
        asyncio.run(run_coroutines)
        self.clear_coroutines()
