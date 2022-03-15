import os, re, logging, asyncio, json, yaml

from datetime import date, datetime
import time
from threading import Lock
from typing import List, Coroutine

import pandas
from numpy import where
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
        self.terminal_output = self.set_logger('terminal_output', 'terminal_output.log')
        self.command_put = self.set_logger('command_put', 'command_put.log')
        self.error = self.set_logger('error', 'error.log')
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
    config_example['timeout_socket'] = 50
    config_example['timeout_transport'] = 50

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
        data = pandas.read_excel(filename)
        for node in data.iloc:
            if ('run' not in node) or (str(node['run']).lower() != 'false'):
                config = self.config_example.copy()
                config['host'] = node['IP_DEVICE']
                config['auth_username'] = node['LOGIN']
                config['auth_password'] = node['PASSWORD']
                dev = Device(connect_param=config.copy(),
                             city=node['Город'],
                             name=node['NAME_DEVICE'],
                             id=str(node['ID']))
                self.device_list.append(dev)
                # self.logger.root.setLevel(logging.INFO)
                self.logger.tu.info(f'load_from_excel: {dev.city} {dev.ip} ({node["NAME_DEVICE"]}) ,'
                                    f' transport={config["transport"]}')

    def load_export_compact_from_files(self, dir_='', date_=''):
        """
        DONE Метод загружает конфигурацию каждого устройства из отдельного файла в выделенном каталоге dir
        """
        self.logger.root.info(f'Load "export compact" from files...')
        print(time.strftime("%H:%M:%S"), 'Load "export compact" from files...')
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
                    self.logger.export_compact.warning(f'Could not load config from "{filename}". File does not exist.')
        else:
            self.logger.error.error(f'! Dir "{dir_}" does not exist. Call method: "load_export_compact_from_files"')
        self.logger.root.info(f'Load "export compact" success.')
        print(time.strftime("%H:%M:%S"), 'Load "export compact" success.')

    def save_export_compact_to_files(self, dir_=''):
        """
        Метод сохраняет конфигурации каждого устройства в отдельный файл в выделенном каталоге dir
        """
        self.logger.root.info(f'Save "export compact" to files...')
        print(time.strftime("%H:%M:%S"), 'Save "export compact" to files...')
        if not dir_:
            dir_ = os.path.join(self.dir_export_compact, str(date.today()))
        if not os.path.exists(dir_):
            os.mkdir(dir_)
        for dev in self.device_list:
            if dev.export_compact:
                filename = tools.get_file_name(dev.city + '_' + dev.name, suffix=self.dir_export_compact, dir=dir_)
                with open(filename, 'wt') as file:
                    file.write(dev.export_compact)
                self.logger.export_compact.info(f'device with ip:{dev.ip} save config to {filename}')
            else:
                self.logger.export_compact.warning(f'device with ip:{dev.ip} don''t have config')
        self.logger.root.info(f'Save "export compact" success.')
        print(time.strftime("%H:%M:%S"), 'Save "export compact" success.')

    def save_parse_result_to_files(self, dir_=''):
        """
        Метод сохраняет результат парсинга конфигураций каждого устройства в отдельный файл в выделенном каталоге dir
        + file_summary
        """
        self.logger.root.info(f'Save parse config to files...')
        print(time.strftime("%H:%M:%S"), 'Save parse config to files...')
        if not dir_:
            dir_ = os.path.join(self.dir_output_parse, str(date.today()))
        if not os.path.exists(dir_):
            os.mkdir(dir_)
        summary = []
        for dev in self.device_list:
            if dev.mikroconfig is not None:
                general_param = GeneralParam(dev.mikroconfig)
                output_msg, text_for_output_in_file = general_param.get_output_info()
                dev.result_parsing = output_msg % (dev.name, dev.ip, dev.city) + text_for_output_in_file
                if dev.result_parsing:
                    filename = tools.get_file_name(dev.city + '_' + dev.name, suffix=self.dir_output_parse, dir=dir_)
                    with open(filename, 'wt') as file:
                        file.write(dev.result_parsing)
                    self.logger.output_parse.info(f'device with ip:{dev.ip} save result parse config to {filename}')
                    summary.append(dev.get_summary_parse_result())
                else:
                    self.logger.output_parse.warning(f'device with ip:{dev.ip} don''t have result parse')
            else:
                summary.append(dev.get_summary_parse_result())
        file_name = 'summary_' + str(date.today())
        file_summary = tools.get_file_name(file_name, suffix=self.dir_output_parse, dir=dir_, ext='xlsx')
        ind = 0
        while os.path.exists(file_summary):
            ind += 1
            file_name_new = file_name + f'({str(ind)})'
            file_summary = tools.get_file_name(file_name_new, suffix=self.dir_output_parse, dir=dir_, ext='xlsx')
        try:
            summary_json = json.dumps(summary)
            summary_data_frame = pandas.read_json(summary_json)
            summary_data_frame.to_excel(file_summary, index=0)
            # pandas.read_json(json.dumps(summary)).sort_values('City').to_excel(file_summary)
        except Exception as err:
            msg = f'! Error save file summary {file_summary} with parse result: {err}'
            print(msg)
            self.logger.error.error(msg)
        self.logger.root.info(f'Save parse config success.')
        print(time.strftime("%H:%M:%S"), 'Save parse config success.')

    def parse_config(self):
        self.logger.root.info(f'Parse config...')
        print(time.strftime("%H:%M:%S"), 'Parse config...')
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
        print(time.strftime("%H:%M:%S"), 'Parse config success.')

    def save_icmp_result_to_files(self, type_ip_list):
        self.logger.root.info(f'Save ICMP {type_ip_list} result to files...')
        print(time.strftime("%H:%M:%S"), f'Save ICMP {type_ip_list} result to files...')
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
                    print(time.strftime("%H:%M:%S"), f'save file {file_icmp}')
                except Exception as err:
                    msg = f'! Error save file {file_icmp} with icmp result. Call method: "save_icmp_result2files"\n' \
                          f'{err}'
                    print(msg)
                    self.logger.error.error(msg)
        self.logger.root.info(f'Save ICMP result success.')
        print(time.strftime("%H:%M:%S"), f'Save ICMP {type_ip_list} result success.')


class Device:
    count = -1

    # def __new__(cls, *args, **kwargs):
    #     cls.count += 1
    #     return super().__new__(cls)

    def __init__(self, connect_param, city, name, id):
        self.connect_error = ''
        self.connect_param = connect_param
        self.city = city
        self.name = name
        self.id = id
        self.false_icmp_list = []
        self.enabled = False
        self.ip = connect_param['host']
        self.result_parsing = ''
        self.icmp_ip_free_result = dict()
        self.icmp_ip_in_tu_result = dict()
        self.export_compact = ''
        self.ip_ppp_active = set()
        self.mikroconfig: MikrotikConfig = None
        self.count_interface = -1
        self.count_interface_active = -1
        self.count_interface_disabled = -1
        self.count_ppp_active = -1
        self.logger = Logger()

    def get_summary_parse_result(self):
        res = dict()
        res['ID'] = self.id
        res['City'] = self.city
        res['sys name'] = self.name
        res['MikroTik IP'] = self.ip
        res['Сonnected'] = self.connect_error
        if self.mikroconfig is not None:
            res['Bridge\nempty'] = len(self.mikroconfig.br_empty)
            res['Bridge\nsingle'] = len(self.mikroconfig.br_single)
            res['int\nsingle'] = len(self.mikroconfig.int_single_dict)
            res['vlans\nfree'] = len(self.mikroconfig.vlans_free)
            res['EOIP\nfree'] = len(self.mikroconfig.eoip_free)
            res['PPP\nfree'] = len(self.mikroconfig.ip_ppp_free)
            # res['Vlans\nunknow'] = len(self.mikroconfig.int_from_vlans_unknow)
            res['IP\nfree'] = len(self.mikroconfig.ip_free)
            res['False ICMP\nIP free'] = len(self.mikroconfig.icmp_false)
            res['True ICMP\nIP free'] = len(self.mikroconfig.icmp_true)
            res['IP\nin TU'] = len(self.mikroconfig.ip_in_tu)
            res['False ICMP\nIP in TU'] = len(self.mikroconfig.icmp_ip_in_tu_false)
            res['True ICMP\nIP in TU'] = len(self.mikroconfig.icmp_ip_in_tu_true)
            res['int\ncount'] = self.count_interface
            res['int\nactive'] = self.count_interface_active
            res['int\ndisabled'] = self.count_interface_disabled
            res['PPP\nactive'] = self.count_ppp_active
        return res


class DeviceManagement:
    """
    Класс отвечает за асинхронное выполнение команд на одном устройстве
    """

    def __init__(self, device: Device):
        self.device = device
        self.session = None  # self.open_session()

    async def open_session(self, get_error=False):
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
            # msg = f'[{id}]: Connecting to {self.session.host} via {self.session.transport_name}:{self.session.port}...'
            # print(msg)
            # self.device.logger.terminal_output.info(msg)
            await self.session.open()
            # if self.session.isalive():
            #     msg = f'[{id}]: Connected to {self.device.city}({self.session.host})'
            #           # f'via {self.session.transport_name}:{self.session.port}'
            #     print(msg)
            #     self.device.logger.terminal_output.info(msg)
        except Exception as err:
            msg = f'[{id}]: ! Open session error {self.device.city} {self.session.host}- {err}'
            # f'via {self.session.transport_name}:{self.session.port}: {err}'
            print(msg)
            if get_error:
                self.device.connect_error = str(err)
            self.device.logger.terminal_output.warning(msg)
            self.device.logger.error.error(msg)
        return self.session

    async def close_session(self):
        try:
            id = self.device.id
            await self.session.close()
            # msg = f'[{id}]: Host {self.session.host} disconnected'
            #       # f' via {self.session.transport_name}:{self.session.port}'
            # print(msg)
            # self.device.logger.terminal_output.info(msg)
        except ScrapliException or OSError as err:
            msg = f'[{id}]: ! Close error from {self.session.host}- {err}'
            # f' via {self.session.transport_name}:{self.session.port}'
            print(msg)
            self.device.logger.terminal_output.warning(msg)
            self.device.logger.error.error(msg)
        return None

    async def send_command(self, command, print_result=True, is_need_open=True, timeout=None, get_error=False):
        if is_need_open:
            self.session = await self.open_session(get_error=True)
        response = None
        if self.session.isalive():
            try:
                id = self.device.id
                pr = await self.session.get_prompt()
                await asyncio.sleep(SLEEP)
                if timeout:
                    response = await self.session.send_command(command, timeout_ops=timeout)
                else:
                    response = await self.session.send_command(command)
                # f' via {self.session.transport_name}:{self.session.port}'
                if print_result:
                    msg = f'{"-" * 50}\n[{id}]: Result from {self.session.host}:'
                    print(msg)
                    self.device.logger.terminal_output.info(msg)
                    print(pr, response.channel_input)
                    self.device.logger.terminal_output.info(pr + ' ' + response.channel_input)

                    msg = str(response.result).encode().decode('ascii', 'ignore')
                    print(msg)
                    self.device.logger.terminal_output.info(msg)

                    msg = 'elapsed time = ' + str(response.elapsed_time)
                    print(msg)
                    self.device.logger.terminal_output.info(msg)
                # else:
                    # msg = f'--- No output. Variable "print_result" set is {print_result}'
                    # print(msg)
                    # self.device.logger.terminal_output.info(msg)
                    # msg = 'elapsed time = ' + str(response.elapsed_time)
                    # print(msg)
                    # self.device.logger.terminal_output.info(msg)
            except Exception as err:
                msg = f'[{id}]: !Error send command "{command}" on {self.device.city} {self.session.host}- {err}'
                # f' via {self.session.transport_name}:{self.session.port} Call method: "send_command"\n' \
                # f'{err}'
                print(msg)
                self.device.logger.error.error(msg)
                if get_error:
                    response = err
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
                # response_list = await self.session.send_commands(commands,strip_prompt=True)
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
    TIMEOUT_GET_CONFIG = 120
    GET_PPP_ACTIVE = '/ppp active pr detail'
    GET_NAME = '/system identity print'

    GET_COUNT_INTERFACE = '/interface print count-only'
    GET_COUNT_INTERFACE_ACTIVE = '/interface print count-only where running'
    GET_COUNT_INTERFACE_DISABLED = '/interface print count-only where disabled'
    GET_COUNT_PPP_ACTIVE = '/ppp active print count-only'

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
                        # TODO IndexError: list index out of range
                        try:
                            ping_count = re.findall(regx, response.result)
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
                            msg = msg % 'Error' + str(ping_count) + 'Call method: "check_icmp"'
                            self.logger.output_icmp.error(msg)
                            self.logger.error.error(msg)
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
            now = time.time()
            response = await self.send_command(self.GET_CONFIG,
                                               print_result=print_result,
                                               timeout=self.TIMEOUT_GET_CONFIG)
            if response is not None:
                self.device.export_compact = response.result
                msg = f'Host with IP {self.device.ip} {self.device.city} ({self.device.name}) ' \
                      f'return config. ' \
                      f'Elapsed {"%.3s" % (time.time() - now)} seconds.'

                self.logger.device_com.info(msg)
                print(time.strftime("%H:%M:%S"), msg)
            else:
                msg = f'Error from host with IP {self.device.ip} {self.device.city} ({self.device.name}) ' \
                      f'don`t return config. ' \
                      f'Elapsed {"%.3s" % (time.time() - now)} seconds.'
                self.logger.device_com.warning(msg)
                print(time.strftime("%H:%M:%S"), msg)

    async def get_ppp_active(self, print_result=False, check_enabled=False):
        regx = r'address=((?:\d+\.){3}\d+)'
        if (not check_enabled) or self.device.enabled:
            response = await self.send_command(self.GET_PPP_ACTIVE, print_result=print_result)
            if response is not None:
                res = re.findall(regx, response.result)
                self.device.ip_ppp_active = set(res)
                self.logger.device_com.info(f'Host with IP {self.device.ip} ({self.device.name})'
                                            f' return ppp active')
            else:
                self.logger.device_com.warning(f'Host with IP {self.device.ip} ({self.device.name})'
                                               f' don`t return ppp active')

    async def get_counting(self, print_result=False, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            response_list = await self.send_commands([self.GET_COUNT_INTERFACE,
                                                      self.GET_COUNT_INTERFACE_ACTIVE,
                                                      self.GET_COUNT_INTERFACE_DISABLED,
                                                      self.GET_COUNT_PPP_ACTIVE
                                                      ], print_result=print_result)
            try:
                self.device.count_interface = response_list[0].result
                self.device.count_interface_active = response_list[1].result
                self.device.count_interface_disabled = response_list[2].result
                self.device.count_ppp_active = response_list[3].result
                self.logger.device_com.info(f'Host with IP {self.device.ip} ({self.device.name}) return counting')
            except Exception as err:
                msg = f'! Error get_counting response_list = {response_list}'
                print(msg)
                self.logger.error.error(msg)

    async def get_sysname(self, print_result):
        """
        Метод проверяет каждое устройство из device_list на доступность
        и устанавливает признак в self.device_list[i].enabled
        + заполняет name
        """
        response = await self.send_command(self.GET_NAME, print_result, get_error=True)
        if response is not None:
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
    PUT_DISABLE_INTERFACE_BY_NAME = '/interface {0} disable [find where {2}="{1}"]'  # {0} = [bridge|vlan|eoip]
    PUT_ENABLE_INTERFACE_BY_NAME = '/interface {0} enable [find where {2}="{1}"]'  # {0} = [bridge|vlan|eoip]
    PRINT_INTERFACE_BY_NAME = '/interface {0} print where {2}="{1}"'  # {0} = [bridge|vlan|eoip]

    PRINT_PPP_SECRET = '/ppp secret print where remote-address ="{1}"'
    PUT_DISABLE_PPP_SECRET = '/ppp secret disable [find where remote-address ="{1}"]'
    PUT_ENABLE_PPP_SECRET = '/ppp secret enable [find where remote-address ="{1}"]'

    PRINT_BRIDGE_PORT = '/interface bridge port print where {0} ="{1}"'
    PUT_DISABLE_BRIDGE_PORT = '/interface bridge port disable [find where {0} ="{1}"]'
    PUT_ENABLE_BRIDGE_PORT = '/interface bridge port enable [find where {0} ="{1}"]'

    PUT_DISABLE_EOIP_BY_REMOTE_IP = '/interface eoip disable [find where remote-address={0}]'
    PUT_ENABLE_EOIP_BY_REMOTE_IP = '/interface eoip enable [find where remote-address={0}]'

    def __init__(self, device):
        super().__init__(device)
        self.logger = Logger()

    async def set_status_interfaces(self, action, print_result):
        if self.device.mikroconfig:
            bridges = self.device.mikroconfig.br_empty | self.device.mikroconfig.br_single
            await self.set_status_interfaces_by_name(action, 'bridge', bridges,
                                                     print_result=print_result)  # set_status bridge empty and single

            eoip_single = [int for int, type in self.device.mikroconfig.int_single_dict.items() if type == 'eoip']
            await self.set_status_interfaces_by_name(action, 'eoip', eoip_single,
                                                     print_result=print_result)  # set_status eoip single

            vlan_single = [int for int, type in self.device.mikroconfig.int_single_dict.items() if type == 'vlan']
            await self.set_status_interfaces_by_name(action, 'vlan', vlan_single,
                                                     print_result=print_result)  # set_status vlan single

            eoips = self.device.mikroconfig.eoip_free
            await self.set_status_interfaces_by_name(action, 'eoip', eoips,
                                                     print_result=print_result)  # set_status eoip free

            vlans = self.device.mikroconfig.vlans_free
            await self.set_status_interfaces_by_name(action, 'vlan', vlans,
                                                     print_result=print_result)  # set_status vlan free

            bridge_ports = self.device.mikroconfig.int_single_dict.keys()
            await self.set_status_bridge_port_by_name(action, 'interface', bridge_ports,
                                                      print_result=print_result)  # set_status bridge ports

            # """int_from_vlans_unknow = self.device.mikroconfig.int_from_vlans_unknow
            # await self.set_status_interfaces_by_name(action, 'vlan', int_from_vlans_unknow, where_by='interface',
            #                                        print_result=print_result)  # set_status int_from_vlans_unknow"""

            ip_ppp = self.device.mikroconfig.ip_ppp_free
            await self.set_status_ppp_secret_by_ip(action, 'ppp secret', ip_ppp,
                                                   print_result=print_result)  # set_status ip_ppp free

    async def set_status_interfaces_by_name(self, action, type_int, int_list, where_by=None,
                                            print_result=True, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            if not where_by:
                where_by = 'name'
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
                await self.send_command_run(action, type_int, int_list, set_status_command, print_result, where_by)
        # await asyncio.sleep(SLEEP)

    async def send_command_run(self, action, type_int, int_list, set_status_command, print_result, where_by=None):
        try:
            await self.open_session()
            count = 0
            if not where_by:
                where_by = 'name'
            if self.session.isalive():
                for int in int_list:
                    count += 1
                    msg = f'{count}/{len(int_list)} {action} {type_int} in {self.device.city}: ' \
                          f'{self.device.ip}({self.device.name}) ' \
                          f'{set_status_command.format(type_int, int, where_by)}'
                    print(msg)
                    self.logger.command_put.info(msg)
                    await self.send_command(set_status_command.format(type_int, int, where_by),
                                            print_result=print_result,
                                            is_need_open=False)
        finally:
            msg = f'Сomplete {action} {type_int} in {self.device.city}: ' \
                  f'{self.device.ip}({self.device.name}) for {len(int_list)} interfaces.'
            print(msg)
            self.logger.command_put.info(msg)
            await self.close_session()
            # DONE отправка команды на ЦМ - set_status_command

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

    async def set_status_ppp_secret_by_ip(self, action, type_int, ip_ppp, print_result=True, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            if type(ip_ppp) is set:
                ip_ppp = list(ip_ppp)
            set_status_command = ''
            if action == 'disable':
                set_status_command = self.PUT_DISABLE_PPP_SECRET
            elif action == 'enable':
                set_status_command = self.PUT_ENABLE_PPP_SECRET
            elif action == 'print':
                set_status_command = self.PRINT_PPP_SECRET
            if set_status_command:
                await self.send_command_run(action, type_int, ip_ppp, set_status_command, print_result)

    async def set_status_bridge_port_by_name(self, action, type_int, br_port_list,
                                             print_result=True, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            if type(br_port_list) is set:
                br_port_list = list(br_port_list)
            set_status_command = ''
            if action == 'disable':
                set_status_command = self.PUT_DISABLE_BRIDGE_PORT
            elif action == 'enable':
                set_status_command = self.PUT_ENABLE_BRIDGE_PORT
            elif action == 'print':
                set_status_command = self.PRINT_BRIDGE_PORT
            if set_status_command:
                await self.send_command_run(action, type_int, br_port_list, set_status_command, print_result)


class CommandRunner_Remove(DeviceManagement):
    """
    Класс реализует выполнение команд удаления на одном устройстве
    """
    GET_COUNT_DISABLED_PPP = '/ppp secret print count-only where disabled'
    GET_COUNT_DISABLED_EOIP = '/interface eoip print count-only where disabled'
    GET_COUNT_DISABLED_VLAN = '/interface vlan print count-only where disabled'
    GET_COUNT_DISABLED_BRIDGE_PORT = '/interface bridge port print count-only where disabled'
    GET_COUNT_DISABLED_BRIDGE = '/interface bridge print  count-only where disabled'

    REMOVE_DISABLED_PPP = '/ppp secret remove [find where disabled ]'
    REMOVE_DISABLED_EOIP = '/interface eoip remove [find where disabled]'
    REMOVE_DISABLED_VLAN = '/interface vlan remove [find where disabled]'
    REMOVE_DISABLED_BRIDGE_PORT = '/interface bridge port remove [find where disabled]'
    REMOVE_DISABLED_BRIDGE = '/interface bridge remove [find where disabled]'

    def __init__(self, device):
        super().__init__(device)
        self.logger = Logger()

    async def get_disabled_counting(self, print_result=False, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            response_list = await self.send_commands([self.GET_COUNT_DISABLED_PPP,
                                                      self.GET_COUNT_DISABLED_EOIP,
                                                      self.GET_COUNT_DISABLED_VLAN,
                                                      self.GET_COUNT_DISABLED_BRIDGE_PORT,
                                                      self.GET_COUNT_DISABLED_BRIDGE
                                                      ], print_result=False)
            try:
                msg = f"DISABLED_PPP = {response_list[0].result}\n" \
                      f"DISABLED_EOIP = {response_list[1].result}\n" \
                      f"DISABLED_VLAN = {response_list[2].result}\n" \
                      f"DISABLED_BRIDGE_PORT = {response_list[3].result}\n" \
                      f"DISABLED_BRIDGE = {response_list[4].result}\n" \
                      f"SUM = {sum(int(res.result) for res in response_list)}"
                if print_result:
                    print(time.strftime("%H:%M:%S"), f'Return disabled counting from '
                                                     f'{self.device.city} - {self.device.ip} - '
                                                     f'({self.device.name}):', msg, sep='\n')
                self.logger.device_com.info(f'return disabled counting from {self.device.ip} ({self.device.name}):'
                                            f'\n{msg}')
            except Exception as err:
                msg = f'! Error get_disabled_counting = {response_list}'
                print(msg)
                self.logger.error.error(msg)

    async def remove_disabled(self, print_result=False, check_enabled=False):
        if (not check_enabled) or self.device.enabled:
            response_list = await self.send_commands([self.REMOVE_DISABLED_PPP,
                                                      self.REMOVE_DISABLED_EOIP,
                                                      self.REMOVE_DISABLED_VLAN,
                                                      self.REMOVE_DISABLED_BRIDGE_PORT,
                                                      self.REMOVE_DISABLED_BRIDGE
                                                      ], print_result=print_result)
            try:
                # msg = f"DISABLED_PPP = {response_list[0].result}\n" \
                #       f"DISABLED_EOIP = {response_list[1].result}\n" \
                #       f"DISABLED_VLAN = {response_list[2].result}\n" \
                #       f"DISABLED_BRIDGE_PORT = {response_list[3].result}\n" \
                #       f"DISABLED_BRIDGE = {response_list[4].result}\n"
                # if print_result:
                print(f'remove disabled from {self.device.ip} ({self.device.name}:')
                self.logger.device_com.info(f'remove disabled from {self.device.ip} ({self.device.name})')
            except Exception as err:
                msg = f'! Error remove_disabled = {response_list}'
                print(msg)
                self.logger.error.error(msg)


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
