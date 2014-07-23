""" Clear all page requests
"""
import sys

import transaction
from Testing import makerequest
from AccessControl.SecurityManagement import newSecurityManager
from zope.component import getUtility

from upfront.pagetracker.interfaces import IPageTracker

app = makerequest.makerequest(app)
portal = getattr(app, sys.argv[-1])

user = app.acl_users.getUser('admin')
newSecurityManager(None, user.__of__(app.acl_users))
portal.setupCurrentSkin(portal.REQUEST)

pagetracker = getUtility(IPageTracker, context=portal)
print "Number of requests logged before clearing: ", \
    len(pagetracker.logged_data())
pagetracker._clear_log()
print "Number of requests logged after clearing: ", \
    len(pagetracker.logged_data())

transaction.commit()

