# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2010, 2011 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
import os
import re
import sys
import codecs
import commands
from flask import current_app
import timeout_decorator

MAIN_CAPTION_OR_IMAGE = 0
SUB_CAPTION_OR_IMAGE = 1
CFG_PLOTEXTRACTOR_CONTEXT_EXTRACT_LIMIT = 750
CFG_PLOTEXTRACTOR_CONTEXT_SENTENCE_LIMIT = 2
CFG_PLOTEXTRACTOR_CONTEXT_WORD_LIMIT = 75
CFG_PLOTEXTRACTOR_DISALLOWED_TEX = [
    'begin', 'end', 'section', 'includegraphics', 'caption',
    'acknowledgements',
]

def extract_captions(tex_file, sdir, image_list, primary=True):
    """
    Take the TeX file and the list of images in the tarball (which all,
    presumably, are used in the TeX file) and figure out which captions
    in the text are associated with which images
    @param: lines (list): list of lines of the TeX file

    @param: tex_file (string): the name of the TeX file which mentions
        the images
    @param: sdir (string): path to current sub-directory
    @param: image_list (list): list of images in tarball
    @param: primary (bool): is this the primary call to extract_caption?

    @return: images_and_captions_and_labels ([(string, string, list),
        (string, string, list), ...]):
        a list of tuples representing the names of images and their
        corresponding figure labels from the TeX file
    """
    if os.path.isdir(tex_file) or not os.path.exists(tex_file):
        return []
    fd = open(tex_file)
    lines = fd.readlines()
    fd.close()
    # possible figure lead-ins
    figure_head = '\\begin{figure'  # also matches figure*
    figure_tail = '\\end{figure'  # also matches figure*
    picture_head = '\\begin{picture}'
    displaymath_head = '\\begin{displaymath}'
    subfloat_head = '\\subfloat'
    subfig_head = '\\subfigure'
    includegraphics_head = '\\includegraphics'
    epsfig_head = '\\epsfig'
    input_head = '\\input'
    # possible caption lead-ins
    caption_head = '\\caption'
    figcaption_head = '\\figcaption'
    label_head = '\\label'
    rotate = 'rotate='
    angle = 'angle='
    eps_tail = '.eps'
    ps_tail = '.ps'

    doc_head = '\\begin{document}'
    doc_tail = '\\end{document}'

    extracted_image_data = []
    cur_image = ''
    caption = ''
    labels = []
    active_label = ""

    # cut out shit before the doc head
    if primary:
        for line_index in range(len(lines)):
            if lines[line_index].find(doc_head) < 0:
                lines[line_index] = ''
            else:
                break

    # are we using commas in filenames here?
    commas_okay = False
    for dummy1, dummy2, filenames in \
            os.walk(os.path.split(os.path.split(tex_file)[0])[0]):
        for filename in filenames:
            if filename.find(',') > -1:
                commas_okay = True
                break

    # a comment is a % not preceded by a \
    comment = re.compile("(?<!\\\\)%")

    for line_index in range(len(lines)):
        # get rid of pesky comments by splitting where the comment is
        # and keeping only the part before the %
        line = comment.split(lines[line_index])[0]
        line = line.strip()
        lines[line_index] = line

    in_figure_tag = 0

    for line_index in range(len(lines)):
        line = lines[line_index]

        if line == '':
            continue
        if line.find(doc_tail) > -1:
            return extracted_image_data

        """
        FIGURE -
        structure of a figure:
        \begin{figure}
        \formatting...
        \includegraphics[someoptions]{FILENAME}
        \caption{CAPTION}  %caption and includegraphics may be switched!
        \end{figure}
        """

        index = line.find(figure_head)
        if index > -1:
            in_figure_tag = 1
            # some punks don't like to put things in the figure tag.  so we
            # just want to see if there is anything that is sitting outside
            # of it when we find it
            cur_image, caption, extracted_image_data = put_it_together(
                cur_image, caption, active_label, extracted_image_data,
                line_index, lines)

        # here, you jerks, just make it so that it's fecking impossible to
        # figure out your damn inclusion types

        index = max([line.find(eps_tail), line.find(ps_tail),
                     line.find(epsfig_head)])
        if index > -1:
            if line.find(eps_tail) > -1 or line.find(ps_tail) > -1:
                ext = True
            else:
                ext = False
            filenames = intelligently_find_filenames(line, ext=ext,
                                                     commas_okay=commas_okay)

            # try to look ahead!  sometimes there are better matches after
            if line_index < len(lines) - 1:
                filenames.extend(intelligently_find_filenames(
                    lines[line_index + 1], commas_okay=commas_okay))
            if line_index < len(lines) - 2:
                filenames.extend(intelligently_find_filenames(
                    lines[line_index + 2], commas_okay=commas_okay))

            for filename in filenames:
                filename = str(filename)
                if cur_image == '':
                    cur_image = filename
                elif type(cur_image) == list:
                    if type(cur_image[SUB_CAPTION_OR_IMAGE]) == list:
                        cur_image[SUB_CAPTION_OR_IMAGE].append(filename)
                    else:
                        cur_image[SUB_CAPTION_OR_IMAGE] = [filename]
                else:
                    cur_image = ['', [cur_image, filename]]

#        """
#        Rotate and angle
#        """
#        index = max(line.find(rotate), line.find(angle))
#        if index > -1:
#            # which is the image associated to it?
#            filenames = intelligently_find_filenames(
#                line, commas_okay=commas_okay)
#            # try the line after and the line before
#            if line_index + 1 < len(lines):
#                filenames.extend(intelligently_find_filenames(
#                    lines[line_index + 1], commas_okay=commas_okay))
#            if line_index > 1:
#                filenames.extend(intelligently_find_filenames(
#                    lines[line_index - 1], commas_okay=commas_okay))
#            already_tried = []
#            for filename in filenames:
#                if filename != 'ERROR' and not filename in already_tried:
#                    if rotate_image(filename, line, sdir, image_list):
#                        break
#                    already_tried.append(filename)
#
        """
        INCLUDEGRAPHICS -
        structure of includegraphics:
        \includegraphics[someoptions]{FILENAME}
        """
        index = line.find(includegraphics_head)
        if index > -1:
            open_curly, open_curly_line, close_curly, dummy = \
                find_open_and_close_braces(line_index, index, '{', lines)
            filename = lines[open_curly_line][open_curly + 1:close_curly]
            if cur_image == '':
                cur_image = filename
            elif type(cur_image) == list:
                if type(cur_image[SUB_CAPTION_OR_IMAGE]) == list:
                    cur_image[SUB_CAPTION_OR_IMAGE].append(filename)
                else:
                    cur_image[SUB_CAPTION_OR_IMAGE] = [filename]
            else:
                cur_image = ['', [cur_image, filename]]

        """
        {\input{FILENAME}}
        \caption{CAPTION}

        This input is ambiguous, since input is also used for things like
        inclusion of data from other LaTeX files directly.
        """
        index = line.find(input_head)
        if index > -1:
            new_tex_names = intelligently_find_filenames(line, TeX=True,
                                                         commas_okay=commas_okay)
            for new_tex_name in new_tex_names:
                if new_tex_name != 'ERROR':
                    new_tex_file = get_tex_location(new_tex_name, tex_file)
                    if new_tex_file and primary: #to kill recursion
                        extracted_image_data.extend(extract_captions(
                                                    new_tex_file, sdir,
                                                    image_list,
                                                    primary=False))

        """PICTURE"""

        index = line.find(picture_head)
        if index > -1:
            # structure of a picture:
            # \begin{picture}
            # ....not worrying about this now
            #write_message('found picture tag')
            #FIXME
            pass

        """DISPLAYMATH"""

        index = line.find(displaymath_head)
        if index > -1:
            # structure of a displaymath:
            # \begin{displaymath}
            # ....not worrying about this now
            #write_message('found displaymath tag')
            #FIXME
            pass

        """
        CAPTIONS -
        structure of a caption:
        \caption[someoptions]{CAPTION}
        or
        \caption{CAPTION}
        or
        \caption{{options}{CAPTION}}
        """

        index = max([line.find(caption_head), line.find(figcaption_head)])
        if index > -1:
            open_curly, open_curly_line, close_curly, close_curly_line = \
                find_open_and_close_braces(line_index, index, '{', lines)

            cap_begin = open_curly + 1

            cur_caption = assemble_caption(open_curly_line, cap_begin,
                                           close_curly_line, close_curly, lines)

            if caption == '':
                caption = cur_caption
            elif type(caption) == list:
                if type(caption[SUB_CAPTION_OR_IMAGE]) == list:
                    caption[SUB_CAPTION_OR_IMAGE].append(cur_caption)
                else:
                    caption[SUB_CAPTION_OR_IMAGE] = [cur_caption]
            elif caption != cur_caption:
                caption = ['', [caption, cur_caption]]

        """
        SUBFLOATS -
        structure of a subfloat (inside of a figure tag):
        \subfloat[CAPTION]{options{FILENAME}}

        also associated with the overall caption of the enclosing figure
        """

        index = line.find(subfloat_head)
        if index > -1:
            # if we are dealing with subfloats, we need a different
            # sort of structure to keep track of captions and subcaptions
            if type(cur_image) != list:
                cur_image = [cur_image, []]
            if type(caption) != list:
                caption = [caption, []]

            open_square, open_square_line, close_square, close_square_line = \
                find_open_and_close_braces(line_index, index, '[', lines)
            cap_begin = open_square + 1

            sub_caption = assemble_caption(open_square_line,
                                           cap_begin, close_square_line, close_square, lines)
            caption[SUB_CAPTION_OR_IMAGE].append(sub_caption)

            open_curly, open_curly_line, close_curly, dummy = \
                find_open_and_close_braces(close_square_line,
                                           close_square, '{', lines)
            sub_image = lines[open_curly_line][open_curly + 1:close_curly]

            cur_image[SUB_CAPTION_OR_IMAGE].append(sub_image)

        """
        SUBFIGURES -
        structure of a subfigure (inside a figure tag):
        \subfigure[CAPTION]{
        \includegraphics[options]{FILENAME}}

        also associated with the overall caption of the enclosing figure
        """

        index = line.find(subfig_head)
        if index > -1:
            # like with subfloats, we need a different structure for keepin
            # track of this stuff
            if type(cur_image) != list:
                cur_image = [cur_image, []]
            if type(caption) != list:
                caption = [caption, []]

            open_square, open_square_line, close_square, close_square_line = \
                find_open_and_close_braces(line_index, index, '[', lines)
            cap_begin = open_square + 1

            sub_caption = assemble_caption(open_square_line,
                                           cap_begin, close_square_line,
                                           close_square, lines)
            caption[SUB_CAPTION_OR_IMAGE].append(sub_caption)

            index_cpy = index

            # find the graphics tag to get the filename
            # it is okay if we eat lines here
            index = line.find(includegraphics_head)
            while index == -1 and (line_index + 1) < len(lines):
                line_index += 1
                line = lines[line_index]
                index = line.find(includegraphics_head)
            if line_index == len(lines):
                # didn't find the image name on line
                line_index = index_cpy

            open_curly, open_curly_line, close_curly, dummy = \
                find_open_and_close_braces(line_index,
                                           index, '{', lines)
            sub_image = lines[open_curly_line][open_curly + 1:close_curly]

            cur_image[SUB_CAPTION_OR_IMAGE].append(sub_image)

        """
        LABELS -
        structure of a label:
        \label{somelabelnamewhichprobablyincludesacolon}

        Labels are used to tag images and will later be used in ref tags
        to reference them.  This is interesting because in effect the refs
        to a plot are additional caption for it.

        Notes: labels can be used for many more things than just plots.
        We'll have to experiment with how to best associate a label with an
        image.. if it's in the caption, it's easy.  If it's in a figure, it's
        still okay... but the images that aren't in figure tags are numerous.
        """
        index = line.find(label_head)
        if index > -1 and in_figure_tag:
            open_curly, open_curly_line, close_curly, dummy =\
                find_open_and_close_braces(line_index,
                                           index, '{', lines)
            label = lines[open_curly_line][open_curly + 1:close_curly]
            if label not in labels:
                active_label = label
            labels.append(label)

        """
        FIGURE

        important: we put the check for the end of the figure at the end
        of the loop in case some pathological person puts everything in one
        line
        """
        index = max([line.find(figure_tail), line.find(doc_tail)])
        if index > -1:
            in_figure_tag = 0
            cur_image, caption, extracted_image_data = \
                    put_it_together(cur_image, caption, active_label, extracted_image_data,
                                    line_index, lines)
        """
        END DOCUMENT

        we shouldn't look at anything after the end document tag is found
        """

        index = line.find(doc_tail)
        if index > -1:
            break

    return extracted_image_data


def put_it_together(cur_image, caption, context, extracted_image_data, line_index,
                    lines):
    """
    Takes the current image(s) and caption(s) and assembles them into
    something useful in the extracted_image_data list.

    @param: cur_image (string || list): the image currently being dealt with, or
        the list of images, in the case of subimages
    @param: caption (string || list): the caption or captions currently in scope
    @param: extracted_image_data ([(string, string), (string, string), ...]):
        a list of tuples of images matched to captions from this document.
    @param: line_index (int): the index where we are in the lines (for
        searchback and searchforward purposes)
    @param: lines ([string, string, ...]): the lines in the TeX

    @return: (cur_image, caption, extracted_image_data): the same arguments it
        was sent, processed appropriately
    """

    if type(cur_image) == list:
        if cur_image[MAIN_CAPTION_OR_IMAGE] == 'ERROR':
            cur_image[MAIN_CAPTION_OR_IMAGE] = ''
        for image in cur_image[SUB_CAPTION_OR_IMAGE]:
            if image == 'ERROR':
                cur_image[SUB_CAPTION_OR_IMAGE].remove(image)

    if cur_image != '' and caption != '':

        if type(cur_image) == list and type(caption) == list:

            if cur_image[MAIN_CAPTION_OR_IMAGE] != '' and\
                    caption[MAIN_CAPTION_OR_IMAGE] != '':
                extracted_image_data.append(
                    (cur_image[MAIN_CAPTION_OR_IMAGE],
                     caption[MAIN_CAPTION_OR_IMAGE],
                     context))
            if type(cur_image[MAIN_CAPTION_OR_IMAGE]) == list:
                # why is the main image a list?
                # it's a good idea to attach the main caption to other
                # things, but the main image can only be used once
                cur_image[MAIN_CAPTION_OR_IMAGE] = ''

            if type(cur_image[SUB_CAPTION_OR_IMAGE]) == list:
                if type(caption[SUB_CAPTION_OR_IMAGE]) == list:
                    for index in \
                            range(len(cur_image[SUB_CAPTION_OR_IMAGE])):
                        if index < len(caption[SUB_CAPTION_OR_IMAGE]):
                            long_caption = \
                                caption[MAIN_CAPTION_OR_IMAGE] + ' : ' + \
                                caption[SUB_CAPTION_OR_IMAGE][index]
                        else:
                            long_caption = \
                                caption[MAIN_CAPTION_OR_IMAGE] + ' : ' + \
                                'Caption not extracted'
                        extracted_image_data.append(
                            (cur_image[SUB_CAPTION_OR_IMAGE][index],
                             long_caption, context))

                else:
                    long_caption = caption[MAIN_CAPTION_OR_IMAGE] + \
                        ' : ' + caption[SUB_CAPTION_OR_IMAGE]
                    for sub_image in cur_image[SUB_CAPTION_OR_IMAGE]:
                        extracted_image_data.append(
                            (sub_image, long_caption, context))

            else:
                if type(caption[SUB_CAPTION_OR_IMAGE]) == list:
                    long_caption = caption[MAIN_CAPTION_OR_IMAGE]
                    for sub_cap in caption[SUB_CAPTION_OR_IMAGE]:
                        long_caption = long_caption + ' : ' + sub_cap
                    extracted_image_data.append(
                        (cur_image[SUB_CAPTION_OR_IMAGE], long_caption, context))
                else:
                    #wtf are they lists for?
                    extracted_image_data.append(
                        (cur_image[SUB_CAPTION_OR_IMAGE],
                         caption[SUB_CAPTION_OR_IMAGE], context))

        elif type(cur_image) == list:
            if cur_image[MAIN_CAPTION_OR_IMAGE] != '':
                extracted_image_data.append(
                    (cur_image[MAIN_CAPTION_OR_IMAGE], caption, context))
            if type(cur_image[SUB_CAPTION_OR_IMAGE]) == list:
                for image in cur_image[SUB_CAPTION_OR_IMAGE]:
                    extracted_image_data.append((image, caption, context))
            else:
                extracted_image_data.append(
                    (cur_image[SUB_CAPTION_OR_IMAGE], caption, context))

        elif type(caption) == list:
            if caption[MAIN_CAPTION_OR_IMAGE] != '':
                extracted_image_data.append(
                    (cur_image, caption[MAIN_CAPTION_OR_IMAGE], context))
            if type(caption[SUB_CAPTION_OR_IMAGE]) == list:
                # multiple caps for one image:
                long_caption = caption[MAIN_CAPTION_OR_IMAGE]
                for subcap in caption[SUB_CAPTION_OR_IMAGE]:
                    if long_caption != '':
                        long_caption += ' : '
                    long_caption += subcap
                extracted_image_data.append((cur_image, long_caption, context))
            else:
                extracted_image_data.append(
                    (cur_image, caption[SUB_CAPTION_OR_IMAGE]. context))

        else:
            extracted_image_data.append((cur_image, caption, context))

    elif cur_image != '' and caption == '':
        # we may have missed the caption somewhere.
        REASONABLE_SEARCHBACK = 25
        REASONABLE_SEARCHFORWARD = 5
        curly_no_tag_preceding = '(?<!\\w){'

        for searchback in range(REASONABLE_SEARCHBACK):
            if line_index - searchback < 0:
                continue

            back_line = lines[line_index - searchback]
            m = re.search(curly_no_tag_preceding, back_line)
            if m:
                open_curly = m.start()
                open_curly, open_curly_line, close_curly, \
                close_curly_line = find_open_and_close_braces(\
                line_index - searchback, open_curly, '{', lines)

                cap_begin = open_curly + 1

                caption = assemble_caption(open_curly_line, cap_begin, \
                    close_curly_line, close_curly, lines)

                if type(cur_image) == list:
                    extracted_image_data.append(
                            (cur_image[MAIN_CAPTION_OR_IMAGE], caption, context))
                    for sub_img in cur_image[SUB_CAPTION_OR_IMAGE]:
                        extracted_image_data.append((sub_img, caption, context))
                else:
                    extracted_image_data.append((cur_image, caption, context))
                    break

        if caption == '':
            for searchforward in range(REASONABLE_SEARCHFORWARD):
                if line_index + searchforward >= len(lines):
                    break

                fwd_line = lines[line_index + searchforward]
                m = re.search(curly_no_tag_preceding, fwd_line)

                if m:
                    open_curly = m.start()
                    open_curly, open_curly_line, close_curly,\
                    close_curly_line = find_open_and_close_braces(
                        line_index + searchforward, open_curly, '{', lines)

                    cap_begin = open_curly + 1

                    caption = assemble_caption(open_curly_line,
                                               cap_begin, close_curly_line,
                                               close_curly, lines)

                    if type(cur_image) == list:
                        extracted_image_data.append(
                            (cur_image[MAIN_CAPTION_OR_IMAGE], caption, context))
                        for sub_img in cur_image[SUB_CAPTION_OR_IMAGE]:
                            extracted_image_data.append((sub_img, caption, context))
                    else:
                        extracted_image_data.append((cur_image, caption, context))
                    break

        if caption == '':
            if type(cur_image) == list:
                extracted_image_data.append(
                    (cur_image[MAIN_CAPTION_OR_IMAGE], 'No caption found', context))
                for sub_img in cur_image[SUB_CAPTION_OR_IMAGE]:
                    extracted_image_data.append((sub_img, 'No caption', context))
            else:
                extracted_image_data.append(
                    (cur_image, 'No caption found', context))

    elif caption != '' and cur_image == '':
        if type(caption) == list:
            long_caption = caption[MAIN_CAPTION_OR_IMAGE]
            for subcap in caption[SUB_CAPTION_OR_IMAGE]:
                long_caption = long_caption + ': ' + subcap
        else:
            long_caption = caption
        extracted_image_data.append(('', 'noimg' + long_caption, context))

    # if we're leaving the figure, no sense keeping the data
    cur_image = ''
    caption = ''

    return cur_image, caption, extracted_image_data


def intelligently_find_filenames(line, TeX=False, ext=False, commas_okay=False):
    """
    Find the filename in the line.  We don't support all filenames!  Just eps
    and ps for now.

    @param: line (string): the line we want to get a filename out of

    @return: filename ([string, ...]): what is probably the name of the file(s)
    """

    files_included = ['ERROR']

    if commas_okay:
        valid_for_filename = '\\s*[A-Za-z0-9\\-\\=\\+/\\\\_\\.,%#]+'
    else:
        valid_for_filename = '\\s*[A-Za-z0-9\\-\\=\\+/\\\\_\\.%#]+'

    if ext:
        valid_for_filename += '\.e*ps[texfi2]*'

    if TeX:
        valid_for_filename += '[\.latex]*'

    file_inclusion = re.findall('=' + valid_for_filename + '[ ,]', line)

    if len(file_inclusion) > 0:
        # right now it looks like '=FILENAME,' or '=FILENAME '
        for file_included in file_inclusion:
            files_included.append(file_included[1:-1])

    file_inclusion = re.findall('(?:[ps]*file=|figure=)' + \
                                valid_for_filename + '[,\\]} ]*', line)

    if len(file_inclusion) > 0:
        # still has the =
        for file_included in file_inclusion:
            part_before_equals = file_included.split('=')[0]
            if len(part_before_equals) != file_included:
                file_included = file_included[len(part_before_equals) + 1:].strip()
            if not file_included in files_included:
                files_included.append(file_included)

    file_inclusion = re.findall('["\'{\\[]' + valid_for_filename + '[}\\],"\']',
                                line)

    if len(file_inclusion) > 0:
        # right now it's got the {} or [] or "" or '' around it still
        for file_included in file_inclusion:
            file_included = file_included[1:-1]
            file_included = file_included.strip()
            if not file_included in files_included:
                files_included.append(file_included)

    file_inclusion = re.findall('^' + valid_for_filename + '$', line)

    if len(file_inclusion) > 0:
        for file_included in file_inclusion:
            file_included = file_included.strip()
            if not file_included in files_included:
                files_included.append(file_included)

    file_inclusion = re.findall('^' + valid_for_filename + '[,\\} $]', line)

    if len(file_inclusion) > 0:
        for file_included in file_inclusion:
            file_included = file_included.strip()
            if not file_included in files_included:
                files_included.append(file_included)

    file_inclusion = re.findall('\\s*' + valid_for_filename + '\\s*$', line)

    if len(file_inclusion) > 0:
        for file_included in file_inclusion:
            file_included = file_included.strip()
            if not file_included in files_included:
                files_included.append(file_included)

    if files_included != ['ERROR']:
        files_included = files_included[1:] # cut off the dummy

    for file_included in files_included:
        if file_included == '':
            files_included.remove(file_included)
        if ' ' in file_included:
            for subfile in file_included.split(' '):
                if not subfile in files_included:
                    files_included.append(subfile)
        if ',' in file_included:
            for subfile in file_included.split(' '):
                if not subfile in files_included:
                    files_included.append(subfile)

    return files_included

#def rotate_image(filename, line, sdir, image_list):
#    """
#    Given a filename and a line, figure out what it is that the author
#    wanted to do wrt changing the rotation of the image and convert the
#    file so that this rotation is reflected in its presentation.
#
#    @param: filename (string): the name of the file as specified in the TeX
#    @param: line (string): the line where the rotate command was found
#
#    @output: the image file rotated in accordance with the rotate command
#    @return: True if something was rotated
#    """
#
#    file_loc = get_image_location(filename, sdir, image_list)
#    degrees = re.findall('(angle=[-\\d]+|rotate=[-\\d]+)', line)
#
#    if len(degrees) < 1:
#        return False
#
#    degrees = degrees[0].split('=')[-1].strip()
#
#    if file_loc is None or file_loc == 'ERROR' or\
#            not re.match('-*\\d+', degrees):
#        return False
#
#    degrees = str(0 - int(degrees))
#    try:
#        result = mogrify_image(file_loc, degrees)
#    except timeout_decorator.timeout_decorator.TimeoutError:
#        result = 'TimeOut'
#    if result != '':
#        return True
#    else:
#        return True


#@timeout_decorator.timeout(15)
#def mogrify_image(img, angle):
#    cmd = '%s -rotate %s "%s"' % (current_app.config.get('GRAPHICS_ROTATE'),
#                                angle, img)
#    res = commands.getstatusoutput(cmd)
#    return res[1]


def find_open_and_close_braces(line_index, start, brace, lines):
    """
    Take the line where we want to start and the index where we want to start
    and find the first instance of matched open and close braces of the same
    type as brace in file file.

    @param: line (int): the index of the line we want to start searching at
    @param: start (int): the index in the line we want to start searching at
    @param: brace (string): one of the type of brace we are looking for ({, },
        [, or ])
    @param lines ([string, string, ...]): the array of lines in the file we
        are looking in.

    @return: (start, start_line, end, end_line): (int, int, int): the index
        of the start and end of whatever braces we are looking for, and the
        line number that the end is on (since it may be different than the line
        we started on)
    """

    if brace in ['[', ']']:
        open_brace = '['
        close_brace = ']'
    elif brace in ['{', '}']:
        open_brace = '{'
        close_brace = '}'
    elif brace in ['(', ')']:
        open_brace = '('
        close_brace = ')'
    else:
        # unacceptable brace type!
        return (-1, -1, -1, -1)

    open_braces = []
    line = lines[line_index]

    ret_open_index = line.find(open_brace, start)
    line_index_cpy = line_index
    # sometimes people don't put the braces on the same line
    # as the tag
    while ret_open_index == -1:
        line_index = line_index + 1
        if line_index >= len(lines):
            # failed to find open braces...
            return (0, line_index_cpy, 0, line_index_cpy)
        line = lines[line_index]
        ret_open_index = line.find(open_brace)

    open_braces.append(open_brace)

    ret_open_line = line_index

    open_index = ret_open_index
    close_index = ret_open_index

    while len(open_braces) > 0:
        if open_index == -1 and close_index == -1:
            # we hit the end of the line!  oh, noez!
            line_index = line_index + 1

            if line_index >= len(lines):
                # hanging braces!
                return (ret_open_index, ret_open_line, ret_open_index, \
                    ret_open_line)

            line = lines[line_index]
            # to not skip things that are at the beginning of the line
            close_index = line.find(close_brace)
            open_index = line.find(open_brace)

        else:
            if close_index != -1:
                close_index = line.find(close_brace, close_index + 1)
            if open_index != -1:
                open_index = line.find(open_brace, open_index + 1)

        if close_index != -1:
            open_braces.pop()
            if len(open_braces) == 0 and \
                    (open_index > close_index or open_index == -1):
                break
        if open_index != -1:
            open_braces.append(open_brace)

    ret_close_index = close_index

    return (ret_open_index, ret_open_line, ret_close_index, line_index)

def assemble_caption(begin_line, begin_index, end_line, end_index, lines):
    """
    Take write_messageation about the caption of a picture and put it all together
    in a nice way.  If it spans multiple lines, put it on one line.  If it
    contains controlled characters, strip them out.  If it has tags we don't
    want to worry about, get rid of them, etc.

    @param: begin_line (int): the index of the line where the caption begins
    @param: begin_index (int): the index within the line where the caption
        begins
    @param: end_line (int): the index of the line where the caption ends
    @param: end_index (int): the index within the line where the caption ends
    @param: lines ([string, string, ...]): the line strings of the text

    @return: caption (string): the caption, nicely formatted and pieced together
    """

    # stuff we don't like
    label_head = '\\label{'

    # reassemble that sucker
    if end_line > begin_line:
        # our caption spanned multiple lines
        caption = lines[begin_line][begin_index:]

        for included_line_index in range(begin_line + 1, end_line):
            caption = caption + ' ' + lines[included_line_index]

        caption = caption + ' ' + lines[end_line][:end_index]
        caption = caption.replace('\n', ' ')
        caption = caption.replace('  ', ' ')
    else:
        # it fit on one line
        caption = lines[begin_line][begin_index:end_index]

    # clean out a label tag, if there is one
    label_begin = caption.find(label_head)
    if label_begin > -1:
        # we know that our caption is only one line, so if there's a label
        # tag in it, it will be all on one line.  so we make up some args
        dummy_start, dummy_start_line, label_end, dummy_end = \
                find_open_and_close_braces(0, label_begin, '{', [caption])
        caption = caption[:label_begin] + caption[label_end + 1:]

    # clean out characters not allowed in MARCXML
    # not allowed: & < >
    try:
        caption = wash_for_utf8(caption)
        caption = encode_for_xml(caption.encode('utf-8', 'xmlcharrefreplace'),
                                 wash=True)
    except: # that damn encode thing threw an error on astro-ph/0601014
#        sys.stderr.write(caption)
#        sys.stderr.write(' cannot be processed\n')
        caption = caption.replace('&', '&amp;').replace('<', '&lt;')
        caption = caption.replace('>', '&gt;')

    caption = caption.strip()

    if len(caption) > 1 and caption[0] == '{' and caption[-1] == '}':
        caption = caption[1:-1]

    return caption

def get_image_location(image, sdir, image_list, recurred=False):
    """
    This function takes a raw image name and a directory and returns the location of the
    (possibly converted) image

    @param: image (string): the name of the raw image from the TeX
    @param: sdir (string): the directory where everything was unzipped to
    @param: image_list ([string, string, ...]): the list of images that
        were extracted from the tarball and possibly converted

    @return: converted_image (string): the full path to the (possibly
        converted) image file
    """

    if type(image) == list:
        # image is a list, not good
        return None

    image = str(image)

    image = image.strip()

    figure_or_file = '(figure=|file=)'
    figure_or_file_in_image = re.findall(figure_or_file, image)
    if len(figure_or_file_in_image) > 0:
        image.replace(figure_or_file_in_image[0], '')
    includegraphics = '\\includegraphics{'
    includegraphics_in_image = re.findall(includegraphics, image)
    if len(includegraphics_in_image) > 0:
        image.replace(includegraphics_in_image[0], '')

    image = image.strip()

    some_kind_of_tag = '\\\\\\w+ '

    if image.startswith('./'):
        image = image[2:]
    if re.match(some_kind_of_tag, image):
        image = image[len(image.split(' ')[0]) + 1:]
    if image.startswith('='):
        image = image[1:]

    if len(image) == 1:
        return None

    image = image.strip()

    image_path = os.path.join(sdir, image)
    converted_image_should_be = get_converted_image_name(image_path)

    if image_list == None:
        image_list = os.listdir(sdir)

    for png_image in image_list:
        if converted_image_should_be == png_image:
            return png_image

    # maybe it's in a subfolder called eps (TeX just understands that)
    if os.path.isdir(os.path.join(sdir, 'eps')):
        image_list = os.listdir(os.path.join(sdir, 'eps'))
        for png_image in image_list:
            if converted_image_should_be == png_image:
                return os.path.join('eps', png_image)

    if os.path.isdir(os.path.join(sdir, 'fig')):
        image_list = os.listdir(os.path.join(sdir, 'fig'))
        for png_image in image_list:
            if converted_image_should_be == png_image:
                return os.path.join('fig', png_image)

    if os.path.isdir(os.path.join(sdir, 'figs')):
        image_list = os.listdir(os.path.join(sdir, 'figs'))
        for png_image in image_list:
            if converted_image_should_be == png_image:
                return os.path.join('figs', png_image)

    if os.path.isdir(os.path.join(sdir, 'Figures')):
        image_list = os.listdir(os.path.join(sdir, 'Figures'))
        for png_image in image_list:
            if converted_image_should_be == png_image:
                return os.path.join('Figures', png_image)

    if os.path.isdir(os.path.join(sdir, 'Figs')):
        image_list = os.listdir(os.path.join(sdir, 'Figs'))
        for png_image in image_list:
            if converted_image_should_be == png_image:
                return os.path.join('Figs', png_image)

    # maybe it is actually just loose.
    for png_image in os.listdir(sdir):
        if os.path.split(converted_image_should_be)[-1] == png_image:
            return converted_image_should_be
        if os.path.isdir(os.path.join(sdir, png_image)):
            # try that, too!  we just do two levels, because that's all that's
            # reasonable..
            sub_dir = os.path.join(sdir, png_image)
            for sub_dir_file in os.listdir(sub_dir):
                if os.path.split(converted_image_should_be)[-1] == sub_dir_file:
                    return converted_image_should_be

    # maybe it's actually up a directory or two: this happens in nested
    # tarballs where the TeX is stored in a different directory from the images
    for png_image in os.listdir(os.path.split(sdir)[0]):
        if os.path.split(converted_image_should_be)[-1] == png_image:
            return converted_image_should_be
    for png_image in os.listdir(os.path.split(os.path.split(sdir)[0])[0]):
        if os.path.split(converted_image_should_be)[-1] == png_image:
            return converted_image_should_be

    if recurred:
        return None

    # agh, this calls for drastic measures
    for piece in image.split(' '):
        res = get_image_location(piece, sdir, image_list, recurred=True)
        if res != None:
            return res

    for piece in image.split(','):
        res = get_image_location(piece, sdir, image_list, recurred=True)
        if res != None:
            return res

    for piece in image.split('='):
        res = get_image_location(piece, sdir, image_list, recurred=True)
        if res != None:
            return res

    #write_message('Unknown image ' + image)
    return None

def get_tex_location(new_tex_name, current_tex_name, recurred=False):
    """
    Takes the name of a TeX file and attempts to match it to an actual file
    in the tarball.

    @param: new_tex_name (string): the name of the TeX file to find
    @param: current_tex_name (string): the location of the TeX file where we
        found the reference

    @return: tex_location (string): the location of the other TeX file on
        disk or None if it is not found
    """

    tex_location = None

    current_dir = os.path.split(current_tex_name)[0]

    some_kind_of_tag = '\\\\\\w+ '

    new_tex_name = new_tex_name.strip()
    if new_tex_name.startswith('input'):
        new_tex_name = new_tex_name[len('input'):]
    if re.match(some_kind_of_tag, new_tex_name):
        new_tex_name = new_tex_name[len(new_tex_name.split(' ')[0]) + 1:]
    if new_tex_name.startswith('./'):
        new_tex_name = new_tex_name[2:]
    if len(new_tex_name) == 0:
        #write_message('TeX has been stripped down to nothing.')
        return None
    new_tex_name = new_tex_name.strip()

    new_tex_file = os.path.split(new_tex_name)[-1]
    new_tex_folder = os.path.split(new_tex_name)[0]
    if new_tex_folder == new_tex_file:
        new_tex_folder = ''

    # could be in the current directory
    for any_file in os.listdir(current_dir):
        if any_file == new_tex_file:
            return os.path.join(current_dir, new_tex_file)

    # could be in a subfolder of the current directory
    if os.path.isdir(os.path.join(current_dir, new_tex_folder)):
        for any_file in os.listdir(os.path.join(current_dir, new_tex_folder)):
            if any_file == new_tex_file:
                return os.path.join(os.path.join(current_dir, new_tex_folder),
                                    new_tex_file)

    # could be in a subfolder of a higher directory
    one_dir_up = os.path.join(os.path.split(current_dir)[0], new_tex_folder)
    if os.path.isdir(one_dir_up):
        for any_file in os.listdir(one_dir_up):
            if any_file == new_tex_file:
                return os.path.join(one_dir_up, new_tex_file)

    two_dirs_up = os.path.join(os.path.split(os.path.split(current_dir)[0])[0],
                               new_tex_folder)
    if os.path.isdir(two_dirs_up):
        for any_file in os.listdir(two_dirs_up):
            if any_file == new_tex_file:
                return os.path.join(two_dirs_up, new_tex_file)

    if tex_location == None and not recurred:
        return get_tex_location(new_tex_name + '.tex', current_tex_name, \
                                recurred=True)

    return tex_location

def wash_for_utf8(text, correct=True):
    """Return UTF-8 encoded binary string with incorrect characters washed away.

    :param text: input string to wash (can be either a binary or Unicode string)
    :param correct: whether to correct bad characters or throw exception
    """
    if isinstance(text, unicode):
        return text.encode('utf-8')

    errors = "ignore" if correct else "strict"
    return text.decode("utf-8", errors).encode("utf-8", errors)

def encode_for_xml(text, wash=False, xml_version='1.0', quote=False):
    """Encode special characters in a text so that it would be XML-compliant.

    :param text: text to encode
    :return: an encoded text
    """
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    if quote:
        text = text.replace('"', '&quot;')
    if wash:
        text = wash_for_xml(text, xml_version=xml_version)
    return text

try:
    unichr(0x100000)
    RE_ALLOWED_XML_1_0_CHARS = re.compile(
        u'[^\U00000009\U0000000A\U0000000D\U00000020-'
        u'\U0000D7FF\U0000E000-\U0000FFFD\U00010000-\U0010FFFF]')
    RE_ALLOWED_XML_1_1_CHARS = re.compile(
        u'[^\U00000001-\U0000D7FF\U0000E000-\U0000FFFD\U00010000-\U0010FFFF]')
except ValueError:
    # oops, we are running on a narrow UTF/UCS Python build,
    # so we have to limit the UTF/UCS char range:
    RE_ALLOWED_XML_1_0_CHARS = re.compile(
        u'[^\U00000009\U0000000A\U0000000D\U00000020-'
        u'\U0000D7FF\U0000E000-\U0000FFFD]')
    RE_ALLOWED_XML_1_1_CHARS = re.compile(
        u'[^\U00000001-\U0000D7FF\U0000E000-\U0000FFFD]')

def wash_for_xml(text, xml_version='1.0'):
    """Remove any character which isn't a allowed characters for XML.

    The allowed characters depends on the version
    of XML.

        - XML 1.0:
            <http://www.w3.org/TR/REC-xml/#charsets>
        - XML 1.1:
            <http://www.w3.org/TR/xml11/#charsets>

    :param text: input string to wash.
    :param xml_version: version of the XML for which we wash the
        input. Value for this parameter can be '1.0' or '1.1'
    """
    if xml_version == '1.0':
        return RE_ALLOWED_XML_1_0_CHARS.sub(
            '', unicode(text, 'utf-8')).encode('utf-8')
    else:
        return RE_ALLOWED_XML_1_1_CHARS.sub(
            '', unicode(text, 'utf-8')).encode('utf-8')


def get_converted_image_name(image):
    """
    Gives the name of the image after it has been converted to png format.
    Strips off the old extension.

    @param: image (string): The fullpath of the image before conversion

    @return: converted_image (string): the fullpath of the image after convert
    """
    png_extension = '.png'

    if image[(0 - len(png_extension)):] == png_extension:
        # it already ends in png!  we're golden
        return image

    img_dir = os.path.split(image)[0]
    image = os.path.split(image)[-1]

    # cut off the old extension
    if len(image.split('.')) > 1:
        old_extension = '.' + image.split('.')[-1]
        if image.split('.')[-1].isdigit():
            converted_image = image + png_extension
        else:
            converted_image = image[:(0 - len(old_extension))] + png_extension

    else:
        #no extension... damn
        converted_image = image + png_extension

    return os.path.join(img_dir, converted_image)

def remove_dups(extracted_image_data):
    """
    So now that we spam and get loads and loads of stuff in our lists, we need
    to intelligently get rid of some of it.

    @param: extracted_image_data ([(string, string, list, list),
        (string, string, list, list),...]): the full list of images, captions,
        labels and contexts extracted from this file

    @return: extracted_image_data ([(string, string, list, list),
        (string, string, list, list),...)]: the same list, but if there are
        duplicate images contained in it, then their captions are condensed
    """

    img_list = {}
    pared_image_data = []

    # combine relevant captions
    for (image, caption, label, contexts) in extracted_image_data:
        if image in img_list:
            if not caption in img_list[image]:
                img_list[image].append(caption)
        else:
            img_list[image] = [caption]

    # order it (we know that the order in the original is correct)
    for (image, caption, label, contexts) in extracted_image_data:
        if image in img_list:
            pared_image_data.append((image, \
                                           ' : '.join(img_list[image]), label, contexts))
            del img_list[image]
        # else we already added it to the new list

    return pared_image_data

def prepare_image_data(extracted_image_data, tex_file, image_list):
    """
    Prepare and clean image-data from duplicates and other garbage.

    @param: extracted_image_data ([(string, string, list, list) ...],
        ...])): the images and their captions + contexts, ordered
    @param: tex_file (string): the location of the TeX (used for finding the
        associated images; the TeX is assumed to be in the same directory
        as the converted images)
    @param: image_list ([string, string, ...]): a list of the converted
        image file names
    @return extracted_image_data ([(string, string, list, list) ...],
        ...])) again the list of image data cleaned for output
    """
    sdir = os.path.split(tex_file)[0]
    image_locs_and_captions_and_labels = []
    for (image, caption, label) in extracted_image_data:
        if image == 'ERROR':
            continue
        if not image == '':
            image_loc = get_image_location(image, sdir, image_list)
            if image_loc != None and os.path.exists(image_loc):
                image_locs_and_captions_and_labels.append(
                        (image_loc, caption, label))
        else:
            image_locs_and_captions_and_labels.append((image, caption, label))
    return image_locs_and_captions_and_labels

def extract_context(tex_file, extracted_image_data):
    """
    Given a .tex file and a label name, this function will extract the text before
    and after for all the references made to this label in the text. The number
    of characters to extract before and after is configurable.

    @param tex_file (list): path to .tex file
    @param extracted_image_data ([(string, string, list), ...]):
        a list of tuples of images matched to labels and captions from
        this document.

    @return extracted_image_data ([(string, string, list, list),
        (string, string, list, list),...)]: the same list, but now containing
        extracted contexts
    """
    if os.path.isdir(tex_file) or not os.path.exists(tex_file):
        return []
    fd = open(tex_file)
    lines = fd.read()
    fd.close()

    # Generate context for each image and its assoc. labels
    new_image_data = []
    for image, caption, label in extracted_image_data:
        context_list = []

        # Generate a list of index tuples for all matches
        indicies = [match.span()
                    for match in re.finditer(r"(\\(?:fig|ref)\{%s\})" % (re.escape(label),),
                    lines)]
        for startindex, endindex in indicies:
            # Retrive all lines before label until beginning of file
            i = startindex - CFG_PLOTEXTRACTOR_CONTEXT_EXTRACT_LIMIT
            if i < 0:
                text_before = lines[:startindex]
            else:
                text_before = lines[i:startindex]
            context_before = get_context(text_before, backwards=True)

            # Retrive all lines from label until end of file and get context
            i = endindex + CFG_PLOTEXTRACTOR_CONTEXT_EXTRACT_LIMIT
            text_after = lines[endindex:i]
            context_after = get_context(text_after)
            context_list.append(context_before + ' \\ref{' + label + '} ' + context_after)
        new_image_data.append((image, caption, label, context_list))
    return new_image_data

def get_context(lines, backwards=False):
    """
    Given a relevant string from a TeX file, this function will extract text
    from it as far as it is deemed contextually relevant, either backwards or forwards
    in the text. The level of relevance allowed is configurable. When it reaches some
    point in the text that is determined to be out of scope from the current context,
    like text that is identified as a new paragraph, a complex TeX structure
    ('/begin', '/end', etc.) etc., it will return the previously allocated text.

    For use when extracting text with contextual value for an figure or plot.

    @param lines (string): string to examine
    @param reversed (bool): are we searching backwards?

    @return context (string): extracted context
    """
    tex_tag = re.compile(r".*\\(\w+).*")
    sentence = re.compile(r"(?<=[.?!])[\s]+(?=[A-Z])")
    context = []

    word_list = lines.split()
    if backwards:
        word_list.reverse()

    # For each word we do the following:
    #   1. Check if we have reached word limit
    #   2. If not, see if this is a TeX tag and see if its 'illegal'
    #   3. Otherwise, add word to context
    for word in word_list:
        if len(context) >= CFG_PLOTEXTRACTOR_CONTEXT_WORD_LIMIT:
            break
        match = tex_tag.match(word)
        if match and match.group(1) in CFG_PLOTEXTRACTOR_DISALLOWED_TEX:
            # TeX Construct matched, return
            if backwards:
                # When reversed we need to go back and
                # remove unwanted data within brackets
                temp_word = ""
                while len(context):
                    temp_word = context.pop()
                    if '}' in temp_word:
                        break
            break
        context.append(word)

    if backwards:
        context.reverse()
    text = " ".join(context)
    sentence_list = sentence.split(text)

    if backwards:
        sentence_list.reverse()

    if len(sentence_list) > CFG_PLOTEXTRACTOR_CONTEXT_SENTENCE_LIMIT:
        return " ".join(sentence_list[:CFG_PLOTEXTRACTOR_CONTEXT_SENTENCE_LIMIT])
    else:
        return " ".join(sentence_list)
