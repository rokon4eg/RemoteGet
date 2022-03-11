import time
from datetime import datetime

import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner_Get
import tools

REMOTE_NODE_FILE = 'remote_node.yaml'
REMOTE_CM_LIST = 'cm_list_for_run.xlsx'
PUT_REMOTE_CM_LIST = 'cm_list_put_2022-03-11.xlsx'
SLICE = 50  # максимальное кол-во ip адресов для проверки в одном потоке


def main():
    devices = dc.Devices()
    # devices.load_from_yaml(REMOTE_NODE_FILE)

    # devices.load_from_excel(REMOTE_CM_LIST)
    devices.load_from_excel(PUT_REMOTE_CM_LIST)

    devcom = dc.DevicesCommander(devices)

    # devices_for_work = devcom.devices.device_list[1:2]
    devices_for_work = devcom.devices.device_list
    # TODO продумать как devices_for_work передавать во все зависимые методы которые выполняются ниже

    devices_get_sysname(devcom, devices_for_work, print_result=False)  # Get "sysname" from devices_for_work
    devcom.devices.load_export_compact_from_files(date_='2022-03-11')  # Load "export compact" from files...
    # devices_get_config(devcom, devices_for_work)  # Get "config"
    # devcom.devices.save_export_compact_to_files()  # Save "export compact" to files...
    # devices_get_ppp_active_and_counting(devcom, devices_for_work, print_result=False)  # Get "ppp active" and_counting
    devcom.devices.parse_config()  # Parse config...
    # devices_check_icmp(devcom, devices_for_work)  # Check ICMP ip_free and ip_in_tu...
    # """# devices_check_icmp(devcom, devices_for_work)  # Check ICMP ip_in_tu..."""
    # devcom.devices.save_parse_result_to_files()  # Save parse config to files...
    # devcom.devices.save_icmp_result_to_files('ip_free')  # Save ICMP ip_free result to files...
    # devcom.devices.save_icmp_result_to_files('ip_in_tu')  # Save ICMP ip_in_tu result to files...
    #
    # devices.logger.root.info(f'REMOVE DISABLED in CM at {len(devices_for_work)} hosts...')
    # devices_get_disabled_counting(devcom, devices_for_work, print_result=True)
    # # devices_remove_disabled(devcom, devices_for_work, print_result=True)
    # devices.logger.root.info(f'REMOVE DISABLED in CM success.')

    devices.logger.root.info(f'DISABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    devices_set_status(devcom, devices_for_work, 'print', print_result=True)
    # devices_set_status(devcom, devices_for_work, 'disable', print_result=False)
    devices.logger.root.info(f'DISABLE PUT commands in CM success.')

    # devices.logger.root.info(f'ENABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    # devices_set_status(devcom, devices_for_work, 'enable', print_result=False)
    # devices.logger.root.info(f'ENABLE PUT commands in CM success.')


def devices_set_status(devcom, devices_for_work, action, print_result):
    for device in devices_for_work:
        comrun1 = dc.CommandRunner_Put(device)
        devcom.append_coroutine(comrun1.set_status_interfaces(action, print_result))
    devcom.run()


def devices_get_disabled_counting(devcom, devices_for_work, print_result):
    print(time.strftime("%H:%M:%S"), 'Get disabled counting for:', get_device_list(devices_for_work), sep='\n')
    for device in devices_for_work:
        comrun1 = dc.CommandRunner_Remove(device)
        devcom.append_coroutine(comrun1.get_disabled_counting(print_result))
    devcom.run()


def devices_remove_disabled(devcom, devices_for_work, print_result):
    devices_get_disabled_counting(devcom, devices_for_work, print_result)
    confirm = input(f'Are you sure remove disabled from {len(devices_for_work)} CM?\n'
                    f'type "Y" for continue:')
    if confirm == "Y":
        for device in devices_for_work:
            comrun1 = dc.CommandRunner_Remove(device)
            devcom.append_coroutine(comrun1.remove_disabled(print_result))
        devcom.run()
        print(time.strftime("%H:%M:%S"), 'Operation for remove disabled success!')
    else:
        print(time.strftime("%H:%M:%S"), 'Cancel operation for remove disabled!')
    devices_get_disabled_counting(devcom, devices_for_work, print_result)


def get_device_list(devices_for_work):
    return '\n'.join(f'{dev.city} - {dev.name} - {dev.ip}' for dev in devices_for_work)


def devices_check_icmp(devcom, devices_for_work):
    """type_ip_list = [ 'ip_free' | 'ip_in_tu' ]"""
    # devcom.devices.logger.root.info(f'Check ICMP {type_ip_list}...')
    msg = f'Check ICMP from {len(devices_for_work)} CM......'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)
    for device in devices_for_work:
        if device.enabled and not (device.mikroconfig is None):
            # ip_list = ''
            # if type_ip_list == 'ip_free':
            #     ip_list = device.mikroconfig.ip_free
            # elif type_ip_list == 'ip_in_tu':
            #     ip_list = device.mikroconfig.ip_in_tu
            # if ip_list:
            ip_list = device.mikroconfig.ip_free
            type_ip_list = 'ip_free'
            for slice_ip_list in tools.list_split(ip_list, SLICE):
                comrun1 = dc.CommandRunner_Get(device)
                devcom.append_coroutine(comrun1.check_icmp(slice_ip_list, type_ip_list))

            ip_list = device.mikroconfig.ip_in_tu
            type_ip_list = 'ip_in_tu'
            for slice_ip_list in tools.list_split(ip_list, SLICE):
                comrun2 = dc.CommandRunner_Get(device)
                devcom.append_coroutine(comrun2.check_icmp(slice_ip_list, type_ip_list))

    devcom.run()
    # devcom.devices.logger.root.info(f'Check ICMP {type_ip_list} success.')
    msg = f'Check ICMP success.'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)


def devices_get_config(devcom, devices_for_work):
    msg = f'Get "config" from {len(devices_for_work)} hosts...'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)
    for device in devices_for_work:
        if device.enabled:
            comrun1 = dc.CommandRunner_Get(device)
            devcom.append_coroutine(comrun1.get_config())
    devcom.run()
    msg = f'Get "config" success.'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)


def devices_get_ppp_active_and_counting(devcom, devices_for_work, print_result=False):
    msg = f'Get "ppp active" and "counting" from {len(devices_for_work)} hosts...'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)
    for device in devices_for_work:
        if device.enabled:
            comrun1 = dc.CommandRunner_Get(device)
            devcom.append_coroutine(comrun1.get_ppp_active(print_result))

            comrun2 = dc.CommandRunner_Get(device)
            devcom.append_coroutine(comrun2.get_counting(print_result))
    devcom.run()
    msg = f'Get "ip ppp active" and "counting" success.'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%m:%S"), msg)


# def devices_get_counting(devcom, devices_for_work, print_result=False):
#     devcom.devices.logger.root.info(f'Get "counting" from {len(devices_for_work)} hosts...')
#     for device in devices_for_work:
#         if device.enabled:
#             comrun2 = dc.CommandRunner_Get(device)
#             devcom.append_coroutine(comrun2.get_counting(print_result))
#     devcom.run()
#     devcom.devices.logger.root.info(f'Get "counting" success.')


def devices_get_sysname(devcom, devices_for_work, print_result):
    msg = f'Get "sysname" from {len(devices_for_work)} hosts...'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)
    for device in devices_for_work:
        comrun = dc.CommandRunner_Get(device)
        devcom.append_coroutine(comrun.get_sysname(print_result))
    devcom.run()
    msg = f'Get "sysname" success.'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)


if __name__ == "__main__":
    main()
