'''
Module with general file operations:
 - work with TAR files
 - work with graphics files (e.g. convert)
'''
import sys
import os
import re
import tarfile
import magic
import commands
from flask import current_app
import timeout_decorator
from invenio_tools import get_converted_image_name
from PIL import Image

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split('(\d+)', text) ]

def untar(tar_archive, bibcode):
    '''
    Check validity of TAR archive and unpack in temporary directory
    :param tar_archive:
    :return:
    '''
    # The list 'tex_files' contains all (La)TeX source files
    tex_files = []
    # The list 'img_files' contains all image files (PNG, JPG, PS, EPS, PDF)
    # UPDATE: we are ignoring PDF files, because more often than not these
    #         fail to convert
    img_files = []
    try:
        contents = [m.name for m in tarfile.open(tar_archive, 'r:*').getmembers()]
    except:
        contents = []
    TMP_DIR = current_app.config.get('GRAPHICS_TMP_DIR')
    extract_dir = "%s/%s" % (TMP_DIR, bibcode)
    t = tarfile.open(tar_archive, 'r:*')
    t.extractall(extract_dir)
    for f in contents:
        extracted_file = "%s/%s" % (extract_dir, f)
        if not os.path.exists(extracted_file):
            sys.stderr.write('File not found: %s\n' % extracted_file)
            continue
        try:
            mtype = magic.from_file(extracted_file)
        except magic.MagicException:
            mtype = 'unknown'
        if mtype.find('TeX') > -1:
            tex_files.append(extracted_file)
        elif mtype.find('image') > -1 or mtype.find('type EPS') > -1 or mtype.lower().find('postscript') > -1:
            img_files.append(extracted_file)
#        elif mtype.find('PDF') > -1:
#            img_files.append(extracted_file)
        else:
            if extracted_file.lower().split('.')[-1] in ['eps', 'png', 'ps', 'jpg']:
                img_files.append(extracted_file)
            else:
                continue
    return tex_files, img_files, extract_dir

def convert_images(image_list):
    done_list = []
    remainder = []
    for image in image_list:
        try:
            mtype = magic.from_file(image)
        except magic.MagicException:
            mtype = 'unknown'
        # Other image type. First construct the name of the target PNG file
        img_dir = os.path.split(image)[0]
        image_name = os.path.split(image)[-1]
        extension = image_name.split('.')[-1].lower()
        # There are cases where folks named there image files like
        # 'image.1', 'image.2', ...
        if extension.isdigit():
            image_name = image_name.replace('.','_')
        # First check if we already have a PNG
        if mtype.find('PNG') > -1 or extension == 'png':
            done_list.append(image)
            continue
        # replace the old extension
        png_image = get_converted_image_name(image)
        try:
            result = convert_to_png_file(image, png_image)
        except timeout_decorator.timeout_decorator.TimeoutError:
            result = {'status':'failure', 'file':image, 'reason':'timeout'}
        if os.path.exists(png_image):
            done_list.append(png_image)
            remainder.append(image)

    done_list.sort(key=natural_keys)
    return remainder, done_list

@timeout_decorator.timeout(15)
def convert_to_png_file(img, png):
#    cmd = '%s "%s" "%s"' % (current_app.config.get('GRAPHICS_CONVERTER'), img, png)
#    res = commands.getstatusoutput(cmd)
#    return res[1]
    result = {'status':'success'}
    try:
        Image.open(img).save(png)
    except Exception, e:
        result = {'status':'failure', 'file':img, 'reason':e}
    return result


