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

from random import randint
import constants

if constants.DBLIB == 'mysql':
	RAND = 'rand()*100'
elif constants.DBLIB == 'postgres':
	RAND = 'random()*100'
elif constants.DBLIB == 'sqlite':
	RAND = 'abs(random())/20000000'
elif constants.DBLIB == 'monet5':
	RAND = 'abs(rand())/20000000'
else:
	RAND = '1'

if constants.DBLIB == 'monet5':
	ST = 'START TRANSACTION;'
else:
	ST = 'BEGIN;'
	
ET = 'COMMIT;'

if constants.DBLIB == 'monet5':
	WD = 'WITH DATA'
else:
	WD = ''

if constants.DBLIB == 'monet5':
	print ST
	print 'create function rand() returns int external name mmath.rand;'
	print ET
#
#
# Tests work only wit "medium" size  !!!!!
#
#
dbSize = "medium"	#"small" / "medium" / "large"

#these are not taken from constants !!!
FACTTABLE = "fact"
NRDIMS = 7

#this table contains metadata for Model
def genMetadata():
	res = [ST]
	res.append('create table metadata (dim int, name varchar(20), ' + \
		'tbl_name varchar(20), ' + \
		'selectable_root int, '+ \
		'is_partition int, def_node int, is_table int);')
	res.append(ET)
	return '\n'.join(res)
		
def addMetadata(d, n, tn, sr, ip, dn, it):
	return "insert into metadata values(%d,'%s','%s',%d,%d,%d,%d);" % \
		(d, n, tn, sr, ip, dn, it)

def genInsert(n,k,p,g, table, prefix):
	return 	' '.join( ('INSERT INTO', table, ' VALUES('+repr(k) + \
		",'"+n+"',"+repr(p)+","+repr(k)+","+repr(k)+","+repr(g)+");") )

#these 2 funcs generate a dimension table with 2 levels
#dim: dimension nr
#ver: table version (unused)
#prefix : used for root, ex: "all time"
#x1, x2: range for level1, ex: prod_0 .. prod_5
#y1, y2: same fo level2, ex: prod_0_0 .. prod_0_5 
#sr: selectable root = not all dimensions have root = sum(members). 
# Ex: you probably don't want to have "all scenario" as sum of ACTUAL + BUDGET  
#ip: is partition by
#dn: default node. Ex: ACTUAL instead of "all scenario"
def gen2LevelTable(dim, ver, prefix, x1, x2, y1, y2, sr, ip, dn, it):
	print ST
	t = 'dim%d_%s' % (dim, ver)
	print addMetadata(dim, prefix, t, sr, ip, dn, it)
	print '''create table %s (id int, name varchar(20), parent_id int, start_range int, end_range int, gen int, PRIMARY KEY (id) ); ''' % t
	print genInsert('all '+prefix, 0, 0, 0, t, prefix)

	for x in range(x1, x2):
		print genInsert(prefix + '_' + repr(x), x-x1+1, 0, 1, t, prefix)
		for y in range(y1, y2):
			print genInsert(prefix + '_' + repr(x) + '_' + repr(y), 1+x2-x1+(x-x1)*(y2-y1)+y-y1, x-x1+1, 2, t, prefix)
	
	for x in range(2):
		print '''create table fake%s as select * from %s %s;''' % (t,t,WD)
		print '''update %s set start_range=(select min(start_range) from fake%s where fake%s.parent_id = %s.id) where exists (select * from fake%s where fake%s.parent_id = %s.id);''' % (t,t,t,t,t,t,t)
		print '''update %s set end_range=(select max(end_range) from fake%s where fake%s.parent_id = %s.id) where exists (select * from fake%s where fake%s.parent_id = %s.id);''' % (t,t,t,t,t,t,t)	
		print '''drop table fake%s;''' % t
	print ET

#PARTITION BY RANGE (d_0) 
#---not anymore ! --- SUBPARTITION BY KEY(kSubPart...) 		
def genPartitions(tbl, kPart, nrPart, nrSubPart):
	if constants.DBLIB != 'mysql':
		return ''
	
	a = ['alter table %s PARTITION BY RANGE (%s) (' % (tbl, kPart)]
	#a.append('SUBPARTITION BY KEY (%s) SUBPARTITIONS %d (' % \
	#	(kSubPart, nrSubPart) )
	a.extend( ['PARTITION p%d VALUES LESS THAN(%d),' % (i,i) \
		for i in xrange(1,nrPart+2)] )
	a[-1] = a[-1][:-1]	#cut ending ','
	a.append(');')
	return ' '.join(a)

#gen random data by joining all dimensions, 
#ex sparsity = 80%
#partKey = PARTITION BY (...)
#partNr = 300 or 0 if don't need partitions
def genFigures(fact_table, sparsity, lastTableDims, kPart, nrPart, nrSubPart):
	print ST

	#cr will be: 
	#create table fact_01 (dim_0 int(10), dim_1 int(10), .. ,figure decimal(10,4));'
	cr =  ['create table %s (' % fact_table]
	cr1 = []
	#ins will be:
	#insert into fact_01 select dim0_01.id, dim1_01.id .., 
	# rand()*1000 
	# from dim0_01, dim1_01 .. 
	# where dim0_01.start_range=dim0_01.end_range and dim1_01.start_range=dim1_01.end_range ..
	# and rand()*100 > 80;'
	ins1 = ['insert into %s select' % fact_table]
	ins2 = ['from']
	ins3 = ['where']
	for t in xrange(NRDIMS - lastTableDims):
		cr.append('''dim_%d int, ''' % t)
		cr1.append('dim_%d,' % t)
		ins1.append('dim%d_01.id,' % t)
		ins2.append('dim%d_01,' % t)
		ins3.append('dim%d_01.start_range=dim%d_01.end_range and' % (t,t))
	#cr.append('figure decimal(10,4), PRIMARY KEY(')
	cr.append('figure decimal(10,4));')
	ins1.append(RAND)
	ins2[-1] = ins2[-1][:-1]	#cut ending ','
	cr1[-1] = cr1[-1][:-1]	#cut ending ','
	ins3.append('%s > %d;' % (RAND, sparsity) )
	#print ' '.join(cr + cr1 + ['));'])
	print ' '.join(cr)
	
	if nrSubPart > 0:
		print genPartitions(fact_table, kPart, nrPart, nrSubPart)
	
	print ' '.join(ins1 + ins2 + ins3)
	print ET
	

def genSecurityTables():
	res = []
	
	res.append('create table users_01 (id int, name varchar(20), ' + \
		'PRIMARY KEY(id));')
	res.append('create table auth_01 (id int, dim int, element varchar(20), '+\
		'PRIMARY KEY(id, dim), FOREIGN KEY(id) REFERENCES users_01(id));')
	return "\n".join(res)
		
def genSecurity():
	print ST
	print genSecurityTables()
	print "insert into users_01 values(25945, 'anonymous');" #random IDs
	print "insert into users_01 values(45656, 'a');"

	print "insert into auth_01 values(25945, 0, 'all time');"
	print "insert into auth_01 values(25945, 1, 'all region');"
	print "insert into auth_01 values(25945, 2, 'all prod');"
	print "insert into auth_01 values(25945, 3, 'all customer');"
	print "insert into auth_01 values(25945, 4, 'all campaign');"
	print "insert into auth_01 values(25945, 5, 'all scenario');"
	print "insert into auth_01 values(25945, 6, 'all measure');"
	
	print "insert into auth_01 values(45656, 0, 'all time');"
	print "insert into auth_01 values(45656, 1, 'region_0');"
	print "insert into auth_01 values(45656, 2, 'prod_0');"
	print "insert into auth_01 values(45656, 3, 'all customer');"
	print "insert into auth_01 values(45656, 4, 'all campaign');"
	print "insert into auth_01 values(45656, 5, 'all scenario');"
	print "insert into auth_01 values(45656, 6, 'all measure');"
	print ET
	
def genIndexes(tbl_name):
	if constants.DBLIB in ['postgres', 'sqlite']:
		print 'create index idx_%s on %s (dim_0);' % (tbl_name, tbl_name)
		
	if constants.DBLIB == 'postgres':
		print 'cluster idx_%s on %s;'  % (tbl_name, tbl_name)

def runMain():
	if constants.DBLIB == 'mysql':
		print 'use %s;' % constants.DATABASE

	isTimePartition = constants.DBLIB == 'mysql'
		
	print genMetadata()

	#recommended nr of range partitions: (x2-x1)*(y2-y1)+x2-x1
	dim0_part = (2007-2005)*(13-1)+(2007-2005)
	gen2LevelTable(0, '01', 'time', 2005, 2007, 1, 13, 1, isTimePartition, 0, 0)

	if dbSize == "small":
		#
		#NOTE test.py WILL FAIL !!! because there is minimal data
		#
		#no partitioning
		#
		gen2LevelTable(1, '01', 'region', 0, 3, 0, 2, 1, 0, 0, 0)
		gen2LevelTable(2, '01', 'prod', 0, 3, 0, 3, 1, 0, 0, 0)
		gen2LevelTable(3, '01', 'customer', 0, 3, 0, 3, 1, 0, 0, 0)
		gen2LevelTable(4, '01', 'campaign', 0, 3, 0, 3, 1, 0, 0, 0)
		#last dimensions are "split table"
		gen2LevelTable(5, '01', 'scenario', 0, 4, 0, 0, 0, 0, 1, 1)
		gen2LevelTable(6, '01', 'measure', 0, 4, 0, 0, 0, 0, 1, 1)		
	elif dbSize == "medium":
		gen2LevelTable(1, '01', 'region', 0, 5, 0, 2, 1, 0, 0, 0)
		gen2LevelTable(2, '01', 'prod', 0, 5, 0, 4, 1, 0, 0, 0)
		gen2LevelTable(3, '01', 'customer', 0, 10, 0, 4, 1, 0, 0, 0)
		gen2LevelTable(4, '01', 'campaign', 0, 3, 0, 4, 1, 0, 0, 0)
		#last dimensions are "split table"
		gen2LevelTable(5, '01', 'scenario', 0, 4, 0, 0, 0, 0, 1, 1)
		gen2LevelTable(6, '01', 'measure', 0, 4, 0, 0, 0, 0, 1, 1)		
	else:
		gen2LevelTable(1, '01', 'region', 0, 5, 0, 5, 1, 0, 0, 0)
		gen2LevelTable(2, '01', 'prod', 0, 10, 0, 8, 1, 0, 0, 0)
		gen2LevelTable(3, '01', 'customer', 0, 10, 0, 8, 1, 0, 0, 0)
		gen2LevelTable(4, '01', 'campaign', 0, 3, 0, 4, 1, 0, 0, 0)
		#last dimensions are "split table"
		gen2LevelTable(5, '01', 'scenario', 0, 4, 0, 0, 0, 0, 1, 1)
		gen2LevelTable(6, '01', 'measure', 0, 4, 0, 0, 0, 0, 1, 1)

	#remember which partitions you set before (ip=is_part)
	#last dimensions are "split table"
	for d4 in xrange(1,5):
		for d5 in xrange(1,5):
			tbl_name = '''fact_%d_%d''' % (d4, d5)
			genFigures(tbl_name, 80, 2, 'dim_0', dim0_part, 16)
			genIndexes(tbl_name)
		
	#metadata for fact table
	print ST
	print addMetadata(-1, 'fact', FACTTABLE, 0, 0, 0, 0)
	print ET

	genSecurity()
	
	
if __name__ == '__main__':
	runMain()
