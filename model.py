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

import md5, logging

try:
	from decimal import Decimal #mySQLdb sometimes uses Decimal()
except:
	pass

import memcache

from constants import *
from sqlutil import *

import cherrypy #only for logging

def sprintf(f):
	try:
		fmt = '%' + CELLROUNDING + 'f'
		return fmt % eval(str(f))
	except:
		assert f == EMPTYCELL
		pass

###############################
import metadata
meta = metadata.meta
NRDIMS = meta.NRDIMS
DEFHIER = meta.DEFHIER
DEFFILTER = meta.DEFFILTER
FACTTABLE = meta.FACTTABLE

################################	
class PipelinedSQLException(Exception):
	pass

################################	
class Model:
	def getMemcachedKey(self, x):
		return md5.new(repr(x)).hexdigest()
			
	def runSQL(self, sql, cachedOnly = False):
		try:
			mc = cherrypy.thread_data.mc
		except:
			#SQL can be called in init part, before there are PRIMARY threads
			#for testing
			mc = memcache.Client(MEMCACHESRV, debug=0)
		key = self.getMemcachedKey(sql)
		v = mc.get(key)
		if cachedOnly:
			if not v:
				return []
			elif eval(v)[0] == sql:
				return eval(v)[1]
			else:
				try:
					cherrypy.log('memcached collision:'+repr(param), \
						context='getCellCachedData', \
						severity=logging.ERROR, traceback=False)
				except:
					pass
				print 'memcached collision:'+repr(param)
			
		if (not v) or (eval(v)[0] != sql):
			#try:
			res = runSQL_uncached(sql)			
			#except:
			if (not v):
				mc.set(key, repr( (sql,res) ))
			else:
				try:
					cherrypy.log('memcached collision:'+repr(param), \
						context='getCellCachedData', \
						severity=logging.ERROR, traceback=False)
				except:
					pass
				print 'memcached collision:'+repr(param)
			return res

		return eval(v)[1]
					
	def getMinMax(self):
		mins = []
		maxs = []
		for i in range(NRDIMS):
			sql = """select start_range, end_range from %s where id=parent_id;""" % \
				meta.tableNames[i]
			res = self.runSQL(sql)
			mins.append(int(res[0][0]))
			maxs.append(int(res[0][1]))
		return (mins, maxs)
	
	def getAuthChildren(self, dim, hier, filters):
		#only authorised children
		sql = 'select distinct id, name, start_range, end_range, gen from ' + \
			"""%s where %d <= start_range and end_range <= %d and (parent_id in (%s) or id in (%s)) """ \
			% (meta.tableNames[dim], filters[2*dim], filters[2*dim+1], \
				repr(hier)[1:-1], 
				repr([abs(a) for a in hier])[1:-1]) + \
			 ' order by start_range,gen;'
			 
		res = self.runSQL(sql)
		return res
		
	def getHier(self, dim, user):
		#first 2 columns match getAuthChildren, so it can be used for genDrillLinks()
		#sql = """select id, name, parent_id,  start_range, end_range, gen from %s order by start_range,gen""" \
		#	% meta.tableNames[dim]
		sql = "select d.id, d.name, d.parent_id,  d.start_range, d.end_range, d.gen " +\
			"from %(dim_tbl)s d, %(dim_tbl)s p, users_01, auth_01 " +\
			"where auth_01.dim=%(dim)s and " +\
			"users_01.name = '%(user)s' and users_01.id = auth_01.id and " +\
			"auth_01.element = p.name and p.start_range <= d.start_range and d.end_range <= p.end_range " \
			"order by d.start_range,d.gen;"
		d =	{'dim_tbl' : meta.tableNames[dim], 
			'dim' : dim,
			'user' : user}
		res = self.runSQL(sql % d)
		return res

	def getNode(self, dim, id):
		sql = """select id, name, start_range, end_range, gen from %s where id=%d""" % \
			(meta.tableNames[dim], id)
		res = self.runSQL(sql)
		return res[0]
			
	def getRoot(self, dim):
		sql = """select id, name, start_range, end_range, gen from %s where gen=0""" % \
			(meta.tableNames[dim])
		res = self.runSQL(sql)
		return res[0]
				
	def getCellCachedData(self, param):
		#paired with pipelinedSQL* functions
		assert isinstance(param, list)
		assert len(param) == 2*NRDIMS
		param2 = map(int, param)
				
		try:
			mc = cherrypy.thread_data.mc
		except:
			#used by test.py
			mc = memcache.Client(MEMCACHESRV, debug=0)
		key = self.getMemcachedKey(param2)
		r = mc.get(key)
		
		try:
			if eval(r)[0] != param2:			
				"""Steven Grimm:
				If you use a good hash function like SHA-1, false collisions are 
				basically a nonissue. You're more likely to be killed by a falling 
				airplane while holding a winning lottery ticket than to ever see an 
				SHA-1 collision between valid SQL queries."""
				#still, handle collisions by forcing SQL query
				print 'memcached collision:'+repr(param)
				try:
					cherrypy.log('memcached collision:'+repr(param), \
						context='getCellCachedData', \
						severity=logging.ERROR, traceback=False)
				except:
					pass
				return None
			else:
				return eval(r)[1]
		except:
			pass
			
		return None
		
	
	def lookupCache(self, qDict):
		try:
			mc = cherrypy.thread_data.mc
		except:
			#for testing
			mc = memcache.Client(MEMCACHESRV, debug=0)
		
		uncachedL = []
		cachedL = []
		toCalculateL = []
		for (k,q) in qDict.items():
			if isinstance(q, list):
				cachedRes = self.getCellCachedData(q)
				if cachedRes != None:
					cachedL.append( (k, sprintf(cachedRes) ) )
				else:
					uncachedL.append( (k, q) )
			else:
				toCalculateL.append( (k, q) )
		
		"""mc.get_multi( \
			map(lambda x: md5.new(repr(self.sqlFromList(MINORSEP.join(x)))).hexdigest(), \
			"""
		return (cachedL, uncachedL, toCalculateL)
		
	def calculateFormulas(self, toCalculateL, readyL):
		#sample item ('0_0', "-1*float(q['1_0'])" )
		#treat value 'n/a' as 0.0 internally, ex in order to make sums
		#return 'n/a' for exceptions
		def avoidEMPTYCELL(l):
			replacedElems = [(k,'0.0') for (k,v) in l if v in (EMPTYCELL, None) ]
			origElems = [(k,v) for (k,v) in l if v not in (EMPTYCELL, None) ]
			return replacedElems + origElems
		
		readyLZeros = avoidEMPTYCELL(readyL)
		res = []
		crtL = toCalculateL
		nextL = []
		for iter in xrange(FORMULA_ITERATIONS):
			q = dict(readyLZeros + avoidEMPTYCELL(res) )
			for (k,f) in crtL:
				try:
					#print 'eval', k, f
					res.append( (k, eval(f)) )
				except KeyError:
					#print 're-iterate', k, f
					# formula based on formula ..
					nextL.append( (k,f) )
				except:# ValueError:
					#print 'ValueError', res, f
					res.append( (k,EMPTYCELL) )					
			crtL = nextL
			nextL = []
		#print '%'*5, toCalculateL, res
		return res
		
	def getTableNames(self, rowL):
		#get the explicit segregated tableNames + surrounding 
		# from TTTTT where
		res = []
		for (k,q) in rowL:
			tmp = FACTTABLE[0]
			for d in xrange(NRDIMS):
				if meta.isTable[d] == 1:
					#queries should be "segregated" by non-selectable dims
					assert q[2*d] == q[2*d+1]
					tmp += "_%s" % q[2*d]
			res.append(''' from %s where ''' % tmp)
		return res

		
	def buildUnionAllSQL(self, oncols, filters, rowL):
		#build SQL for given params
		#suitable if MySQL database is partitioned by dimension "on columns" 
		#..OR.. databases other than MySQL

		assert len(rowL) > 0
		
		(mins, maxs) = self.getMinMax()
				
		try:
			sumArgs = [ (k, q[2*oncols: 2*oncols+2]) for (k,q) in rowL]
		except:
			#list if 1 element
			(k,q) = rowL
			sumArgs = [ (k, q[2*oncols: 2*oncols+2])]
			
		#some rows might be NULL , use select 0, sum()
		sqlStart = '''select 0, sum( %s ) ''' % FACTMEASURE 
	
		if meta.isTable[oncols] == 0 :
			extraWhere = []
			for (k,a) in sumArgs:
				if a[0] == a[1]:
					extraWhere.append( ''' dim_%s = %s ''' % (oncols, a[0]) )
				else:
					extraWhere.append(''' %s <= dim_%s and dim_%s <= %s ''' % \
						(a[0], oncols, oncols, a[1]) )
		else:
			extraWhere = [''] * len(sumArgs)
			
		sqlTable = self.getTableNames(rowL)
					
		whereArgs = rowL[0][1]		
			
		whereClause = []
		for w in xrange(len(whereArgs)/2):
			#oncols are in extraWhere; isTable filters are redundant
			if w != oncols and meta.isTable[w] == 0 and \
					(int(whereArgs[2*w]) != mins[w] or \
					int(whereArgs[2*w+1]) != maxs[w]): # cut away "all XXX" filters
				if whereArgs[2*w] == whereArgs[2*w+1]:
					#avoid "10 <= dim_1 and dim_1 <= 10"
					whereClause.append('''dim_%s = %s and''' % (w, whereArgs[2*w]) )
				else:
					whereClause.append( '''%s <= dim_%s and dim_%s <= %s and''' % \
						(whereArgs[2*w], w, w, whereArgs[2*w+1]) )
			
		whereClauseStr = ' '.join(whereClause)
		
		s = ' union all\n'.join(\
			[sqlStart + sqlTable[ew] + whereClauseStr + extraWhere[ew] \
			for ew in xrange(len(extraWhere))] )
		s += ';'
		for j in xrange(2):
			s = s.replace(' and union', ' union')
			s = s.replace(' and;', ';')
			s = s.replace(' where union', ' union')	
			s = s.replace(' where ;', ';')
		return s
		
	def runUnionAllHelper(self, oncols, filters, rowL, workerThreadNr):
		#run the query fragmets
		if len(rowL) == 0:
			#happens if workload % MAX_PIPELINED_UNION == 0
			return []
		sql = self.buildUnionAllSQL(oncols, filters, rowL)
		
		#some rows might be NULL
		dbResNones = runSQL_uncached(sql, workerThreadNr)
		dbRes = []
		for x in dbResNones:
			if x[1] == None:
				dbRes.append(EMPTYCELL)
			else:
				dbRes.append(x[1])
		return dbRes
		
	def runUnionAllSQL(self, oncols, filters, rowL, workerThreadNr):
		#if you run too many UNION ALLs over partitioned table, 
		#mySQL runs out of file descriptors
		for retry in xrange(2):
			try:
				dbRes = []
				for i in xrange(1+len(rowL)/MAX_PIPELINED_UNION):
					dbRes.extend(	self.runUnionAllHelper(oncols, filters, \
						rowL[ i*MAX_PIPELINED_UNION : (i+1)*MAX_PIPELINED_UNION ],\
						workerThreadNr ) )
				if dbRes[-1] == []:
					#happens if workload % MAX_PIPELINED_UNION == 0
					dbRes = dbRes[:-1]
				if len(dbRes) != len(rowL):
					raise 'retry SQL'
				return dbRes
			except:
				try:
					cherrypy.log('retry SQL in thread %d' % workerThreadNr, \
						context='runUnionAllSQL', \
						severity=logging.ERROR, traceback=True)
				except:
					pass
				print 'retry SQL in thread %d' % workerThreadNr
		
	def buildConjunctiveSQL(self, oncols, filters, rowL):
		#
		# read http://www.cs.columbia.edu/~kar/pubsk/selections.pdf
		#
		#build SQL for given params

		(mins, maxs) = self.getMinMax()
		
		sumArgs = [ (k, q[2*oncols: 2*oncols+2]) for (k,q) in rowL]
		sql = ['select']
		sql.extend( ['''sum(%s *(%s <= dim_%s and dim_%s <= %s)) as c_%s,''' % \
				(FACTMEASURE, a[0], oncols, oncols, a[1], k) \
				for (k,a) in sumArgs] )
		sql[-1] = sql[-1][:-1] #remove trailing ','
		
		sql.append('''from %s where''' % self.getTableNames(rowL))
			
		whereArgs = rowL[0][1]		
				
		for w in xrange(len(whereArgs)/2):
			if w != oncols and meta.isTable[w] == 0 and \
					(int(whereArgs[2*w]) != mins[w] or \
					int(whereArgs[2*w+1]) != maxs[w]): # cut away "all XXX" filters
				if whereArgs[2*w] == whereArgs[2*w+1]:
					#avoid "10 <= dim_1 and dim_1 <= 10"
					sql.append('''dim_%s = %s and''' % (w, whereArgs[2*w]) )
				else:
					sql.append( '''%s <= dim_%s and dim_%s <= %s and''' % \
						(whereArgs[2*w], w, w, whereArgs[2*w+1]) )
			
		
		sql[-1] = sql[-1][:-4] #remove trailing ' and'
		sql.append(';')
		s = ' '.join(sql)
		return s
		
	def runConjunctiveSQL(self, oncols, filters, rowL, workerThreadNr):
		sql = self.buildConjunctiveSQL(oncols, filters, rowL)
		
		for retry in xrange(2):
			try:
				#some cols might be NULL
				dbResNones = runSQL_uncached(sql, workerThreadNr)
				dbRes = []
				for x in dbResNones[0]:
					if x == None:
						dbRes.append(EMPTYCELL)
					else:
						dbRes.append(x)
				if len(dbRes) != len(rowL):
					raise 'retry SQL'
				return dbRes
			except:
				try:
					cherrypy.log('retry SQL in thread %d' % workerThreadNr, \
						context='runConjunctiveSQL', \
						severity=logging.ERROR, traceback=True)
				except:
					pass
				print 'retry SQL in thread %d' % workerThreadNr
				
		
	def runPipelinedQueriesFromDict(self, params):
		#run together SQL bellonging to same row; dict key is "rowID/cellID"
		#params=dict flattened as list
		
		(uncachedL, oncols, filters, workerThreadNr) = params
		
		try:
			res = []
			try:
				mc = cherrypy.thread_data.mc
			except:
				mc = memcache.Client(MEMCACHESRV, debug=0)
			
			duplicatedHeads = [k[:k.find(MINORSEP)] for (k,q) in uncachedL]
			heads = dict( [(x, True) for x in duplicatedHeads] ).keys()
			
			#O(N), rewrite
			for h in heads:
				rowL = [(k,q) for (k,q) in uncachedL if k.split(MINORSEP)[0]==h]
				#check start_range/end_range other than oncols are same within rowID...
				otherThanOnCols = dict(\
					[ (repr(q[:2*oncols]+q[2*oncols+2:]), True) \
						for (k,q) in rowL])
				if len(otherThanOnCols) != 1:
					raise PipelinedSQLException
				
				assert len(rowL) > 0
				if 1==1: #DBLIB != 'mysql' or meta.isPartition[oncols] or meta.isTable[oncols]:
					dbRes = self.runUnionAllSQL(oncols, filters, rowL,\
						workerThreadNr)
				else:
					dbRes = self.runConjunctiveSQL(oncols, filters, rowL, \
						workerThreadNr)
				
				for i in xrange(len(rowL)):
					res.append( (rowL[i][0], dbRes[i]) )
					elementSQL = map(int, rowL[i][1])
					key = self.getMemcachedKey(elementSQL)

					#handle HASH collisions
					mc.set(key, repr( (elementSQL, dbRes[i] ) ))
			
			return [(x[0], sprintf(x[1])) for x in res]
			
		except PipelinedSQLException:
			print 'PipelinedSQLException: SQL queries not "on same row"', '!'*20, params 
			raise PipelinedSQLException
			
	def securityByUser(self, filters, webuser):
		#restrict filters to what user is authorised
		perms = runSQL_uncached('''select a.dim,a.element from auth_01 a, ''' + \
			'''users_01 u where a.id=u.id and u.name='%s' order by a.dim;''' % webuser)
		
		mM = []
		for p in perms:
			s = "select start_range, end_range from %s where name='%s' " % \
				(meta.tableNames[p[0]], p[1])
			tmp = runSQL_uncached(s)
			mM.extend(tmp[0][0:2])
		
		if len(mM) != NRDIMS * 2:
			return [-1]*NRDIMS*2
		
		res = []
		for i in xrange(len(filters)/2):
			res.append(max(filters[2*i], mM[2*i]))
			res.append(min(filters[2*i+1], mM[2*i+1]))
				
		return res
		