import logging
import os
from time import sleep

import yaml
from scrapli import Scrapli

# set the name for the logfile and the logging level... thats about it for bare minimum!
logging.basicConfig(filename="scrapli.log", level=logging.DEBUG)

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
CHECK_ICMP = '/ping %s count=3'
GET_CONFIG = '/export compact'
GET_PPP_ACTIVE = '/ppp active print'


def send_commands(device, commands):
    with Scrapli(**device) as session:
        sleep(0.125)
        if type(commands) != list:
            commands = [commands]
        for command in commands:
            resp = session.send_command(command, strip_prompt = False)
            print('\n'+'---', device['transport'], '---\t', resp.elapsed_time)
            print(session.get_prompt(), command)
            # print('\n', resp.result)


def manual_send_command(device):
    with Scrapli(**device) as session:
        while True:
            command = input(session.get_prompt())
            if command.lower() == ('q' or 'exit'):
                break
            resp = session.send_command(command)
            print(resp.result)
            # print(resp.genie_parse_output())


def main():
    with open(REMOTE_NODE_FILE, 'rt') as file_yaml:
        device_list = yaml.safe_load(file_yaml.read())
    for device in device_list:
        send_commands(device, [GET_IP, CHECK_ICMP % '8.8.8.8', GET_CONFIG])
        # send_commands(device, CHECK_ICMP % '8.8.8.8')
        # send_commands(device,GET_CONFIG)
    # manual_send_command(device_list[0])

if __name__ == "__main__":
    main()
