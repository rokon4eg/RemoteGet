import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner_Get
import tools

REMOTE_NODE_FILE = 'remote_node.yaml'
REMOTE_CM_LIST = 'cm_list.xlsx'
PUT_REMOTE_CM_LIST = 'cm_list_put.xlsx'
SLICE = 50  # максимальное кол-во ip адресов для проверки в одном потоке

def main():
    devices = dc.Devices()
    # devices.load_from_yaml(REMOTE_NODE_FILE)

    devices.load_from_excel(REMOTE_CM_LIST)
    # devices.load_from_excel(PUT_REMOTE_CM_LIST)

    devcom = dc.DevicesCommander(devices)

    # devices_for_work = devcom.devices.device_list[27:30]
    devices_for_work = devcom.devices.device_list

    devices_get_sysname(devcom, devices, devices_for_work)  # Get "sysname" from devices_for_work
    devices_get_config_and_ppp_active(devcom, devices, devices_for_work)  # Get "config" and "ip ppp active"
    devices_save_export_compact_to_files(devices)  # Save "export compact" to files...
    # devices_load_export_compact_from_files(devices, '2022-03-02')  # Load "export compact" from files...
    devices_parse_config(devices)  # Parse config...
    devices_check_icmp(devcom, devices, devices_for_work)  # Check ICMP...
    devices_save_parse_config_to_files(devices)  # Save parse config to files...
    devices_save_icm_result_to_files(devices)  # Save ICMP result to files...

    # devices.logger.root.info(f'DISABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    # # devices_set_status(devcom, devices_for_work, 'print')
    # devices_set_status(devcom, devices_for_work, 'disable')
    # devices.logger.root.info(f'DISABLE PUT commands in CM success.')

    # devices.logger.root.info(f'ENABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    # devices_set_status(devcom, devices_for_work, 'enable')
    # devices.logger.root.info(f'ENABLE PUT commands in CM success.')


def devices_set_status(devcom, devices_for_work, action):
    for device in devices_for_work:
        comrun1 = dc.CommandRunner_Put(device)
        devcom.append_coroutine(comrun1.set_status_interfaces(action))
    devcom.run()


def devices_save_icm_result_to_files(devices):
    devices.logger.root.info(f'Save ICMP result to files...')
    devices.save_icmp_result2files()
    devices.logger.root.info(f'Save ICMP result success.')


def devices_save_parse_config_to_files(devices):
    devices.logger.root.info(f'Save parse config to files...')
    devices.save_parse_result2files()
    devices.logger.root.info(f'Save parse config success.')


def devices_check_icmp(devcom, devices, devices_for_work):
    devices.logger.root.info(f'Check ICMP...')
    for device in devices_for_work:
        if device.enabled and not (device.mikroconfig is None):
            # DONE Реализовать запуск check_icmp в несколько потоков если ip больше 100
            # SLICE максимальное кол-во ip адресов для проверки в одном потоке
            for ip_list in tools.list_split(device.mikroconfig.ip_free, SLICE):
                comrun1 = dc.CommandRunner_Get(device)
                devcom.append_coroutine(comrun1.check_icmp(ip_list))
    devcom.run()
    devices.logger.root.info(f'Check ICMP success.')


def devices_parse_config(devices):
    devices.logger.root.info(f'Parse config...')
    devices.parse_config()
    devices.logger.root.info(f'Parse config success.')


def devices_load_export_compact_from_files(devices, date_):
    devices.logger.root.info(f'Load "export compact" from files...')
    devices.load_export_compact_from_files(date_)
    devices.logger.root.info(f'Load "export compact" success.')


def devices_save_export_compact_to_files(devices):
    devices.logger.root.info(f'Save "export compact" to files...')
    devices.save_export_compact2files()
    devices.logger.root.info(f'Save "export compact" success.')


def devices_get_config_and_ppp_active(devcom, devices, devices_for_work):
    devices.logger.root.info(f'Get "config" and "ip ppp active" from {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        if device.enabled:
            comrun1 = dc.CommandRunner_Get(device)
            devcom.append_coroutine(comrun1.get_config())

            comrun2 = dc.CommandRunner_Get(device)
            devcom.append_coroutine(comrun2.get_ppp_active())
    devcom.run()
    devices.logger.root.info(f'Get "config" and "ip ppp active" success.')


def devices_get_sysname(devcom, devices, devices_for_work):
    devices.logger.root.info(f'Get "sysname" from {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        comrun = dc.CommandRunner_Get(device)
        devcom.append_coroutine(comrun.get_sysname())
    devcom.run()
    devices.logger.root.info(f'Get "sysname" success.')


if __name__ == "__main__":
    main()
