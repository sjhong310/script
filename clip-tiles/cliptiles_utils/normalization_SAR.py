# External functions
from scipy import signal
import numpy as np

# Project functions
from .registry import Norm


@Norm.register_module()
def percentile_sar(img, pmin=2, pmax=98):
    """Convert image to 8bit file.

    Convert image to 8bit file and visualize it for labeling.

    Args:
        img(ndarray): Image array. Shape: (y, x, channel)
        pmin(int): Percentile of minimum value. Default: 2 %
        pmax(int): Percentile of maximum value. Default: 98 %

    Returns:
        img_8bit_med(ndarray): Normalized array.
    """
    # cut values outside of pmin% ~ pmax% of image value
    percentile = np.nanpercentile(img, [pmin, pmax])
    img[img < percentile[0]] = percentile[0]
    img[img > percentile[1]] = percentile[1]

    img_max = np.max(img)
    img_min = np.min(img)
    img_8bit = np.uint16((img - img_min) / (img_max - img_min) * 255)
    if img_8bit.ndim == 3:
        img_8bit_med = np.zeros(img_8bit.shape, dtype=np.uint16)
        for n in range(img_8bit.shape[2]):
            img_8bit_med[..., n] = signal.medfilt2d(img_8bit[..., n], kernel_size=3)
    else:
        img_8bit_med = signal.medfilt2d(img_8bit, kernel_size=3)

    return img_8bit_med