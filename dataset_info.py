"""Get dataset information

Count number of objects per each category from annotation file.

This code expects below directory structure.
Home_directory
  |-----20210712T095500.xml
  |-----20210805T095616.xml
        .
        .
        .

Annotation file should be structured like below.
<annotation>
  <object>
    <name>ship</name>
    <robndbox>
      <w></w>
      <h></h>
      <angle></angle>
    </robndbox>
  </object>
</annotation>
"""
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
import xmltodict

from tabulate import tabulate
import pandas as pd


def count_objs(xml_path, interval=5):
    """
    Count ships sizes in one xml file

    Args:
        xml_path(str): xml path
        interval(int): Size interval to count objects. Default: 5

    Returns:
        size(dict): Object sizes per size per category. Format: {cat1: {sector1: 0, sector2: 0, ...}, ...}
    """
    sizes = dict()

    with open(xml_path, 'r') as f:
        doc = xmltodict.parse(f.read())

    annotations = doc['annotation']
    objects = annotations['object'] if isinstance(annotations['object'], list) else [annotations['object']]
    for obj in objects:
        name = obj['name']
        if float(obj['robndbox']['h']) > float(obj['robndbox']['w']):
            length = float(obj['robndbox']['h'])
        else:
            length = float(obj['robndbox']['w'])

        if name not in sizes.keys():
            sizes[name] = dict()

        sector = int(length - length % interval)
        if sector not in sizes[name].keys():
            sizes[name][sector] = 0

        sizes[name][sector] += 1

    return sizes


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('home', type=str, help='Directory path to annotation files')
    parser.add_argument('--interval', type=int, default=5, help='Size interval to count objects. Default: 5')
    parser.add_argument('--save_dir', type=str, help='Path to save dir. If it is not given, '
                                                     'save it on the same hierarchy as home. (Optional)')
    args = parser.parse_args()

    return args


def main():
    print('=' * 100)
    print('{:^100}'.format('Getting dataset information'))
    print('=' * 100)
    print('\n')

    args = parse_args()

    if args.save_dir is None:
        save_dir = os.path.dirname(os.path.abspath(args.home))
    else:
        save_dir = args.save_dir

    save_path = os.path.join(save_dir, 'Dataset_Information.csv')
    os.makedirs(save_dir, exist_ok=True)

    sizes = dict()
    xml_paths = [os.path.join(args.home, xml_name) for xml_name in os.listdir(args.home)]
    for xml_path in xml_paths:
        size = count_objs(xml_path, args.interval)
        for cat in size.keys():
            if cat not in sizes.keys():
                sizes[cat] = dict()
            for sector in size[cat].keys():
                if sector not in sizes[cat]:
                    sizes[cat][sector] = 0
                sizes[cat][sector] += size[cat][sector]

    df = pd.DataFrame(sizes)
    df = df.fillna(0).astype(int).transpose().sort_index(axis=0).sort_index(axis=1)

    # Rename value interval to range interval
    rename = dict()
    for sector in df.keys():
        rename[sector] = f'{sector} ~ {sector + args.interval}'
    df = df.rename(columns=rename).transpose()

    # Add total number of each categories
    totals = {'total': dict()}
    for key in df.keys():
        totals['total'][key] = sum(df[key].values)
    totals = pd.DataFrame(totals).transpose()
    df = df.append(totals)

    df.to_csv(save_path)

    table = tabulate(df, headers='keys', tablefmt='simple_grid')
    print(table)


if __name__ == '__main__':
    main()
