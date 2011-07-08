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

#import MySQLdb
try:
	from decimal import Decimal #mySQLdb sometimes uses Decimal()
except:
	pass
#from DBUtils.PersistentDB import PersistentDB
#import memcache

from constants import *
from sqlutil import *

class Metadata:
	def __init__(self):
		def col(l, c):
			#column from SQL result with multiple rows
			return map(lambda x: x[c], l)
				
		sql = "select tbl_name from metadata where dim=-1;"
		self.FACTTABLE = runSQL_uncached(sql)[0]
		
		#fix for postgres
		if isinstance(self.FACTTABLE, list):
			self.FACTTABLE = self.FACTTABLE[0]
		
		sql = "select * from metadata where dim>=0 order by dim;"
		res = runSQL_uncached(sql)

		self.NRDIMS = len(res)
		self.dimensionNames = col(res, 1)
		self.tableNames = col(res, 2)
		self.selectableRoot = col(res, 3)
		self.isPartition = col(res, 4)
		self.defNode = col(res, 5)
		self.isTable = col(res, 6)
		self.DEFFILTER = []
				
		#get nodes from dimension tables
		for d in xrange(self.NRDIMS):
			sql = 'select start_range, end_range, id from %s ' % self.tableNames[d] + \
				' where id = %d;' % self.defNode[d]
			res = runSQL_uncached(sql)
			self.DEFFILTER.extend(res[0][0:2])

			
		self.DEFFILTER = MAJORSEP.join(map(str, self.DEFFILTER))
		
		#Cubulus had id of root=0
		#AUTOINCREMENT seems to start from 1, so etl generates root id =1
		sql = 'select id from %s where gen=0' % self.tableNames[0]
		rootIdNumbering = str(runSQL_uncached(sql)[0][0])
		self.DEFHIER = MAJORSEP.join([rootIdNumbering]*self.NRDIMS)

		
################################
#module initialization
meta = Metadata()
