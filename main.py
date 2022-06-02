import os.path
import time
from datetime import datetime

import pandas

import devicecontrol as dc
# from devicecontrol import DevicesCommander, CommandRunner_Get
import tools

REMOTE_NODE_FILE = 'remote_node.yaml'
REMOTE_CM_LIST = 'cm_list_for_run_new.xlsx'
# REMOTE_CM_LIST = 'cm_list_for_run_test.xlsx'
DISABLE_REMOTE_CM_LIST = 'cm_list_disable_2022-03-30.xlsx'
REMOVE_REMOTE_CM_LIST = 'cm_list_remove_2022-04-11.xlsx'

REMOTE_CTR_LIST = 'ctr_list_for_run.xlsx'


DIR_PPR_IP_FREE = 'ppr_ip_free'
# FILE_NAME_PPR_IP_FREE = 'ppr_ip_free_2022-05-25.xlsx'
FILE_NAME_PPR_IP_FREE = 'ppr_ip_free_2022-05-25_enable_Казань.xlsx'
# FILE_NAME_PPR_IP_FREE = 'summary_ip_free_resoult.xlsx'
# FILE_NAME_PPR_IP_FREE = 'ppr_ip_free_test.xlsx'

SLICE = 200  # максимальное кол-во ip адресов для проверки в одном потоке
SLICE_STATS = 100 # максимальное кол-во ip адресов для получения статистики в одном потоке


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

    devices_get_sysname(devcom, devices_for_work, print_result=False, check_enabled=True)  # Get "sysname"
    # # devcom.devices.load_export_compact_from_files(date_='2022-03-09')  # Load "export compact" from files...
    # devices_get_config(devcom, devices_for_work)  # Get "config" from Remote CM
    # devcom.devices.save_export_compact_to_files()  # Save "export compact" to files...
    # # devcom.devices.save_export_compact_to_files(dir_='ctr_export_compact')  # Save CTR "export compact" to files...
    #
    # devices_get_ppp_active_and_counting(devcom, devices_for_work, print_result=False)  # Get "ppp active" and_counting
    # devcom.devices.parse_config()  # Parse config...
    #
    # devices_check_icmp(devcom, devices_for_work)  # Check ICMP ip_free and ip_in_tu...
    # #
    # devcom.devices.save_parse_result_to_files()  # Save parse config to files...
    # # devcom.devices.save_parse_result_to_files(dir_='ctr_output_parse')  # Save CTR parse config to files...
    # #
    # devcom.devices.save_icmp_result_to_files('ip_free')  # Save ICMP ip_free result to files...
    # devcom.devices.save_icmp_result_to_files('ip_in_tu')  # Save ICMP ip_in_tu result to files...
    # # #
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
    # devices_run_any_command(devcom, devices_for_work, '/interface bridge add name="bridge-temp-for-backup-2022-05-25"',
    #                         print_result=True)
    # devices.logger.root.info(f'ENABLE PUT commands in CM success.')

    # devices.logger.root.info(f'ENABLE PUT commands in CM at {len(devices_for_work)} hosts...')
    file_with_ip = os.path.join(DIR_PPR_IP_FREE, FILE_NAME_PPR_IP_FREE)
    output_file =  os.path.join(DIR_PPR_IP_FREE, 'with_stats_'+FILE_NAME_PPR_IP_FREE)
    # devices.logger.root.info(f'ENABLE IP FREE in CM for IP in {file_with_ip}...')
    columns = None
    # columns = ['IP remote CPE', 'City', 'CMikroTik Name', 'CMikroTik IP']

    # devices_for_work_from_ip_free = get_devices_for_work_from_file_with_ip(devcom, file_with_ip, columns)
    # get_stats_by_file_with_ip(devcom, file_with_ip, output_file, print_result=False, check_enabled=True, columns=None)
    file_with_ip = os.path.join(DIR_PPR_IP_FREE, 'other_ip.xlsx')
    output_file = os.path.join(DIR_PPR_IP_FREE, 'with_stats_other_ip.xlsx')
    get_stats_by_file_with_ip(devcom, file_with_ip, output_file, print_result=True, check_enabled=True, columns=None)

    # devices_set_status_ip_free(devcom, file_with_ip, 'print', print_result=True, check_enabled=False, columns=columns)
    # devices_run_any_command(devcom, devices_for_work_from_ip_free,
    #                         '/interface bridge add name="bridge-temp-for-backup-2022-05-25"', print_result=True)
    # devices_remove_disabled(devcom, devices_for_work_from_ip_free, print_result=True, check_enabled=False)
    # devices_set_status_ip_free(devcom, file_with_ip, 'disable', print_result=True, check_enabled=False, columns=columns)
    # devices_get_disabled_counting(devcom, devices_for_work_from_ip_free, print_result=True, check_enabled=True)
    # devices_set_status_ip_free(devcom, file_with_ip, 'enable', print_result=True, check_enabled=False, columns=columns)
    # devices_get_disabled_counting(devcom, devices_for_work_from_ip_free, print_result=True, check_enabled=True)
    # devices.logger.root.info(f'DISABLE IP FREE in CM success.')


def devices_set_status(devcom, devices_for_work, action, print_result, check_enabled):
    for device in devices_for_work:
        comrun1 = dc.CommandRunner_Put(device)
        devcom.append_coroutine(comrun1.set_status_interfaces(action, print_result, check_enabled))
    devcom.run()


def read_and_group_data_from_file_with_ip(devcom, file_with_ip, columns=None, group_by=None):
    devices_for_work = []
    data = pandas.read_excel(file_with_ip)
    if columns:
        data = data[columns]
    framegr = data.groupby(group_by) if group_by else None
    for cmikrotik in framegr.groups:
        devices = devcom.devices.find_devices_by_ip(cmikrotik)
        devices_for_work += devices
    return data, framegr, devices_for_work


def get_stats_by_file_with_ip(devcom, file_with_ip, output_file, print_result, check_enabled, columns=None):
    data, framegr, devices_for_work = read_and_group_data_from_file_with_ip(devcom, file_with_ip, columns, 'CMikroTik IP')
    stats = ['tx-byte',
             'rx-byte',
             'disabled',
             'running']
    for cmikrotik in framegr.groups:
        ip_list = framegr.get_group(cmikrotik)['IP remote CPE'].to_list()
        devices = devcom.devices.find_devices_by_ip(cmikrotik)
        for device in devices:
            for slice_ip_list in tools.list_split(ip_list, SLICE_STATS):
                comrun1 = dc.CommandRunner_Get(device)
                devcom.append_coroutine(comrun1.get_stats_by_ip(slice_ip_list, print_result, check_enabled))

    devcom.run()
    for stat_item in stats:
        data[stat_item] = ''
    data['up-time CM'] = ''
    for device in devices_for_work:
        cm_data = data[data['CMikroTik IP'] == device.ip]  # фильтр всех записей для одного СМ
        for remote_ip in device.ip_stats.keys():
            ip_stats = device.ip_stats[remote_ip]
            ip_data = cm_data[cm_data['IP remote CPE'] == remote_ip]
            data.loc[ip_data.index, 'up-time CM'] = device.uptime
            if isinstance(ip_stats, dict):
                for stat_item in stats:
                    data.loc[ip_data.index, stat_item] = \
                        device.ip_stats[remote_ip].get(stat_item, f'no item {stat_item} in stats info')
            else:
                data.loc[ip_data.index, stats[0]] = ip_stats

    data.to_excel(output_file)


def devices_set_status_ip_free(devcom, file_with_ip, action, print_result, check_enabled, columns=None):
    data, framegr, devices_for_work = read_and_group_data_from_file_with_ip(devcom, file_with_ip, columns, 'CMikroTik IP')
    for cmikrotik in framegr.groups:
        ip_list = framegr.get_group(cmikrotik)['IP remote CPE'].to_list()
        devices = devcom.devices.find_devices_by_ip(cmikrotik)
        for device in devices:
            comrun1 = dc.CommandRunner_Put(device)
            devcom.append_coroutine(comrun1.set_status_ip_free(action, ip_list, print_result, check_enabled))
    devcom.run()


def devices_get_disabled_counting(devcom, devices_for_work, print_result, check_enabled):
    def get_device_list(devices_for_work):
        return '\n'.join(f'{dev.city} - {dev.name} - {dev.ip}' for dev in devices_for_work)

    print(time.strftime("%H:%M:%S"), 'Get disabled interface in:', get_device_list(devices_for_work), sep='\n')
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


def devices_check_icmp(devcom, devices_for_work):
    """type_ip_list = [ 'ip_free' | 'ip_in_tu' ]"""
    # devcom.devices.logger.root.info(f'Check ICMP {type_ip_list}...')
    msg = f'Check ICMP from {len(devices_for_work)} CM......'
    devcom.devices.logger.root.info(msg)
    print(time.strftime("%H:%M:%S"), msg)
    for device in devices_for_work:
        if device.enabled and not (device.mikroconfig is None):
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
