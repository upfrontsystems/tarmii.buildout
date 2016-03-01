import sys

import transaction
from Testing import makerequest
from AccessControl.SecurityManagement import newSecurityManager

app = makerequest.makerequest(app)
portal = getattr(app, sys.argv[-1])

user = app.acl_users.getUser('admin')
newSecurityManager(None, user.__of__(app.acl_users))
portal.setupCurrentSkin(portal.REQUEST)
wftool = portal.portal_workflow

for item in portal.portal_catalog(
        portal_type='upfront.assessmentitem.content.assessmentitem'
    ):
    obj = item.getObject()
    status = wftool.getInfoFor(obj, 'review_state')
    if status == 'internal':
        wftool.doActionFor(obj, 'submit')
        print "Submitting", '/'.join(obj.getPhysicalPath())

transaction.commit()

