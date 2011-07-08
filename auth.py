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
from constants import *

def getAuthUser():
	#get authorization from apache/lighttpd/squid
	
	try:
		hdr = cherrypy.request.headers['Authorization']
		start = hdr.find('Digest username="')
		end = hdr.find('"', start+17)
		return hdr[start+17:end]
	except KeyError:
		#prepare database for this
		return ANONYMOUS