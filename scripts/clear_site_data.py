""" Clear site stats
"""
import sys

import transaction
from Testing import makerequest
from AccessControl.SecurityManagement import newSecurityManager
from zope.component import getUtility

from tarmii.theme.interfaces import ISiteData
from BTrees.OOBTree import OOBTree

app = makerequest.makerequest(app)
portal = getattr(app, sys.argv[-1])

user = app.acl_users.getUser('admin')
newSecurityManager(None, user.__of__(app.acl_users))
portal.setupCurrentSkin(portal.REQUEST)

sitedata = getUtility(ISiteData, context=portal)
sitedata.user_data = OOBTree()
sitedata.log_data = OOBTree()

print "Site data cleared"

transaction.commit()

