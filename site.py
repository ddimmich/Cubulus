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

import os.path, threading

import cherrypy
#from cherrypy.lib import httpauth
#import MySQLdb
#from DBUtils.PersistentDB import PersistentDB
#import memcache
#from decimal import Decimal	#mySQLdb sometimes uses Decimal()
#import threadpool	#http://chrisarndt.de/en/software/python/threadpool/
#credits: dtree www.destroydrop.com/javascript/tree/ , Copyright (c) 2002-2003 Geir Landro

from constants import *
from sqlutil import *
from model import *
from drillview import *
from layout import *
from drillform import *
		
		
################################
def connect(threadIndex):
	#Create a connection and store it in the current thread
	cherrypy.thread_data.mc = memcache.Client(MEMCACHESRV, debug=0)

	if THREADPOOL_SECONDARY > 1:
		#run the parallel SQL from these threads
		cherrypy.thread_data.threadpool = threadpool.ThreadPool(THREADPOOL_SECONDARY)
		cherrypy.thread_data.result = []
		#by default, all threads connect to same database server
		
		#allow scale-out by connecting to different database servers
		#
		#this means database replication is already taken care of
		#


# Tell CherryPy to call "connect" for each thread, when it starts up
cherrypy.engine.on_start_thread_list = [connect]

		
################################
root = Layout()
root.data = DrillForm()

################################
if __name__ == '__main__':
	current_dir = os.path.dirname(os.path.abspath(__file__))
	
	cherrypy.config.update({
		'server.thread_pool': THREADPOOL_PRIMARY,
		'tools.sessions.on': False,
		'server.socket_port': SERVER_SOCKET})
		
	if ENVIRONMENT != '':
		cherrypy.config.update({
			'log.screen': False,
			'log.access_file': ACCESS_LOG,
			'log.error_file': ERROR_LOG,
			'environment': ENVIRONMENT})
			#'tools.proxy.on': True,
			#'tools.proxy.base': 'http://macu.local/cub/'})
	
	conf = {'/static': {'tools.staticdir.on': True,
				'tools.staticdir.dir': os.path.join(current_dir, 'static'),
				'tools.staticdir.content_types': {'js': 'application/x-javascript'}},
			'/data/img' : {'tools.staticdir.on': True,
				'tools.staticdir.dir': os.path.join(current_dir, 'img')}
			}
			
	cherrypy.quickstart(root, MOD_PROXY_ROOT, conf)