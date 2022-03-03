import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner_Get
import tools

REMOTE_NODE_FILE = 'remote_node.yaml'
REMOTE_CM_LIST = 'cm_list.xlsx'
PUT_REMOTE_CM_LIST = 'cm_list_put_2022-03-03.xlsx'
SLICE = 50  # максимальное кол-во ip адресов для проверки в одном потоке


def main():
    devices = dc.Devices()
    # devices.load_from_yaml(REMOTE_NODE_FILE)

    devices.load_from_excel(REMOTE_CM_LIST)
    # devices.load_from_excel(PUT_REMOTE_CM_LIST)

    devcom = dc.DevicesCommander(devices)

    # devices_for_work = devcom.devices.device_list[6:7]
    devices_for_work = devcom.devices.device_list
    # TODO продумать как devices_for_work передавать во все зависимые методы которые выполняются ниже

    devices_get_sysname(devcom, devices_for_work)  # Get "sysname" from devices_for_work
    devices_get_config_and_ppp_active(devcom, devices_for_work)  # Get "config" and "ip ppp active"
    devcom.devices.save_export_compact2files()  # Save "export compact" to files...
    # devcom.devices.load_export_compact_from_files('2022-03-02')  # Load "export compact" from files...
    devcom.devices.parse_config()  # Parse config...
    devices_check_icmp(devcom, devices_for_work, 'ip_free')  # Check ICMP ip_free...
    devices_check_icmp(devcom, devices_for_work, 'ip_in_tu')  # Check ICMP ip_in_tu...
    devcom.devices.save_parse_result2files()  # Save parse config to files...
    devcom.devices.save_icmp_result2files('ip_free')  # Save ICMP ip_free result to files...
    devcom.devices.save_icmp_result2files('ip_in_tu')  # Save ICMP ip_in_tu result to files...

    # devices.logger.root.info(f'DISABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    # # devices_set_status(devcom, devices_for_work, 'print', print_result=True)
    # devices_set_status(devcom, devices_for_work, 'disable', print_result=False)
    # devices.logger.root.info(f'DISABLE PUT commands in CM success.')

    # devices.logger.root.info(f'ENABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    # devices_set_status(devcom, devices_for_work, 'enable', print_result=False)
    # devices.logger.root.info(f'ENABLE PUT commands in CM success.')


def devices_set_status(devcom, devices_for_work, action, print_result):
    for device in devices_for_work:
        comrun1 = dc.CommandRunner_Put(device)
        devcom.append_coroutine(comrun1.set_status_interfaces(action, print_result))
    devcom.run()


def devices_check_icmp(devcom, devices_for_work, type_ip_list):
    """type_ip_list = [ 'ip_free' | 'ip_in_tu' ]"""
    devcom.devices.logger.root.info(f'Check ICMP {type_ip_list}...')
    for device in devices_for_work:
        if device.enabled and not (device.mikroconfig is None):
            ip_list = ''
            if type_ip_list == 'ip_free':
                ip_list = device.mikroconfig.ip_free
            elif type_ip_list == 'ip_in_tu':
                ip_list = device.mikroconfig.ip_in_tu
            if ip_list:
                for slice_ip_list in tools.list_split(ip_list, SLICE):
                    comrun1 = dc.CommandRunner_Get(device)
                    devcom.append_coroutine(comrun1.check_icmp(slice_ip_list, type_ip_list))
    devcom.run()
    devcom.devices.logger.root.info(f'Check ICMP {type_ip_list} success.')


def devices_get_config_and_ppp_active(devcom, devices_for_work):
    devcom.devices.logger.root.info(f'Get "config" and "ip ppp active" from {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        if device.enabled:
            comrun1 = dc.CommandRunner_Get(device)
            devcom.append_coroutine(comrun1.get_config())

            comrun2 = dc.CommandRunner_Get(device)
            devcom.append_coroutine(comrun2.get_ppp_active())
    devcom.run()
    devcom.devices.logger.root.info(f'Get "config" and "ip ppp active" success.')


def devices_get_sysname(devcom, devices_for_work):
    devcom.devices.logger.root.info(f'Get "sysname" from {len(devices_for_work)} hosts...')
    for device in devices_for_work:
        comrun = dc.CommandRunner_Get(device)
        devcom.append_coroutine(comrun.get_sysname())
    devcom.run()
    devcom.devices.logger.root.info(f'Get "sysname" success.')


if __name__ == "__main__":
    main()
