#!/usr/bin/env python

import os
import sys
import urllib
import zipfile
from cStringIO import StringIO

sys.path[0:0] = [
    '/home/roche/.buildout/eggs/lxml-2.3.4-py2.7-linux-i686.egg',
    ]

from lxml import etree

template_filename = sys.argv[1]
docx_dir = sys.argv[2]
outfile = sys.argv[3]

template = zipfile.ZipFile(os.path.join(os.getcwd(), template_filename))

zf = zipfile.ZipFile(outfile, 'w')
namelist = template.namelist()
docindex = namelist.index('word/document.xml')

for filepath in namelist:
    if filepath == 'word/media/image0.PNG':
        filepath = 'word/media/image1.png'
    filename = os.path.join(os.getcwd(), docx_dir, filepath)
    content = open(filename).read()
    if filepath == 'word/document.xml':
        content = content.replace('\r\n', '')
        content = content.replace('\n', '')

    zf.writestr(filepath, content)
    
template.close()
zf.close()
