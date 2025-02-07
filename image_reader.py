import argparse
import os
import xml.etree.ElementTree as ET

from osgeo import gdal, ogr, osr
import numpy as np


class ImageReader:
    def __init__(self, img_path, kml_path=None):
        """
        input_image (str): Path to the input image file.
        kml_path (str): Path to the kml file.
        """
        self.dataset = self.get_dataset(img_path)
        if not self.validate_dataset():
            print('좌표계 정보가 존재하지 않는 영상은 사용할 수 없습니다.')
            exit()
        self.kml_path = self.validate_path(kml_path)

    def validate_path(self, path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        return path

    def validate_dataset(self):
        if self.get_epsg():
            return True
        else:
            False

    def subset(self, output_img):
        """
        Extracts a subset of a TIFF file and saves it as a new TIFF file with dimensions [height, width, channel].

        Args:
            output_img (str): Path to save the output subset image file.
        """
        epsg = self.get_epsg()
        if epsg:
            roi = self.get_roi(epsg=epsg)
            subset = gdal.Warp("",
                               self.dataset,
                               outputBounds=[roi[0], roi[3], roi[2], roi[1]],
                               format="MEM")

            # it gets only first 3 bands of the original image.
            subset = gdal.Translate("", subset, format="MEM", bandList=[1, 2, 3])

        else:
            print('좌표계 정보가 존재하지 않는 영상은 사용할 수 없습니다.')
            exit()
            # x_off, y_off, x_size, y_size = 3000, 3000, 1000, 1000  # 기능 개발용 상수
            # subset = gdal.Translate('', self.dataset, srcWin=[x_off, y_off, x_size, y_size], format='MEM')

        # Read as NumPy array and swap axes
        array = subset.ReadAsArray()
        if array.ndim == 3:  # Ensure it's multi-band
            array = np.transpose(array, (1, 2, 0))  # Change from [C, H, W] to [H, W, C]
        if self.dataset.RasterCount != 3:
            array = array[..., :3]  # Assume the channel order is [B, G, R, ...]. Use BGR only.
        array = self.normalize(array)

        # Determine output format based on file extension
        if output_img.lower().endswith(".tif"):
            driver = gdal.GetDriverByName("GTiff")
        elif output_img.lower().endswith(".jp2"):
            driver = gdal.GetDriverByName("JP2OpenJPEG")
        else:
            raise ValueError("Unsupported output format. Use .tif or .jp2")

        for i in range(array.shape[2]):
            subset.GetRasterBand(i + 1).WriteArray(array[..., i])

        driver.CreateCopy(output_img, subset)

    def get_epsg(self, ds=None):
        if ds is None:
            ds = self.dataset
        proj = osr.SpatialReference(wkt=ds.GetProjection())
        epsg = proj.GetAttrValue('AUTHORITY', 1)
        return int(epsg)

    def normalize(self, img, pmin=0.1, pmax=99.9):
        """Stretch and normalize it to the 8 bit image.

        Args:
            img(ndarray): Image array. shape: (height, width, channel)
            pmin(float): Minimum percentile value. Default: 0.1%
            pmax(float): Maximum percentile value. Default: 99.9%
        Returns:
            img_norm(ndarray): Normalised image array. Range of the value is [0, 255].
        """
        img_norm = np.zeros(img.shape)
        for c in range(img.shape[2]):
            band = img[..., c]
            buffer = band[band != 0]
            stretch_min = np.nanpercentile(buffer, pmin)
            stretch_max = np.nanpercentile(buffer, pmax)

            img_norm[..., c] = (band - stretch_min) / (stretch_max - stretch_min) * 255

        img_norm[img_norm < 0] = 0
        img_norm[img_norm > 255] = 255

        return np.array(img_norm, dtype=np.uint16)

    def get_roi(self, epsg=None):
        """
        Get coordinates of a region of interest(roi). The reference coordinate system
        of the kml must be WGS84(=EPSG 4326). If EPSG code is given, it converts coordinates
        to the given coordinate system.

        Args:
            epsg (int): EPSG code of a target image. Default: 4326

        Returns:
            (list(float)): Top-left(lon_min, lat_max), Bottom-right(lon_max, lat_min)
        """
        tree = ET.parse(self.kml_path)
        root = tree.getroot()

        coords = None
        for elm in root.getiterator():
            if 'coordinates' in elm.tag:
                coords = elm.text
                break

        if coords is None:
            print("KML 파일의 형식이 잘못 되었습니다.")
            exit()

        def get_coords(coords):
            for coord in coords.split(' '):
                coord = coord.strip()
                if coord == '':
                    continue
                yield coord.split(',')

        coords = get_coords(coords)
        lon, lat, _ = coords.__next__()
        lon_min = lon_max = float(lon)
        lat_min = lat_max = float(lat)
        for lon, lat, _ in coords:
            lon = float(lon)
            lat = float(lat)

            if lon_min > lon:
                lon_min = lon
            elif lon_max < lon:
                lon_max = lon

            if lat_min > lat:
                lat_min = lat
            elif lat_max < lat:
                lat_max = lat

        if epsg:
            lon_min, lat_min, lon_max, lat_max = self.convert_point(lon_min,
                                                                    lat_min,
                                                                    lon_max,
                                                                    lat_max,
                                                                    dst_epsg=epsg)

        return lon_min, lat_max, lon_max, lat_min

    def convert_point(self, min_x, min_y, max_x, max_y, src_epsg=4326, dst_epsg=32651):
        """
        Convert given lat, lon points to a given epsg system.
        Lat ,lon points must be of WGS84 coordinate system.

        Args:
            min_x (float): Upper left x coordinate
            min_y (float): Lower right y coordinate
            max_x (float): Lower right x coordinate
            max_y (float): Upper left y coordinate
            src_epsg (int): EPSG code of a source system
            dst_epsg (int): EPSG code of a target system
        Returns:
            (list(float)): min_x, min_y, max_x, max_y
        """
        in_rcs = osr.SpatialReference()
        in_rcs.ImportFromEPSG(src_epsg)
        out_rcs = osr.SpatialReference()
        out_rcs.ImportFromEPSG(dst_epsg)

        transform = osr.CoordinateTransformation(in_rcs, out_rcs)
        min_x, min_y, _ = transform.TransformPoint(min_y, min_x)
        max_x, max_y, _ = transform.TransformPoint(max_y, max_x)

        return min_x, min_y, max_x, max_y

    def get_dataset(self, img_paths):
        """
        Args:
            img_paths (list(str)): Path(s) to the input image file.
        Returns:
            dataset (gdal.Dataset): Gdal dataset of the input image.
        """
        for img_path in img_paths:
            self.validate_path(img_path)

        if len(img_paths) > 1:
            dataset = self.merge_bands(img_paths)
        else:
            dataset = gdal.Open(img_paths[0],
                                gdal.GA_ReadOnly)

        return dataset

    def merge_bands(self, paths):
        """Merge bands into one image.

        Args:
            paths(list(str)): Paths to band images. Images must be in order of blue, green, red. shape: (3,)
        Returns:
            ds_merged(gdal.Dataset): Merged image dataset. Band order is [blue, green, red]
        """
        if len(paths) != 3:
            print(f'Number of bands must be 3. Given bands: {len(paths)}')
            exit()

        ds_blue = gdal.Open(paths[0])
        ds_green = gdal.Open(paths[1])
        ds_red = gdal.Open(paths[2])
        ds_list = [ds_blue, ds_green, ds_red]

        # Check availability of merge.
        isProjectionEqual = ds_red.GetProjection() == ds_green.GetProjection() == ds_blue.GetProjection()
        isGeotransformEqual = ds_red.GetGeoTransform() == ds_green.GetGeoTransform() == ds_blue.GetGeoTransform()
        isSizeEqual = ds_red.RasterXSize == ds_green.RasterXSize == ds_blue.RasterXSize and ds_red.RasterYSize == ds_green.RasterYSize == ds_blue.RasterYSize

        if not isProjectionEqual:
            print('Error: 입력 영상들의 좌표계 정보가 서로 동일하지 않습니다.')
            print('입력 영상들의 좌표계는 아래와 같습니다.')
            for idx in range(len(paths)):
                epsg = get_epsg(ds_list[idx])
                print('{}: {}'.format(paths[idx], epsg))
            exit()
        if not isGeotransformEqual:
            print('Error: 입력 영상들의 기하 변환 행렬 정보가 다릅니다.')
            print('입력 영상들의 기하 변환 행렬은 아래와 같습니다.')
            for idx in range(len(paths)):
                print('{}: {}'.format(paths[idx], ds_list[idx].GetGeoTransform()))
            exit()
        if not isSizeEqual:
            print('Error: 입력 영상들의 파일 크기가 다릅니다.')
            print('입력 영상들의 파일 크기는 아래와 같습니다.')
            for idx in range(len(paths)):
                print('{}: [{}, {}]'.format(paths[idx], ds_list[idx].RasterYSize, ds_list[idx].RasterXSize))
            exit()

        # driver = ds_red.GetDriver()
        driver = gdal.GetDriverByName("MEM")
        data_type = ds_blue.GetRasterBand(1).DataType
        ds_merged = driver.Create('', ds_blue.RasterXSize, ds_blue.RasterYSize, 3, data_type)
        ds_merged.SetProjection(ds_blue.GetProjection())
        ds_merged.SetGeoTransform(ds_blue.GetGeoTransform())

        for ind, ds in enumerate(ds_list):
            buffer = ds.GetRasterBand(1).ReadAsArray(buf_type=data_type)
            ds_merged.GetRasterBand(ind + 1).WriteArray(buffer)

        return ds_merged


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path_img', nargs='+', type=str, help='Path to an image. If multiple images are given,'
                                                   'merge them into one image.')
    parser.add_argument('path_kml', type=str, help='Path to a kml file')
    parser.add_argument('--output', type=str, help='Path to save a file')
    args = parser.parse_args()

    if args.output is None:
        path_output = 'subset_' + os.path.basename(args.path_img[0])
    else:
        path_output = args.output

    if not path_output.endswith('tif'):
        path_output = path_output.split('.')[0] + '.tif'
        print('Only .tif is supported for the output at the moment. '
              'Output file will be saved as: {}'.format(path_output))

    reader = ImageReader(args.path_img, args.path_kml)
    reader.subset(path_output)
