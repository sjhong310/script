# Internal functions
import math
import os

# External functions
from osgeo import gdal, gdal_array, osr
import numpy as np

# Source: https://wiki.openstreetmap.org/wiki/Zoom_levels
# zoom level: m/pixel
ZOOM = {0: 156543, 1: 78272, 2: 39136, 3: 19568, 4: 9784, 5: 4892, 6: 2446,
        7: 1223, 8: 611.496, 9: 305.748, 10: 152.874, 11: 76.437, 12: 38.219, 13: 19.109,
        14: 9.555, 15: 4.777, 16: 2.389, 17: 1.194, 18: 0.597, 19: 0.299, 20: 0.149}


class Tile:
    def __init__(self, tile_size=256):
        """Tile class

        Args:
            tile_size(int): Tile size. Length of a width and a height are the same
        """
        self.tile_size = tile_size
        self.rgb = [1]  # TODO: Update for EO in next version.

    def resize_raster(self, ds, zoom_level):
        """Resize an input image based on zoom level

        Resize an image and change its resolution based on zoom level.

        Args:
            ds(gdal.Dataset): Gdal dataset of an input image.
            zoom_level(int): Zoom level.

        Returns:
            resized_ds(gdal.Dataset): Gdal dataset of a resized image
        """
        options = gdal.WarpOptions(xRes=ZOOM[zoom_level],
                                   yRes=ZOOM[zoom_level],
                                   outputType=ds.GetRasterBand(1).DataType)
        resized_ds = gdal.Warp('.proc_tile/resize', ds, options=options)

        return resized_ds

    def lonlat2tile(self, lon_deg, lat_deg, zoom_level):
        """Get tile X, Y index

        Get tile X, Y index which covers given longitude, latitude.
        Source: https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Implementations

        Args:
            lon_deg(float): Longitude in degree.
            lat_deg(float): Latitude in degree.
            zoom_level(int): Zoom level of a tile.

        Returns:
            tile_x(int): X index of a tile.
            tile_y(int): Y index of a tile.
        """
        n = 2 ** zoom_level
        lat_rad = lat_deg * math.pi / 180

        x = int((180 + lon_deg) / 360 * n)
        y = int((1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n)

        return x, y

    def tile2lonlat(self, x, y, zoom_level):
        """Get longitude and latitude of a tile.

        Get minimum lat/lon and maximum lat/lon of a tile.
        Source: https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Implementations

        Args:
            x(int): X index of a tile.
            y(int): Y index of a tile.
            zoom_level(int): Zoom level of a tile.

        Returns:
            (float): lon_deg_min, lat_deg_min, lon_deg_max, lat_deg_max
        """
        n = 2 ** zoom_level
        eps = 1e-8

        # Secure x, y index are in the valid range.
        x %= n
        y %= n

        x2 = x + 1
        y2 = y + 1

        lon_deg_min = x / n * 360 - 180
        lat_rad_max = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg_max = lat_rad_max * 180 / math.pi

        lon_deg_max = x2 / n * 360 - 180 - eps
        lat_rad_min = math.atan(math.sinh(math.pi * (1 - 2 * y2 / n)))
        lat_deg_min = lat_rad_min * 180 / math.pi + eps

        return lon_deg_min, lat_deg_min, lon_deg_max, lat_deg_max

    def create_base_raster(self, ds, zoom_level):
        """Create empty base raster.

        Create base raster having the same attributes as the input dataset.
        Its width and height size are minimum total tile sizes cover a reference raster.

        Args:
            ds(gdal.Dataset): Reference raster.
            zoom_level(int): Zoom level.

        Returns:
            base_ds(gdal.Dataset): Empty dataset.
            (tuple): Tile indexes. (tile_x_tl, tile_y_tl, tile_x_br, tile_y_br)
        """
        interim_ds = gdal.Warp('',
                               ds,
                               dstSRS='EPSG:4326',
                               format='VRT',
                               outputType=ds.GetRasterBand(1).DataType)  # Reproject to EPSG4326 to get lat., lon.

        lon, x_res, _, lat, _, y_res = interim_ds.GetGeoTransform()
        lon_tl = lon
        lon_br = lon + interim_ds.RasterXSize * x_res
        lat_tl = lat
        lat_br = lat + interim_ds.RasterYSize * y_res
        del interim_ds

        tile_x_tl, tile_y_tl = self.lonlat2tile(lon_tl, lat_tl, zoom_level)
        tile_x_br, tile_y_br = self.lonlat2tile(lon_br, lat_br, zoom_level)

        size_x = (tile_x_br - tile_x_tl + 1) * self.tile_size  # Num. of pixels in x direction.
        size_y = (tile_y_br - tile_y_tl + 1) * self.tile_size  # Num. of pixels in y direction.
        lon_tl_base, _, _, lat_tl_base = self.tile2lonlat(tile_x_tl, tile_y_tl, zoom_level)

        # Convert lat./lon. to the target CSR.
        src = osr.SpatialReference()
        src.ImportFromEPSG(4326)
        dst = osr.SpatialReference()
        proj = osr.SpatialReference(wkt=ds.GetProjection())
        epsg = proj.GetAttrValue('AUTHORITY', 1)
        dst.ImportFromEPSG(int(epsg))
        ct = osr.CoordinateTransformation(src, dst)
        x_tl_base, y_tl_base, z = ct.TransformPoint(lat_tl_base, lon_tl_base)
        _, x_res, _, _, _, y_res = ds.GetGeoTransform()
        geotransform = (x_tl_base, x_res, 0, y_tl_base, 0, y_res)

        driver = gdal.GetDriverByName(ds.GetDriver().ShortName)
        base_ds = driver.Create('.proc_tile/base_ds', size_x, size_y, len(self.rgb), ds.GetRasterBand(1).DataType)
        base_ds.SetProjection(ds.GetProjection())
        base_ds.SetGeoTransform(geotransform)
        base_ds.GetRasterBand(1).Fill(0)
        base_ds.GetRasterBand(1).SetNoDataValue(0)

        return base_ds, (tile_x_tl, tile_y_tl, tile_x_br, tile_y_br)

    def cut_tiles(self, img, indexes, output_dir):
        """Cut tiles from d raster and save it on the output directory.

        Args:
            img(ndarray): Image array to cut
            indexes(tuple): Tile indexes. (tile_x_tl, tile_y_tl, tile_x_br, tile_y_br)
            output_dir(str): Path to a zoom-level directory where tiles will be saved.
        """
        size_x = int(img.shape[1] / self.tile_size)
        size_y = int(img.shape[0] / self.tile_size)
        driver = gdal.GetDriverByName('PNG')

        for x in range(size_x):
            path_x = os.path.join(output_dir, str(indexes[0] + x))
            os.makedirs(path_x, exist_ok=True)
            offset_x = x * self.tile_size
            for y in range(size_y):
                offset_y = y * self.tile_size
                if img.ndim == 2:  # img is 1 channel
                    tile = np.zeros([self.tile_size, self.tile_size, 3], dtype=np.uint8)
                    tile[..., 2] = tile[..., 1] = tile[..., 0] = img[offset_y:offset_y+self.tile_size,
                                                                 offset_x:offset_x+self.tile_size]

                else:  # img is 3 channel
                    tile = img[offset_y:offset_y + self.tile_size, offset_x:offset_x + self.tile_size]

                # Generate an image with transparent background
                alpha = np.array(tile, dtype=bool)
                alpha = alpha[..., 0] * alpha[..., 1] * alpha[..., 2] * 255
                alpha = np.expand_dims(alpha, axis=2)
                tile = np.concatenate((tile, alpha), axis=2)
                tile = np.transpose(tile, axes=[2, 0, 1])
                tile = np.uint8(tile)
                gtile = gdal_array.OpenArray(tile)
                name = str(indexes[1] + y) + '.png'
                name = os.path.join(path_x, name)
                driver.CreateCopy(name, gtile)

    def write_tiles(self, ds, zoom_level, output_dir):
        """Write tiles on disk.

        This function calculates tiles and write them on the given output path.

        Args:
            ds(gdal.Dataset): Gdal dataset of an input image.
            zoom_level(int): Zoom level.
            output_dir(str): Path to a zoom-level directory where tiles will be saved.
        """
        resized_ds = self.resize_raster(ds, zoom_level)
        base_ds, indexes = self.create_base_raster(resized_ds, zoom_level)

        offset_x = int((resized_ds.GetGeoTransform()[0] - base_ds.GetGeoTransform()[0]) / resized_ds.GetGeoTransform()[1])
        offset_y = int((base_ds.GetGeoTransform()[3] - resized_ds.GetGeoTransform()[3]) / -resized_ds.GetGeoTransform()[5])  # y resolution is negative

        for idx, band in enumerate(self.rgb):
            s_band = resized_ds.GetRasterBand(band)
            t_band = base_ds.GetRasterBand(idx+1)
            t_band.WriteRaster(offset_x, offset_y, resized_ds.RasterXSize, resized_ds.RasterYSize,
                               s_band.ReadRaster(), resized_ds.RasterXSize, resized_ds.RasterYSize, t_band.DataType)

        img = base_ds.ReadAsArray()
        if len(self.rgb) == 3:
            img = np.transpose(img, axes=[1, 2, 0])
        self.cut_tiles(img, indexes, output_dir)

        gdal.Unlink(base_ds.GetDescription())
        gdal.Unlink(resized_ds.GetDescription())