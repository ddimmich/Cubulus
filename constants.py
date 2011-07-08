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

import os

CUBULUS_VERSION = '0.57'

#carefull in setting too many therads, there is Python Global Interpreter Lock !
#try using multiple CherryPy processes with few theads
THREADPOOL_PRIMARY = 4 #CherryPy threadpool
#try secondary threads = nr CPUs in database severs
#set to 1 if you want to disable secondary threads
THREADPOOL_SECONDARY = 1 #worker theads (for doing sql) in each CherryPy thread
SERVER_SOCKET = 8080		#CherryPy port, try default 8080
MOD_PROXY_ROOT ='/'	#if CherryPy is behind Apache mod_proxy; otherwise '/'
ENVIRONMENT = ''	#CherryPy config, use 'production' OR ''
ACCESS_LOG = 'access_cubulus.log'
ERROR_LOG = 'error_cubulus.log'
ANONYMOUS =	'anonymous'	#if there is no apache/squid/lighhtpd auth

MAJORSEP = '/'	#separators for form fields
MINORSEP = '_'	
VERBDRILL = '0'	#values for submit
VERBFILTER = '1'
VERBNEST = '2'
VERBSETFILTER = '3'
VERBMDX = '4'
DEFROW = 1	#default values for first view
DEFCOL = 0

DBLIB = 'postgres' # 'mysql', 'sqlite' , 'postgres', 'monet5'

#You don't want to store passwords in code, especially not on a webserver
#for some reason ~/.my.cnf does not work in Python
try:
	PASSWORDFILE = os.environ['HOME']+'/' + '.my.cnf'
except:
	PASSWORDFILE = 'c:\my.cnf'

DBSERVERS = ['localhost']*THREADPOOL_SECONDARY	#mySQL server
DBPORTS = [5432]*THREADPOOL_SECONDARY	#for 'localhost' MySQLdb will use socket, not port !!
DATABASE = 'cubulus'
FACTMEASURE = 'figure'
SQLDEBUG = False	#prints SQL statements and results to console
#if you run too many UNION ALLs over partitioned table, 
#mySQL runs out of file descriptors
MAX_PIPELINED_UNION = 10

MEMCACHESRV = ['127.0.0.1:11211']

CACHEABLE = 'public,max-age=60'	#don't use unless you need squid proxy

FORMULA_ITERATIONS=3	#calculate cell formulas (that are formulas)*

SUBMITMETHOD="post"		#use GET only for squid proxy / other good reason
FORMFIELDS = "hidden"		#invisible form fields (text/hidden)
CELLHEIGHT = 30
CELLWIDTH = 120
CELLROUNDING = "6.2"	# %6.2f
EMPTYCELL = 'n/a'
C_WEAVE = 'c_weave'
R_WEAVE = 'r_weave'
FILTERHIGHLIGHT = 'bgcolor="lightblue"'
ERRORMESSAGE = 'bad request'	#use one error message for users
JAVASCRIPT = """<script type="text/javascript">
	function drill(ve, di, it) {
		frm = document.getElementById('cubulus')
		frm.verb.value = ve;
		frm.dim.value = di;
		frm.item.value = it;	
		frm.submit();};</script>"""
		
MOD_PROXY_ROOT_2 = ''	#used to avoid links like //data
if MOD_PROXY_ROOT != '/':
	MOD_PROXY_ROOT_2 = MOD_PROXY_ROOT
		
DATAROOT = MOD_PROXY_ROOT_2 +'/data'	#used for location of hier menus

CONTENT_TYPE = "application/xhtml+xml"

#sanity check
assert THREADPOOL_PRIMARY >= 4
assert THREADPOOL_SECONDARY >= 1
assert ENVIRONMENT in ('', 'production')
assert len(DBSERVERS) == len(DBPORTS)
assert SUBMITMETHOD in ['post','get']
assert FORMFIELDS in ['text', 'hidden']
assert DBLIB in ['mysql', 'sqlite' , 'postgres','monet5']
