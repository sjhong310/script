"""Visualize box on .npy image
Read xml file of rolabelImg structure and visualize robndbox on npy image.
To generate gray scale image, use only 1st channel of the image.
"""
import argparse
import cv2
import os
import xml.etree.ElementTree as ET
import numpy as np
import math
import warnings


def draw_box(img_path, xml_path, use_angle=False):
    """Draw robndbox on npy image

    Args:
        img_path(str): Path to .npy image
        xml_path(str): Path to .xml file (rolabelImg structure)
        use_angle(bool): If true, draw box using angle
    Returns:
        drawn_img(ndarray): Gray scale image which robdnboxes are drawn. shape: (h, w, c)
    """
    if not os.path.isfile(xml_path):
        raise FileNotFoundError(f'XML file: {xml_path}')
    if not os.path.isfile(img_path):
        raise FileNotFoundError(f'Image file: {img_path}')

    img = np.load(img_path)
    np.nan_to_num(img, copy=False, nan=0.0)


    # Converting image to gray scale. Range: [0, 255]
    img[..., 0] = (img[..., 0] - np.min(img[..., 0])) / (np.max(img[..., 0]) - np.min(img[..., 0])) * 255
    img[..., 1] = img[..., 0].copy()
    img[..., 2] = img[..., 0].copy()

    with open(xml_path, 'r', encoding='utf-8') as f:
        doc = f.read()
    root = ET.fromstring(doc)

    ps = []
    if use_angle:
        for obj in root.findall('object'):
            box = obj.find('robndbox')
            cx = round(float(box.find('cx').text))
            cy = round(float(box.find('cy').text))
            w = round(float(box.find('w').text))
            h = round(float(box.find('h').text))
            angle = round(float(box.find('angle').text))
            wx, wy = w / 2 * math.cos(angle), w / 2 * math.sin(angle)
            hx, hy = -h / 2 * math.sin(angle), h / 2 * math.cos(angle)
            p1 = (cx - wx - hx, cy - wy - hy)
            p2 = (cx + wx - hx, cy + wy - hy)
            p3 = (cx + wx + hx, cy + wy + hy)
            p4 = (cx - wx + hx, cy - wy + hy)
            ps.append(np.array([p1, p2, p3, p4], dtype=np.int0))
    else:
        for obj in root.findall('object'):
            box = obj.find('robndbox')
            x1 = float(box.find('x1').text)
            x2 = float(box.find('x2').text)
            x3 = float(box.find('x3').text)
            x4 = float(box.find('x4').text)
            y1 = float(box.find('y1').text)
            y2 = float(box.find('y2').text)
            y3 = float(box.find('y3').text)
            y4 = float(box.find('y4').text)
            p1 = (x1, y1)
            p2 = (x2, y2)
            p3 = (x3, y3)
            p4 = (x4, y4)
            ps.append(np.array([p1, p2, p3, p4], dtype=np.int0))

    drawn_img = cv2.drawContours(img, ps, -1, (0, 0, 255), thickness=1)
    drawn_img = np.array(drawn_img, dtype=np.int0)

    return drawn_img


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--img_dir', type=str, help='Directory path to image files')
    parser.add_argument('--xml_dir', type=str, help='Directory path to annotation files')
    parser.add_argument('--save_dir', type=str, help='Path to save dir. If it is not given, '
                                                     'save it on the same hierarchy as home. (Optional)')
    parser.add_argument('--angle', action='store_true', help='Draw boxes using angle')
    args = parser.parse_args()

    return args


def main():
    print('=' * 100)
    print('{:^100}'.format('Visualize robndbox'))
    print('=' * 100)
    print('\n')

    args = parse_args()

    print('Image directory: ', args.img_dir)
    print('Annotation directory: ', args.xml_dir)
    print('Save directory: ', args.save_dir)
    print('Angle: ', args.angle)
    print('\n')

    if args.save_dir is None:
        save_dir = os.path.join(os.path.dirname(os.path.abspath(args.img_dir)), 'Visualization')
    else:
        save_dir = args.save_dir
    os.makedirs(save_dir, exist_ok=True)

    xml_names = [xml_name for xml_name in sorted(os.listdir(args.xml_dir)) if xml_name[-4:] == '.xml']
    if not xml_names:
        print('Path is empty: ', args.xml_dir)
        return -1

    # Checking if every npy file exists.
    for xml_name in xml_names:
        img_name = xml_name[:-4] + '.npy'
        img_path = os.path.join(args.img_dir, img_name)
        if not os.path.isfile(img_path):
            raise FileNotFoundError(f'Image not exists. File: {img_path}')

    for xml_name in xml_names:
        xml_path = os.path.join(args.xml_dir, xml_name)
        img_path = os.path.join(args.img_dir, xml_name[:-4] + '.npy')
        save_path = os.path.join(save_dir, xml_name[:-4] + '.png')

        print('Drawing {}'.format(save_path))
        drawn_img = draw_box(img_path, xml_path, args.angle)
        x = cv2.imwrite(save_path, drawn_img)
        if not x:
            warnings.warn(f'File is not saved: {save_path}')

    print('Done')


if __name__ == '__main__':
    main()
