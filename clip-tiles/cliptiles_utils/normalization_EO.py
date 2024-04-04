# External functions
import numpy as np

# Project functions
from .registry import Norm


@Norm.register_module()
def percentile_eo(img, pmin=0.1, pmax=99.9):
    """Stretch image

    Args:
        img(ndarray): Image array. shape: (height, width)
        pmin(float): Minimum percentile value. Default: 0.1%
        pmax(float): Maximum percentile value. Default: 99.9%
    Returns:
        img_norm(ndarray): Normalised image array. Value range is [0, 255].
    """
    buffer = img[img != 0]
    stretch_min = np.nanpercentile(buffer, pmin)
    stretch_max = np.nanpercentile(buffer, pmax)

    img_norm = (img - stretch_min) / (stretch_max - stretch_min) * 255
    return img_norm
