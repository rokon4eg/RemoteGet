# import logging
import os
import re
from time import sleep
from parse_config import parse_config

import yaml
from scrapli import Scrapli

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

GET_IP = '/ip address print'
CHECK_ICMP = '/ping %s count=5'
GET_CONFIG = '/export compact'
GET_PPP_ACTIVE = '/ppp active print'


def get_device_session(device, conn_session=None):
    if not conn_session:
        session = Scrapli(**device)
        try:
            print(f'\n{"-" * 50}\nConnecting to host {session.host} via {session.transport_name}:{session.port}...')
            session.open()
            if session.isalive():
                print('Connected')
        except:
            print(f'!!! Failed connect to host {session.host} via {session.transport_name}:{session.port}')
            return session
    else:
        session = conn_session
    return session


def close_session(session, conn_session=None):
    if not conn_session:
        session.close()
        print(f'Host {session.host} disconnected via {session.transport_name}:{session.port}')


def send_command(device, command, print_result=True, conn_session=None):
    session = get_device_session(device, conn_session)
    response = None
    if session.isalive():
        try:
            print(session.get_prompt(), command)
            response = session.send_command(command)
            if print_result:
                print(response.result)
            print('elapsed time =', response.elapsed_time)
        finally:
            close_session(session, conn_session)
    return response


def send_commands(device, commands, print_result=True):
    response_list = []
    session = get_device_session(device)
    if session.isalive():
        try:
            if type(commands) != list:
                commands = [commands]
            for command in commands:
                response = send_command(device, command, print_result=print_result, conn_session=session)
                response_list.append(response)
        finally:
            close_session(session)
    return response_list


def manual_send_command(device):
    with Scrapli(**device) as session:
        while True:
            command = input(session.get_prompt())
            if command.lower() == ('q' or 'exit'):
                break
            resp = session.send_command(command)
            print(resp.result)
            # print(resp.genie_parse_output())


def check_icmp(device, ip_list, conn_session=None):
    regx = r'sent=(\d)+.*received=(\d)+.*packet-loss=(\d+%)'
    result = dict()
    if not (type(ip_list) == list):
        ip_list = [ip_list]
    session = get_device_session(device, conn_session)
    if session.isalive():
        try:
            for ip in ip_list:
                response = send_command(device, CHECK_ICMP % ip, conn_session=session)
                ping_count = re.findall(regx, response.result)
                if int(ping_count[0][1]) >= 3:
                    result.update({ip: ping_count[0]})
                    print(f'ICMP {ip} is True')
                else:
                    result.update({ip: False})
                    print(f'ICMP {ip} is False')
        finally:
            close_session(session, conn_session)
    return result



def main():
    with open(REMOTE_NODE_FILE, 'rt') as file_yaml:
        device_list = yaml.safe_load(file_yaml.read())
    commands = [GET_IP,
                CHECK_ICMP % '4.1.8.8',
                CHECK_ICMP % '8.8.8.8',
                # GET_CONFIG
                ]
    for device in device_list:
        # send_command(device, GET_CONFIG, print_result=False)
        # send_commands(device, commands)
        icmp = check_icmp(device, ['1.1.1.1','8.8.8.8','4.1.8.8'])
        if icmp: print(icmp)


if __name__ == "__main__":
    main()
