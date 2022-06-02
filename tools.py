import json
import os, pandas, numpy
import time

cities_ekt = ('Екатеринбург', 'Пермь', 'Уфа', 'Хабаровск', 'Тюмень', 'Челябинск', 'Самара', 'Нижний Тагил', 'Ижевск',
              'Тольятти', 'Каменск-Уральский', 'Магнитогорск', 'Сызрань', 'Златоуст', 'Миасс', 'Ванино', 'Киров',
              'Нижневартовск', 'Сургут', 'Курган', 'Сибай')
cities_nsk = ('Новосибирск', 'Барнаул', 'Красноярск', 'Владивосток', 'Иркутск', 'Новокузнецк', 'Омск', 'Оренбург',
              'Йошкар-Ола', 'Тула', 'Комсомольск-на-Амуре', 'Нижний Новгород', 'Томск', 'Кемерово', 'Прокопьевск',
              'Орск', 'Южно-Сахалинск', 'Новомосковск', 'Ангарск', 'Бийск', 'Рубцовск', 'Дзержинск', 'Артём',
              'Чебоксары', 'Иваново', 'Благовещенск', 'Волжск')
cities_spb = ('Санкт-Петербург', 'Пенза', 'Рязань', 'Ульяновск', 'Ярославль', 'Уссурийск', 'Находка', 'Саратов',
              'Димитровград', 'Братск', 'Рыбинск', 'Биробиджан', 'Казань', 'Калуга', 'Белгород', 'Саранск', 'Владимир',
              'Набережные Челны', 'Сыктывкар', 'Орёл', 'Мурманск', 'Череповец', 'Смоленск', 'Псков', 'Брянск',
              'Вологда', 'Тверь', 'Чита', 'Калининград', 'Кострома', 'Архангельск', 'Великий Новгород')
cities_rnd = ('Ростов-на-Дону', 'Воронеж', 'Липецк', 'Волгоград', 'Краснодар', 'Таганрог', 'Шахты', 'Новочеркасск',
              'Астрахань', 'Улан-Удэ', 'Армавир', 'Сочи', 'Новороссийск', 'Махачкала', 'Курск', 'Тамбов', 'Элиста',
              'Ставрополь')
cities_msk = ('Москва',)

SERVERS = {cities_ekt: 'Екатеринбург',
           cities_msk: 'Москва',
           cities_nsk: 'Новосибирск',
           cities_spb: 'Санкт-Петербург',
           cities_rnd: 'Ростов-на-Дону'
           }

SERVICE_FILES = {cities_ekt: 'Клиенты по аналитич.группам с трафиком ver2 - Екатеринбург.xlsx',
                 cities_msk: 'Клиенты по аналитич.группам с трафиком ver2 - Москва.xlsx',
                 cities_nsk: 'Клиенты по аналитич.группам с трафиком ver2 - Новосибирск.xlsx',
                 cities_spb: 'Клиенты по аналитич.группам с трафиком ver2 - Санкт-Петербург.xlsx',
                 cities_rnd: 'Клиенты по аналитич.группам с трафиком ver2 - Ростов на Дону.xlsx'
                 }

TU_FILES = {cities_ekt: 'Устройства с данными для мониторинга - Екатеринбург.xlsx',
            cities_msk: 'Устройства с данными для мониторинга - Москва.xlsx',
            cities_nsk: 'Устройства с данными для мониторинга - Новосибирск.xlsx',
            cities_spb: 'Устройства с данными для мониторинга - СПБ.xlsx',
            cities_rnd: 'Устройства с данными для мониторинга - РНД.xlsx'
            }


class ExtDataBase:
    def __init__(self, filename, columns=None, column_for_check_na=None):
        # self.data = None
        self.filename = filename
        self.columns = columns
        self.data = self.load_data_from_file(column_for_check_na)

    def load_data_from_file(self, column_for_check_na=None):
        data = ''
        ext = self.filename.rsplit(".")[-1]
        if 'xls' in ext and not self.filename.startswith('~'):
            print('Loading data from', self.filename, '...')
            now = time.time()
            data = pandas.read_excel(self.filename,
                                     usecols=self.columns)
            if column_for_check_na:
                data = data[~data[column_for_check_na].isna()]
            print('Success.', 'Elapsed', '%.3s' % (time.time() - now), 'seconds.')
        return data


class ExternalDataTU(ExtDataBase):

    def group_ip_by_city(self):
        """Вернуть список IP для каждого города"""
        framegr = self.data[['Город', 'IP_DEVICE']].groupby('Город')
        res = dict()
        for city in framegr.groups:
            res.update({city: framegr.get_group(city).IP_DEVICE.sort_values().to_list()})
        return res

    def save_ip2files(self, suffix, dir=''):
        if not dir:
            dir = 'tu'
        if not os.path.exists(dir):
            os.mkdir(dir)

        group_ip = self.group_ip_by_city()
        for city, ip_list in group_ip.items():
            # filename = group_name + '_' + dir + '.txt'
            filename = get_file_name(city, suffix, dir)
            with open(filename, 'wt') as file:
                file.write('\n'.join(ip_list))
                print(f'\tSave {len(ip_list)} ip to file {filename}')

    def get_cm_logipass(self):
        """Вернуть список ЦМ:
        Город	NAME_DEVICE	IP_DEVICE	LOGIN	PASSWORD где NAME_DEVICE = eoip%cs """
        cm = self.data[self.data['NAME_DEVICE'].str.contains('eoip') & self.data['NAME_DEVICE'].str.contains('cs')]
        res = list()
        for values in cm.sort_values('Город').values:
            res.append(dict(zip(cm.keys(), values)))
        return res

    def get_ctr_logipass(self):
        """Вернуть список CTR:
        Город	NAME_DEVICE	IP_DEVICE	LOGIN	PASSWORD где NAME_DEVICE = ctr """
        cm = self.data[self.data['NAME_DEVICE'].str.contains('ctr')]
        res = list()
        for values in cm.sort_values('Город').values:
            res.append(dict(zip(cm.keys(), values)))
        return res


class ExternalDataService(ExtDataBase):
    pass


def get_file_name(name, suffix, dir, ext='txt'):
    '''return -> dir/name_dir.ext'''
    filename = name + '_' + suffix + '.' + ext
    return os.path.join(dir, filename)


def save_list2json_file(cm_list, dir, filename):
    with open(os.path.join(dir, filename), 'wt') as file:
        file.write(json.dumps(cm_list))


def save_list2excel_file(cm_list, dir, filename):
    cm_json = json.dumps(cm_list)
    data = pandas.read_json(cm_json)
    data.to_excel(os.path.join(dir, filename))


def load_list_from_json_file(dir, filename):
    with open(os.path.join(dir, filename), 'rt') as file:
        return json.loads(file.read())


def load_list_from_excel_file(dir, filename):
    data = pandas.read_excel(filename)
    with open(os.path.join(dir, filename), 'rt') as file:
        return json.loads(file.read())


def list_split(ip_list, base):
    if isinstance(ip_list, set):
        ip_list = list(ip_list)
    res = []
    if len(ip_list) > base:
        slice = len(ip_list) // base + 1
    else:
        slice = 1
    for i in range(slice):
        res.append(ip_list[base * i:base * (i + 1)])
    return res


def extract_IP_from_tu_excel():
    dir = 'tu_excel'
    # file = 'тест - РНД.xlsx'
    cm_list = []
    ctr_list = []
    # file_list = os.listdir(dir)
    file_list = ['Устройства с данными для мониторинга - Москва.xlsx']
    for file in file_list:
        ext = file.rsplit(".")[-1]
        if 'xls' in ext and not file.startswith('~'):
            extdata = ExternalDataTU(os.path.join(dir, file),
                                     columns=['Город', 'NAME_DEVICE', 'IP_DEVICE', 'LOGIN', 'PASSWORD'],
                                     column_for_check_na='IP_DEVICE')
            extdata.save_ip2files('tu')
            # cm_list += extdata.get_cm_logipass()
            ctr_list += extdata.get_ctr_logipass()
    # save_list2json_file(cm_list, dir, 'cm_list.txt')
    # save_list2excel_file(cm_list, dir, 'cm_list.xlsx')
    save_list2excel_file(ctr_list, '', 'ctr_list.xlsx')


def extract_IP_from_tu_service():
    """
    К содержимому файла {FILE_IP_TU} основываясь на "Remote IP" добавляет данные из файла с услугами и с данными из ТУ
    Результат сохраняет в "summary_ip_service.xlsx"
    """
    DIR_SERVICE = 'service_excel'
    DIR_TU = 'tu_excel'
    # FILE_SERVICE_MSK = 'Клиенты по аналитич.группам с трафиком ver2 - Москва.xlsx'

    DIR_IP = 'output_icmp_ip_in_tu'
    FILE_IP_TU = 'summary_ip_in_tu.xlsx'

    DIR_OUTPUT = 'output_ip_service'
    data_ip = ExternalDataService(os.path.join(DIR_IP, FILE_IP_TU),
                                  # columns=['ID_STR', 'ID подключения', 'Клиент', '№ договора', 'Текущий тариф',
                                  #          'Адрес предоставления услуги', 'Услуга', 'Рабочее место (название)',
                                  #          'IP адрес', 'Маска сети', 'Тип устройства', 'IP Aдрес устройства'],
                                  # column_for_check_na='IP Aдрес устройства',
                                  )
    summary_ip_services = pandas.core.frame.DataFrame()
    for server in SERVERS:
        print(f'Анализ городов на сервере {SERVERS[server]}.')
        data_service = ExternalDataService(os.path.join(DIR_SERVICE, SERVICE_FILES[server]),
                                           columns=['ID_STR', 'ID подключения', 'Статус подключения', 'Клиент',
                                                    '№ договора', 'Текущий тариф', 'Адрес предоставления услуги',
                                                    'Услуга', 'Рабочее место (название)', 'IP адрес', 'Маска сети',
                                                    'Тип устройства', 'IP Aдрес устройства'],
                                           column_for_check_na='IP Aдрес устройства')
        data_tu = ExternalDataService(os.path.join(DIR_TU, TU_FILES[server]),
                                      columns=['Город', 'ID_DEVICE', 'NAME_DEVICE', 'IP_DEVICE', 'ADDRESS',
                                               'TYPE_NAME', 'Услуги'],
                                      column_for_check_na='IP_DEVICE')
        # Фильтруем данные только по Городу и удаляем дубликаты IP
        for city in server:
            print(f'Фильтруем по городу {city}')
            city_ip_cpe = data_ip.data[data_ip.data['City'] == city].drop_duplicates(subset=['IP remote CPE'])
            city_ip_service = pandas.merge(city_ip_cpe, data_service.data,
                                           right_on='IP Aдрес устройства', left_on='IP remote CPE', how='left')
            columns = list(city_ip_service.columns)
            columns.remove('IP Aдрес устройства')
            if city_ip_service[city_ip_service['ID_STR'].notna()]['ID_STR'].count() > 0:
                city_ip_service[city_ip_service['ID_STR'].notna()][columns].to_excel(os.path.join(DIR_OUTPUT,
                                                                                                  city + '_ip_service.xlsx'))
            # ip_service = pandas.merge(data_service.data, city_ip_data,
            #                           left_on='IP Aдрес устройства', right_on='IP remote CPE', how='right')
            # city_ip_service_and_tu = pandas.merge(city_ip_service[columns], data_tu.data[data_tu.data['Город'] == city],
            city_ip_service_and_tu = pandas.merge(city_ip_service[columns], data_tu.data,
                                                  left_on='IP remote CPE',
                                                  right_on='IP_DEVICE', how='left')
            summary_ip_services = pandas.concat([summary_ip_services, city_ip_service_and_tu])
    summary_ip_services.to_excel(os.path.join(DIR_OUTPUT, 'summary_ip_service.xlsx'))


def analyzeDynamicICMP(dir_path, file_mask, output_file):
    import glob

    def filter_good(df, column):
        # Отбираем успешные ICMP запросы
        return (df[column]).values.astype(str) > 'Успешно'

    def filter_bad(df, column):
        # Отбираем не успешные ICMP запросы
        return (df[column]).values.astype(str) < 'Успешно'

    def analyze_column(df, column):
        # Успешные ICMP запросы помечаем 1, не успешные - 0
        df[column][filter_bad(df, column)] = 0
        df[column][filter_good(df, column)] = 1

    file_list = glob.glob1(dir_path, f'{file_mask}')
    all_city_icmp_data = None
    for file in file_list:
        city_name = file[:file.find('_')]
        city_icmp = ExtDataBase(os.path.join(dir_path, file),
                                # columns=['Город', 'NAME_DEVICE', 'IP_DEVICE', 'LOGIN', 'PASSWORD'],
                                # column_for_check_na='IP_DEVICE')
                                )
        for column in city_icmp.data.columns[1:-3]:
            analyze_column(city_icmp.data, column)

        ip_list = []
        city_name_list = []
        cmikrotik_name_list = []
        cmikrotik_ip_list = []

        icmp_sum_list = []
        icmp_sum_last7_list = []
        for row in city_icmp.data.iterrows():
            row_val = row[1]
            ip_list.append(row_val[0])
            city_name_list.append(row_val['City'])
            cmikrotik_name_list.append(row_val['CMikroTik Name'])
            cmikrotik_ip_list.append(row_val['CMikroTik IP'])

            # сумма всех значений, за исключением трех столбцов - City, CMikroTik Name, CMikroTik IP
            icmp_sum_list.append(row_val[1:-3].sum())
            try:
                # сумма последних семи значений, за исключением трех столбцов - City, CMikroTik Name, CMikroTik IP
                icmp_sum_last7_list.append(row_val[-4:-11:-1].sum())
            except BaseException:
                icmp_sum_last7_list.append('Error')

        d = {'Remote IP': ip_list,
             'CityCM': city_name_list,
             'CMikroTik Name': cmikrotik_name_list,
             'CMikroTik IP': cmikrotik_ip_list,
             'ICMP TOTAL': len(city_icmp.data.columns) - 4,
             'TRUE ICMP ALL TIME': icmp_sum_list,
             'TRUE ICMP LAST WEEK': icmp_sum_last7_list}
        city_icmp_data = pandas.read_json(json.dumps(d))
        if all_city_icmp_data is None:
            all_city_icmp_data = city_icmp_data
        else:
            all_city_icmp_data = pandas.concat([all_city_icmp_data, city_icmp_data])

    all_city_icmp_data.to_excel(os.path.join(dir_path, output_file))


def main():
    # extract_IP_from_tu_excel()
    # extract_IP_from_tu_service()
    # analyzeDynamicICMP('output_icmp_ip_free_new', 'Кемерово*', 'temp_summary_ip_free_dynamic.xlsx')
    analyzeDynamicICMP('output_icmp_ip_free_new', '[!~$]*icmp_ip_free*', 'summary_ip_free_dynamic.xlsx')
    analyzeDynamicICMP('output_icmp_ip_in_tu_new', '[!~$]*icmp_ip_in_tu*', 'summary_ip_in_tu_dynamic.xlsx')


if __name__ == "__main__":
    main()
