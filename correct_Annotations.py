from xml.dom import minidom
import argparse
import copy
import math
import os
import xml.etree.ElementTree as ET


class Xml:
    def __init__(self, tree):
        """Clone given xml file and empty objects

        Args:
            tree(xml.etree.ElementTree.ElementTree): XML tree object
        """
        self.tree = copy.deepcopy(tree)
        self.root = self.tree.getroot()
        for obj in self.root.findall('object'):
            self.root.remove(obj)

    def add(self, obj):
        """Add object into the xml file

        Args:
            obj(Object): Object to be added
        """
        self.root.append(obj)

    def save(self, path):
        xmlstr = minidom.parseString(ET.tostring(self.root)).toprettyxml(indent='  ')
        xmlstr = "\n".join(line for line in xmlstr.split("\n") if line.strip())
        with open(path, 'w') as f:
            f.write(xmlstr)


def get_shape(obj_box):
    """Get a shape of a box

    Args:
        obj_box(Element): box object

    Returns:
        width(int or float): Width of a box
        height(int or float): Height of a box
    """
    if obj_box.tag == 'bndbox':
        box = [float(value.text) for value in obj_box]  # [xmin, ymin, xmax, ymax] Integer
        width = abs(box[2] - box[0])
        height = abs(box[3] - box[1])
    elif obj_box.tag == 'robndbox':
        box = [float(value.text) for value in obj_box]  # [x1, y1, ..., x4, y4, cx, cy, w, h, angle] Float
        width = box[10]
        height = box[11]
    else:
        raise Exception('Wrong box type: ', obj_box.tag)

    return width, height


def convert_box_type(obj):
    """Convert box type between bndbox and robndbox

    If a given box type is bndbox, return robndbox.
    If a given box type is robndbox, return bndbox.

    Args:
        obj(Element): object having box element

    Returns:
        obj(Element): converted object
    """
    if obj.find('bndbox') is not None:
        box = [round(float(value.text)) for value in obj.find('bndbox')]  # [xmin, ymin, xmax, ymax]
        obj.remove(obj.find('bndbox'))
        robndbox = {'x1': str(box[0]), 'y1': str(box[1]),
                    'x2': str(box[2]), 'y2': str(box[1]),
                    'x3': str(box[2]), 'y3': str(box[3]),
                    'x4': str(box[0]), 'y4': str(box[3]),
                    'cx': str((box[2] - box[0]) / 2),
                    'cy': str((box[3] - box[1]) / 2),
                    'w': str(box[2] - box[0]),
                    'h': str(box[3] - box[1]),
                    'angle': '0.0'}
        e_robndbox = ET.Element('robndbox')
        for key, value in robndbox.items():
            e_sub = ET.SubElement(e_robndbox, key)
            e_sub.text = value
        obj.append(e_robndbox)
        obj.find('type').text = 'robndbox'
    elif obj.find('robndbox') is not None:
        box = [float(value.text) for value in
               obj.find('robndbox')]  # [x1, y1, ..., x4, y4, cx, cy, w, h, angle]
        obj.remove(obj.find('robndbox'))

        xmin, ymin = reverse_rotation(box[0], box[1], box[8], box[9], box[12])
        xmax, ymax = reverse_rotation(box[4], box[5], box[8], box[9], box[12])
        bndbox = {'xmin': str(round(xmin)),
                  'ymin': str(round(ymin)),
                  'xmax': str(round(xmax)),
                  'ymax': str(round(ymax))}
        e_bndbox = ET.Element('bndbox')
        for key, value in bndbox.items():
            e_sub = ET.SubElement(e_bndbox, key)
            e_sub.text = value
        obj.append(e_bndbox)
        obj.find('type').text = 'bndbox'
    else:
        raise Exception('Box type is not supported: ', obj)

    return obj


def restore_robndbox(robndbox):
    """Restore x,y coordinates of a robndbox

    Fill out all attributes that robndboxes must have.

    Args:
        robndbox(Element): robndbox element

    Returns:
        restored_robndbox(Element): restored robndbox element
    """
    cx = float(robndbox.find('cx').text)
    cy = float(robndbox.find('cy').text)
    w = float(robndbox.find('w').text)
    h = float(robndbox.find('h').text)
    angle = float(robndbox.find('angle').text)

    t_xs = [cx - w / 2, cx + w / 2, cx + w / 2, cx - w / 2]
    t_ys = [cy - h / 2, cy - h / 2, cy + h / 2, cy + h / 2]

    xs = []
    ys = []
    for t_x, t_y in zip(t_xs, t_ys):
        x, y = cvt_angle(t_x, t_y, cx, cy, angle)
        xs.append(x)
        ys.append(y)

    new_robndbox = {'x1': str(xs[0]), 'y1': str(ys[0]),
                    'x2': str(xs[1]), 'y2': str(ys[1]),
                    'x3': str(xs[2]), 'y3': str(ys[2]),
                    'x4': str(xs[3]), 'y4': str(ys[3]),
                    'cx': str(cx), 'cy': str(cy),
                    'w': str(w), 'h': str(h),
                    'angle': str(angle)}

    restored_robndbox = ET.Element('robndbox')
    for key, value in new_robndbox.items():
        e_sub = ET.SubElement(restored_robndbox, key)
        e_sub.text = value

    return restored_robndbox


def cvt_angle(x, y, cx, cy, angle):
    """Counter clock-wise rotation

    Args:
        x(list): x coordinates. shape: (4,)
        y(list): y coordinates. shape: (4,)
        cx(float): x center coordinate
        cy(float): y center coordinate
        angle(float): radian angle
    Returns:
        rx(list): rotated x coordinates. shape: (4,)
        ry(list): rotated y coordinates. shape: (4,)
    """
    tx = x - cx
    ty = y - cy

    rx = tx * math.cos(angle) - ty * math.sin(angle) + cx
    ry = ty * math.cos(angle) + tx * math.sin(angle) + cy

    return rx, ry


def reverse_rotation(x, y, cx, cy, angle):
    """Restore original x, y coordinates to which before it was rotated

    Args:
        x(float): x coordinate
        y(float): x coordinate
        cx(float): cx coordinate
        cy(float): cy coordinate
        angle(float): angle

    Returns:
        rx(float): restored x coordinate
        ry(float): restored y coordinate
    """
    tx = x - cx
    ty = y - cy

    rx = tx * math.cos(angle) + ty * math.sin(angle) + cx
    ry = ty * math.cos(angle) - tx * math.sin(angle) + cy

    return rx, ry


def valdiate_obj(obj):
    """Validate object

    Validate if an object has all attributes.
    Attributes : [type, name, pose, truncated, difficult, robndbox or bndbox]

    Sometimes, robndbox's [x, y] coordinates don't exist but [cx, cy, w, h, angle] do.
    In that case, calculate it using its cx, cy, w, h, angle.
    If a robndbox is just empty, return False.

    Args:
        obj(Element): object
    Returns:
        True(bool): If it is validate object otherwise return false
    """
    attributes = [attr.tag for attr in obj]

    if 'type' not in attributes:
        print('type false')
        return False

    if 'name' not in attributes:
        print('name false')
        return False

    if 'bndbox' in attributes:
        attr_box = [attr.tag for attr in obj.find('bndbox')]
        val_attr = ['xmin', 'ymin', 'xmax', 'ymax']
        for attr in val_attr:
            if attr not in attr_box:
                print('bndbox false: ', attr_box)
                return False
    elif 'robndbox' in attributes:
        attr_box = [attr.tag for attr in obj.find('robndbox')]
        val_attr = ['x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4', 'cx', 'cy', 'w', 'h', 'angle']
        restore_attr = ['cx', 'cy', 'w', 'h', 'angle']

        # If any attribute is missed, check if it is restorable
        for v_attr in val_attr:
            if v_attr not in attr_box:
                for r_attr in restore_attr:
                    if r_attr not in attr_box:
                        print('restoration failed')  # temp
                        return False
                break
        restored_robndbox = restore_robndbox(obj.find('robndbox'))
        obj.remove(obj.find('robndbox'))
        obj.append(restored_robndbox)

    return True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('home', help='Directory path where annotations files are located')
    parser.add_argument('sensor', choices=['S1', 'K5'], help='S1: Sentinel-1, K5: KOMPSAT-5')
    args = parser.parse_args()

    return args


def main():
    args = parse_args()

    sensor = args.sensor # S1: Sentinel-1, K5: KOMPSAT-5
    home = os.path.abspath(args.home)
    cor_home = os.path.join(os.path.dirname(home), os.path.basename(home) + '_correction')
    os.makedirs(cor_home, exist_ok=True)

    err_file_path = os.path.join(os.path.dirname(cor_home), 'Error_list.txt')
    cor_file_path = os.path.join(os.path.dirname(cor_home), 'Corrected_list.txt')
    empty_file_path = os.path.join(os.path.dirname(cor_home), 'Empty_list.txt')

    s1_classes = ('ship', 'wind farm')
    k5_classes = ('ship', 'oil tank', 'wind farm', 'floating oil tank', 'fixed oil tank')
    box_classes = {'ship': 'robndbox', 'oil tank': 'bndbox', 'wind farm': 'bndbox', 'floating oil tank': 'bndbox',
                   'fixed oil tank': 'bndbox'}

    sensor_classes = {'K5': k5_classes, 'S1': s1_classes}
    classes = sensor_classes[sensor]

    err_ann = []
    cor_ann = []
    empty_ann = []

    err_info = ''
    cor_info = ''

    # Print script information
    print('=' * 80)
    print('Sensor: ', args.sensor)
    print('Class & Box type')
    for idx, (k, v) in enumerate(box_classes.items()):
        print(f' ({idx+1}) {k}: {v}')
    print('Save path: ', cor_home)
    print('=' * 80)

    print(f'Validating and Correcting {len(os.listdir(home))} files')
    for ann_name in os.listdir(home):
        ann_path = os.path.join(home, ann_name)

        tree = ET.parse(ann_path)
        new_xml = Xml(tree)

        root = tree.getroot()
        objs = root.findall('object')

        if not objs:
            empty_ann.append(ann_name)

        for obj in objs:
            if not valdiate_obj(obj):
                err_info = f'ann: {ann_name}\ncause: Wrong object'
                break
            obj_cls = obj.find('name').text
            if obj_cls in classes:
                if box_classes[obj_cls] != obj.find('type').text:
                    obj = convert_box_type(obj)
                    cor_info = ann_name

                obj_box = obj.find(box_classes[obj_cls])

                width, height = get_shape(obj_box)
                if width * height < 4:
                    err_info = f'ann: {ann_name}\ncause: Wrong box size'
                    break
                else:
                    new_xml.add(obj)
            else:
                err_info = f'ann: {ann_name}\ncause: Wrong class ({obj_cls})'
                break

        if err_info:
            err_ann.append(err_info)
            err_info = ''
            continue

        if cor_info:
            cor_ann.append(ann_name)

        cor_info = ''
        new_xml.save(os.path.join(cor_home, ann_name))

    if err_ann:
        with open(err_file_path, 'w') as f:
            for file in err_ann:
                f.write(file + '\n')

    if cor_ann:
        with open(cor_file_path, 'w') as f:
            for file in cor_ann:
                f.write(file + '\n')

    if empty_ann:
        with open(empty_file_path, 'w') as f:
            for file in empty_ann:
                f.write(file + '\n')

    print('Errors: ', len(err_ann))
    if err_ann:
        print('NOTE: You must check error files and correct it manually')

    print('Corrected: ', len(cor_ann))
    print('Empty: ', len(empty_ann))
    print('Done')





if __name__ == '__main__':
    main()


