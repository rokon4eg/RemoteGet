import asyncio
import re
from datetime import date
from typing import List, Coroutine
from scrapli.exceptions import ScrapliException
import yaml
from parse_config import parse_config


from scrapli import Scrapli, AsyncScrapli

REMOTE_NODE_FILE = 'remote_node.yaml'
'''
- host: 192.168.0.1
  auth_username: admin
  auth_password: pass
  auth_strict_key: false
  platform: mikrotik_routeros
  transport: ssh2
'''
SLEEP = 0.1

device_list = []


class DeviceManagement:
    """
    Класс отвечает за асинхронное выполнение команд на одном устройстве
    """

    def __init__(self, device):
        self.device = device
        # self.conn_session = conn_session
        self.session = None  # self.open_session()

    async def open_session(self):
        try:
            if self.session is None:
                self.session = AsyncScrapli(**self.device)
            elif not self.session.isalive():
                self.session = AsyncScrapli(**self.device)
        except AttributeError:
            self.session = AsyncScrapli(**self.device)
        # await
        await asyncio.sleep(SLEEP)
        # self.session = session
        try:
            id = device_list.index(self.device)
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
            id = device_list.index(self.device)
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
                id = device_list.index(self.device)
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
        return await self.send_command(self.GET_CONFIG, print_result=print_result)

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

    def __init__(self, device_list, coroutines: List[Coroutine]=None):
        self.device_list = device_list
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


def main():
    global device_list

    with open(REMOTE_NODE_FILE, 'rt') as file_yaml:
        device_list += yaml.safe_load(file_yaml.read())

    ip_list = [
        '10.76.0.1',
        # '1.1.1.1',
        # '2.2.2.2',
        # '4.1.8.8',
        # '1.1.1.1',
        # '2.2.2.2',
        '4.1.8.8',
        '1.1.1.1'
    ]
    # com_run_list=[]
    devcom = DevicesCommander(device_list)
    for device in devcom.device_list:
        comrun = CommandRunner(device)
        devcom.append_coroutine(comrun.get_any_commands([comrun.GET_IP, comrun.GET_NAME]))
        #
        # comrun = CommandRunner(device)
        # devcom.append_coroutine(comrun.get_any_commands(comrun.GET_CONFIG))

        comrun = CommandRunner(device)
        devcom.append_coroutine(comrun.check_icmp(ip_list))

        comrun = CommandRunner(device)
        devcom.append_coroutine(comrun.get_config())
        #
    devcom.run()


if __name__ == "__main__":
    main()
