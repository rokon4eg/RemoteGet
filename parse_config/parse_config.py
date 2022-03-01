import re
import os.path
from sys import exit, argv
from .regex_example import parse_section, regex_section, regExFindIP


class MikrotikConfig:
    """
1. Сравнить IP адреса из PPP secrets с адресами в ТУ (ip_from_address_plan.txt)
Исключить активные PPP (ppp_active_from_cm.txt)

2 Исключить те EOIP для которых local-addresses участвуют в "ip addresses"

3. Исключить те EOIP для которых remote-addresses есть в ТУ (ip_from_address_plan.txt)
Исключить активные PPP (ppp_active_from_cm.txt)

4. Исключить бриджы которые участвуют в "ip addresses"
Вывести бриджы без портов
Вывести бриджы с одним портом и эти одиночные порты

5 Вывести вланы, не участвующие в бриджах и в "ip addresses"
    """
    def __init__(self, config, file_tu='', ip_active_ppp='', file_active=''):
        self.file_tu = file_tu
        self.file_active = file_active
        self.config = config
        self.ip_from_tu = set(self.getipfromfile(file_tu, regExFindIP)) if self.file_tu else set()
        if ip_active_ppp:
            self.ip_active_ppp = ip_active_ppp
        else:
            self.ip_active_ppp = set(self.getipfromfile(file_active, regExFindIP)) if self.file_active else set()
        self.br_empty = set()  # ---br_empty
        self.br_single = set()  # ---br_single
        self.int_single_dict = dict()  # --intsingle
        self.set_bridges()  # br_empty, br_single, int_single_dict
        self.vlans_free = self.get_vlans_free()  # --vlans_free
        self.eoip_free = self.get_eoip_free()  # --eoip_free
        self.ip_free = self.get_ip_free()  # --ip_free
        self.icmp_false = set()  # --icmp_false
        self.icmp_true = set()  # --icmp_true

    @property
    def all_bridges(self):
        return set(parse_section(regex_section.interface_bridge, self.config))

    @property
    def bonding(self):
        return set(parse_section(regex_section.interface_bonding, self.config))

    @property
    def name_eoip(self):
        return set(parse_section(regex_section.interface_eoip, self.config))

    @property
    def int_ip_addr(self):
        return set(parse_section(regex_section.ip_address, self.config))

    @property
    def ports_only_from_bridges(self):
        """Получаем список всех интерфейсов в бридж портах """
        return set(parse_section(regex_section.interface_bridge_port, self.config, reg_id=2))

    @property
    def bridge_port_from_bridges(self):
        """Получаем список bridge и interface из бридж портов """
        return set(parse_section(regex_section.interface_bridge_port, self.config))

    @property
    def vlans(self):
        return set(parse_section(regex_section.interface_vlan, self.config))

    @property
    def int_vlans(self):
        """список интерфейсов на которых есть влан"""
        return set(parse_section(regex_section.interface_vlan, self.config, reg_id=2))

    @staticmethod
    def exclude_int_in_bonding(int_list, slaves_list):
        res = set(int_list)
        for int in int_list:
            for slaves in slaves_list:
                if int in slaves:
                    res.remove(int)
                    break
        return res

    @staticmethod
    def getipfromfile(filename, regex):
        """Получаем список IP адресов из текста с помощью регулярного выражения"""
        with open(filename, encoding='ANSI') as file:
            return list(re.findall(regex, file.read()))

    def get_ip_free(self):
        """
        Сравнить IP адреса из PPP secrets и remote address из EOIP с адресами в ТУ (ip_from_address_plan.txt)
        Исключить активные PPP (ppp_active_from_cm.txt)
        """
        res = set()
        ip_ppp = set(parse_section(regex_section.ppp_secret, self.config))
        ip_eoip = set(parse_section(regex_section.interface_eoip, self.config, 3))
        res.update((ip_ppp | ip_eoip) - self.ip_from_tu - self.ip_active_ppp)
        return res

    def get_eoip_free(self):
        """
        Исключить те EOIP которых нет в бридж портах, вланах, bonding
        """
        res = set()
        eoip_int = self.name_eoip - self.ports_only_from_bridges - self.int_ip_addr - self.int_vlans
        res.update(self.exclude_int_in_bonding(eoip_int, self.bonding))
        return res

    def set_bridges(self):
        """
        Исключить бриджы которые участвуют в "ip addresses"
        Найти бриджы без портов - br_empty
        Найти бриджы с одним портом - br_single
        Найти порты в одиночны бриджах - int_single_dict
        """
        br_without_ipaddr = self.all_bridges - self.int_ip_addr  # исключаем бриджы на которых есть ip
        bridge_dict = dict(
            [(bridge, []) for bridge in br_without_ipaddr])  # формируем словарь из бриджей, пока без портов
        for bridge, port in self.bridge_port_from_bridges:
            if bridge in bridge_dict:
                bridge_dict[bridge] += [port]

        for bridge, ports in bridge_dict.items():
            if not ports:
                self.br_empty.add(bridge)
            elif len(ports) == 1:
                self.br_single.add(bridge)
                if ports[0] not in self.int_ip_addr:
                    # исключаем интерфейсы которые есть в "ip addresss" и в bonding
                    # DONE! переписать вычитание bonding с учетом проверки на вхождение
                    # int_single.update(exclude_int_in_bonding([ports[0]], bonding))
                    # int = ''.join(exclude_int_in_bonding([ports[0]], bonding))
                    if int := ''.join(self.exclude_int_in_bonding([ports[0]], self.bonding)):
                        type_int = ''
                        if int in self.name_eoip:
                            type_int = 'eoip'
                        elif int in self.vlans:
                            type_int = 'vlan'
                        self.int_single_dict.update({int: type_int})

    def get_vlans_free(self):
        """
        Вывести вланы, не участвующие в бриджах и в "ip addresses"
        """
        res = set()
        res.update(self.exclude_int_in_bonding(self.vlans - self.int_ip_addr -
                                               self.ports_only_from_bridges - self.int_vlans, self.bonding))
        return res


class GeneralParam:

    def __init__(self, mikrot: MikrotikConfig):
        self.value = dict()
        self.mikrotik = mikrot
        self.init_general_param(mikrot)

    def add(self, param_name, description, variable, print_command, disable_command):
        self.value.update({param_name: (description, variable, print_command + '\t' + disable_command)})

    def init_general_param(self, mikrot: MikrotikConfig):
        self.add('--empty', 'Бриджы без портов', mikrot.br_empty,
                 '/interface bridge port print where bridge="{0}"',
                 '/interface bridge disable [find where name="{0}"]')
        self.add('--single', 'Бриджы с одним портом', mikrot.br_single,
                 '/interface bridge port print where bridge="{0}"',
                 '/interface bridge disable [find where name="{0}"]')
        self.add('--intsingle', 'Одиночные интерфейсы в бриджах', mikrot.int_single_dict,
                 '/interface {1} print where name="{0}"',
                 '/interface {1} disable [find where name="{0}"]')
        self.add('--vlans_free', 'Вланы, которых нет ни в бриджах, ни в IP адресах, ни в bonding', mikrot.vlans_free,
                 '/interface vlan print where name="{0}"',
                 '/interface vlan disable [find where name="{0}"]')
        self.add('--eoip_free', 'EOIP, которых нет ни в бриджах, ни во вланах, ни в bonding', mikrot.eoip_free,
                 '/interface eoip print where name="{0}"',
                 '/interface eoip disable [find where name="{0}"]')
        self.add('--ip_free', 'Remote ip адреса из PPP и EOIP которых нет в ТУ и нет в активных PPP', mikrot.ip_free,
                 '/interface eoip print where remote-address={0}',
                 '/interface eoip disable [find where remote-address={0}]')
        self.add('--icmp_false', 'IP из списка --ip_free, не отвечающие на ICMP c ЦМ ', mikrot.icmp_false,
                 '/interface eoip print where remote-address={0}',
                 '/interface eoip disable [find where remote-address={0}]')

    def get_description(self):
        key_param = ''
        for key, value in self.value.items():
            key_param += f'if use key "{key}"\t - {value[0]}\n   '

        return f''' 
        parse_config.exe export_compact.rsc [-tu ip_from_address_plan.txt] [-active ip_ppp_active_from_cm.txt] 
        [{'|'.join(self.value)}] [-out {output_file}]

        export_compact.rsc - файл с конфигурацией, полученный командой /export compact file=export_compact
        -tu file_name - файл с ip адересами из ТУ КРУС
        -active file_name - файл с активными сессиями PPP на, получен командой /ppp active pr file=ip_ppp_active_from_cm

        -out file_name - файл для вывода результата, по-умолчанию {output_file}

        2. {key_param}
        Если ни один ключ не указан выводятся все!

        Пример: parse_config.exe export_compact.rsc -tu ip_from_address_plan.txt \
        -active ip_ppp_active_from_cm.txt -out file.txt
        '''

    def print_interfaces(self, params=None):
        res = ''
        sum = 0
        if params is None:
            params = self.value.keys()
        for param in params:  # Формирование шапки
            count = len(self.value[param][1])
            stroka = f"{self.value[param][0].capitalize()} - {count}\n"
            sum += count
            res += stroka
            # print(stroka)
        stroka = 'Итого: ' + str(sum) + '\n'
        res += stroka
        # print(stroka)

        for param in params:
            variable_for_print = self.value[param][1]
            template_for_print = self.value[param][2]
            s = f"\n---{self.value[param][0]} - {len(variable_for_print)}:\n"
            if template_for_print:  # Проверка наличия шаблона для печати
                # Если значения хранятся в словаре, значит есть доп параметр для печати
                if type(variable_for_print) is dict:
                    for int_name, int_type in variable_for_print.items():
                        s += f"{int_name}\t{template_for_print.format(int_name, int_type)}\n"
                else:
                    for int_name in variable_for_print:
                        s += f"{int_name}\t{template_for_print.format(int_name)}\n"
            else:
                s += '\n'.join(variable_for_print) + '\n'
            res += s
            # print(s)
        # print(f'---Подробная информация в файле ---')
        return res

    def get_output_info(self, param=None):
        output_msg = f'''--- Результат анализа конфигурации %s (%s) г. %s ---"
    Исключены remote ip находящиеся в файлах "{self.mikrotik.file_tu}" и "{self.mikrotik.file_active}" 
    Всего проанализировано: вланов - {len(self.mikrotik.vlans)}, еоип - {len(self.mikrotik.name_eoip)}, \
    бриджей - {len(self.mikrotik.all_bridges)}, порт бриджей - {len(self.mikrotik.ports_only_from_bridges)},\
    бондингов - {len(self.mikrotik.bonding)} 
    '''
        if param:
            text_for_output_in_file = self.print_interfaces(param)
        else:
            text_for_output_in_file = self.print_interfaces()
        return output_msg, text_for_output_in_file


def init_args():
    config_file = argv[1] if len(argv) > 1 else 'export_compact.rsc'
    file_tu = argv[argv.index('-tu') + 1] if '-tu' in argv else 'ip_from_address_plan.txt'
    file_active = argv[argv.index('-active') + 1] if '-active' in argv else 'ip_ppp_active_from_cm.txt'
    output_file = argv[argv.index('-out') + 1] if '-out' in argv else 'output_file.txt'
    if not os.path.exists(config_file):
        print(f'! Error: Конфигурационный файл "{config_file}" не указан или не существует.')
        input('Для выхода нажмите ENTER...', )
        exit()
    if not os.path.exists(file_active):
        print(f'! Warning: Файл с IP адресами из PPP active "{file_active}" не указан или не существует.')
        file_active = ''
    if not os.path.exists(file_tu):
        print(f'! Warning: Файл с IP адресами из ТУ "{file_tu}" не указан или не существует.')
        file_tu = ''
    return config_file, file_tu, file_active, output_file


if __name__ == '__main__':
    config_file, file_tu, file_active, output_file = init_args()

    with open(config_file, encoding='ANSI') as file:
        configure = file.read()

    mikroconfig = MikrotikConfig(configure, file_tu=file_tu, file_active=file_active)
    general_param = GeneralParam(mikroconfig)

    print(general_param.get_description())

    params = argv & general_param.value.keys()

    output_msg, text_for_output_in_file = general_param.get_output_info(params)

    print(output_msg)

    print('\nThe End!')

    with open(output_file, 'w', encoding='ANSI', ) as file:
        file.write(output_msg + text_for_output_in_file)

    # input('For exit press ENTER...', )
    # os.system('pause')
