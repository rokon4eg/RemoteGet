import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner_Get
import tools

REMOTE_NODE_FILE = 'remote_node.yaml'
REMOTE_CM_LIST = 'cm_list.xlsx'
SLICE = 50  # максимальное кол-во ip адресов для проверки в одном потоке


# device_list = []


def main():
    devices = dc.Devices()
    # devices.load_from_yaml(REMOTE_NODE_FILE)
    devices.load_from_excel(REMOTE_CM_LIST)

    devcom = dc.DevicesCommander(devices)

    devices_for_work = devcom.devices.device_list[27:30]
    # devices_for_work = devcom.devices.device_list

    devices.logger.root.info(f'Get "sysname" from {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        comrun = dc.CommandRunner_Get(device)
        devcom.append_coroutine(comrun.get_sysname())
    devcom.run()
    devices.logger.root.info(f'Get "sysname" success.')

    # devices.logger.root.info(f'Get "config" and "ip ppp active" from {len(devices_for_work)} hosts...')
    # for device in devices_for_work:
    #     if device.enabled:
    #         # comrun1 = dc.CommandRunner_Get(device)
    #         # devcom.append_coroutine(comrun1.get_config())
    #
    #         # comrun2 = dc.CommandRunner_Get(device)
    #         # devcom.append_coroutine(comrun2.get_ppp_active())
    # devcom.run()
    # devices.logger.root.info(f'Get "config" and "ip ppp active" success.')

    # devices.logger.root.info(f'Save "export compact" to files...')
    # devices.save_export_compact2files()
    # devices.logger.root.info(f'Save "export compact" success.')

    devices.logger.root.info(f'Load "export compact" from files...')
    devices.load_export_compact_from_files(date_='2022-03-01')
    devices.logger.root.info(f'Load "export compact" success.')

    devices.logger.root.info(f'Parse config...')
    devices.parse_config()
    devices.logger.root.info(f'Parse config success.')

    # devices.logger.root.info(f'Save result parse config to files...')
    # devices.save_parse_result2files()
    # devices.logger.root.info(f'Save result parse config success.')

    # devices.logger.root.info(f'Check ICMP...')
    # for device in devices_for_work:
    #     if device.enabled and not (device.mikroconfig is None):
    #         # DONE Реализовать запуск check_icmp в несколько потоков если ip больше 100
    #         # SLICE максимальное кол-во ip адресов для проверки в одном потоке
    #         for ip_list in tools.list_split(device.mikroconfig.ip_free, SLICE):
    #             comrun1 = dc.CommandRunner_Get(device)
    #             devcom.append_coroutine(comrun1.check_icmp(ip_list))
    # devcom.run()
    # devices.logger.root.info(f'Check ICMP success.')

    # devices.logger.root.info(f'Save result parse config to files...')
    # devices.save_parse_result2files()
    # devices.logger.root.info(f'Save result parse config success.')
    #
    # devices.logger.root.info(f'Save ICMP result to files...')
    # devices.save_icmp_result2files()
    # devices.logger.root.info(f'Save ICMP result success.')

    devices.logger.root.info(f'DISABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        bridges =device.mikroconfig.br_empty | device.mikroconfig.br_single
        comrun1 = dc.CommandRunner_Put(device)
        devcom.append_coroutine(comrun1.disable_interface_by_name('bridge', bridges))
    devcom.run()
    devices.logger.root.info(f'DISABLE PUT commands in CM success.')

    devices.logger.root.info(f'ENABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        bridges =device.mikroconfig.br_empty | device.mikroconfig.br_single
        comrun1 = dc.CommandRunner_Put(device)
        devcom.append_coroutine(comrun1.enable_interface_by_name('bridge', bridges))
    devcom.run()
    devices.logger.root.info(f'ENABLE PUT commands in CM success.')


if __name__ == "__main__":
    main()
