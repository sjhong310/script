# Internal functions
from shutil import rmtree
import os

# External functions
from osgeo import gdal
import numpy as np

# Project functions
from .normalization import Normalization
from .sensor import Sensors


class FileIO:
    def __init__(self, sensor):
        """
        Read a TIFF or HDF5 image and write tile images.
        If sensor is not given but norm is True, it applies default normalization function
        which might be inappropriate to the given image.

        Args:
            sensor(str): Satellite name(Optional). Default: None
            norm(bool): Apply normalization to an image(Optional).  Default: True
        """
        self.ds = None
        self.sensor = sensor

    def open(self, path, epsg=None):
        """Open an input file.

        If epsg is given, it transforms input file to the epsg coordinate system.

        Args:
            paths(str): Paths to input files.
            epsg(int): EPSG code of a target projected coordinate system(Optional). Default: None
            #norm(bool): Apply normalization to visualize png file(Optional). Default: True
        """
        os.makedirs('.proc_tile', exist_ok=True)
        fmt = path[0].split('.')[-1]

        if fmt == 'tiff' or fmt == 'tif':
            if len(path) == 1:
                self.ds = gdal.Open(path[0])
            else:
                self.ds = self.merge_bands(path)
        elif fmt == 'h5':
            # Not all hdf5 include metadata in hdf5 file. (KOMPSAT-5, etc.)
            # Need to read Aux.xml
            # ds = gdal.Open(path).GetSubDatasets()[2][0]
            # self.ds = gdal.Open(ds)
            raise NotImplementedError('HDF5 is not supported yet.')
        else:
            raise NotImplementedError(f'Not supported file type: {fmt}')

        self.norm()

        if epsg:
            self.transform_crs(epsg)

    def close(self):
        # Error occurred
        # ERROR 6: WriteBlock() not supported for this dataset.
        self.ds = None
        rmtree('.proc_tile')

    def norm(self):
        """Generate a normalized image

        Normalize band(s) of an image.
        This reduces processing time in case the bands are more than 4.
        """
        if self.sensor is None:
            raise NameError(f'Unknown sensor name.')

        img = np.zeros([self.ds.RasterYSize, self.ds.RasterXSize, self.ds.RasterCount], dtype=np.uint16)
        for idx in range(self.ds.RasterCount):
            img[..., idx] = self.ds.GetRasterBand(idx+1).ReadAsArray()

        img = Normalization(self.sensor)(img)

        # Create a dataset for a normalized image
        driver = gdal.GetDriverByName(self.ds.GetDriver().ShortName)
        base_ds = driver.Create('.proc_tile/norm_ds', self.ds.RasterXSize, self.ds.RasterYSize, self.ds.RasterCount,
                                self.ds.GetRasterBand(1).DataType)
        base_ds.SetProjection(self.ds.GetProjection())
        base_ds.SetGeoTransform(self.ds.GetGeoTransform())
        self.ds = base_ds

        for idx in range(self.ds.RasterCount):
            self.ds.GetRasterBand(idx+1).WriteArray(img[..., idx])

    def transform_crs(self, epsg):
        """Transform a coordinate reference system to a given epsg sysytem.

        Args:
            epsg(int): EPSG code of a target projected coordinate system.
        """
        self.ds = gdal.Warp('', self.ds, dstSRS=f'EPSG:{epsg}', format='VRT',
                            outputType=gdal.GDT_UInt16)  # Reprojected dataset

    def write(self, tile, output_dir, zoom_min, zoom_max):
        """Write tile images to the given path

        Args:
            tile(Tile): Tile class.
            output_dir(str): Path to an output directory.
            zoom_min(int): Minimum zoom level.
            zoom_max(int): Maximum zoom level.
        """
        if not isinstance(self.ds, gdal.Dataset):
            print('Open an input image first.')
            exit()

        for zoom in range(zoom_min, zoom_max+1):
            path_z = os.path.join(output_dir, str(zoom))
            os.makedirs(path_z, exist_ok=True)
            tile.write_tiles(ds=self.ds,
                             zoom_level=zoom,
                             output_dir=path_z)

    def merge_bands(self, paths):
        """Merge bands into one image.

        Args:
            paths(list(str)): Paths to images. Images must be in order of red, green, blue. shape: (3,)
        Returns:
            ds_merged(gdal.Dataset): Merged image dataset.
        """
        if len(paths) != 3:
            print(f'Too less bands are given: {len(paths)}')
            exit()

        ds_red = gdal.Open(paths[0])
        ds_green = gdal.Open(paths[1])
        ds_blue = gdal.Open(paths[2])

        # Check availability of merge.
        isProjectionEqual = ds_red.GetProjection() == ds_green.GetProjection() == ds_blue.GetProjection()
        isGeotransformEqual = ds_red.GetGeoTransform() == ds_green.GetGeoTransform() == ds_blue.GetGeoTransform()
        isSizeEqual = ds_red.RasterXSize == ds_green.RasterXSize == ds_blue.RasterXSize and ds_red.RasterYSize == ds_green.RasterYSize == ds_blue.RasterYSize

        if not isProjectionEqual:
            print('Error: Projection of input images are not the same.')
            exit()
        if not isGeotransformEqual:
            print('Error: Geo-Transform of input images are not the same.')
            exit()
        if not isSizeEqual:
            print('Error: Size of input images are not the same.')
            exit()

        driver = ds_red.GetDriver()
        data_type = ds_red.GetRasterBand(1).DataType
        ds_merged = driver.Create('.proc_tile/merged_bands', ds_red.RasterXSize, ds_red.RasterYSize, 3, data_type)
        ds_merged.SetProjection(ds_red.GetProjection())
        ds_merged.SetGeoTransform(ds_red.GetGeoTransform())

        for ind, ds in enumerate([ds_blue, ds_green, ds_red]):
            buffer = ds.GetRasterBand(1).ReadAsArray(buf_type=data_type)
            ds_merged.GetRasterBand(ind+1).WriteArray(buffer)

        return ds_merged

def get_sensor(name):
    """Get sensor type.

    Args:
        name(str): Name of an image.
    Returns:
        sensor(str): Name of a sensor.
    """
    basename = os.path.basename(name)
    splits = basename.split('_')
    for sensor in Sensors.keys():
        if sensor in splits:
            return sensor
