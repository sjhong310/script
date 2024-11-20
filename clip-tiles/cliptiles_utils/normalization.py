from .registry import Norm
from .sensor import Sensors


class Normalization:
    def __init__(self, sensor):
        """Normalization

        Normalize images applying appropriate normalization function for the sensor.

        Args:
            sensor(str): Satellite name.
        """
        self.sensor = sensor

    def __call__(self, img):
        try:
            norm_func = Sensors[self.sensor]['norm']
        except KeyError:
            raise NotImplementedError(f'Normalization for this sensor is not supported yet: {self.sensor}')

        return Norm.get(norm_func)(img)
