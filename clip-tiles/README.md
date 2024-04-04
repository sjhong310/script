# Clip-tiles

Clip-tiles is to make image tiles per zoom level for loading on google openstreetmap.

Zoom level refers to https://wiki.openstreetmap.org/wiki/Zoom_level

Output path structure is [Zoom level]/[X coordinate]/[Y coordinate].png

## How to use

**Description of parameters**

Required
* file: Path to input files. For multi-band, enter in rgb order.
* zoom_min: Minimum zoom level. Minimum zoom level is 0.
* zoom_max: Maximum zoom level. Maximum zoom level is 20.
* output: Path to an output directory.

Options
* epsg_dsc: EPSG code of a target projected coordinate system. Default: 3857
* tile_size: Size of a tile. Default: 256

**Examples**
```
# For SAR
python cliptiles.py K5_201904061_HH.tif 13 17 output_SAR

# For EO
python cliptiles.py K3A_20190129_red.tif K3A_20190129_green.tif K3A_20190129_blue.tif 15 15 output_EO
```

## License

Copyright ©2023 CONTEC, Co., Ltd.