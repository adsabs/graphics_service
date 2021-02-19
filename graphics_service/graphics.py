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

def get_graphics(bibcode):
    # Query graphics database with bibcode supplied
    results = get_graphics_record(bibcode)
    if results and 'thumbnails' in results:
        if len(results['thumbnails']) == 0:
            # No thumbnails = nothing to display
            return {'Error': 'Unable to get results!', 'Error Info': 'No thumbnail data for %s' % bibcode}
        output = {}
        source = results.get('source', 'NA')
        output['bibcode'] = results['bibcode']
        output['number'] = len(results['thumbnails'])
        output['pick'] = graph_link % random.choice(results['thumbnails'])
        if not output['pick'].find('http') >-1:
            return {'Error': 'Unable to get results!', 'Error Info': 'Failed to get thumbnail for display image for %s' % output['bibcode']}
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
            # Non-AAS journals link to IOPscience, rather than AIE
            if source == "IOP" and bibcode[4:9] not in ['ApJ..','ApJS.','AJ...']:
                source = "IOPscience"
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
