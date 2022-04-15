import json
import os, pandas, numpy
import time


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
    DIR_SERVICE = 'service_excel'
    FILE_SERVICE_MSK = 'Клиенты по аналитич.группам с трафиком ver2 - Москва.xlsx'

    DIR_IP = 'output_icmp_ip_in_tu'
    FILE_IP_MSK = 'summary_ip_in_tu.xlsx'

    DIR_OUTPUT = 'output_ip_service'
    data_service = ExternalDataService(os.path.join(DIR_SERVICE, FILE_SERVICE_MSK),
                                       columns=['ID_STR', 'ID подключения', 'Клиент', '№ договора', 'Текущий тариф',
                                                'Адрес предоставления услуги', 'Услуга', 'Рабочее место (название)',
                                                'IP адрес', 'Маска сети', 'Тип устройства', 'IP Aдрес устройства'],
                                       column_for_check_na='IP Aдрес устройства')
    data_ip = ExternalDataService(os.path.join(DIR_IP, FILE_IP_MSK),
                                  # columns=['ID_STR', 'ID подключения', 'Клиент', '№ договора', 'Текущий тариф',
                                  #          'Адрес предоставления услуги', 'Услуга', 'Рабочее место (название)',
                                  #          'IP адрес', 'Маска сети', 'Тип устройства', 'IP Aдрес устройства'],
                                  # column_for_check_na='IP Aдрес устройства',
                                  )
    # Фильтруем данные только по Москве и удаляем дубликаты IP
    msk_ip_data = data_ip.data[data_ip.data['City']=='Москва'].drop_duplicates(subset=['IP remote CPE'])

    ip_service = pandas.merge(data_service.data, msk_ip_data,
                              left_on='IP Aдрес устройства', right_on='IP remote CPE', how='right')
    ip_service.to_excel(os.path.join(DIR_OUTPUT, 'msk_ip_service.xlsx'))


def main():
    # extract_IP_from_tu_excel()
    extract_IP_from_tu_service()


if __name__ == "__main__":
    main()
