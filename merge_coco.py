"""
Merge coco format Json
"""
import os

import argparse
import json


def merge_json(path):
    """Read COCO json files and merge

     Args:
        path(str): Path to directory
    Returns:
        dataset(dict): Merged dataset in COCO format.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f'Given path: {path}')

    dataset = {'info': f"Merged dataset",
               'categories': [],
               'images': [],
               'annotations': []}

    img_idx = 1
    ann_idx = 1
    cat_idx = 1
    categories = []
    cat_luk = dict()
    for p in os.listdir(path):
        with open(os.path.join(path, p)) as f:
            file = json.load(f)

        for cat in file['categories']:
            if cat['name'] not in categories:  # This may change supercategory but doesn't care it.
                categories.append(cat['name'])
                cat_luk[cat['id']] = cat_idx
                cat['id'] = cat_idx
                dataset['categories'].append(cat)
                cat_idx += 1

        img_luk = dict()
        for img in file['images']:
            img_luk[img['id']] = img_idx
            img['id'] = img_idx
            dataset['images'].append(img)
            img_idx += 1

        for ann in file['annotations']:
            ann['id'] = ann_idx
            ann['image_id'] = img_luk[ann['image_id']]
            ann['category_id'] = cat_luk[ann['category_id']]
            dataset['annotations'].append(ann)
            ann_idx += 1

    return dataset


def parse_args():
    parser = argparse.ArgumentParser(description='Convert annotation file of Airbus and Dota format')
    parser.add_argument('dir', type=str, help='Path to json directory')
    parser.add_argument('save', type=str, help='Path to a save file')
    args = parser.parse_args()

    if not os.path.exists(args.dir):
        raise FileNotFoundError(f'Input directory not found: {args.dir}')

    return args


if __name__ == '__main__':
    args = parse_args()
    os.makedirs(os.path.dirname(args.save), exist_ok=True)

    dataset = merge_json(args.dir)

    with open(args.save, 'w') as f:
        json.dump(dataset, f, indent=4)

    print('Convert is done.')
