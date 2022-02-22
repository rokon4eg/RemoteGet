import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner

REMOTE_NODE_FILE = 'remote_node.yaml'
REMOTE_CM_LIST = 'cm_list.xlsx'

# device_list = []


def main():
    devices = dc.Devices()
    # devices.load_from_yaml(REMOTE_NODE_FILE)
    devices.load_from_excel(REMOTE_CM_LIST)

    devcom = dc.DevicesCommander(devices)

    devices_for_work = devcom.devices.device_list[:2]

    devices.logger.root.info(f'Get "sysname" from {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        comrun = dc.CommandRunner(device)
        devcom.append_coroutine(comrun.get_sysname())
    devcom.run()
    devices.logger.root.info(f'Get "sysname" success.')

    devices.logger.root.info(f'Get "config" and "ip ppp active" from {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        if device.enabled:
            comrun1 = dc.CommandRunner(device)
            devcom.append_coroutine(comrun1.get_config())

            comrun2 = dc.CommandRunner(device)
            devcom.append_coroutine(comrun2.get_ppp_active())
    devcom.run()
    devices.logger.root.info(f'Get "config" and "ip ppp active" success.')

    devices.logger.root.info(f'Save export compact to files...')
    devices.save_export_compact2files()
    devices.logger.root.info(f'Save export compact success.')

    devices.logger.root.info(f'Parse config...')
    devices.parse_config()
    devices.logger.root.info(f'Parse config success.')

    devices.logger.root.info(f'Save result parse config to files...')
    devices.save_parse_result2files()
    devices.logger.root.info(f'Save result parse config success.')

    devices.logger.root.info(f'Check ICMP...')
    for device in devices_for_work:
        if device.enabled:
            comrun1 = dc.CommandRunner(device)
            devcom.append_coroutine(comrun1.check_icmp(device.mikroconfig.ip_free))
    devices.logger.root.info(f'Check ICMP success.')

    devices.logger.root.info(f'Save ICMP result to files...')
    devices.save_icmp_result2files()
    devices.logger.root.info(f'Save ICMP result success.')


if __name__ == "__main__":
    main()
