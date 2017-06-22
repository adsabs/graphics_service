import sys
import os
import shutil
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)
from flask_testing import TestCase
import app
import time
import timeout_decorator
import unittest

@timeout_decorator.timeout(2)
def test_timeout(s):
    time.sleep(s)
    return s

@unittest.skip("skip update testing (file operations)")
class TestFileOps(TestCase):

    '''Check if config has necessary entries'''

    def create_app(self):
        '''Create the wsgi application'''
        _app = app.create_app()
        _app.config['GRAPHICS_TMP_DIR'] = "%s/tests/stubdata" % PROJECT_HOME
        return _app

#    def test_graphics_converters(self):
#        '''Test if graphics utilities are available'''
#        # Only test this if we enabled graphics updates
#        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
#            return True
#        # Test if the Imagemagick convert utility is where we
#        # claimed it would be
#        converter = self.app.config.get('GRAPHICS_CONVERTER')
#        self.assertTrue(os.path.exists(converter))
#        # Same deal with the mogrify utility
#        rotate = self.app.config.get('GRAPHICS_ROTATE')
#        self.assertTrue(os.path.exists(rotate))

    def test_timeout(self):
        '''Test if timeout decorator works properly'''
        try:
            res = test_timeout(1)
        except timeout_decorator.timeout_decorator.TimeoutError:
            res = 'timeout'
        self.assertEqual(res, 1)
        try:
            res = test_timeout(3)
        except timeout_decorator.timeout_decorator.TimeoutError:
            res = 'timeout'
        self.assertEqual(res, 'timeout')

    def test_graphics_converter(self):
        '''Test if graphics converter works as expected'''
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        from file_ops import convert_to_png_file
        import magic
        img = "%s/tests/stubdata/test_image.jpg" % PROJECT_HOME
        png = "%s/tests/stubdata/test_image.png" % PROJECT_HOME
        # We are converting the test image to a PNG
        res = convert_to_png_file(img, png)
        # Did the PNG get created?
        self.assertTrue(os.path.exists(png))
        # Is it really a PNG?
        mtype = magic.from_file(png)
        self.assertTrue(mtype.find('PNG') > -1)

    def test_unpack_archive(self):
        '''Test unpacking of file archive '''
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        from file_ops import untar
        archive = "%s/tests/stubdata/arXiv/YY/NN.tar.gz" % PROJECT_HOME
        # Let's be sure the test archive really exists 
        self.assertTrue(os.path.exists(archive))
        # Extract the TeX and image sources from the archive
        tex, imgs, sdir = untar(archive)
        # Did we get the expected extraction directory
        expected = "%s/tests/stubdata/NN" % PROJECT_HOME
        self.assertEqual(sdir, expected)
        # Did we get the expected images?
        imgs_expected = ['figure01.ps',
                         'figure02.ps',
                         'figure03.ps',
                         'figure04.ps',
                         'figure05.ps',
                         'figure06.ps',
                         'figure07.ps',
                         'figure08.ps',
                         'figure09.ps']
        self.assertEqual([os.path.basename(i) for i in imgs],
                         imgs_expected)
        # Did we get the expected TeX sources?
        tex_expected = ['2_m51_eng.tex', 'sao1.sty']
        self.assertEqual([os.path.basename(t) for t in tex],
                         tex_expected)
        # Cleanup after us
        extract_dir = archive = "%s/tests/stubdata/NN" % PROJECT_HOME
        shutil.rmtree(extract_dir)

    def test_convert_images(self):
        '''Test converting images to PNG files'''
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        from file_ops import untar
        from file_ops import convert_images
        import magic
        # Assuming the previous tests succeeded, we know we can extract
        # the images fro the archive
        archive = "%s/tests/stubdata/arXiv/YY/NN.tar.gz" % PROJECT_HOME
        tex, imgs, sdir = untar(archive)
        # Now use the update machinery to convert the images to PNGs
        remainder, converted_images = convert_images(imgs)
        # No files should have failed to convert
        self.assertEqual([os.path.basename(i) for i in imgs],
                         [os.path.basename(i) for i in remainder])
        # Did we get the expected PNGs?
        imgs_expected = ['figure01.png',
                         'figure02.png',
                         'figure03.png',
                         'figure04.png',
                         'figure05.png',
                         'figure06.png',
                         'figure07.png',
                         'figure08.png',
                         'figure09.png']
        self.assertEqual([os.path.basename(i) for i in converted_images],
                         imgs_expected)
        # And they really are all PNG files
        res = [magic.from_file(i).find('PNG') > -1 for i in converted_images]
        self.assertTrue(False not in res)

    def test_extract_captions(self):
        '''Test extracting captions'''
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        from file_ops import untar
        from file_ops import convert_images
        from invenio_tools import extract_captions
        from invenio_tools import prepare_image_data
        from invenio_tools import extract_context
        # Assuming the previous tests succeeded, we know we can extract
        # the images fro the archive
        archive = "%s/tests/stubdata/arXiv/YY/NN.tar.gz" % PROJECT_HOME
        tex, imgs, sdir = untar(archive)
        # Now use the update machinery to convert the images to PNGs
        converted_images = convert_images(imgs)
        # Pick the right TeX file
        tex_file = [f for f in tex if f.split('.')[-1] == 'tex'][0]
        # Extract captions
        TMP = self.app.config.get('GRAPHICS_TMP_DIR')
        im_data = extract_captions(tex_file, TMP, converted_images)
        # Did we get what we expected
        expected = ('', 'noimgDistance to M~51', '')
        self.assertEqual(im_data[0], expected)
        # Check cleaned data
        cleaned = prepare_image_data(im_data, tex_file, converted_images)
        self.assertEqual(os.path.basename(cleaned[-1][0]), 'figure09.png')
        self.assertEqual(cleaned[-1][1], 'figure05.ps')
        self.assertEqual(cleaned[-1][2], '')
        # Check extracted context
        context = extract_context(tex_file, cleaned)
        expected = ('', 'noimgDistance to M~51', '', [])
        self.assertEqual(context[0], expected)
        # Cleanup the extracted data
        extract_dir = "%s/NN" % TMP
        shutil.rmtree(extract_dir)
