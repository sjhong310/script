"""
Convert Airbus and Dota annotation files to Json
"""
import os

import argparse
import pandas as pd
import json
import re


def read_airbus_csv(file):
    """Read Airbus CSV file
    Args:
        file(str): Path to Airbus CSV file
    Returns:
        anno(dict): Airbus annotation
    """
    airbus_anno = pd.read_csv(file)

    anno = dict()
    for idx in range(len(airbus_anno)):
        image_id = airbus_anno['image_id'][idx]
        if image_id not in anno.keys():
            anno[image_id] = {'classes': [], 'objects': []}

        obj = {'class': airbus_anno['class'][idx],
               'rbbox': list(map(int, re.findall('\d+', airbus_anno['geometry'][idx])[:8]))
               }
        anno[image_id]['objects'].append(obj)
        if obj['class'] not in anno[image_id]['classes']:
            anno[image_id]['classes'].append(obj['class'])

    return anno


def read_dota_txt(file):
    """Read Dota text file
    Args:
        file(str): Path to Dota text file
    Returns:
        anno(dict): Airbus annotation
    """
    with open(file, 'r') as f:
        dota_annos = [line.strip() for line in f.readlines()][2:]  # Get rid of header info

    anno = dict()
    image_id = os.path.basename(file)
    anno[image_id] = {'classes': [], 'objects': []}
    for dota_anno in dota_annos:
        items = dota_anno.split(' ')
        obj = {'class': items[8],
               'rbbox': list(map(int, items[:8]))
               }
        anno[image_id]['objects'].append(obj)
        if obj['class'] not in anno[image_id]['classes']:
            anno[image_id]['classes'].append(obj['class'])

    return anno


def read_file_as_json(file, type):
    """Read annotation file as json

     Args:
        file(str): Path to Airbus CSV
        type(str): Annotation type. types: [Airbus, Dota]
    Returns:
        jsons(list(dict)): List of Json annotations.
    """
    if not os.path.isfile(file):
        raise FileNotFoundError(f'Path: {file}')

    type = type.lower()
    if type not in ['airbus', 'dota']:
        raise NotImplementedError(f'Type is not suported: {type}')

    if type == 'airbus':
        objs = read_airbus_csv(file)
    elif type == 'dota':
        objs = read_dota_txt(file)

    jsons = []
    for key in objs.keys():
        info = dict()
        info['file'] = key
        info['categories'] = objs[key]['classes']
        info['objects'] = objs[key]['objects']
        jsons.append(info)

    return jsons


def parse_args():
    parser = argparse.ArgumentParser(description='Convert annotation file of Airbus and Dota format')
    parser.add_argument('file', type=str, help='Files to convert. In case of dota,'
                                               'type directory of dota annotation files.')
    parser.add_argument('type', type=str, choices=['airbus', 'dota'], help='Type of Annotation file.'
                                                                           'Types: [airbus, dota]')
    parser.add_argument('save', type=str, help='Save directory')
    args = parser.parse_args()

    if args.type == 'dota' and os.path.isfile(args.file):
        raise Exception('For dota, input directory of annotation files.')
    if args.type == 'airbus' and os.path.isdir(args.file):
        raise Exception('For airbus, input one annotation file.')
    if not os.path.exists(args.file):
        raise FileNotFoundError(f'Input file not found: {args.file}')

    return args


if __name__ == '__main__':
    args = parse_args()
    os.makedirs(args.save, exist_ok=True)

    if args.type == 'airbus':
        jsons = read_file_as_json('airbus_annotations.csv', 'airbus')
        for info in jsons:
            file_path = os.path.join(args.save, info['file'].split('.')[0] + '.json')
            with open(file_path, 'w') as f:
                json.dump(info, f, indent=4)
    elif args.type == 'dota':
        files = os.listdir(args.file)
        for file in files:
            info = read_file_as_json(os.path.join(args.file, file), 'dota')[0]
            file_path = os.path.join(args.save, info['file'].split('.')[0] + '.json')
            with open(file_path, 'w') as f:
                json.dump(info, f, indent=4)

    print('\nConvert is done.\n')
