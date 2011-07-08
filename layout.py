"""
Cubulus OLAP - free aggregation and reporting
Copyright (C) 2007 Alexandru Toth

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation version 2.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import cherrypy
from model import *
from drillview import *
import auth

################################
import metadata
meta = metadata.meta
NRDIMS = meta.NRDIMS
DEFHIER = meta.DEFHIER
DEFFILTER = meta.DEFFILTER

################################
#need to pass form fileds from /data to /index in order to keep filters hiers
class Layout:
	#
	#if you have parameter 'user', it allows USERNAME SPOOFING ATTACK
	#instead, read the validated headers 
	#
	def __init__(self):
		f = open('html_templates/layout.tmpl','r')
		self.tmpl = f.read()
		f.close()
		
		f = open('html_templates/power_by.tmpl','r')
		self.powerBy = f.read()
		f.close()
	
	def index(self, onrows='0', oncols='1', hiers='', filters = ''):
		user = auth.getAuthUser()
		
		if user == '':
			return '''<a href="http://localhost/cub/login/">login here</a>'''
		else:
			return self.indexNoSecurity(auth.getAuthUser(), \
				onrows, oncols, hiers, filters)
	index.exposed = True
	
	#
	# DON*T EXPOSE !!
	def indexNoSecurity(self, user=ANONYMOUS, onrows='0', oncols='1', hiers='', filters = ''):
		dv = DrillView()
		try:
			myonrows = int(onrows)
		except:
			myonrows = 0

		try:
			myoncols = int(oncols)
		except:
			myoncols = 1
		if myonrows == myoncols:
			myoncols = (myonrows+1) % NRDIMS
			
		cherrypy.response.headers['Content-Type'] = CONTENT_TYPE
		cherrypy.response.headers['cache-control'] = CACHEABLE
		
		#onows, oncols are used once more for tmlp % substitution !!
		iframe = """%(dataroot)s/default?onrows=%(onrows)d%(escape)soncols=%(oncols)d""" % \
			{'onrows': myonrows, 'oncols': myoncols, 'dataroot': DATAROOT, 'escape' : '&amp;'}
			
		if hiers != '':
			iframe += '&amp;hiers='+hiers
			
		if filters != '':
			iframe += '&amp;filters='+filters
			
		d = {'NRDIMS' : NRDIMS,
		'modProxyRoot' : MOD_PROXY_ROOT_2,
		'username' : auth.getAuthUser(),
		'rcfheader': dv.renderDesigner(myonrows, myoncols),
		'onrows': myonrows, 'oncols': myoncols, 'hiers': hiers, 'filters':filters,
		'iframe' : iframe,
		'w' : '100%', 'h' :  '900px',
		'method' : SUBMITMETHOD, 'hidden' : FORMFIELDS,
		'cubulus_version': CUBULUS_VERSION,
		'powered_by': self.powerBy}
		
		return self.tmpl % d





