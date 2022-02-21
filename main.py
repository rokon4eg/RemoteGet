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

    devcom = dc.DevicesCommander(devices)

    for device in devcom.devices.device_list:
        comrun = dc.CommandRunner(device)
        devcom.append_coroutine(comrun.get_sysname())
    devcom.run()

        # comrun = dc.CommandRunner(device)
        # devcom.append_coroutine(comrun.get_any_commands([comrun.GET_IP, comrun.GET_NAME]))
        #
        # comrun = CommandRunner(device)
        # devcom.append_coroutine(comrun.get_any_commands(comrun.GET_CONFIG))

        # comrun = dc.CommandRunner(device)
        # devcom.append_coroutine(comrun.check_icmp(ip_list))

    for device in devcom.devices.device_list:
        if device.enabled:
            comrun1 = dc.CommandRunner(device)
            devcom.append_coroutine(comrun1.get_config())

            comrun2 = dc.CommandRunner(device)
            devcom.append_coroutine(comrun2.get_ppp_active())
    devcom.run()

    devices.save_export_compact2files()
    devices.parse_config()
    devices.save_parse_result2files()

    for device in devcom.devices.device_list:
        if device.enabled:
            comrun1 = dc.CommandRunner(device)
            devcom.append_coroutine(comrun1.check_icmp(device.mikroconfig.ip_free))
    devices.save_icmp_result2files()

    # for device in devices.device_list:
    #     print(device.ip)
        # print(device.export_compact)


if __name__ == "__main__":
    main()
