"""Clip tiles.
Generates tile images per zoom level(openstreetmap).
Zoom level: https://wiki.openstreetmap.org/wiki/Zoom_levels
"""
# Internal functions
import argparse
import os

# External functions
from osgeo import osr

# Project functions
from cliptiles_utils import FileIO, Tile, get_sensor


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+', type=str, help='Path to input files. For multi-band, enter in rgb order.')
    parser.add_argument('zoom_min', type=int, help='Minimum zoom level. Minimum zoom level is 0.')
    parser.add_argument('zoom_max', type=int, help='Maximum zoom level. Maximum zoom level is 20.')
    parser.add_argument('output', type=str, help='Path to an output directory.')
    parser.add_argument('--epsg_dsc', type=int, default=3857, help='EPSG code of a target projected coordinate system(Optional). Default: 3857')
    parser.add_argument('--tile_size', type=int, default=256, help='Size of a tile(Optional). Default: 256')
    args = parser.parse_args()

    return args

def main():
    args = parse_args()

    for file in args.files:
        if not os.path.isfile(file):
            print(f'Input file not exist: {file}')
            exit()
    if args.zoom_min < 0:
        print(f'Minimum zoom level must be greater than or the same as 0.')
        exit()
    if args.zoom_max > 20:
        print(f'Minimum zoom level must be less than or the same as 20.')
        exit()
    if args.zoom_min > args.zoom_max:
        print(f'Minimum zoom level must be less than or equal to the maximum zoom level.')
        exit()
    if osr.SpatialReference().ImportFromEPSG(args.epsg_dsc) != 0:
        print(f'Target EPSG code is not supported: {args.epsg_dsc}')
        exit()

    failename = os.path.basename(args.files[0])
    sensor = get_sensor(failename)

    print('=' * 21, 'Input Parameters', '=' * 21)
    print('File: ', args.files)
    print('Sensor: ', sensor)
    print('Target EPSG: ', args.epsg_dsc)
    print('Minimum zoom level: ', args.zoom_min)
    print('Maximum zoom level: ', args.zoom_max)
    print('Output directory: ', args.output)
    print('Tile size: ', args.tile_size)
    print('=' * 60)
    print()

    os.makedirs(args.output, exist_ok=True)

    file_io = FileIO(sensor)
    file_io.open(path=args.files,
                 epsg=args.epsg_dsc)

    file_io.write(tile=Tile(args.tile_size),
                  output_dir=args.output,
                  zoom_min=args.zoom_min,
                  zoom_max=args.zoom_max)

    file_io.close()

if __name__ == '__main__':
    main()
