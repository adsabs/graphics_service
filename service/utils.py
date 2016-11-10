import os
import re
import sys
import glob
import shutil
import commands
import urllib
from operator import itemgetter
import requests
from flask import current_app, request
from client import client
from models import db, GraphicsModel
import file_ops
from datetime import datetime
from invenio_tools import extract_captions, prepare_image_data,\
    extract_context, remove_dups
from aws_tools import get_boto_session

requests.packages.urllib3.disable_warnings()

def get_identifiers(bibstem, year, source):
    """
    :param bibstem:
    :param year:
    :param arXiv:
    :return:
    """
    ids = []
    identifiers = []
    # In the case of arXiv we get the general bibstem arXiv and filter
    # later on the actual bibstem (if this is other than "arXiv")
    if source == 'arXiv':
#        q = 'pub:"ArXiv e-prints" year:%s' % year
        q = 'bibstem:arXiv year:%s' % year
        fl= 'bibcode, eid'
        idtype = 'eid'
    else:
        q = 'bibstem:%s year:%s' % (bibstem, year)
        fl= 'bibcode, identifier, doi'
        idtype = 'identifier'
    solr_args = {'wt': 'json',
                 'q': q,
                 'fl': fl,
                 'rows': 100000}
    headers = {'X-Forwarded-Authorization':
               request.headers.get('Authorization')}
    response = client().get(
        current_app.config.get("GRAPHICS_SOLR_PATH"),
        params=solr_args, headers=headers)

    if response.status_code != 200:
        return []
    resp = response.json()
    for doc in resp['response']['docs']:
        if idtype == 'eid':
            arx_id = doc[idtype]
        else:
            try:
                arx_id = [i for i in doc[idtype] if '/' in i or
                          'arXiv' in i][0]
            except:
                arx_id = None
        doi = doc.get('doi',['NA'])[0]
        try:
            ids.append({'bibcode': doc['bibcode'], 'arxid': arx_id, 'doi':doi})
        except:
            pass
    if source == 'arXiv' and bibstem != 'arXiv':
        identifiers = [b for b in ids if bibstem in b['bibcode'] and
                       b['arxid']]
    elif source == 'arXiv':
        identifiers = [b for b in ids if b['arxid']]
    else:
        identifiers = [b for b in ids]
    return identifiers


def process_IOP_graphics(identifiers, force, dryrun=False):
    """
    For the set of identifiers supplied, retrieve the graphics data.
    If force is false, skip a bibcode if already in the database. The list of
    identifiers is a list of dictionaries because for all records we need the
    bibcode (to check if a record already exists) and the arXiv ID, to find
    the full text TAR archive
    :param bibcodes:
    :param force:
    :return:
    """
    # Regular expression for parsing full text files
    doi_pat = re.compile(
        '''<article-id\s+pub-id-type="doi">(?P<doi>.*?)</article-id>''')
    # Create the mapping from bibcode to full text location
    bibcode2fulltext = {}
    map_file = current_app.config.get('GRAPHICS_FULLTEXT_MAPS').get('IOP')
    with open(map_file) as fh_map:
        for line in fh_map:
            try:
                bibcode, ft_file, source = line.strip().split('\t')
                if ft_file[-3:].lower() == 'xml':
                    bibcode2fulltext[bibcode] = ft_file
            except:
                continue
    # If there is back data for image data, load this
    back_file = current_app.config.get('GRAPHICS_BACK_DATA_FILE').get('IOP')
    id2thumb = {}
    if back_file and os.path.exists(back_file):
        with open(back_file) as back_data:
            for line in back_data:
                doi, id, thumb = line.strip().split(',')
                id2thumb[doi] = thumb
    # Get source name
    src = current_app.config.get('GRAPHICS_SOURCE_NAMES').get('IOP')
    # Now process the records submitted
    nfigs = None
    updates = []
    new = []
    bibcodes = [b['bibcode'] for b in identifiers]
    for bibcode in bibcodes:
        resp = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == bibcode).first()
        if force and resp:
            updates.append(bibcode)
        elif not resp:
            new.append(bibcode)
        else:
            continue
    # First process the updates
    for paper in updates:
        # Get the full text for this article
        ft_file = bibcode2fulltext.get(paper, None)
        if ft_file and os.path.exists(ft_file):
            buffer = open(ft_file).read()
        else:
            # No full text file, skip
            continue
        dmat = doi_pat.search(buffer)
        try:
            DOI = dmat.group('doi')
        except:
            sys.stderr.write('Cannot find DOI: %s\n' % ft_file)
            continue
        nfigs = manage_IOP_graphics(buffer, paper, DOI, src, id2thumb,
                                    update=True, dryrun=dryrun)

    # Next, process the new records
    for paper in new:
        # Get the full text for this article
        ft_file = bibcode2fulltext.get(paper, None)
        if ft_file and os.path.exists(ft_file):
            buffer = open(ft_file).read()
        else:
            # No full text file, skip
            if ft_file:
                sys.stderr.write('Incorrect full text mapping for %s: %s\n'%(paper, ft_file))
            else:
                sys.stderr.write('No full text found for %s\n' % paper)
            continue
        dmat = doi_pat.search(buffer)
        try:
            DOI = dmat.group('doi')
        except:
            sys.stderr.write('Cannot find DOI: %s\n' % ft_file)
            continue
        try:
            nfigs = manage_IOP_graphics(buffer, paper, DOI, src, id2thumb, dryrun=dryrun)
        except Exception, e:
            sys.stderr.write('Error processing %s (%s)\n'%(paper, e))
            continue
    return nfigs

def manage_IOP_graphics(fulltext, bibcode, DOI, source, id2thumb,
                        update=False, dryrun=False):
    # If we're updating, grab the existing database entry
    if update:
        graphic = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == bibcode).first()
    else:
        graphic = None
    # URL templates for thumbnail images and high res images
    thumbURL = "https://s3.amazonaws.com/aasie/images/%s/%s_tb.%s"
    loresURL = "https://s3.amazonaws.com/aasie/images/%s/%s_lr.%s"
    highURL = "http://www.astroexplorer.org/details/%s"
    # Regular expression for parsing full text files
    fig_pat = re.compile(
        r'''<fig(-section)?\s+id="(?P<figID>.*?)"(?P<rest>.*?)>(?P<figure>.*?)
        </fig(-section)?>''', re.VERBOSE | re.DOTALL | re.IGNORECASE)
    lbl_pat = re.compile(
        r'''<label>(?P<label>.*?)</label>''',
        re.VERBOSE | re.DOTALL | re.IGNORECASE)
    cap_pat = re.compile(
        r'''<caption.*?>(?P<caption>.*?)</caption>''',
        re.VERBOSE | re.DOTALL | re.IGNORECASE)
    thumb_pat = re.compile(
        '<graphic\s+id="(?P<id>.*?)"\s+'
        'content-type="thumb"\s+'
        'alt-version="yes"\s+xlink:href="(?P<href>.*?)"/>')
    lores_pat = re.compile(
        '<graphic\s+id="(?P<id>.*?)"\s+'
        'content-type="low"\s+'
        'xlink:href="(?P<href>.*?)"/>')
    figures = []
    # Strip publisher part from DOI to use in thumbnail URL
    art_path = re.sub('^.*?/', '', DOI)
    # Retrieve information for all figures
    cursor = 0
    amat = fig_pat.search(fulltext, cursor)
    while amat:
        fig_data = {}
        images = []
        id = amat.group('figID')
        fg = amat.group('figure')
        lm = lbl_pat.search(fg)
        try:
            label = lm.group('label')
        except:
            label = None
        cm = cap_pat.search(fg)
        try:
            caption = cm.group('caption')
            caption = re.sub('</?(xref|p).*?>', '', caption)
        except:
            caption = None
        fig_data['figure_id'] = id
        fig_data['figure_label'] = label
        fig_data['figure_caption'] = caption
        cs = 0
        imat = thumb_pat.search(fg, cs)
        done = []
        while imat:
            image_id = imat.group('id').split('_')[0]
            format = 'gif'
            if imat.group('href').split('.')[-1].lower() == 'jpg':
                format = 'jpg'
            thumb = id2thumb.get(
                image_id, thumbURL % (art_path, image_id, format))
            # fix for AJ (they use print ISSN in file path, but electronic ISSN
            # in URL
            if bibcode[4:9] == 'AJ...':
                thumb = thumb.replace('0004-6256', '1538-3881')
            # Unfortunately we have to test if the thumbnail URL exists
            check = requests.get(thumb)
            if image_id not in done:
                if int(check.status_code) == 200:
                    images.append({'image_id': image_id,
                               'format': format,
                               'thumbnail': thumb,
                               'highres': highURL % image_id})
                    done.append(image_id)
                else:
                    sys.stderr.write('Thumb URL returned status %s: %s\n'%(check.statuscode, thumb))
            cs = imat.end()
            imat = thumb_pat.search(fg, cs)
        # The images list will be empty for articles mid-2015 on, since it
        # seems that there is no longer a thumbnail entry among the graphics
        # entries. The low-res seems to have taken it place. Therefore we
        # need to parse out those in that case
        if len(images) == 0:
            cs = 0
            imat = lores_pat.search(fg, cs)
            done = []
            while imat:
                image_id = imat.group('id').split('_')[0]
                format = 'gif'
                if imat.group('href').split('.')[-1].lower() == 'jpg':
                    format = 'jpg'
                thumb = id2thumb.get(
                    image_id, thumbURL % (art_path, image_id, format))
                # fix for AJ (they use print ISSN in file path, but electronic ISSN
                # in URL
                if bibcode[4:9] == 'AJ...':
                    thumb = thumb.replace('0004-6256', '1538-3881')
                # Unfortunately we have to test if the thumbnail URL exists
                check = requests.get(thumb)
                if image_id not in done:
                    if int(check.status_code) == 200:
                        images.append({'image_id': image_id,
                                   'format': format,
                                   'thumbnail': thumb,
                                   'highres': highURL % image_id})
                        done.append(image_id)
                    else:
                        sys.stderr.write('Thumb URL returned status %s: %s\n'%(check.statuscode, thumb))
                cs = imat.end()
                imat = lores_pat.search(fg, cs)
        if len(images) > 0:
            fig_data['images'] = images
            figures.append(fig_data)
        cursor = amat.end()
        amat = fig_pat.search(fulltext, cursor)
    if len(figures) > 0 and not dryrun:
        graph_src = current_app.config.get('GRAPHICS_SOURCE_NAMES').get('IOP')
        if update:
            sys.stderr.write('Updating %s\n'%bibcode)
            graphic.source = graph_src
            graphic.figures = figures
            graphic.modtime = datetime.now()
        else:
            sys.stderr.write('Creating new record for %s\n'%bibcode)
            graphic = GraphicsModel(
                bibcode=bibcode,
                doi=DOI,
                source=graph_src,
                eprint=False,
                figures=figures,
                modtime=datetime.now()
            )
            db.session.add(graphic)
        db.session.commit()
    if not dryrun:
        return len(figures)
    else:
        return figures


def process_arXiv_graphics(identifiers, force, dryrun=False):
    """
    For the set of bibcodes supplied, retrieve the graphics data.
    If force is false, skip a bibcode if already in the database.
    :param identifiers:
    :param force:
    :return:
    """
    updates = []
    new = []
    ft_base = current_app.config.get('GRAPHICS_FULLTEXT_MAPS').get('arXiv')
    # Process the identifiers submitted
    for identifier in identifiers:
        resp = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == identifier['bibcode']).first()
        if force and resp:
            updates.append(identifier)
        elif not resp:
            new.append(identifier)
        else:
            continue
    # First process the updates
    yy = '9999'
    aid= '9999'
    cat= 'arXiv'
    for entry in updates:
        paper = entry['arxid']
        bibcode = entry['bibcode']
        if '/' in paper:
            cat = paper.split('/')[0]
            year = paper.split('/')[1][:2]
            if int(year) > 80:
                yy = "19%s" % year
            else:
                yy = "20%s" % year
            aid = paper.split('/')[1]
        elif ':' in paper:
            cat = 'arXiv'
            yy = paper.split(':')[1].split('.')[0]
            aid = paper.split(':')[1].split('.')[1]
        ft_file = "%s/%s/%s/%s.tar.gz" % (ft_base, cat, yy, aid)
        if not os.path.exists(ft_file):
            continue
        # We found a TAR archive to be processed
        res = manage_arXiv_graphics(ft_file, bibcode, paper, cat, dryrun=dryrun, update=True)

    for entry in new:
        paper = entry['arxid']
        bibcode = entry['bibcode']
        if '/' in paper:
            cat = paper.split('/')[0]
            year = paper.split('/')[1][:2]
            if int(year) > 80:
                yy = "19%s" % year
            else:
                yy = "20%s" % year
            aid = paper.split('/')[1]
        elif ':' in paper:
            cat = 'arXiv'
            yy = paper.split(':')[1].split('.')[0]
            aid = paper.split(':')[1].split('.')[1]
        ft_file = "%s/%s/%s/%s.tar.gz" % (ft_base, cat, yy, aid)
        if not os.path.exists(ft_file):
            continue
        # We found a TAR archive to be processed
        res = manage_arXiv_graphics(ft_file, bibcode, paper, cat, dryrun=dryrun)
    return res

def manage_arXiv_graphics(ft_file, bibcode, arx_id, category, update=False, dryrun=False):
    # If we're updating, grab the existing database entry
    if update:
        graphic = db.session.query(GraphicsModel).filter(
                GraphicsModel.bibcode == bibcode).first()
        if not graphic:
            sys.stderr.write('Note: update for %s, but no existing record found!\n'%bibcode)
    else:
        graphic = None
    # First get lists of (La)TeX and image files
    tex_files, img_files, xdir = file_ops.untar(ft_file)
    # If we didn't find any image files, skip
    if len(img_files) == 0:
        return
    figures = []
    # Next convert the image files
    # All the original images than cannot be converted will be
    # removed from the list of originals
    try:
        img_files, converted_images = file_ops.convert_images(img_files)
    except Exception, exc:
        sys.stderr.write('Image conversion barfed for %s. Skipping.\n'%bibcode)
        # Remove the temporary directory
        try:
            shutil.rmtree(xdir)
        except:
            pass
        return
    # We now have a list with successfully converted (PNG) images
    extracted_image_data = []
    for tex_file in tex_files:
        # Extract images, captions and labels
        partly_extracted_image_data = extract_captions(tex_file, xdir,
                                                       img_files)
        if not partly_extracted_image_data == []:
            # Add proper filepaths and do various cleaning
            cleaned_image_data = prepare_image_data(partly_extracted_image_data,
                                                    tex_file, converted_images)

            # Using prev. extracted info, get contexts for each image found
            extracted_image_data.extend((extract_context(tex_file,
                                                         cleaned_image_data)))
    extracted_image_data = remove_dups(extracted_image_data)
    fid = 1
    source2target = {}
    for item in extracted_image_data:
        if not os.path.exists(item[0]) or not item[0].strip():
            continue
        fig_data = {}
        if arx_id.find('arXiv') > -1:
            figure_id = 'arxiv%s_f%s' % (arx_id.replace('arXiv:', ''), fid)
            subdir = arx_id.replace('arXiv:', '').split('.')[0]
            eprdir = arx_id.replace('arXiv:', '').split('.')[1]
        else:
            figure_id = '%s_f%s' % (arx_id.replace('/', '_'), fid)
            subdir = arx_id.split('/')[1][:4]
            eprdir = arx_id.split('/')[1][4:]
        source2target[item[0]] = "%s/%s/%s/%s/%s.png" % (
            current_app.config.get('GRAPHICS_IMAGE_DIR'),
            category,
            subdir,
            eprdir,
            figure_id)
        fig_data['figure_id'] = figure_id
        try:
            fig_data['figure_label'] = item[2].encode('ascii','ignore')
        except:
            fig_data['figure_label'] = ''
        try:
            fig_data['figure_caption'] = item[1].encode('ascii','ignore')
        except:
            fig_data['figure_caption'] = ''
        image_url = "http://arxiv.org/abs/%s" % arx_id.replace('arXiv:','')
        thumb_url = "%s/%s/%s/%s/%s.png/%s" % (
            current_app.config.get('GRAPHICS_BASE_URL'),
            category,
            subdir,
            eprdir,
            figure_id,
            current_app.config.get('GRAPHICS_THMB_PAR'),
        )
        fig_data['images'] = [
            {
                'image_id': fid,
                'format': 'png',
                'thumbnail': thumb_url,
                'highres': image_url
            }
        ]
        figures.append(fig_data)
        fid += 1
    # Now it is time to move the PNGs to their final location, renaming
    # them in the process
    for source, target in source2target.items():
        target_dir, fname = os.path.split(target)
        if not os.path.exists(target_dir):
            cmmd = 'mkdir -p %s' % target_dir
            commands.getoutput(cmmd)
        shutil.copy(source, target)
    # Now it's time to clean up stuff we've extracted
    TMP_DIR = current_app.config.get('GRAPHICS_TMP_DIR')
    extract_dir = "%s/%s" % (TMP_DIR, os.path.basename(ft_file).split('.')[0])
    try:
        shutil.rmtree(extract_dir)
    except:
        pass
    # Finally update the database
    graph_src = current_app.config.get('GRAPHICS_SOURCE_NAMES').get('arXiv')
    if len(figures) > 0 and not dryrun:
        if update:
            sys.stderr.write('Updating %s\n'%bibcode)
            graphic.source = graph_src
            graphic.figures = figures
            graphic.modtime = datetime.now()
        else:
            sys.stderr.write('Creating new record for %s\n'%bibcode)
            try:
                graphic = GraphicsModel(
                    bibcode=bibcode,
                    doi=arx_id,
                    source=graph_src,
                    eprint=True,
                    figures=figures,
                    modtime=datetime.now()
                )
                db.session.add(graphic)
            except Exception, e:
                sys.stderr.write('Failed adding data for %s: %s\n'%(bibcode, e))
        try:
            db.session.commit()
        except Exception, e:
            sys.stderr.write('Data commit failed for %s: %s\n'%(bibcode, e))

    if not dryrun:
        return len(figures)
    else:
        return figures

def process_Elsevier_graphics(identifiers, force, dryrun=False):
    """
    For the set of identifiers supplied, retrieve the graphics data.
    If force is false, skip a bibcode if already in the database. The list of
    identifiers is a list of dictionaries because for all records we need the
    bibcode (to check if a record already exists) and the arXiv ID, to find
    the full text TAR archive
    :param bibcodes:
    :param force:
    :return:
    """
    # Process the records submitted
    nfigs = None
    updates = []
    new = []
    for entry in identifiers:
        resp = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == entry['bibcode']).first()
        if force and resp:
            updates.append(entry)
        elif not resp:
            new.append(entry)
        else:
            continue
    # First process the updates
    for paper in updates:
        nfigs = manage_Elsevier_graphics(paper, update=True, dryrun=dryrun)
    # Next, process the new records
    for paper in new:
        try:
            nfigs = manage_Elsevier_graphics(paper, dryrun=dryrun)
        except Exception, e:
            sys.stderr.write('Error processing %s (%s)\n'%(paper, e))
            continue
    return nfigs

def manage_Elsevier_graphics(record, update=False, dryrun=False):
    # If we're updating, grab the existing database entry
    if update:
        graphic = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == record['bibcode']).first()
    else:
        graphic = None
    # URL templates for thumbnail images
    thumbURL = "http://ars.els-cdn.com/content/image/%s"
    queryURL = "http://api.elsevier.com/content/object/doi/%s"
    figures = []
    # Retrieve graphics info from Elsevier API
    APIkey = current_app.config.get('ELSEVIER_API_KEY')
    headers = {'Accept': 'application/json', 'X-ELS-APIKey': APIkey}
    r = requests.get(queryURL % record.get('doi'), headers=headers)
    try:
        PII = r.json()['attachment-metadata-response']['coredata']['dc:identifier'].replace('PII:','')
    except:
        PII = None
    # Retrieve information for all figures
    try:
        thumbs = [r for r in r.json()['attachment-metadata-response']['attachment'] if r['type'] == 'IMAGE-THUMBNAIL']
    except:
        thumbs = []
    for thumb in thumbs:
        fig_data = {}
        images = []
        try:
            fignr = int(re.sub("[^0-9]", "",thumb['ref']))
        except:
            fignr = re.sub("[^0-9]", "",thumb['ref'])
        fig_data['figure_id'] = thumb['eid']
        fig_data['figure_label'] = "Figure %s" % fignr
        fig_data['figure_caption'] = ''
        fig_data['figure_number'] = fignr
        if PII:
            highres = "http://www.sciencedirect.com/science/article/pii/%s" % PII
        else:
            highres = "http://dx.doi.org/%s" % record['doi']
        image = {'image_id': thumb['eid'], 
                 'thumbnail': thumbURL % thumb['eid'],
                 'format': thumb['mimetype'].split('/')[1],
                 'highres': highres}
        fig_data['images'] = [image]
        figures.append(fig_data)
    figures = sorted(figures, key=itemgetter('figure_number'))
    if len(figures) > 0 and not dryrun:
        graph_src = current_app.config.get('GRAPHICS_SOURCE_NAMES').get('Elsevier')
        if update:
            sys.stderr.write('Updating %s\n'%record['bibcode'])
            graphic.source = graph_src
            graphic.figures = figures
            graphic.modtime = datetime.now()
        else:
            sys.stderr.write('Creating new record for %s\n'%record['bibcode'])
            graphic = GraphicsModel(
                bibcode=record['bibcode'],
                doi=record['doi'],
                source=graph_src,
                eprint=False,
                figures=figures,
                modtime=datetime.now()
            )
            db.session.add(graphic)
        db.session.commit()
    if not dryrun:
        return len(figures)
    else:
        return figures

def process_EDP_graphics(identifiers, force, dryrun=False):
    """
    For the set of identifiers supplied, retrieve the graphics data.
    If force is false, skip a bibcode if already in the database. The list of
    identifiers is a list of dictionaries because for all records we need the
    bibcode (to check if a record already exists) and the arXiv ID, to find
    the full text TAR archive
    :param bibcodes:
    :param force:
    :return:
    """
    # Create the mapping from bibcode to full text location
    bibcode2fulltext = {}
    map_file = current_app.config.get('GRAPHICS_FULLTEXT_MAPS').get('EDP')
    with open(map_file) as fh_map:
        for line in fh_map:
            try:
                bibcode, ft_file, source = line.strip().split('\t')
                if ft_file[-3:].lower() == 'xml':
                    bibcode2fulltext[bibcode] = ft_file
            except:
                continue
    # Get source name
    src = current_app.config.get('GRAPHICS_SOURCE_NAMES').get('EDP')
    # Now process the records submitted
    nfigs = None
    updates = []
    new = []
    for entry in identifiers:
        resp = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == entry['bibcode']).first()
        if force and resp:
            updates.append(entry)
        elif not resp:
            new.append(entry)
        else:
            continue
    # First process the updates
    nfigs = None
    for paper in updates:
        # Get the full text for this article
        fulltext = bibcode2fulltext.get(paper['bibcode'], None)
        if not fulltext:
            # No full text file, skip
            sys.stderr.write('No full text found for %s (update)\n' % paper['bibcode'])
            continue
        try:
             nfigs = manage_EDP_graphics(paper, fulltext, update=True, dryrun=dryrun)
        except Exception, e:
            sys.stderr.write('Error processing update %s (%s)\n'%(paper['bibcocde'], e))
            continue
    # Next, process the new records
    for paper in new:
        # Get the full text for this article
        fulltext = bibcode2fulltext.get(paper['bibcode'], None)
        if not fulltext:
            # No full text file, skip
            sys.stderr.write('No full text found for %s (new record)\n' % paper['bibcode'])
            continue
        try:
            nfigs = manage_EDP_graphics(paper, fulltext, dryrun=dryrun)
        except Exception, e:
            sys.stderr.write('Error processing new %s (%s)\n'%(paper['bibcode'], e))
            continue
    return nfigs

def manage_EDP_graphics(record, ft_file, update=False, dryrun=False):
    # If we're updating, grab the existing database entry
    if update:
        graphic = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == record['bibcode']).first()
    else:
        graphic = None
    # Get the article identifier from the full text file name
    identifier = os.path.basename(ft_file).replace('.xml','')
    # and get the location of the full text files
    srcdir = current_app.config.get('GRAPHICS_GRAPHICS_LOCATION').get('EDP')
    # Get the JPEG files in the source directory
    thumbs = glob.glob('%s/%s/*.jpg'%(srcdir, identifier))
    # Filter out any images with 'small' in the file name
    # and that don't have 'fig' in the file name  
    thumbs = [t for t in thumbs if t.lower().find('fig') > -1 and t.lower().find('small') == -1]
    #thumbs = [t for t in thumbs if t.lower().find('small') > -1]
    # On S3, thumbnails go to
    #  <bucket>/seri/A+A/<volume>/<article ID>
    bucket = current_app.config.get('GRAPHICS_AWS_S3_BUCKET')
    volno = record['bibcode'][9:13].replace('.','0')
    thumb_bucket = "seri/A+A/%s/%s" % (volno, identifier)
    # Create the S3 session and copy over the files
    client = get_boto_session().client('s3')
    # Currently we just process JPEG files
    mimetype = 'image/jpeg'
    # Copy files over to S3
    figures = []
    for thumb in thumbs:
        fig_data = {}
        images = []
        # Try to distill the figure number from file name
        try:
            fignr = int(re.sub('^.*fig(\d+).*',r'\1',os.path.basename(thumb)))
        except:
            fignr = 0
        fig_data['figure_id'] = re.sub('^(.*)\..*',r'\1',os.path.basename(thumb))
        fig_data['figure_label'] = "Figure %s" % fignr
        fig_data['figure_caption'] = ''
        fig_data['figure_number'] = fignr
        highres = "http://dx.doi.org/%s" % record['doi']
        # S3 URL for thumbnail is:
        # https://s3.amazonaws.com/adsabs-thumbnails/seri/A%2BA/0595/aa29175-16/aa29175-16-fig1.jpg
        key = "%s/%s" % (thumb_bucket, os.path.basename(thumb))
        thumbURL = "%s/%s/%s" % (current_app.config.get('GRAPHICS_AWS_S3_URL'), bucket, urllib.quote(key))
        image = {'image_id': re.sub('^(.*)\..*',r'\1',os.path.basename(thumb)),
                 'thumbnail': thumbURL,
                 'format': mimetype.split('/')[1],
                 'highres': highres}
        fig_data['images'] = [image]
        figures.append(fig_data)
        # Upload the image to S3
        try:
            data = open(thumb, 'rb')
        except Exception, e:
            sys.stderr.write('Error loading image data for %s: %s\n' % (thumb, str(e)))
            continue
        client.put_object(Key=key, Bucket=bucket ,Body=data, ACL='public-read', ContentType=mimetype)
    figures = sorted(figures, key=itemgetter('figure_number'))
    if len(figures) > 0 and not dryrun:
        graph_src = current_app.config.get('GRAPHICS_SOURCE_NAMES').get('EDP')
        if update:
            sys.stderr.write('Updating %s\n'%record['bibcode'])
            graphic.source = graph_src
            graphic.figures = figures
            graphic.modtime = datetime.now()
        else:
            sys.stderr.write('Creating new record for %s\n'%record['bibcode'])
            graphic = GraphicsModel(
                bibcode=record['bibcode'],
                doi=record['doi'],
                source=graph_src,
                eprint=False,
                figures=figures,
                modtime=datetime.now()
            )
            db.session.add(graphic)
        db.session.commit()
