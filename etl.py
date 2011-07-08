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

#here you find example for importing star schemas

import gen


from random import randint
import constants

if constants.DBLIB != 'postgres':
	AUTOINC = 'int NOT NULL AUTO_INCREMENT'
else:
	AUTOINC = 'serial'

#where to create schema
#not necesarily different database than the one in constants.py 
DATABASE = 'star_xx'
#this will populate a random star schema
#with 1 and 2 level "dimension tables"
#edit CREATESCRIPT to suit your needs
#
#in case you already have a star schema, set to ''
#customize runMain()
CREATESCRIPT = 'star_create.sql'

sqlCommon = """
drop table if exists %(dest_table)s;
create table %(dest_table)s (id %(autoinc)s, 
 name varchar(20), parent_id int, start_range int, end_range int, gen int,
 old_id int, PRIMARY KEY (id) );
--create index idx_%(dest_table)s on %(dest_table)s (old_id);


insert into %(dest_table)s values(0,'all %(source_table)s',1,NULL,NULL,0,NULL);
insert into auth_01 values(1, %(table_nr)d, 'all %(source_table)s');

"""

sql1Dim = """
insert into %(dest_table)s (name,old_id, parent_id, gen) 
 select distinct %(source_col_1)s, %(source_pk)s, 1, 1 
 from %(source_table)s order by %(source_col_1)s;
update %(dest_table)s set start_range=id, end_range=id where gen=1;
"""

sql2Dim0 = """
insert into %(dest_table)s (name,parent_id, gen) select distinct %(source_col_1)s,
 1, 1 from %(source_table)s order by %(source_col_1)s;
 
insert into %(dest_table)s (name, old_id, gen) 
 select concat(%(source_col_1)s, '_', %(source_col_2)s),
 %(source_pk)s,2 from %(source_table)s order by %(source_col_1)s, %(source_col_2)s;
update %(dest_table)s set start_range=id, end_range=id where gen=2;

update %(dest_table)s child, %(dest_table)s parent set 
 child.parent_id = parent.id where child.gen=2 and parent.gen=1 and SUBSTRING(child.name,1,LENGTH(parent.name))=parent.name;
"""

sql2Dim1 = """
create temporary table t_min (id int, start_range int);
create temporary table t_max (id int, end_range int);
insert into t_min select a.id, min(b.start_range) from %(dest_table)s a, 
 %(dest_table)s b where a.gen=%(gen)d and a.id = b.parent_id group by a.id;
insert into t_max select a.id, max(b.end_range) from %(dest_table)s a, 
 %(dest_table)s b where a.gen=%(gen)d and a.id = b.parent_id group by a.id;
update %(dest_table)s, t_min set %(dest_table)s.start_range = t_min.start_range 
 where %(dest_table)s.id=t_min.id;
update %(dest_table)s, t_max set %(dest_table)s.end_range = t_max.end_range 
 where %(dest_table)s.id=t_max.id;
drop table t_min;
drop table t_max;
"""

sqlAlterFact = """
alter table %(fact)s add column dim_%(n)d int;
"""

sqlLookupFact = """
drop table if exists %(dest)s;
create %(tmp)s table %(dest)s as select * from %(orig)s limit 0;
%(part_stmt)s;
-- create index idx_%(src)s_%(opk)s on %(src)s (%(opk)s);
insert into %(dest)s (dim_%(n)d, %(other_fields)s ) 
 select dim%(n)d.id,  %(src)s.%(other_fields)s
  from %(src)s, dim%(n)d
  where %(src)s.%(opk)s=dim%(n)d.old_id;
"""

factTableFields = []

def transform1Dim(sourceTable, sourcePK, sourceCol1,
		selRoot, defNode, isTable):
	destTableNr = len(factTableFields)
	factTableFields.append(sourcePK)	
	destTable = 'dim' + str(destTableNr)
	l = [('source_table', sourceTable), 
		('dest_table', destTable),
		('source_pk', sourcePK),
		('table_nr',destTableNr),
		('source_col_1', sourceCol1),
		('autoinc', AUTOINC)]
	res = sqlCommon % dict(l) 
	res += sql1Dim % dict(l)
	gen0 = dict(l + [('gen',0)])
	res += sql2Dim1 % gen0
	res += gen.addMetadata(destTableNr, sourceTable, destTable, selRoot, 0, 
		defNode, isTable)
	return res

def transform2Dim(sourceTable, sourcePK, sourceCol1, sourceCol2,
		selRoot, defNode, isTable):
	destTableNr = len(factTableFields)
	factTableFields.append(sourcePK)
	destTable = 'dim' + str(destTableNr)
	l = [('source_table', sourceTable), 
		('dest_table', destTable),
		('source_pk', sourcePK),
		('table_nr',destTableNr),
		('source_col_1', sourceCol1),
		('source_col_2', sourceCol2),
		('autoinc', AUTOINC)]
	gen1 = dict(l + [('gen',1)])
	gen0 = dict(l + [('gen',0)])
	res = sqlCommon % dict(l) 
	res += sql2Dim0 % dict(l)
	res += 	sql2Dim1 % gen1 
	res += sql2Dim1 % gen0
	res += gen.addMetadata(destTableNr, sourceTable, destTable, selRoot, 0,
		defNode, isTable)
	return res
		
def transformFact(factTable, partStmt):
	nrDims = len(factTableFields)
	factTableFields.append('figure')
	factTableFields.extend(['dim_'+str(x) for x in xrange(nrDims)])
	
	res = ''
	for k in xrange(nrDims):
		#it is slow to add column to populated table; moved to star_create.sql
		#res += sqlAlterFact % dict([('fact',factTable),('n',k)])
		src = 'tmp_fact_'+str(k-1)
		dest = 'tmp_fact_'+str(k)
		tmp = 'temporary'
		partStmt2 = ''
		if k == 0:
			src = 'fact'
		elif k == nrDims-1:
			dest = 'fact_cub'
			tmp = ''
			partStmt2 = partStmt

		otherFields = [x for x in factTableFields if x != 'dim_'+str(k)]
		
		d = {'tmp' : tmp,
			'part_stmt' : partStmt2,
			'src' : src,
			'dest' : dest,
			'orig': 'fact',
			'n' : k,
			'other_fields' : ",".join(otherFields),
			'opk' : factTableFields[k] }
		res += sqlLookupFact % d
		
		if src != 'fact':
			print 'drop table if exists %s;' % src
			
	return res
	

def runMain():	
	print 'use ' + DATABASE
	
	#if constants.DBLIB == 'mysql':
	#	#this allows portable || instead of concat()
	#	print "set @@sql_mode='ansi';"
		
	#init the start schema
	if CREATESCRIPT != '':
		f = open(CREATESCRIPT, 'r')
		s=f.read()
		f.close()
		print s

	print gen.genMetadata()
	
	#continues at the very end
	print gen.genSecurityTables()
	print 'insert into users_01 values(1, "anonymous");' #hardcoded ID's !!
	print 'insert into users_01 values(45, "a");'
	print 'insert into users_01 values(99, "b");'
	
	#source table called "time" will become dim0
	#source table has PK t_id, level-1 = t_year, level-2 = t_month
	#1=hierarchy root is Selectable
	#1=default node is "all time"
	#
	#normally root would have ID=0, but for some reason 
	#autoincrement generates IDs starting with 1
	print transform2Dim('time', 't_id', 't_year','t_month',1,1,0)
	print transform2Dim('prod', 'p_id', 'p_cat','p_prod',1,1,0)
	print transform2Dim('customer', 'c_id', 'c_type','c_cust',1,1,0)
	print transform2Dim('packaging', 'pck_id', 'pck_type','pck_pack',1,1,0)
	#source table called "measure" will become dim4
	#PK = s_id, level-1 = s_scenario
	#0=hierarchy root not selectable
	#2=default node is not the root
	print transform1Dim('measure', 'm_id', 'm_measure',0,2,0)
	print transform1Dim('scenario', 's_id', 's_scenario',0,2,0)
	
	#remember which columns you set before as partitions
	#and what cardinality you need
	partStmt = gen.genPartitions('fact_cub', \
		'dim_0', (2007-2005)*(13-1)+(2007-2005)+1, 'dim_3, dim_4')
		
	print transformFact('fact', partStmt)
	
	
	#fact table is looked up by mandatory id 'fact'
	#fact table is called 'fact_cub'
	#0,0,0 = ignored for fact (not a dimension table)
	print gen.addMetadata(-1, 'fact', 'fact_cub', 0, 0, 0, 0)

	#simple authorizations
	print "insert into auth_01 select  users_01.id, dim, element " +\
		"from auth_01 a, users_01 where users_01.name in('a','b');"


	
if __name__ == "__main__":
	runMain()
