import cherrypy, logging, time

from constants import *

from DBUtils.PooledDB import PooledDB

if DBLIB == 'mysql':
	#you will have to manually install MySQLdb
	import MySQLdb
elif DBLIB == 'postgres':
	import bpgsql
elif DBLIB == 'monet5':
	import MonetSQLdb
else:
	try:
		#Python2.5 has builtin sqlite3
		from sqlite3 import dbapi2 as sqlite
	except:
		#in Python 2.4 (and earlier?) you can install for ex: pysqlite package
		from pysqlite2 import dbapi2 as sqlite
	#you can't login & logoff SQLite
	from DBUtils.PersistentDB import PersistentDB


################################
dbServersPool = [] # init later
################################
	
def getPW():
	def searchHelper(s, subs):
		start = s.find(subs) + len(subs)+2
		end = s.find('"', start+1)
		res = s[start:end]
		return res

	try:
		f=open(PASSWORDFILE,'r')
		s=f.read()
		f.close()
		return (searchHelper(s, 'password'),searchHelper(s, 'user'))
	except IOError:
		return ('','')

def dbInit(workerThreadNr):
	(pw,usr) = getPW()
	for i in xrange(len(DBPORTS)):
		try:
			srv = (workerThreadNr + i) % THREADPOOL_SECONDARY
			if DBLIB == 'mysql':
				if DBSERVERS[srv] != 'localhost':
					res = PooledDB(MySQLdb, \
						mincached = 1, maxcached = 1+THREADPOOL_PRIMARY,
						maxconnections = 1+THREADPOOL_SECONDARY,\
						host = DBSERVERS[srv], \
						port = DBPORTS[srv], \
						db = DATABASE, passwd = pw, user = usr)
				else:
					res = PooledDB(MySQLdb, \
						mincached = 1, maxcached = 1+THREADPOOL_PRIMARY,
						maxconnections = 1+THREADPOOL_SECONDARY,\
						db = DATABASE, passwd = pw, user = usr)

			elif DBLIB == 'postgres':
				res = PooledDB(bpgsql, \
					host = DBSERVERS[srv], \
					dbname = DATABASE, user = 'cubulus', password='cubulus')
			elif DBLIB == 'monet5':
				res = PooledDB(MonetSQLdb, host = DBSERVERS[srv], lang = 'sql')
			else:
				res = PersistentDB(sqlite, 0, database = "cubulus.db")
			print 'dbInit()', res
			return res
		except: # OperationalError:
			print 'error init connection to %s:%d' % \
				(DBSERVERS[srv] , DBPORTS[srv])

	try:
		cherrypy.log('all databases down !!!', \
			context='dbInit', \
			severity=logging.ERROR, traceback=False)
	except: 
		pass
	print 'dbInit: all databases down !!!'
		
	
def poolInit():
	return [dbInit(workerThreadNr) \
		for workerThreadNr in xrange(THREADPOOL_SECONDARY)]
	
################################
def runSQL_uncached(sql, workerThreadNr=0):
	global dbServersPool
	if SQLDEBUG:
		print '>'*5,sql
	try:
		#prevent repeated initialization of connections
		dummy = dbServersPool[0]
	except IndexError:
		dbServersPool = poolInit()
		
	for reconnect in xrange(2):
		for i in xrange(len(DBPORTS)):
			try:
				dbIdx = (workerThreadNr + i) % len(DBPORTS) 
				#find working server, starting with assigned one
				db = dbServersPool[dbIdx].connection()
								
				c = db.cursor()
				c.execute(sql)
				res = c.fetchall()
				c.close()
				try:
					#fails for PersistentDB , ex: for sqlite
					dbServersPool[dbIdx].close()
				except AttributeError:
					pass

				if SQLDEBUG:
					print '>'*5,'.'*5, res
					#c.execute('explain partitions '+sql)
					#print '>plan>', c.fetchall()
				return res
								
			except:
				import traceback
				print traceback.print_exc()
				emsg = DBSERVERS[dbIdx] + ':' + str(DBPORTS[dbIdx])
				try:
					cherrypy.log('database %s down !!!' % emsg, \
						context='runSQL_uncached', \
						severity=logging.ERROR, traceback=False)
				except:
					pass
				print 'runSQL_uncached: database %s down !!!' % emsg
				
		
		#try re-connecting again to all servers
		#some may be live again
		#
		time.sleep(2)				
		#dbServersPool = poolInit()


	try:
		cherrypy.log('all databases down !!!', \
			context='runSQL_uncached', \
			severity=logging.ERROR, traceback=False)
	except:
		pass
	print 'all databases down !!!'
	return None
