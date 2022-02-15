import yaml
import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner

REMOTE_NODE_FILE = 'remote_node.yaml'
'''
- host: 192.168.0.1
  auth_username: admin
  auth_password: pass
  auth_strict_key: false
  platform: mikrotik_routeros
  transport: ssh2
'''

# device_list = []


def main():
    devices = dc.Devices()
    devices.load_from_yaml(REMOTE_NODE_FILE)

    # with open(REMOTE_NODE_FILE, 'rt') as file_yaml:
    #     device_list += yaml.safe_load(file_yaml.read())

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
    devcom = dc.DevicesCommander(devices)
    for device in devcom.devices.device_list:
        # comrun = dc.CommandRunner(device)
        # devcom.append_coroutine(comrun.get_any_commands([comrun.GET_IP, comrun.GET_NAME]))
        #
        # comrun = CommandRunner(device)
        # devcom.append_coroutine(comrun.get_any_commands(comrun.GET_CONFIG))

        # comrun = dc.CommandRunner(device)
        # devcom.append_coroutine(comrun.check_icmp(ip_list))

        comrun = dc.CommandRunner(device)
        devcom.append_coroutine(comrun.get_config())
        #
    devcom.run()

    devices.save_export_compact2files()

    for device in devices.device_list:
        print(device.ip)
        # print(device.export_compact)


if __name__ == "__main__":
    main()
