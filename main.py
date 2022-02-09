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
SLEEP = 0.1

GET_IP = '/ip address print'
SEND_PING = '/ping %s count=5'
GET_CONFIG = '/export compact'
GET_PPP_ACTIVE = '/ppp active print'
GET_NAME = '/system identity print'

device_list = []


async def get_device_session(device, conn_session=None):
    if not conn_session:
        session = AsyncScrapli(**device)
        # await
        await asyncio.sleep(SLEEP)
        try:
            id = device_list.index(device)
            print(f'[{id}]: Connecting to host {session.host} via {session.transport_name}:{session.port}...')
            await session.open()
            if session.isalive():
                print(f'[{id}]: Connected to host {session.host} via {session.transport_name}:{session.port}')
        except Exception as err:
            print(f'[{id}]: !!! Error from host {session.host} via {session.transport_name}:{session.port}\n'
                  f'{err}')
    else:
        session = conn_session
    return session


async def close_session(device, session, conn_session=None):
    if not conn_session:
        try:
            id = device_list.index(device)
            await session.close()
            print(f'[{id}]: Host {session.host} disconnected via {session.transport_name}:{session.port}')
        except ScrapliException or OSError as err:
            print(f'[{id}]: !!! Error from host {session.host} via {session.transport_name}:{session.port}\n'
                  f'{err}')


async def send_command(device, command, print_result=True, conn_session=None):
    session = await get_device_session(device, conn_session)
    response = None
    if session.isalive():
        try:
            pr = await session.get_prompt()
            await asyncio.sleep(SLEEP)
            # print(pr)

            response = await session.send_command(command)
            id = device_list.index(device)
            print(f'{"-" * 50}\n[{id}]: Result from host {session.host} via {session.transport_name}:{session.port}')
            print(pr, response.channel_input)
            if print_result:
                print(response.result)
            else:
                print(f'--- No output. Variable "print_result" set is {print_result}')
            print('elapsed time =', response.elapsed_time)
        finally:
            await close_session(device, session, conn_session)
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
            await close_session(device, session)
    else:
        return None
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


async def check_icmp(device, ip_list, conn_session=None, print_result=True):
    regx = r'sent=(\d)+.*received=(\d)+.*packet-loss=(\d+%)'
    result = dict()
    if not (type(ip_list) == list):
        ip_list = [ip_list]
    session = await get_device_session(device, conn_session)
    if session.isalive():
        try:
            for ip in ip_list:
                response = await send_command(device, SEND_PING % ip, conn_session=session, print_result=print_result)
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
            await close_session(device, session, conn_session)
    else: return None
    return result


async def get_coroutines_for_run(coroutines):
    return await asyncio.gather(*coroutines)


def create_coroutine_list(func, devices, *ars, **kwargs):
    return [func(device=device, *ars, **kwargs) for device in devices]


def main():
    global device_list

    with open(REMOTE_NODE_FILE, 'rt') as file_yaml:
        device_list += yaml.safe_load(file_yaml.read())

    ip_list = [
        '8.8.8.8',
        # '1.1.1.1',
        # '2.2.2.2',
        # '4.1.8.8',
        # '1.1.1.1',
        # '2.2.2.2',
        '4.1.8.8',
        '1.1.1.1'
    ]

    coroutines = []
    coroutines += create_coroutine_list(check_icmp, device_list, ip_list=ip_list)
    coroutines += create_coroutine_list(send_command,device_list, command=GET_CONFIG, print_result = False)
    coroutines += (create_coroutine_list(send_commands, device_list, commands=[GET_IP, GET_NAME]))

    run_coroutines = get_coroutines_for_run(coroutines)
    asyncio.run(run_coroutines)


if __name__ == "__main__":
    main()
