import numpy as np

def read_img(path, height=0, width=0):
    if path[-4:] == '.img':
        with open(path) as f:
            img = np.fromfile(f, dtype='float16').byteswap()  # SNAP .img
            img = np.reshape(img, [height, width])

    elif path[-4:] == '.npy':
        img = np.load(path)

    img = np.nan_to_num(img)

    return img

def generate_slc(img_i, img_q):
    slc = np.zeros(img_i.shape, dtype='<F')  # csingle == float64 (8byte)
    slc.real = img_i
    slc.imag = img_q
    return slc

def hist_equalization(image, number_bins=256):
    # cut values outside of 2% ~ 98% of image value
    percentile = np.nanpercentile(image, [2, 98])
    image[image > percentile[1]] = percentile[1]
    image[image < percentile[0]] = percentile[0]

    # get image histogram
    image_histogram, bins = np.histogram(image.flatten(), number_bins, density=True)
    cdf = image_histogram.cumsum()  # cumulative distribution function
    cdf = (number_bins-1) * cdf / cdf[-1]  # normalize

    # use linear interpolation of cdf to find new pixel values
    image_equalized = np.interp(image.flatten(), bins[:-1], cdf)
    image_equalized = image_equalized.reshape(image.shape)
    image_equalized = np.int32(image_equalized)

    return image_equalized
