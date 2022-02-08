# import logging
import asyncio
import os
import re
from datetime import date
from time import sleep

from scrapli.exceptions import ScrapliException, ScrapliConnectionError

from parse_config import parse_config

import yaml
from scrapli import Scrapli, AsyncScrapli

# set the name for the logfile and the logging level... thats about it for bare minimum!
# logging.basicConfig(filename="scrapli.log", level=logging.DEBUG)

REMOTE_NODE_FILE = 'remote_node.yaml'
'''
- host: 192.168.0.1
  auth_username: admin
  auth_password: pass
  auth_strict_key: false
  platform: mikrotik_routeros
  transport: ssh2
'''
SLEEP = 0.2

GET_IP = '/ip address print'
SEND_PING = '/ping %s count=5'
GET_CONFIG = '/export compact'
GET_PPP_ACTIVE = '/ppp active print'


async def get_device_session(device, conn_session=None):
    if not conn_session:
        session = AsyncScrapli(**device)
        sleep(0.25)
        try:
            print(f'Connecting to host {session.host} via {session.transport_name}:{session.port}...')
            await session.open()
            if session.isalive():
                print(f'\n{"-" * 50}\nConnected to host {session.host} via {session.transport_name}:{session.port}')
        except ScrapliException as err:
            print('!!!', err)
    else:
        session = conn_session
    return session


async def close_session(session, conn_session=None):
    if not conn_session:
        await session.close()
        print(f'Host {session.host} disconnected via {session.transport_name}:{session.port}')


async def send_command(device, command, print_result=True, conn_session=None):
    session = await get_device_session(device, conn_session)
    response = None
    if session.isalive():
        try:
            # print(session.get_prompt(), command)
            sleep(SLEEP)
            response = await session.send_command(command)
            if print_result:
                print(f'Result from host {session.host} via {session.transport_name}:{session.port}')
                print(response.result)
            print('elapsed time =', response.elapsed_time)
        finally:
            await close_session(session, conn_session)
    return response


async def send_commands(device, commands, print_result=True, conn_session=None):
    response_list = []
    session = await get_device_session(device, conn_session)
    if session.isalive():
        try:
            if type(commands) != list:
                commands = [commands]
            for command in commands:
                response = await send_command(device, command, print_result=print_result, conn_session=session)
                response_list.append(response)
        finally:
            await close_session(session)
    return response_list


async def manual_send_command(device):
    try:
        async with AsyncScrapli(**device) as session:
            sleep(0.25)
            while True:
                # session.send_command('\n', strip_prompt=False)
                # print('1')
                # prompt = session.get_prompt()
                # async for prompt in session.get_prompt():
                command = input()
                if command.lower() == ('q' or 'exit'):
                    break
                resp = await session.send_command(command, strip_prompt=False)
                # print(session.get_prompt())
                print(resp.result)
                # print(resp.genie_parse_output())
    except ScrapliException as err:
        print(err)
    except asyncio.exceptions.TimeoutError:
        print("asyncio.exceptions.TimeoutError", device["host"])


async def check_icmp(device, ip_list, conn_session=None):
    regx = r'sent=(\d)+.*received=(\d)+.*packet-loss=(\d+%)'
    result = dict()
    if not (type(ip_list) == list):
        ip_list = [ip_list]
    session = await get_device_session(device, conn_session)
    if session.isalive():
        try:
            for ip in ip_list:
                response = await send_command(device, SEND_PING % ip, conn_session=session)
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
            await close_session(session, conn_session)
    return result


async def send_command_to_devices(devices, commands):
    coroutines = [send_commands(device, commands) for device in devices]
    result = await asyncio.gather(*coroutines)
    return result


async def func_to_devices(func, devices, *ars, **kwargs):
    coroutines = [func(device=device, *ars, **kwargs) for device in devices]
    result = await asyncio.gather(*coroutines)
    return result


def main():
    with open(REMOTE_NODE_FILE, 'rt') as file_yaml:
        device_list = yaml.safe_load(file_yaml.read())

    # asyncio.run(manual_send_command(device_list[1]))
    # asyncio.run(send_command(device_list[1],GET_IP))

    # asyncio.run(send_command_to_devices(device_list, [GET_IP,GET_PPP_ACTIVE]))
    ip_list = [
        '8.8.8.8',
        '1.1.1.1',
        '2.2.2.2',
        '4.1.8.8',
        '1.1.1.1',
        '2.2.2.2',
        '4.1.8.8',
        '1.1.1.1'
    ]
    asyncio.run(func_to_devices(check_icmp, device_list, ip_list = ip_list))

    # for device in device_list:
    #     send_commands(device, [GET_PPP_ACTIVE, GET_CONFIG], print_result=False)
    #     icmp = check_icmp(device, ['8.8.8.8', '4.1.8.8'])
    #     if icmp: print(icmp)


if __name__ == "__main__":
    main()
