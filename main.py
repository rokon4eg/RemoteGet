import os.path
import time
from datetime import datetime

import pandas

import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner_Get
import tools

REMOTE_NODE_FILE = 'remote_node.yaml'
REMOTE_CM_LIST = 'cm_list_for_run_new.xlsx'
DISABLE_REMOTE_CM_LIST = 'cm_list_disable_2022-03-30.xlsx'
REMOVE_REMOTE_CM_LIST = 'cm_list_remove_2022-04-11.xlsx'

REMOTE_CTR_LIST = 'ctr_list_for_run.xlsx'


DIR_PPR_IP_FREE = 'ppr_ip_free'
FILE_NAME_PPR_IP_FREE = 'ppr_ip_free_2022-05-16.xlsx'

SLICE = 200  # максимальное кол-во ip адресов для проверки в одном потоке


def main():
    devices = dc.Devices()
    # devices.load_from_yaml(REMOTE_NODE_FILE)

    # devices.load_from_excel(REMOTE_CTR_LIST)

    devices.load_from_excel(REMOTE_CM_LIST)
    # devices.load_from_excel(DISABLE_REMOTE_CM_LIST)
    # devices.load_from_excel(REMOVE_REMOTE_CM_LIST)

    devcom = dc.DevicesCommander(devices)

    # devices_for_work = devcom.devices.device_list[4:5]
    # devices_for_work += devcom.devices.device_list[131:132]
    devices_for_work = devcom.devices.device_list
    # TODO продумать как devices_for_work передавать во все зависимые методы которые выполняются ниже

    # devices_get_sysname(devcom, devices_for_work, print_result=False, check_enabled=True)  # Get "sysname" from devices_for_work
    # devcom.devices.load_export_compact_from_files(date_='2022-03-09')  # Load "export compact" from files...
    # devices_get_config(devcom, devices_for_work)  # Get "config" from Remote CM
    # devcom.devices.save_export_compact_to_files()  # Save "export compact" to files...
    # devcom.devices.save_export_compact_to_files(dir_='ctr_export_compact')  # Save CTR "export compact" to files...

    # devices_get_ppp_active_and_counting(devcom, devices_for_work, print_result=False)  # Get "ppp active" and_counting
    # devcom.devices.parse_config()  # Parse config...

    # devices_check_icmp(devcom, devices_for_work)  # Check ICMP ip_free and ip_in_tu...
    #
    # devcom.devices.save_parse_result_to_files()  # Save parse config to files...
    # devcom.devices.save_parse_result_to_files(dir_='ctr_output_parse')  # Save CTR parse config to files...
    #
    # devcom.devices.save_icmp_result_to_files('ip_free')  # Save ICMP ip_free result to files...
    # devcom.devices.save_icmp_result_to_files('ip_in_tu')  # Save ICMP ip_in_tu result to files...
    #
    # devcom.devices.save_summary_icmp_result('ip_free')  # Save summary ICMP ip_free result...
    # devcom.devices.save_summary_icmp_result('ip_in_tu')  # Save summary ICMP ip_in_tu result...
    # # # #
    # devices.logger.root.info(f'REMOVE DISABLED in CM at {len(devices_for_work)} hosts...')
    # # devices_get_disabled_counting(devcom, devices_for_work, print_result=True, check_enabled=True)
    # devices_remove_disabled(devcom, devices_for_work, print_result=True, check_enabled=True)
    # devices.logger.root.info(f'REMOVE DISABLED in CM success.')
    # # # #
    # devices.logger.root.info(f'DISABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    # # devices_set_status(devcom, devices_for_work, 'print', print_result=True, check_enabled=True)
    # devices_set_status(devcom, devices_for_work, 'disable', print_result=False, check_enabled=True)
    # devices.logger.root.info(f'DISABLE PUT commands in CM success.')

    # devices.logger.root.info(f'ENABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    # # devices_set_status(devcom, devices_for_work, 'enable', print_result=False, check_enabled=True)
    # # devices_run_any_command(devcom, devices_for_work, '/system identity print', print_result=True, check_enabled=True)
    # devices_run_any_command(devcom, devices_for_work, '/interface bridge add name="bridge-temp-for-backup-2022-03-30"',
    #                         print_result=True, check_enabled=True)
    # devices.logger.root.info(f'ENABLE PUT commands in CM success.')

    file_with_ip = os.path.join(DIR_PPR_IP_FREE, FILE_NAME_PPR_IP_FREE)
    devices.logger.root.info(f'DISABLE IP FREE in CM for IP in {file_with_ip}...')
    devices_set_status_ip_free(devcom, file_with_ip, 'print', print_result=True, check_enabled=False)
    devices.logger.root.info(f'DISABLE IP FREE in CM success.')


def devices_set_status(devcom, devices_for_work, action, print_result, check_enabled):
    for device in devices_for_work:
        comrun1 = dc.CommandRunner_Put(device)
        devcom.append_coroutine(comrun1.set_status_interfaces(action, print_result, check_enabled))
    devcom.run()

def devices_set_status_ip_free(devcom, file_with_ip, action, print_result, check_enabled):
    # ToDO:
    #  read file "file_with_ip" +
    #  group by "CMikroTik IP" +
    #  iterate by group +
    #  find device by "CMikroTik IP" in devices +
    #  fill ip_list as "IP remote CPE" from the group +
    # devices_for_work = devcom.devices.device_list
    data = pandas.read_excel(file_with_ip)
    framegr = data[['IP remote CPE', 'City', 'CMikroTik Name',  'CMikroTik IP']].groupby('CMikroTik IP')
    for cmikrotik in framegr.groups:
        ip_list = framegr.get_group(cmikrotik)['IP remote CPE'].to_list()
        devices = devcom.devices.get_devices_by_ip(cmikrotik)
        for dev in devices:
            comrun1 = dc.CommandRunner_Put(dev)
            devcom.append_coroutine(comrun1.set_status_ip_free(action, ip_list, print_result, check_enabled))
    devcom.run()

def devices_get_disabled_counting(devcom, devices_for_work, print_result, check_enabled):
    print(time.strftime("%H:%M:%S"), 'Get disabled counting for:', get_device_list(devices_for_work), sep='\n')
    for device in devices_for_work:
        comrun1 = dc.CommandRunner_Remove(device)
        devcom.append_coroutine(comrun1.get_disabled_counting(print_result=print_result, check_enabled=check_enabled))
    devcom.run()


def devices_remove_disabled(devcom, devices_for_work, print_result, check_enabled):
    devices_get_disabled_counting(devcom, devices_for_work, print_result, check_enabled)
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
    devices_get_disabled_counting(devcom, devices_for_work, print_result, check_enabled)


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


def devices_get_sysname(devcom, devices_for_work, print_result, check_enabled):
    msg = f'Get "sysname" from {len(devices_for_work)} hosts...'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)
    for device in devices_for_work:
        comrun = dc.CommandRunner_Get(device)
        devcom.append_coroutine(comrun.get_sysname(print_result, check_enabled=check_enabled))
    devcom.run()
    msg = f'Get "sysname" success.'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)


def devices_run_any_command(devcom, devices_for_work, commands, print_result):
    msg = f'Run command {commands} in {len(devices_for_work)} hosts...'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)
    for device in devices_for_work:
        comrun = dc.CommandRunner_Get(device)
        devcom.append_coroutine(comrun.get_any_commands(commands, print_result))
    devcom.run()
    msg = f'Run command {commands}.'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)


if __name__ == "__main__":
    main()
