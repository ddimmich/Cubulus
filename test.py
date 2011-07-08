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

import unittest, random, sys, time,os

import MySQLdb
from DBUtils.PersistentDB import PersistentDB
import memcache
from decimal import Decimal	#mySQLdb sometimes uses Decimal()
import threadpool
import cherrypy	

from constants import *
from sqlutil import *
from model import *
from drillview import DrillView
from drillform import DrillForm

def neutralFilter(minMax):
	nf = []
	[nf.extend([minMax[0][i], minMax[1][i]]) for i in xrange(NRDIMS)]
	return nf
	
class ETLTestCase(unittest.TestCase):
	def test_runGen(self):
		fd = os.popen('python gen.py | grep error')
		assert fd.read() == ''
		
	def test_runETL(self):
		fd = os.popen('python etl.py | grep error')
		assert fd.read() == ''
	
################################
class LibsTestCase(unittest.TestCase):
	def test_memcached(self):
		mc = memcache.Client(MEMCACHESRV, debug=0)

		mc.set('key', 'value')
		#this fails if memcached is not started / not installed
		assert mc.get('key') == 'value'
		
	def test_mySQL(self):
		pw = ''
		try:
			(pw,us) = getPW()
		except:
			print 'DIAGNOSTIC: create a ~/.my.cnf file with password / '
			print '.. OR .. fix ALL DB CONNECT code to suit your needs'
		
		try:
			con = MySQLdb.Connect(host=DBSERVERS[0], user = us, \
				passwd=pw, db=DATABASE)
			crs = con.cursor()
			sql = "SELECT count(*) FROM metadata;"
			crs.execute(sql)
			res = crs.fetchall()
			print res
		except:
			print 'DIAGNOSTIC: start mySQL, install MySQLdb'
			print ' .. or .. generate database'
		
		try:	
			res = PersistentDB(MySQLdb,1000,host=DBSERVERS[0], db=DATABASE, \
				user = us, passwd=pw)
		except:			
			print 'DIAGNOSTIC: start mySQL, install DBUtils'
			
	def test_threadpool(self):
		#
		#copied from 
		# http://chrisarndt.de/en/software/python/threadpool/threadpool.py.html
		#
		#
		# the work the threads will have to do (rather trivial in our example)
		def do_something(data):
			time.sleep(1)
			result = round(random.random() * data, 5)
			return result

		# this will be called each time a result is available
		def print_result(request, result):
			print "**Result: %s from request #%s" % (result, request.requestID)

		# this will be called when an exception occurs within a thread
		def handle_exception(request, exc_info):
			print "Exception occured in request #%s: %s" % \
			  (request.requestID, exc_info[1])

		# assemble the arguments for each job to a list...
		data = [random.randint(1,10) for i in range(5)]
		# ... and build a WorkRequest object for each item in data
		requests = threadpool.makeRequests(do_something, data, print_result)


		# we create a pool of 3 worker threads
		main = threadpool.ThreadPool(3)

		# then we put the work requests in the queue...
		for req in requests:
			main.putRequest(req)
			print "Work request #%s added." % req.requestID
		
		main.wait()


################################
class ModelTestCase(unittest.TestCase):
	def setUp(self):
		self.model = Model()
		self.neutralFilter = neutralFilter(self.model.getMinMax())
		
	def test_dbInit(self):
		assert dbServersPool != None
		
	def test_runSQL_uncached(self):
		r = runSQL_uncached('select count(*) from metadata;')
		assert len(r) == 1
		assert r[0][0] >= 0
		
	def test_runSQL_cached(self):
		rnd = random.randint(0,100000)
		s = '''select count(*) from metadata where %d=%d;''' % (rnd, rnd)
		
		#check there is nothing in memcache
		cached = self.model.runSQL(s,True)
		assert cached == []
		
		#run query
		r = self.model.runSQL(s)
		assert len(r) == 1
		assert r[0][0] >= 0
		
		#check cache again
		cached2 = self.model.runSQL(s,True)
		assert repr(cached2) == repr(r)
		
			
	def test_getMinMax(self):
		r = self.model.getMinMax()
		assert len(r[0]) == len(r[1])
		for i in xrange(NRDIMS):
			assert r[0][i] <= r[1][i]
			
	def disabled_test_getAuthChildren(self):
		#bad filter
		x = self.model.getAuthChildren(1,[0], [0]*NRDIMS*2)
		assert len(x) == 0
		
		#children of root
		x = self.model.getAuthChildren(1,[0], self.neutralFilter)
		assert len(x) > 0
		
		#children of first node
		y = self.model.getAuthChildren(1,[1], self.neutralFilter)
		assert len(y) > 0
		
		sx = set(x)
		sy = set(y)
		assert sx.intersection(sy) == set([])
		
		#common hier
		z = self.model.getAuthChildren(1,[0,1], self.neutralFilter)
		assert set(z) == set(x+y)
		
	def test_getHier(self):
		#irrelevant .. better ideas?
		r1 = self.model.getHier(0,ANONYMOUS)
		assert len(r1) != 0
		r2 = self.model.getHier(1,ANONYMOUS)
		assert len(r2) != 0
		assert r1 != r2
		assert self.model.getNode(0, r1[0][0])[1] == r1[0][1]
		
	def test_getNode(self):
		#see test_getHier()
		pass
		
	def test_getRoot(self):
		pass
		
	def test_getCellCachedData(self):
		mc = memcache.Client(MEMCACHESRV, debug=0)
		#unlikely key
		k = [random.randint(0,100000)] * NRDIMS * 2
		assert self.model.getCellCachedData(k) == None
		mc.set(self.model.getMemcachedKey(k), repr((k,'1.1')))
		x = self.model.getCellCachedData(k)
		assert self.model.getCellCachedData(k) == '1.1'
		
	def test_lookupCache(self):
		mc = memcache.Client(MEMCACHESRV, debug=0)
		#unlikely keys
		k1 = [random.randint(0,100000)] * NRDIMS * 2
		k2 = [random.randint(0,100000)] * NRDIMS * 2
		
		qDict = {'k_1' : k1, 'k_2' : k2 }
		(cachedL, uncachedL, toCalculateL) = self.model.lookupCache(qDict)
		assert len(cachedL) == 0
		assert len(uncachedL) == 2
		
		#
		#
		#write suitable test for toCalculateL!!
		#
		assert len(toCalculateL) == 0
		#assert 1==0
		
		#test when test_lookupCache actually finds domething ..
		
	def test_buildPipelinedSQL(self):
		res = self.model.buildConjunctiveSQL(1,
			[0, 24087, 0, 15, 0, 25, 0, 50, 0, 15, 1, 1, 0, 4], 
			[('2_0', ['24076', '24087', '0', '15', '0', '25', '0', '50', '0', '15', '1', '1', '0', '4']), 
			('2_1', ['24076', '24087', '6', '7', '0', '25', '0', '50', '0', '15', '1', '1', '0', '4']), 
			('2_2', ['24076', '24087', '8', '9', '0', '25', '0', '50', '0', '15', '1', '1', '0', '4']), 
			('2_3', ['24076', '24087', '10', '11', '0', '25', '0', '50', '0', '15', '1', '1', '0', '4']), 
			('2_4', ['24076', '24087', '12', '13', '0', '25', '0', '50', '0', '15', '1', '1', '0', '4']), 
			('2_5', ['24076', '24087', '14', '15', '0', '25', '0', '50', '0', '15', '1', '1', '0', '4'])])
		#testing for optimisations of avoiding all=all and equality instead of range test
		assert res == "select sum(figure *(0 <= dim_1 and dim_1 <= 15)) as c_2_0,"+\
			" sum(figure *(6 <= dim_1 and dim_1 <= 7)) as c_2_1, "+\
			"sum(figure *(8 <= dim_1 and dim_1 <= 9)) as c_2_2, "+\
			"sum(figure *(10 <= dim_1 and dim_1 <= 11)) as c_2_3, "+\
			"sum(figure *(12 <= dim_1 and dim_1 <= 13)) as c_2_4, "+\
			"sum(figure *(14 <= dim_1 and dim_1 <= 15)) as c_2_5 "+\
			"from fact where 24076 <= dim_0 and dim_0 <= 24087 and dim_5 = 1 ;"
									
	def test_runPipelinedQueriesFromDict(self):
		N = 5
		#unlikely keys, in a list
		#list elements not on "same row"
		print 'expecting PipelinedSQLException'
		l = [('0_%d' % i, [random.randint(0,100000)] * NRDIMS * 2) 
			for i in xrange(N)]
		self.assertRaises(PipelinedSQLException, \
			self.model.runPipelinedQueriesFromDict, \
			(l, 0, self.neutralFilter,0) )
			
		#now requests are on same row, all must have same result
		x = [random.randint(0,100000)] * NRDIMS * 2
		l = [('0_%d' % i, x) for i in xrange(N)]			
		res = self.model.runPipelinedQueriesFromDict( (l, 0, self.neutralFilter,0))
		for elem in res[1:]:
			assert elem[1] == res[0][1]
			
		#now requests are on same row, all different
		l = [('%d_%d' % (i,i), [random.randint(0,100000)] * NRDIMS * 2) 
			for i in xrange(N)]			
		res = self.model.runPipelinedQueriesFromDict( (l, 0, self.neutralFilter,0))
		uniqHeads = dict( [(x[0],1) for x in res] ).items()
		assert len(uniqHeads) == N
		
		#check runPipelinedQueriesFromDict did the caching
		qDict = dict(l)
		(cachedL, uncachedL,toCalculateL) = self.model.lookupCache(qDict)
		assert len(uncachedL) == 0
		
	def test_securityByUser(self):
		secA = self.model.securityByUser(self.neutralFilter, 'a')
		secB = self.model.securityByUser(self.neutralFilter, 'anonymous')
		
		#assert repr(secA) != repr(secB)
		#assert repr(secA) == repr(self.neutralFilter)

		#test unknown user
		#assert 1==0

################################				
class DrillViewTestCase(unittest.TestCase):
	def setUp(self):
		pass
		
	def test_renderDesigner(self):
		html = DrillView().renderDesigner(0,1)
		#assert html.find('Dim 0 on rows') == -1
		#assert html.find('Dim 1 on rows') == -1
		#assert html.find('Dim 2 on rows') != -1
		
		#assert html.find('Dim 0 on cols') == -1
		#assert html.find('Dim 1 on cols') == -1
		#assert html.find('Dim 2 on cols') != -1
		
		assert html.find("javascript:set_r('0')") == -1
		assert html.find("javascript:set_r('1')") == -1
		assert html.find("javascript:set_r('2')") != -1
		
		assert html.find("javascript:set_c('0')") == -1
		assert html.find("javascript:set_c('1')") == -1
		assert html.find("javascript:set_c('2')") != -1
		
	def test_genCellQueryStr(self):
		xx = [-99]*NRDIMS*2
		res = DrillView().genCellQueryStr(0,1,xx,\
			(1L, 'prod_0', 4L, 44L, 1L), (1L, 'region_0', 5L, 55L, 1L))
		assert res[0] == '4'
		assert res[1] == '44'
		assert res[2] == '5'
		assert res[3] == '55'
		assert res[4:] == ['-99'] * (2*NRDIMS-4)
		
	def sample_genCellRowDict(self):
		#this is just an usage sample
		#when generating new random database this will fail
		onrows = 0
		oncols = 1
		filters = [4, 13, 6, 13, 24044, 24044, 0, 60]
		rowelem = (1L, 'prod_0', 4L, 13L, 1L)
		rownr = 0
		cols = ((1L, 'region_0', 6L, 13L, 1L),
			(6L, 'region_0_0', 6L, 6L, 2L), 
			(7L, 'region_0_1', 7L, 7L, 2L),
			(8L, 'region_0_2', 8L, 8L, 2L),
			(9L, 'region_0_3', 9L, 9L, 2L),
			(10L, 'region_0_4', 10L, 10L, 2L),
			(11L, 'region_0_5', 11L, 11L, 2L),
			(12L, 'region_0_6', 12L, 12L, 2L),
			(13L, 'region_0_7', 13L, 13L, 2L))		
		qDict = {'0_8': ['4', '13', '13', '13', '24044', '24044', '0', '60'],
			'0_6': ['4', '13', '11', '11', '24044', '24044', '0', '60'],
			'0_7': ['4', '13', '12', '12', '24044', '24044', '0', '60'],
			'0_4': ['4', '13', '9', '9', '24044', '24044', '0', '60'], 
			'0_5': ['4', '13', '10', '10', '24044', '24044', '0', '60'], 
			'0_2': ['4', '13', '7', '7', '24044', '24044', '0', '60'], 
			'0_3': ['4', '13', '8', '8', '24044', '24044', '0', '60'], 
			'0_0': ['4', '13', '6', '13', '24044', '24044', '0', '60'], 
			'0_1': ['4', '13', '6', '6', '24044', '24044', '0', '60']}		
		dictIdx = 0
		
		(res, dictIdx) = DrillView().genCellRowDict(\
			onrows, oncols, filters, rowelem, rownr, cols, qDict, dictIdx)
		
		assert res == ['<td id="0_0">%(0_0)s</td>', 
			'<td id="0_1">%(0_1)s</td>', '<td id="0_2">%(0_2)s</td>', 
			'<td id="0_3">%(0_3)s</td>', '<td id="0_4">%(0_4)s</td>', 
			'<td id="0_5">%(0_5)s</td>', '<td id="0_6">%(0_6)s</td>', 
			'<td id="0_7">%(0_7)s</td>', '<td id="0_8">%(0_8)s</td>']
		assert dictIdx == 9
		
	"""def test_genHierDrillLinks(self):
		pass
		
	def test_genDrillLinks(self):
		pass
		
	def test_genFilterLinks(self):
		pass
		
	def test_genCachedCells(self):
		pass"""
		
	def sample_renderRowColFiltersTable(self):
		#this is just an usage sample
		#when generating new random database this will fail
		onrows = 2 
		oncols = 1
		filters = [4, 13, 6, 13, 0, 24079, 0, 60]
		rows = ((0L, 'all time', 0L, 24079L, 0L), 
			(2001L, 'time_2000', 24008L, 24019L, 1L), 
			(2002L, 'time_2001', 24020L, 24031L, 1L), 
			(2003L, 'time_2002', 24032L, 24043L, 1L), 
			(2004L, 'time_2003', 24044L, 24055L, 1L), 
			(2005L, 'time_2004', 24056L, 24067L, 1L), 
			(2006L, 'time_2005', 24068L, 24079L, 1L)) 
		cols = ((1L, 'region_0', 6L, 13L, 1L),) 

		(res, qDict) = DrillView().renderRowColFiltersTable(onrows, oncols, filters, rows, cols)

		assert res == ['<table border="1">', 
			'<tr><td bgcolor="lightgrey">&nbsp;</td><td bgcolor="lightgrey">&nbsp;</td>', 
			'<td>&nbsp;</td>',
			'<tr><td bgcolor="lightgrey">&nbsp;</td><td bgcolor="lightgrey">&nbsp;</td>', 
			'<td><a href="javascript:drill(\'0\',\'1\',\'1\')"> region_0 </a></td>', 
			'</tr>', '<tr>', '<td>', 
			'<a href="javascript:drill(\'0\',\'2\',\'0\')"> all time </a>', 
			'</td>', '<td>', '&nbsp;', '</td>', '<td id="0_0">%(0_0)s</td>', 
			'</tr>', '<tr>', '<td>', '&nbsp;', '</td>', '<td>', 
			'<a href="javascript:drill(\'0\',\'2\',\'2001\')"> time_2000 </a>', 
			'</td>', '<td id="1_1">%(1_1)s</td>', '</tr>', '<tr>', '<td>', 
			'&nbsp;', '</td>', '<td>', 
			'<a href="javascript:drill(\'0\',\'2\',\'2002\')"> time_2001 </a>', 
			'</td>', '<td id="2_2">%(2_2)s</td>', '</tr>', '<tr>', '<td>', 
			'&nbsp;', '</td>', '<td>', 
			'<a href="javascript:drill(\'0\',\'2\',\'2003\')"> time_2002 </a>', 
			'</td>', '<td id="3_3">%(3_3)s</td>', '</tr>', '<tr>', '<td>', 
			'&nbsp;', '</td>', '<td>', 
			'<a href="javascript:drill(\'0\',\'2\',\'2004\')"> time_2003 </a>', 
			'</td>', '<td id="4_4">%(4_4)s</td>', '</tr>', '<tr>', '<td>', 
			'&nbsp;', '</td>', '<td>', 
			'<a href="javascript:drill(\'0\',\'2\',\'2005\')"> time_2004 </a>', 
			'</td>', '<td id="5_5">%(5_5)s</td>', '</tr>', '<tr>', '<td>', 
			'&nbsp;', '</td>', '<td>', 
			'<a href="javascript:drill(\'0\',\'2\',\'2006\')"> time_2005 </a>', 
			'</td>', '<td id="6_6">%(6_6)s</td>', '</tr>', '</table>'] 
			
		assert qDict == {'3_3': ['4', '13', '6', '13', '24032', '24043', '0', '60'],
			'5_5': ['4', '13', '6', '13', '24056', '24067', '0', '60'], 
			'2_2': ['4', '13', '6', '13', '24020', '24031', '0', '60'], 
			'6_6': ['4', '13', '6', '13', '24068', '24079', '0', '60'], 
			'0_0': ['4', '13', '6', '13', '0', '24079', '0', '60'], 
			'1_1': ['4', '13', '6', '13', '24008', '24019', '0', '60'], 
			'4_4': ['4', '13', '6', '13', '24044', '24055', '0', '60']}
			
class DrillFormTestCase(unittest.TestCase):
	def setUp(self):
		cherrypy.thread_data.threadpool = threadpool.ThreadPool(THREADPOOL_SECONDARY)
		cherrypy.thread_data.result = []

	def test_default(self):
		df = DrillForm()
		res = df.defaultNoSecurity('a')
		assert len(res) > 100
		
	def test_hiers(self):
		df = DrillForm()
		res = df.hiers()
		assert res.find('javascript:iframedrill') != -1
		assert res.find('dtree.css') != -1
		assert res.find('dtree.js') != -1
		#openTo unused
		#assert res.find('.openTo(') != -1
	
	def test_sanitizeInput(self):
		pass
		
	def test_fixSelectableRoot(self):
		pass
		
	def test_runWorkers(self):
		pass
		
	def test_renderTable(self):
		#includes testing sums match up
		#includes runWorkers
		def lookup(html, row, col):
			assert row < 10
			assert col < 10
			start = res.find('<td id="%d_%d">' % (row, col))
			end = res.find('</td>', start)
			return float(res[start+13:end])
			
		R = 3
		C = 6
		df = DrillForm()
		res = df.renderTable(0, 1, 
			[0, 24087, 0, 15, 0, 25, 0, 50, 0, 15, 1, 1, 0, 4],
			((0, 'all time', 0, 26, 0), 
				(2006, 'time_2005', 3, 14, 1), 
				(2007, 'time_2006', 15, 26, 1)),
			((0L, 'all region', 0L, 15L, 0L), 
				(1L, 'region_0', 6L, 7L, 1L), 
				(2L, 'region_1', 8L, 9L, 1L), 
				(3L, 'region_2', 10L, 11L, 1L),
				(4L, 'region_3', 12L, 13L, 1L),
				(5L, 'region_4', 14L, 15L, 1L)))
			
		#don't forget to sync with gen.py !!!
		#all_time = sum(time_2005) 
		#same for other cols
		for c in xrange(C):
			col = map(lambda x: lookup(res, x, c), xrange(R))
			scol = sum(col[1:])
			assert (col[0] - scol) / col[0] < 0.01
		
		#all region = sum(regions)
		#same for other rows
		for r in xrange(R):
			row = map(lambda x: lookup(res, 0, x), xrange(C))
			srow = sum(row[1:])
			
			assert (row[0] - srow) / row[0] < 0.01

		
	def test_performVerb(self):
		flt = [random.randint(0,100000) for x in xrange(NRDIMS * 2)]
		df = DrillForm()
		res = df.performVerb(0, 1, \
			df.hierStr2List(DEFHIER),\
			flt,\
			VERBDRILL, 0, 0,'',ANONYMOUS)
		assert repr(res[4]) == repr(flt)
		#
		#more
		#
				

################################	
if __name__ == "__main__":
	import metadata
	mm = metadata.meta
	NRDIMS = mm.NRDIMS
	DEFHIER = mm.DEFHIER
	DEFFILTER = mm.DEFFILTER
	
	unittest.main()
	