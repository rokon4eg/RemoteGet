import json
import os, pandas, numpy
import time


class ExternalData:
    def __init__(self, filename):
        self.data = None
        self.filename = filename
        self.load_data_from_file(self.filename)

    def group_ip_by_city(self):
        """Вернуть список IP для каждого города"""
        framegr = self.data[['Город', 'IP_DEVICE']].groupby('Город')
        res = dict()
        for group in framegr.groups:
            res.update({group: framegr.get_group(group).IP_DEVICE.sort_values().to_list()})
        return res

    def save_ip2files(self, dir=''):
        if not dir:
            dir = 'tu'
        if not os.path.exists(dir):
            os.mkdir(dir)

        group_ip = self.group_ip_by_city()
        for group_name, ip_list in group_ip.items():
            # filename = group_name + '_' + dir + '.txt'
            filename = get_file_name(group_name, dir)
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

    def load_data_from_file(self, filename):
        data = ''
        ext = filename.rsplit(".")[-1]
        if 'xls' in ext and not filename.startswith('~'):
            print('Loading data from', filename, '...')
            now = time.time()
            data = pandas.read_excel(filename,
                                     usecols=['Город', 'NAME_DEVICE', 'IP_DEVICE', 'LOGIN', 'PASSWORD'])
            data = data[~data.IP_DEVICE.isna()]
            print('Success.', 'Elapsed', '%.3s' % (time.time() - now), 'seconds.')
        self.data = data


def get_filelist_from_dir(dir):
    return os.listdir(dir)


def get_file_name(name, dir, ext='txt'):
    '''return -> dir/name_dir.ext'''
    filename = name + '_' + dir + '.' + ext
    return os.path.join(dir, filename)


def save_list2json_file(cm_list, dir, filename):
    with open(os.path.join(dir, filename), 'wt') as file:
        file.write(json.dumps(cm_list))


def load_list_from_json_file(dir, filename):
    with open(os.path.join(dir, filename), 'rt') as file:
        return json.loads(file.read())


def main():
    dir = 'tu_excel'
    # file = 'тест - РНД.xlsx'
    cm_list = []
    file_list = get_filelist_from_dir(dir)
    for file in file_list:
        ext = file.rsplit(".")[-1]
        if 'xls' in ext and not file.startswith('~'):
            extdata = ExternalData(os.path.join(dir, file))
            extdata.save_ip2files('tu')
            cm_list += extdata.get_cm_logipass()
    save_list2json_file(cm_list, dir, 'cm_list.txt')


if __name__ == "__main__":
    main()
