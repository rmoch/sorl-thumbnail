from sorl.thumbnail.conf import settings, defaults as default_settings
from sorl.thumbnail.helpers import tokey, serialize
from sorl.thumbnail.images import ImageFile, DummyImageFile
from sorl.thumbnail import default
from sorl.thumbnail.parsers import parse_geometry
from sorl.thumbnail.helpers import toint


EXTENSIONS = {
    'JPEG': 'jpg',
    'PNG': 'png',
    'GIF': 'gif',
}

AUTO_FORMATS = ['gif']

class ThumbnailBackend(object):
    """
    The main class for sorl-thumbnail, you can subclass this if you for example
    want to change the way destination filename is generated.
    """
    default_options = {
        'format': settings.THUMBNAIL_FORMAT,
        'quality': settings.THUMBNAIL_QUALITY,
        'colorspace': settings.THUMBNAIL_COLORSPACE,
        'upscale': settings.THUMBNAIL_UPSCALE,
        'alternative_resolutions': settings.THUMBNAIL_ALTERNATIVE_RESOLUTIONS,
        'crop': False,
        'cropbox': None,
        'rounded': None,
    }

    extra_options = (
        ('progressive', 'THUMBNAIL_PROGRESSIVE'),
        ('orientation', 'THUMBNAIL_ORIENTATION'),
    )

    def get_thumbnail(self, file_, geometry_string, **options):
        """
        Returns thumbnail as an ImageFile instance for file with geometry and
        options given. First it will try to get it from the key value store,
        secondly it will create it.
        """
        if not options.get('format'):
            ext = str(file_).split('.')[-1].lower()
            options['format'] = ext.upper() if ext in AUTO_FORMATS else settings.THUMBNAIL_FORMAT
                    
        source = ImageFile(file_)
        for key, value in self.default_options.items():
            options.setdefault(key, value)
        # For the future I think it is better to add options only if they
        # differ from the default settings as below. This will ensure the same
        # filenames beeing generated for new options at default.
        for key, attr in self.extra_options:
            value = getattr(settings, attr)
            if value != getattr(default_settings, attr):
                options.setdefault(key, value)
        name = self._get_thumbnail_filename(source, geometry_string, options)
        thumbnail = ImageFile(name, default.storage)
        cached = default.kvstore.get(thumbnail)
        if cached:
            return cached
        if not thumbnail.exists():
            # We have to check exists() because the Storage backend does not
            # overwrite in some implementations.
            try: 
                source_image = default.engine.get_image(source)
            except IOError:
                if settings.THUMBNAIL_IMAGE_MISSING_DUMMY:
                    return DummyImageFile(geometry_string)
                else:
                    raise
            
            # We might as well set the size since we have the image in memory
            size = default.engine.get_image_size(source_image)
            source.set_size(size)
            self._create_thumbnail(source_image, geometry_string, options,
                                   thumbnail)
            self._create_alternative_resolutions(source, geometry_string,
                                                 options, thumbnail.name)
        # If the thumbnail exists we don't create it, the other option is
        # to delete and write but this could lead to race conditions so I
        # will just leave that out for now.
        default.kvstore.get_or_set(source)
        default.kvstore.set(thumbnail, source)
        return thumbnail

    def delete(self, file_, delete_file=True):
        """
        Deletes file_ references in Key Value store and optionally the file_
        it self.
        """
        image_file = ImageFile(file_)
        if delete_file:
            image_file.delete()
        default.kvstore.delete(image_file)

    def _create_thumbnail(self, source_image, geometry_string, options,
                          thumbnail):
        """
        Creates the thumbnail by using default.engine
        """
        ratio = default.engine.get_image_ratio(source_image, options)
        geometry = parse_geometry(geometry_string, ratio)
        image = default.engine.create(source_image, geometry, options)
        default.engine.write(image, options, thumbnail)
        # It's much cheaper to set the size here
        size = default.engine.get_image_size(image)
        thumbnail.set_size(size)

    def _create_alternative_resolutions(self, source, geometry_string, options, name):
        """
        Creates the thumbnail by using default.engine with multiple output
        sizes.  Appends @<ratio>x to the file name.
        """
        if not options['alternative_resolutions']:
            return
        
        source_image = default.engine.get_image(source)
        ratio = default.engine.get_image_ratio(source_image, options)
        geometry_orig = parse_geometry(geometry_string, ratio)
        file_type = name.split('.')[len(name.split('.'))-1]

        for res in options['alternative_resolutions']:
            geometry = (toint(geometry_orig[0]*res), toint(geometry_orig[1]*res))
            thumbnail_name = name.replace(".%s" % file_type,
                                          "@%sx.%s" % (res, file_type))
            source_image = default.engine.get_image(source)
            image = default.engine.create(source_image, geometry, options)
            thumbnail = ImageFile(thumbnail_name, default.storage)
            default.engine.write(image, options, thumbnail)
            size = default.engine.get_image_size(image)
            thumbnail.set_size(size)

    def _get_thumbnail_filename(self, source, geometry_string, options):
        """
        Computes the destination filename.
        """
        key = tokey(source.key, geometry_string, serialize(options))
        # make some subdirs
        path = '%s/%s/%s' % (key[:2], key[2:4], key)
        return '%s%s.%s' % (settings.THUMBNAIL_PREFIX, path,
                            EXTENSIONS[options['format']])



