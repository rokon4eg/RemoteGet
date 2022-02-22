import os, re, logging, asyncio, json, yaml

from datetime import date
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
        self.dir = 'log'
        if not os.path.exists(self.dir):
            os.mkdir(self.dir)
        log_format = '%(asctime)s: %(name)s - %(levelname)s - %(message)s'
        self.root = self.set_logger('main', log_format, 'main.log')
        self.export_compact = self.set_logger('export_compact', log_format, 'export_compact.log')
        self.output_parse = self.set_logger('output_parse', log_format, 'output_parse.log')
        self.output_icmp = self.set_logger('output_icmp', log_format, 'output_icmp.log')
        self.device_com = self.set_logger('device_com', log_format, 'device_com.log')
        self.tu = self.set_logger('tu', log_format, 'tu.log')

    def set_logger(self, logger_name, log_format, file_out):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(os.path.join(self.dir, file_out))
        handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(handler)
        # handler_info = self.__get_handler(file_out, log_format, logging.INFO)
        # handler_warn = self.__get_handler(file_out, log_format, logging.WARNING)
        # logger.addHandler(handler_info)
        # logger.addHandler(handler_warn)
        return logger

    # def __get_handler(self, file_out, log_format, level):
    #     handler = logging.FileHandler(os.path.join(self.dir, file_out))
    #     handler.setLevel(level)
    #     handler.setFormatter(logging.Formatter(log_format))
    #     return handler

    # def send_msg(self, logger: logging.Logger, level, msg, ):
    #     logger.setLevel(level)
    #     logger.


class Devices:
    config_example = dict()
    config_example['host'] = ''
    config_example['auth_username'] = ''
    config_example['auth_password'] = ''
    config_example['auth_strict_key'] = False
    config_example['platform'] = 'mikrotik_routeros'
    config_example['transport'] = 'asyncssh'

    def __init__(self):
        self.device_list: List[Device] = []
        self.dir_export_compact = 'export_compact'
        self.dir_tu = 'tu'
        self.dir_output_parse = 'output_parse'
        self.dir_output_icmp = 'output_icmp'
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

    def load_export_compactfromfiles(self, dir=''):
        """
        TODO Метод загружает конфигурацию каждого устройства из отдельного файла в выделенном каталоге dir
        """
        if not dir:
            dir = self.dir_export_compact
        pass

    def save_export_compact2files(self, dir=''):
        """
        Метод сохраняет конфигурации каждого устройства в отдельный файл в выделенном каталоге dir
        """
        if not dir:
            dir = self.dir_export_compact
        if not os.path.exists(dir):
            os.mkdir(dir)
        # logger = logging
        for dev in self.device_list:
            if dev.export_compact:
                # filename = dev.name + '_' + dir + '.txt'
                filename = tools.get_file_name(dev.name, dir)
                with open(filename, 'wt') as file:
                    file.write(dev.export_compact)
                # self.logger.export_compact.setLevel(logging.INFO)
                self.logger.export_compact.info(f'device with ip:{dev.ip} save config to {filename}')
            else:
                # self.logger.export_compact.setLevel(logging.WARNING)
                self.logger.export_compact.warning(f'device with ip:{dev.ip} don''t have config')

    def save_parse_result2files(self, dir=''):
        """
        Метод сохраняет результат парсинга конфигураций каждого устройства в отдельный файл в выделенном каталоге dir
        """
        if not dir:
            dir = self.dir_output_parse
        if not os.path.exists(dir):
            os.mkdir(dir)
        summary = []
        for dev in self.device_list:
            if dev.result_parsing:
                filename = tools.get_file_name(dev.name, dir)
                with open(filename, 'wt') as file:
                    file.write(dev.result_parsing)
                self.logger.output_parse.info(f'device with ip:{dev.ip} save result parse config to {filename}')
                summary.append(dev.get_summary_parse_result())
            else:
                self.logger.output_parse.warning(f'device with ip:{dev.ip} don''t have result parse')
        file_summary = tools.get_file_name('summary', dir, 'xlsx')
        pandas.read_json(json.dumps(summary)).to_excel(file_summary)

    def parse_config(self):
        for dev in self.device_list:
            if dev.export_compact:
                file_tu = tools.get_file_name(dev.city, self.dir_tu)
                if not os.path.exists(file_tu):
                    self.logger.tu.warning(f'! File with IP from TU {file_tu} not exists')
                    file_tu = ''
                dev.mikroconfig = MikrotikConfig(dev.export_compact, file_tu, dev.ip_ppp_active)
                general_param = GeneralParam(dev.mikroconfig)

                output_msg, text_for_output_in_file = general_param.get_output_info()
                # print(output_msg)
                dev.result_parsing = output_msg % (dev.name, dev.ip, dev.city) + text_for_output_in_file

    def save_icmp_result2files(self):
        if not os.path.exists(self.dir_output_icmp):
            os.mkdir(self.dir_output_icmp)
        for dev in self.device_list:
            if dev.icmp_result:
                file_icmp = tools.get_file_name(dev.name, self.dir_output_icmp, 'xlsx')
                old_data = None
                res_json = json.dumps({str(date.today()): dev.icmp_result})
                new_data = pandas.read_json(res_json)
                if os.path.exists(file_icmp):
                    old_data = pandas.read_excel(file_icmp, index_col=0)
                    data = old_data.merge(new_data, left_index=True, right_index=True, how='outer')
                else:
                    data = new_data
                data.to_excel(file_icmp)


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
        self.icmp_result = dict()
        self.export_compact = ''
        self.ip_ppp_active = set()
        self.mikroconfig: MikrotikConfig = None
        # self.logger = Logger()

    def get_summary_parse_result(self):
        res = dict()
        if not self.mikroconfig is None:
            res['City'] = self.city
            res['sys name'] = self.name
            res['MikroTik IP'] = self.ip
            res['Bridge empty'] = len(self.mikroconfig.br_empty)
            res['Bridge single'] = len(self.mikroconfig.br_single)
            res['int single'] = len(self.mikroconfig.int_single_dict)
            res['vlans free'] = len(self.mikroconfig.vlans_free)
            res['EOIP free'] = len(self.mikroconfig.eoip_free)
            res['IP free'] = len(self.mikroconfig.ip_free)
            res['False ICMP'] = len(self.false_icmp_list)
        return res


class DeviceManagement:
    """
    Класс отвечает за асинхронное выполнение команд на одном устройстве
    """

    def __init__(self, device: Device):
        self.device = device
        # self.conn_session = conn_session
        self.session = None  # self.open_session()

    async def open_session(self):
        try:
            if self.session is None:
                self.session = AsyncScrapli(**self.device.connect_param)
            elif not self.session.isalive():
                self.session = AsyncScrapli(**self.device.connect_param)
        except AttributeError:
            self.session = AsyncScrapli(**self.device.connect_param)
        # await
        await asyncio.sleep(SLEEP)
        # self.session = session
        try:
            # id = 0  # device_list.index(self.device)
            id = self.device.id
            print(
                f'[{id}]: Connecting to {self.session.host} via {self.session.transport_name}:{self.session.port}...')
            await self.session.open()
            if self.session.isalive():
                print(
                    f'[{id}]: Connected to {self.session.host} via {self.session.transport_name}:{self.session.port}')
        except Exception as err:
            print(
                f'[{id}]: ! Open error from {self.session.host} via {self.session.transport_name}:{self.session.port}\n'
                f'{err}')
        # else:
        #     self.session = self.conn_session
        return self.session

    async def close_session(self):
        # if not self.conn_session:
        # self.session = session
        try:
            # id = 0  # device_list.index(self.device)
            id = self.device.id
            await self.session.close()
            print(f'[{id}]: Host {self.session.host} disconnected'
                  f' via {self.session.transport_name}:{self.session.port}')
        except ScrapliException or OSError as err:
            print(f'[{id}]: ! Close error from {self.session.host}'
                  f' via {self.session.transport_name}:{self.session.port}\n'
                  f'{err}')
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
                # id = 0  # device_list.index(self.device)
                id = self.device.id
                print(f'{"-" * 50}\n[{id}]: Result from {self.session.host}'
                      f' via {self.session.transport_name}:{self.session.port}')
                print(pr, response.channel_input)
                if print_result:
                    print(response.result)
                else:
                    print(f'--- No output. Variable "print_result" set is {print_result}')
                print('elapsed time =', response.elapsed_time)
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


class CommandRunner(DeviceManagement):
    """
    Класс реализует расширенное выполнение команд на одном устройстве
    """
    GET_IP = '/ip address print'
    SEND_PING = '/ping %s count=5'
    GET_CONFIG = '/export compact'
    GET_PPP_ACTIVE = '/ppp active pr detail'
    GET_NAME = '/system identity print'

    def __init__(self, device):
        super().__init__(device)
        self.logger = Logger()

    async def check_icmp(self, ip_list, print_result=True, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            regx = r'sent=(\d)+.*received=(\d)+.*packet-loss=(\d+%)'
            result = dict()
            count = 0
            true_icmp = 0
            false_icmp = 0
            # false_icmp_list = []
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
                        if int(ping_count[0][1]) >= 3:
                            date.today()
                            result.update({ip: ping_count[0]})
                            true_icmp += 1
                            print(msg % 'TRUE')
                            self.logger.output_icmp.info(msg % 'TRUE')
                        else:
                            result.update({ip: False})
                            false_icmp += 1
                            self.device.false_icmp_list.append(ip)
                            print(msg % 'FALSE')
                            self.logger.output_icmp.info(msg % 'FALSE')
            finally:
                message = f'Check ICMP for {len(ip_list)} host from {self.device.ip} ({self.device.name}) complete!' \
                          f'\n ICMP is True - {true_icmp}. ICMP is False - {false_icmp}.'
                print(message)
                self.logger.root.info(message)
                await self.close_session()
            self.device.icmp_result = result

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
