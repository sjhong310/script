"""
Merge xml files in the same directory into coco json file.
"""
import argparse
import cv2
import numpy as np
import os
import xml.etree.ElementTree as ET
import json


def make_empty_json():
    ann = {}
    ann['info'] = {"description": "CONTEC Dataset",
                   "url": "https://www.contec.kr",
                   "version": 2024,
                   "contributor": "Contec",
                   "data_created": 2024
                   }

    ann['licenses'] = {"url": "https://www.contec.kr",
                       "name": "contec"
                       }

    ann['categories'] = [{"supercategory": "tank", "id": 1, "name": "tank"}]

    ann['images'] = []
    ann['annotations'] = []

    return ann


def xml2coco(xml_dir, output):
    img_id = 1
    anno_id = 1
    cat_lut = {'tank': 1}  # 클래스 ID 정의
    coco = make_empty_json()
    for xml in [name for name in os.listdir(xml_dir) if '.xml' in name]:
        tree = ET.parse(os.path.join(xml_dir, xml))
        root = tree.getroot()

        # Fill images
        filename = root.find('filename').text
        size = root.find('size')
        width = int(size[0].text)
        height = int(size[1].text)
        coco['images'].append({'id': img_id,
                               'width': width,
                               'height': height,
                               'file_name': filename + '.png'})
        # Fill annotations of 'filename' image
        for obj in root.findall('object'):
            name = obj.find('name').text
            try:
                # cat_id = cat_lut[name]  # >> 현재 클래스명 검수가 안 되어 있음. 우선 Tank로 믿고 가야 함. Evan쿤.. 코드로 검수해달라고요 ㅠㅠ
                cat_id = 1
            except:
                raise Exception('정의되지 않은 클래스 발견.\nFile: {}\nClass: {}'.format(filename, name))
            bbox = [int(float(x.text)) for x in obj.find('robndbox')][:8]
            area = cv2.contourArea(np.array([[bbox[0], bbox[1]],
                                             [bbox[2], bbox[3]],
                                             [bbox[4], bbox[5]],
                                             [bbox[6], bbox[7]]]))
            coco['annotations'].append({'id': anno_id,
                                        'image_id': img_id,
                                        'category_id': cat_id,
                                        'bbox': bbox,
                                        'segmentation': [0],
                                        'area': area,
                                        'iscrowd': 0})
            anno_id += 1
        img_id += 1

    with open(output, 'w') as f:
        json.dump(coco, f, indent=4)


def main():
    parser = argparse.ArgumentParser(description='parameters')
    parser.add_argument('--xml-dir', type=str, help='Enter the name of input image directory')
    parser.add_argument('--output', type=str, help='Enter the name of input json(COCO Format) directory')
    args = parser.parse_args()

    dirname = os.path.dirname(args.output)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    print(args.output)

    xml2coco(xml_dir=args.xml_dir, output=args.output)


if __name__ == '__main__':
    main()