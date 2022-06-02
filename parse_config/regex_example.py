import re

from collections import namedtuple
from pprint import pprint

regex_flash = r'\\\n *'  # удаление переносов из конфигурационного файла


# Выбор одноименной секции из export_compact
sections = dict([
    ('interface_bridge', [r'add(?:.+)name=\"?(.+?)\"?(?: protocol-mode|\n)']),  # возвращает имя bridge
    ('interface_eoip', [r'add\b(?:.+?)name=\"?(.+?)\"? remote-address',  # возвращает имя EOIP
                        r'add\b(?:.+?)local-address=((?:\d+\.){3}\d+)',  # возвращает ip local-address
                        r'add\b(?:.+?)remote-address=((?:\d+\.){3}\d+)'  # возвращает ip remote-address
                        ]),
    # [r'add\b(?:.+?)local-address=((?:\d+\.){3}\d+)(?:.+?)name=(.+?) remote-address=((?:\d+\.){3}\d+)']),
    ('interface_vlan', [r'add(?:.+)name=\"?(.+?)\"?(?: vlan-id|\n)',  # возвращает имя vlan
                        r'add(?:.+)interface=\"?(.+?)\"?(?: [-\w]+=|\n|$|"$)']),  # возвращает имя интерфейса
    ('interface_bridge_port', [r'add(?:.+)bridge=\"?(.+?)(?: (?:[-\w]+=)|\n|\"| inter).*face=\"?(.+?)\"?(?:\n|$|"$)',
                               # возвращает bridge и interface
                               r'add(?:.+)interface=\"?(.+?)(?:\"[ \n]| [-\w]+=|\n|$|"$)']),  # возвращает только interface
    ('ppp_secret', [r'add(?:.+)remote-address=((?:\d+\.){3}\d+)(?: service|\n| )']),  # возвращает remote-address
    ('ip_address', [r'add(?:.+)interface=\"?(.+?)\"?(?: network|\n)',  # возвращает interface
                    r'add address=((?:\d+\.){3}\d+)']),  # возвращает ip
    ('interface_bonding', [r'add(?:.+)slaves=\"?(.+?)\"?(?: transmit|\n)',   # возвращает список всех slaves строкой
                           r'add(?:.+)arp-ip-targets=((?:\d+\.){3}\d+)'])  # возвращает список IP из arp-ip-targets
])


# формирование регулярного выражения для заданной секции для выборки из "export_compact"
def new_regex_section(section):
    return rf'\{section}\n([\s\S]+?)\n\/'


Regex_sections = namedtuple('Regex_sections', sections)

regex_section = Regex_sections._make([
    [new_regex_section('/' + section.replace('_', ' '))] + sections[section] for section in Regex_sections._fields])
"""Итоговая структура regex_section:
    regex_section.name_of_section: regexlist
    regexlist - список регулярных выражаний для:
    regexlist[0] - для выбора всей секции из конфигурационного файла
    regexlist[1:] - для выбора нужных значений в зависимости от задачи
"""
regExFindIP = r'\d+\.\d+\.\d+\.\d+'


def parse_section(regex_section: Regex_sections, config, reg_id=1):
    """
    :param regex_section:
    :param reg_id: id регулярки из списка в regex_section, с помощью которой парсить секцию
    """
    config = re.sub(regex_flash, '', config)  # удаление переносов из конфигурационного файла
    section_config = '\n'.join(re.findall(regex_section[0], config))  # выбор всей секции из конфигурационного файла
    res = re.findall(regex_section[reg_id], section_config)  # выбор нужных значений в зависимости от reg_id
    return res


if __name__ == '__main__':
    ipfile = 'export_compact.txt.rsc'
    with open(ipfile, encoding='ANSI') as file:
        config = file.read()

    # print(parse_section(regex_section.interface_bridge, config))
    pprint(parse_section(regex_section.interface_eoip, config))
    # pprint(parse_section(regex_section.interface_vlan, config))
    # pprint(parse_section(regex_section.interface_bridge_port, config))
    # pprint(parse_section(regex_section.ppp_secret, config))
    # pprint(set(parse_section(regex_section.ip_address, config)))
