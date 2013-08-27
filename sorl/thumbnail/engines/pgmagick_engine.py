from functools import wraps

from pgmagick import Blob, ColorspaceType, Geometry, Image, ImageType, ImageList
from pgmagick import InterlaceType, OrientationType
from sorl.thumbnail.engines.base import EngineBase

try:
    from pgmagick._pgmagick import get_blob_data
except ImportError:
    from base64 import b64decode
    def get_blob_data(blob):
        return b64decode(blob.base64())


def imagelist_looper(func):
    def _decorator(self, image, *args):
        if not isinstance(image, ImageList):
            image = [image]
        for image_ in image:
            out = func(self, image_, *args)
            if not out.__class__.__name__ == 'Image':
                return out
        if isinstance(image, list):
            return image[0]
        return image
    return wraps(func)(_decorator)

    
class Engine(EngineBase):
    def get_image(self, source):
        blob = Blob()
        blob.update(source.read())
        if source.name.lower().endswith('.gif'):
            image = ImageList()
            image.readImages(blob)
            image.coalesceImags()
        else:
            image = Image(blob)
        return image
    
    @imagelist_looper
    def get_image_ratio(self, image, options=None):
        return super(Engine, self).get_image_ratio(image, options)
        
    @imagelist_looper
    def get_image_size(self, image):
        geometry = image.size()
        return geometry.width(), geometry.height()

    def is_valid_image(self, raw_data):
        blob = Blob()
        blob.update(raw_data)
        im = Image(blob)
        return im.isValid()
    
    @imagelist_looper
    def _cropbox(self, image, x, y, x2, y2):
        geometry = Geometry(x2-x, y2-y, x, y)
        image.crop(geometry)
        return image
    
    @imagelist_looper
    def _orientation(self, image):
        orientation = image.orientation()
        if orientation == OrientationType.TopRightOrientation:
            image.flop()
        elif orientation == OrientationType.BottomRightOrientation:
            image.rotate(180)
        elif orientation == OrientationType.BottomLeftOrientation:
            image.flip()
        elif orientation == OrientationType.LeftTopOrientation:
            image.rotate(90)
            image.flop()
        elif orientation == OrientationType.RightTopOrientation:
            image.rotate(90)
        elif orientation == OrientationType.RightBottomOrientation:
            image.rotate(-90)
            image.flop()
        elif orientation == OrientationType.LeftBottomOrientation:
            image.rotate(-90)
        image.orientation(OrientationType.TopLeftOrientation)

        return image
    
    @imagelist_looper
    def _colorspace(self, image, colorspace):
        if colorspace == 'RGB':
            image.type(ImageType.TrueColorMatteType)
        elif colorspace == 'GRAY':
            image.type(ImageType.GrayscaleMatteType)
        else:
            return image
        return image
    
    def _scale(self, image, width, height):
        geometry = Geometry(width, height)
        if isinstance(image, ImageList):
            image.scaleImages(geometry)
        else:
            image.scale(geometry)
        return image
    
    @imagelist_looper
    def _crop(self, image, width, height, x_offset, y_offset):
        geometry = Geometry(width, height, x_offset, y_offset)
        image.crop(geometry)
        return image

    def _get_raw_data(self, image, format_, quality, progressive=False):
        blob = Blob()
        if isinstance(image, ImageList):
            image.writeImages(blob)
        else:
            image.magick(format_.encode('utf8'))
            image.quality(quality)
            if format_ == 'JPEG' and progressive:
                image.interlaceType(InterlaceType.LineInterlace)
            image.write(blob)
        return get_blob_data(blob)

