'''
Created on Nov 2, 2014

@author: ehenneken
'''
from __future__ import absolute_import
import sys
import os
import simplejson as json
import random
from flask import current_app
from .models import get_graphics_record

graph_link = '<a href="graphics" border=0><img src="%s"></a>'

def get_graphics(identifier):
    # Query graphics database with identifier supplied
    results = get_graphics_record(identifier)
    if results and 'thumbnails' in results:
        try:
            thumbnail_count = len(results['thumbnails'])
        except:
            thumbnail_count = 0
        if thumbnail_count == 0:
            # No thumbnails = nothing to display
            return {'Error': 'Unable to get results!', 'Error Info': 'No thumbnail data for %s' % identifier}
        output = {}
        source = results.get('source', 'NA')
        output['scix_id'] = results['scix_id']
        # We still include the value in the "bibcode" column in the output
        # For backwards compatibility
        output['bibcode'] = results.get('bibcode')
        output['number'] = len(results['thumbnails'])
        output['pick'] = graph_link % random.choice(results['thumbnails'])
        if not output['pick'].find('http') >-1:
            return {'Error': 'Unable to get results!', 'Error Info': 'Failed to get thumbnail for display image for %s' % output['scix_id']}
        # Create this convoluted construct for backwards compatibility
        output['figures'] = []
        n=1
        for t in results['thumbnails']:
            fig_data = {
               'figure_label':'Figure {0}'.format(n),
               'figure_caption':'',
               'figure_type':'',
               'images':[{'thumbnail':t[0], 'highres':t[1]}]
            } 
            output['figures'].append(fig_data)
            n+=1
        if source in current_app.config.get('GRAPHICS_EXTSOURCES'):
            header = current_app.config.get('GRAPHICS_HEADER').get(source,'')
            output['header'] =  header
        elif source.upper() == 'ARXIV' \
                and current_app.config.get('GRAPHICS_INCLUDE_ARXIV'):
            output['header'] = 'Images extracted from the arXiv e-print'
        elif source.upper() == 'TEST':
            output['pick'] = random.choice(results['thumbnails'])
        else:
            output = {'Error': 'Unable to get results!', 'Error Info': 'Unknown data source %s' % source}

        return output

    return results
