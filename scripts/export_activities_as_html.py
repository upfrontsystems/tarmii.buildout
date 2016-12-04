import os
import sys
reload(sys)

import urllib
import transaction

from lxml.html import fromstring, tostring
from Testing import makerequest
from AccessControl.SecurityManagement import newSecurityManager
from zope.app.component.hooks import setSite
from plone.uuid.interfaces import IUUID

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

exportdir = '%s/export' % os.getcwd()

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

        fname = '%s/%s-%s-activities.html' % (gradedir, language.id, grade.id)
        htmlfile = open(fname, 'w+')

        for item in portal.portal_catalog(query):
            obj = item.getObject()

            if obj is None:
                continue

            item_id = getattr(obj, 'item_id', obj.id)

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

            topics = []
            if hasattr(obj, 'topics'):
                for topic in obj.topics:
                    topics.append("<span>%s</span>" % topic.to_object.title)

            topics = ", ".join(topics)

            result = u"""<h1>%(item_id)s</h1>
            <div class="activity">
                %(activity)s
            </div>

                <h5>Content/Concept/Skills Assessed</h5>
                <div>%(content_concept_skills)s</div>

                <h5>Prior Knowledge or Skill(s) Assessed</h5>
                <div>%(prior_knowledge_skills)s</div>

                <h5>Equipment and Administration (For the teacher)</h5>
                <div>%(equipment_and_administration)s</div>
                <p><strong>Topics: </strong> %(topics)s </p>
            <hr/>

        """ % {
            'item_id': item_id, 
            'activity': activity,
            'content_concept_skills': content_concept_skills,
            'prior_knowledge_skills': prior_knowledge_skills,
            'equipment_and_administration': equipment_and_administration,
            'topics': topics
        }

            doc = fromstring(result.decode('utf-8'))

            for element in doc.xpath("//*[@src]"):
                src = element.attrib['src']

                if '/@@images' in src:
                    src = src.split('/@@images')[0]

                if 'resolveuid' in src:
                    uid = src.split('/')[-1]
                    r = portal.portal_catalog(UID=uid)
                    if len(r) == 1:
                        img = r[0].getObject()
                    else:
                        element.attrib['src'] = ''
                        continue
                elif 'http' in src:
                    img_id = src.split('/')[-1]
                    imgname = '%s/%s' % (gradedir, img_id)
                    urllib.urlretrieve(src, imgname) 
                    element.attrib['src'] = img_id
                    continue
                elif 'data:image' in src:
                    basesplit = src.split(';base64,') 
                    data = basesplit[1].decode('base64')
                    ext = basesplit[0].split('/')[-1]
                    imgname = '%s/%s.%s' % (gradedir, obj.id, ext)
                    imgfile = open(imgname, 'wb+')
                    imgfile.write(data)
                    imgfile.close()
                    continue
                else:
                    img = obj.unrestrictedTraverse(src)

                imgfile = open('%s/%s' % (gradedir, img.id), 'wb+')
                imgfile.write(img.data)
                imgfile.close()
                element.attrib['src'] = img.id


            htmlfile.write(tostring(doc))

            print "Exporting %s " % obj.id

        htmlfile.close()
