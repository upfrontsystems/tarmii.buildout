import os
import sys
reload(sys)
import zipfile
from cStringIO import StringIO

from PIL import Image

import urllib
import transaction

from lxml import etree, html
from lxml.html import soupparser
from Testing import makerequest
from AccessControl.SecurityManagement import newSecurityManager
from zope.app.component.hooks import setSite
from plone.uuid.interfaces import IUUID

from upfront.wordmlutils.html2wordml import convertPixelsToEMU, \
    gridcolwidth, tcwidth, imgsize

app = makerequest.makerequest(app)
portal = getattr(app, sys.argv[-1])
setSite(portal)

user = app.acl_users.getUser('admin')
newSecurityManager(None, user.__of__(app.acl_users))
portal.setupCurrentSkin(portal.REQUEST)
wftool = portal.portal_workflow

query = {
    'portal_type': 'upfront.assessmentitem.content.assessmentitem'
}


sys.setdefaultencoding('utf-8')

exportdir = '%s/wordexport' % os.getcwd()


def get_images_from_html(htmltext):

    images = {}
    image_src_map = {}
    rel_id_map = {}

    doc = html.fromstring(htmltext.decode('utf-8'))
    for count, element in enumerate(doc.xpath("//*[@src]")):
        original_src = src = element.attrib['src']
        rel_id = 'image%d' % count

        if '/@@images' in src:
            src = src.split('/@@images')[0]
            image_src_map[original_src] = src

        if 'resolveuid' in src:
            uid = src.split('/')[-1]
            r = portal.portal_catalog(UID=uid)
            if len(r) == 1:
                img = r[0].getObject()
            else:
                element.attrib['src'] = ''
                continue
        elif 'http' in src:
            imgname = src.split('/')[-1]
            data = urllib.urlopen(src)
            data = StringIO(data.read())
            image_src_map[original_src] = imgname
            rel_id_map[imgname] = rel_id
            images[imgname] = data
            continue
        elif 'data:image' in src:
            basesplit = src.split(';base64,') 
            data = basesplit[1].decode('base64')
            ext = basesplit[0].split('/')[-1]
            imgname = '%s.%s' % (obj.id, ext)
            images[imgname] = StringIO(data)
            image_src_map[original_src] = imgname
            rel_id_map[imgname] = rel_id
            continue
        else:
            img = obj.unrestrictedTraverse(src)

        image_src_map[original_src] = img.id
        rel_id_map[img.id] = rel_id

        try:
            images[img.id] = StringIO(img.data)
        except:
            print "No blob file for", img.id
            continue

    return images, image_src_map, rel_id_map


# namespace for word XML tags:
NS_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

# XML tags in Word forms:
TAG_FIELD         = NS_W+'sdt'
TAG_FIELDPROP     = NS_W+'sdtPr'
TAG_FIELDTAG      = NS_W+'tag'
ATTR_FIELDTAGVAL  = NS_W+'val'
TAG_FIELD_CONTENT = NS_W+'sdtContent'
TAG_RUN           = NS_W+'r'
TAG_TEXT          = NS_W+'t'
TAG_BREAK         = NS_W+'br'


def normalize_image_urls(doc, image_src_map, rel_id_map):
    for img in doc.xpath('//img'):
        if not img.attrib.has_key('src'):
            img.getparent().remove(img)
            continue
        src = img.attrib['src']
        if not image_src_map.has_key(src):
            img.getparent().remove(img)
            continue
        filename = image_src_map[src]
        img.set('src', rel_id_map[filename])


def create_word_doc(fname, item_id, intro, activity, content_concept_skills,
                    prior_knowledge_skills, equipment_and_administration,
                    topics):

    if intro:
        raise RuntimeError('Unexpected')

    htmltext = u"""
    <div class="activity">
        %(activity)s
    </div>
    <div>%(content_concept_skills)s</div>
    <div>%(prior_knowledge_skills)s</div>
    <div>%(equipment_and_administration)s</div>""" % {
        'activity': activity,
        'content_concept_skills': content_concept_skills,
        'prior_knowledge_skills': prior_knowledge_skills,
        'equipment_and_administration': equipment_and_administration,
    }

    # register columnwidth extension
    ns = etree.FunctionNamespace('http://upfrontsystems.co.za/wordmlutils')
    ns.prefix = 'upy'
    ns['gridcolwidth'] = gridcolwidth
    ns['tcwidth'] = tcwidth
    ns['imgsize'] = imgsize

    html2wordml_dirname = os.path.join(os.getcwd(), 'src',
                                       'upfront.wordmlutils',
                                       'upfront', 'wordmlutils')
    xslfile = open(os.path.join(html2wordml_dirname, 'xsl/html2wordml.xsl'))

    xslt_root = etree.XML(xslfile.read())
    transform = etree.XSLT(xslt_root)

    images, image_src_map, rel_id_map = get_images_from_html(htmltext)

    scripts_dir = os.path.join(os.getcwd(), 'scripts')
    template = zipfile.ZipFile(os.path.join(scripts_dir, 'form_template.docx'))

    # read and parse relations from template so that we can update it
    # with links to images
    rels = template.read('word/_rels/document.xml.rels')
    rels = etree.parse(StringIO(rels)).getroot()

    wordml = template.read('word/document.xml')

    def _transform(field_content, content):
        content = "<html><body>%s</body></html>" % content
        doc = soupparser.fromstring(content)
        normalize_image_urls(doc, image_src_map, rel_id_map)
        result_tree = transform(doc)
        dom = etree.fromstring(etree.tostring(result_tree))
        body = dom.getchildren()[0]
        for child in field_content.getchildren():
            field_content.remove(child)
        for child in body.getchildren():
            field_content.append(child)

    xmlroot = etree.fromstring(wordml)
    for field in xmlroot.getiterator(TAG_FIELD):
        field_tag = field.find(TAG_FIELDPROP+'/'+TAG_FIELDTAG)
        tag = field_tag.get(ATTR_FIELDTAGVAL, None)
        field_content = field.find(TAG_FIELD_CONTENT)
        for elem in field_content.getiterator():
            if elem.tag != TAG_TEXT:
                continue
            run = elem.getparent()
            if tag == 'item_id':
                elem.text = item_id
            elif tag in topics.keys():
                elem.text = topics.get(tag)
            elif tag == 'activity':
                _transform(field_content, activity)
            elif tag == 'prior_knowledge':
                _transform(field_content, prior_knowledge_skills)
            elif tag == 'equipment_and_administration':
                _transform(field_content, equipment_and_administration)
            elif tag == 'skills_assessed':
                _transform(field_content, content_concept_skills)

    wordml = etree.tostring(xmlroot)

    output = open(fname, 'w+')
    zf = zipfile.ZipFile(output, 'w')
    namelist = template.namelist()
    docindex = namelist.index('word/document.xml')
    relmap = {}
    for filename, img in images.items():

        relid = rel_id_map[filename]
        count = relid[5:]

        # insert image sizes in the wordml
        img = Image.open(img)
        width, height = img.size

        # insert image before document
        filepath = 'word/media/%s' % filename
        namelist.insert(docindex, filepath)
        relmap[filepath] = filename

        # convert to EMU (English Metric Unit) 
        width = convertPixelsToEMU(width)
        height = convertPixelsToEMU(height)

        widthattr = '%s-$width' % relid
        heightattr = '%s-$height' % relid
        idattr = '%s-$id' % relid
        ridattr = '%s-$rid' % relid
        wordml = wordml.replace(widthattr, str(width))
        wordml = wordml.replace(heightattr, str(height))
        wordml = wordml.replace(ridattr, relid)
        wordml = wordml.replace(idattr, count)
        relxml = """<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/%s"/>""" % (
            relid, filename)
        try:
            rels.append(etree.fromstring(relxml))
        except:
            raise str(relxml)

    relsxml = etree.tostring(rels)

    for filepath in namelist:
        if filepath == 'word/document.xml':
            zf.writestr(filepath, wordml)
        elif filepath.startswith('word/media'):
            filename = relmap[filepath]
            filecontent = images[filename]
            filecontent.seek(0)
            zf.writestr(filepath, filecontent.read())
        elif filepath.startswith('word/_rels/document.xml.rels'):
            zf.writestr(filepath, relsxml)
        else:
            content = template.read(filepath)
            zf.writestr(filepath, content)
        
    template.close()
    zf.close()
    output.close()


for language in portal.topictrees.language.objectValues():
    for grade in portal.topictrees.grade.objectValues():
        query['topic_uids'] = {
            'query': [
                IUUID(language),
                '9108db86cd91495cbb0bbbe815c16e76', # subject = language
                IUUID(grade)
            ], 'operator': 'and'}

        langdir = '%s/%s' % (exportdir, language.id)
        gradedir = '%s/%s' % (langdir, grade.id)

        if not os.path.exists(langdir):
            os.mkdir(langdir)

        if not os.path.exists(gradedir):
            os.mkdir(gradedir)

        for i in range(1,5):
            termdir = '%s/%s' % (gradedir, 'term%d' % i)
            if not os.path.exists(termdir):
                os.mkdir(termdir)

        for item in portal.portal_catalog(query):

            obj = item.getObject()

            if obj is None:
                continue

            topics = {}
            for topic in obj.topics:
                topic = topic.to_object
                treetitle = topic.aq_parent.title.lower()
                treetitle = treetitle.replace(' ', '_')
                if treetitle == 'activity_type':
                    treetitle = 'item_type'
                elif treetitle == 'language_component':
                    treetitle = 'subject_component'
                topics[treetitle] = topic.title

            item_id = getattr(obj, 'item_id', obj.id)

            term = topics.get('term', 'no-term')
            # Strip week
            term = ''.join(term.split()[:2]).lower()
            termdir = '%s/%s' % (gradedir, term)
            if not os.path.exists(termdir):
                os.mkdir(termdir)

            fname = '%s/%s.docx' % (termdir, obj.id)

            intro = getattr(obj, 'introduction', None)
            if intro:
                intro = intro.output

            activity = getattr(obj, 'activity', None)
            if activity:
                activity = activity.raw

            content_concept_skills = getattr(obj, 'content_concept_skills', None)
            if content_concept_skills:
                content_concept_skills = content_concept_skills.raw

            prior_knowledge_skills = getattr(obj, 'prior_knowledge_skills', None)
            if prior_knowledge_skills:
                prior_knowledge_skills = prior_knowledge_skills.raw

            equipment_and_administration = getattr(obj, 'equipment_and_administration', None)
            if equipment_and_administration:
                equipment_and_administration = equipment_and_administration.raw

            create_word_doc(fname, item_id, intro, activity,
                            content_concept_skills,
                            prior_knowledge_skills,
                            equipment_and_administration, topics)

            print "Exporting %s " % obj.id

