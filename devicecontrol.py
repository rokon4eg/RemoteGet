import asyncio
import re
from datetime import date
from typing import List, Coroutine

import yaml
from scrapli.exceptions import ScrapliException

from parse_config import parse_config

from scrapli import Scrapli, AsyncScrapli

SLEEP = 0.1

class Devices:

    def __init__(self):
        self.device_list = []
        self.dir_export_compact = 'export_compact'
        self.dir_tu = 'tu'
        self.dir_output_parse = 'output_parse'
        self.dir_output_icmp = 'output_icmp'

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
        pass

    def check_enabled(self):
        '''
        Метод проверяет каждое устройство из device_list на доступность
        и устанавливает признак в self.device_list[i].enabled
        заполняет name, ip, city
        '''
        pass

    def load_export_compactfromfiles(self, dir = ''):
        """
        Метод загружает конфигурацию каждого устройства из отдельного файла в выделенном каталоге dir
        """
        if not dir:
            dir=self.dir_export_compact
        pass

    def save_export_compact2files(self, dir=''):
        """
        Метод сохраняет конфигурации каждого устройства в отдельный файл в выделенном каталоге dir
        """
        if not dir:
            dir = self.dir_export_compact
        pass

    def get_remote_export_compact(self):
        """
        Метод получет конфигурации каждого устройства
        """
        pass

class Device:

    def __init__(self, connect_param):
        self.id = -1
        self.enabled = False
        self.connect_param = connect_param
        self.ip = ''
        self.name = ''
        self.city = ''
        self.result_parsing = ''
        self.icmp_result = dict()
        self.export_compact = ''


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
            id = 0# device_list.index(self.device)
            print(
                f'[{id}]: Connecting to host {self.session.host} via {self.session.transport_name}:{self.session.port}...')
            await self.session.open()
            if self.session.isalive():
                print(
                    f'[{id}]: Connected to host {self.session.host} via {self.session.transport_name}:{self.session.port}')
        except Exception as err:
            print(
                f'[{id}]: !!! Open error from host {self.session.host} via {self.session.transport_name}:{self.session.port}\n'
                f'{err}')
        # else:
        #     self.session = self.conn_session
        return self.session

    async def close_session(self):
        # if not self.conn_session:
        # self.session = session
        try:
            id = 0#device_list.index(self.device)
            await self.session.close()
            print(f'[{id}]: Host {self.session.host} disconnected'
                  f' via {self.session.transport_name}:{self.session.port}')
        except ScrapliException or OSError as err:
            print(f'[{id}]: !!! Close error from host {self.session.host}'
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
                id = 0#device_list.index(self.device)
                print(f'{"-" * 50}\n[{id}]: Result from host {self.session.host}'
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

    def __init__(self, device):
        super().__init__(device)
        self.GET_IP = '/ip address print'
        self.SEND_PING = '/ping %s count=5'
        self.GET_CONFIG = '/export compact'
        self.GET_PPP_ACTIVE = '/ppp active print'
        self.GET_NAME = '/system identity print'

    async def check_icmp(self, ip_list, print_result=True):
        regx = r'sent=(\d)+.*received=(\d)+.*packet-loss=(\d+%)'
        result = dict()
        if not (type(ip_list) == list):
            ip_list = [ip_list]
        try:
            await self.open_session()
            if self.session.isalive():
                for ip in ip_list:
                    response = await self.send_command(self.SEND_PING % ip, print_result=print_result,
                                                       is_need_open=False)
                    ping_count = re.findall(regx, response.result)
                    if int(ping_count[0][1]) >= 3:
                        date.today()
                        result.update({ip:
                                           {str(date.today()): ping_count[0]}
                                       })
                        print(f'ICMP {ip} is True')
                    else:
                        result.update({ip:
                                           {str(date.today()): False}})
                        print(f'ICMP {ip} is False')
        finally:
            await self.close_session()
        return result

    async def get_config(self, print_result=False):
        res = await self.send_command(self.GET_CONFIG, print_result=print_result)
        if not (res is None):
            self.device.export_compact = res.result

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
