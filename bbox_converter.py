import argparse
import os
import numpy as np
import json
import cv2
import math


def cal_line_length(point1, point2):
    """Calculate the length of line.

    Args:
        point1 (List): [x,y]
        point2 (List): [x,y]

    Returns:
        length (float)
    """
    return math.sqrt(
        math.pow(point1[0] - point2[0], 2) +
        math.pow(point1[1] - point2[1], 2))


def get_best_begin_point_single(coordinate):
    """Get the best begin point of the single polygon.

    Args:
        coordinate (List): [x1, y1, x2, y2, x3, y3, x4, y4]

    Returns:
        reorder coordinate (List): [x1, y1, x2, y2, x3, y3, x4, y4]
    """
    x1, y1, x2, y2, x3, y3, x4, y4 = coordinate
    xmin = min(x1, x2, x3, x4)
    ymin = min(y1, y2, y3, y4)
    xmax = max(x1, x2, x3, x4)
    ymax = max(y1, y2, y3, y4)
    combine = [[[x1, y1], [x2, y2], [x3, y3], [x4, y4]],
               [[x2, y2], [x3, y3], [x4, y4], [x1, y1]],
               [[x3, y3], [x4, y4], [x1, y1], [x2, y2]],
               [[x4, y4], [x1, y1], [x2, y2], [x3, y3]]]
    dst_coordinate = [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]]
    force = 100000000.0
    force_flag = 0
    for i in range(4):
        temp_force = cal_line_length(combine[i][0], dst_coordinate[0]) \
                     + cal_line_length(combine[i][1], dst_coordinate[1]) \
                     + cal_line_length(combine[i][2], dst_coordinate[2]) \
                     + cal_line_length(combine[i][3], dst_coordinate[3])
        if temp_force < force:
            force = temp_force
            force_flag = i
    if force_flag != 0:
        pass
    return np.hstack(np.array(combine[force_flag]).reshape(8))


def get_best_begin_point(coordinates):
    """Get the best begin points of polygons.

    Args:
        coordinate (ndarray): shape(n, 8).

    Returns:
        reorder coordinate (ndarray): shape(n, 8).
    """
    coordinates = list(get_best_begin_point_single(coordinates.tolist()))
    coordinates = np.array(coordinates, dtype=np.int32)
    return coordinates


def xyxyxyxy2xywha(bbox):
    """Convert polygons to oriented bounding boxes.

    Angle range is (0, 90]

    Args:
        bbox(list): [x0,y0,x1,y1,x2,y2,x3,y3]

    Returns:
        obbs (ndarray): [x_ctr,y_ctr,w,h,angle]
    """
    bbox = np.array(bbox).reshape((4, 2))
    rbbox = cv2.minAreaRect(bbox)
    x, y, w, h, a = rbbox[0][0], rbbox[0][1], rbbox[1][0], rbbox[1][1], rbbox[2]
    if w < 2 or h < 2:
        return
    while not 0 < a <= 90:
        if a == -90:
            a += 180
        else:
            a += 90
            w, h = h, w
    a = a / 180 * np.pi
    assert 0 < a <= np.pi / 2
    return round(x), round(y), round(w), round(h), a


def xywha2xyxyxyxy(rbbox):
    """Convert oriented bounding boxes to polygons.

        Args:
            rbbox(ndarray): [x_ctr,y_ctr,w,h,angle]

        Returns:
            polys(list): [x0,y0,x1,y1,x2,y2,x3,y3]
        """
    x, y, w, h, a = rbbox
    cosa = np.cos(a)
    sina = np.sin(a)
    wx, wy = w / 2 * cosa, w / 2 * sina
    hx, hy = -h / 2 * sina, h / 2 * cosa
    p1x, p1y = x - wx - hx, y - wy - hy
    p2x, p2y = x + wx - hx, y + wy - hy
    p3x, p3y = x + wx + hx, y + wy + hy
    p4x, p4y = x - wx + hx, y - wy + hy
    polys = np.stack([p1x, p1y, p2x, p2y, p3x, p3y, p4x, p4y], axis=-1)
    polys = get_best_begin_point(polys)
    return polys.tolist()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', type=str, help='Path to a file to convert')
    parser.add_argument('--dsc', type=str, help='Path to a converted file to save')
    parser.add_argument('--mode', default='xyxyxyxy', choices=['xyxyxyxy', 'xywha'], help='The mode of src box coordinate.')
    args = parser.parse_args()

    assert os.path.exists(args.src), FileNotFoundError("File not exists: {}".format(args.src))

    return args


def main():
    args = parse_args()

    with open(args.src, 'r') as f:
        ann = json.load(f)

    if args.mode == 'xyxyxyxy':
        converter = xyxyxyxy2xywha
    else:
        converter = xywha2xyxyxyxy

    for obj in ann['annotations']:
        obj['bbox'] = converter(obj['bbox'])

    with open(args.dsc, 'w') as f:
        json.dump(ann, f, indent=4)


if __name__ == "__main__":
    main()