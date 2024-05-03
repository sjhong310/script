"""
Convert Airbus and Dota annotation files to Json
"""
from PIL import Image
import math
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
        anno(dict): Dota annotation
        image_name(str): Image name of the annotation
    """
    with open(file, 'r') as f:
        dota_annos = [line.strip() for line in f.readlines()][2:]  # Get rid of header info

    image_name = os.path.basename(file).split('.')[0] + '.png'
    anno = {'classes': [], 'objects': []}
    for dota_anno in dota_annos:
        items = dota_anno.split(' ')
        if items[8] != 'plane':  # Read plane only.
            continue
        obj = {'class': items[8],
               'rbbox': list(map(int, items[:8]))
               }
        anno['objects'].append(obj)
        if obj['class'] not in anno['classes']:
            anno['classes'].append(obj['class'])

    return anno, image_name


def read_file_as_json(path, ann_type):
    """Read annotation file as json

     Args:
        path(str): Path to Airbus CSV file or Dota directory
        ann_type(str): Annotation type. types: [Airbus, Dota]
    Returns:
        dataset(dict): Dataset in COCO format.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f'Given path: {path}')

    ann_type = ann_type.lower()
    if ann_type not in ['airbus', 'dota']:
        raise NotImplementedError(f'Given type is not supported: {ann_type}')

    if ann_type == 'airbus':
        annos = read_airbus_csv(path)
    elif ann_type == 'dota':
        annos = dict()
        for p in os.listdir(path):
            anno, fname = read_dota_txt(os.path.join(path, p))
            if anno['objects']:
                annos[fname] = anno

        # # To extract images contain plane in DOTA dataset.
        # home = os.path.dirname(path)
        # new_path = os.path.join(home, 'plane.json')
        # with open(new_path, 'w') as f:
        #     json.dump(list(annos.keys()), f, indent=4)

    dataset = {'info': f"Annotation from {ann_type} dataset",
               'categories': [{
                   'id': 1,  # COCO category id Starts from 1. I will use only 1 category(plane).
                   'name': 'plane',
                   'supercategory': 'plane'
               }],
               'images': [],
               'annotations': []}
    ann_idx = 1
    for img_idx, fname in enumerate(annos.keys()):
        img_path = os.path.join(os.path.dirname(path), 'images', fname)
        width, height = Image.open(img_path).size
        img = {'id': img_idx + 1,
               'width': width,
               'height': height,
               'file_name': fname}
        dataset['images'].append(img)
        for obj in annos[fname]['objects']:
            rbbox = obj['rbbox']
            w = math.sqrt((rbbox[0] - rbbox[2]) ** 2 + (rbbox[1] - rbbox[3]) ** 2)
            h = math.sqrt((rbbox[0] - rbbox[6]) ** 2 + (rbbox[1] - rbbox[7]) ** 2)
            ann = {'id': ann_idx + 1,
                   'image_id': img_idx + 1,
                   'category_id': 1,
                   'bbox': rbbox,
                   'segmentation': [0],
                   'area': round(w * h, 1),
                   'iscrowd': 0}
            ann_idx += 1

            dataset['annotations'].append(ann)

    return dataset


def parse_args():
    parser = argparse.ArgumentParser(description='Convert annotation file of Airbus and Dota format')
    parser.add_argument('file', type=str, help='Files to convert. In case of dota,'
                                               'type directory of dota annotation files.')
    parser.add_argument('type', type=str, choices=['airbus', 'dota'], help='Type of Annotation file.'
                                                                           'Types: [airbus, dota]')
    parser.add_argument('save', type=str, help='Path to a save file')
    args = parser.parse_args()

    if args.type == 'dota' and os.path.isfile(args.file):
        raise Exception('For dota, must input a path to a directory of annotation files.')
    if args.type == 'airbus' and os.path.isdir(args.file):
        raise Exception('For airbus, must input a path to an annotation file.')
    if not os.path.exists(args.file):
        raise FileNotFoundError(f'Input file not found: {args.file}')

    if os.path.isdir(args.save):
        args.save = os.path.join(args.save, f'{args.type}.json')
    else:
        args.save = args.save.split('.')[0] + '.json'
    print('Save file: ', args.save)

    return args


if __name__ == '__main__':
    args = parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)

    dataset = read_file_as_json(args.file, args.type)

    with open(args.save, 'w') as f:
        json.dump(dataset, f, indent=4)

    print('Convert is done.')
