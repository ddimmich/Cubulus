Server requirements
===================
POSIX environments + Windows XP. Python, mySQL are everywhere, Python libraries are platform neutral, and memcached builds on lots of platforms.

Client requirements
===================
Tested browsers:
-Safari 2.0, Camino 1.1, Mac OS X 10.4
-Firefox 2.0, OS X, Windows XP
-Opera 9.10 Mac OS:  There is a problem with Javascript. Click on the hierarchy menus to make them go away.
-Internet Explorer 6, Win XP 

Upgrading from previous versions of Cubulus
===========================================
ALWAYS initialize the database, because it may have different structure!!


Installation guide v0.57
========================

1) Install mysql from www.mysql.org
2) Optional, STRONGLY RECOMMENDED: Install memcached from http://www.danga.com/memcached/ 1.2.1
3) Install Python 2.3 / 2.4 / 2.5 from www.python.org. 
4) Distribution now includes all libraries except sqlite2 (or 3) and MySQLdb (platform dependent). Tested versions:
-CherryPy 3.0.0 (web framework, http://www.cherrypy.org/)
-MySQLdb 1.2.1_p2 (http://mysql-python.sourceforge.net/)
-DBUtils 0.9.2 (persistent and pooled db connections, http://www.python.org/pypi/DBUtils/)
-python-memcached 1.34 (memcached client API, http://www.tummy.com/Community/software/python-memcached/)
-pyparsing-1.4.5 (parsing in Python, from http://pyparsing.wikispaces.com/)
 Threadpool 1.1 (worker threads, http://chrisarndt.de/en/software/python/threadpool)
-bpgsql (Python-only Postgres interface http://barryp.org/software/bpgsql/)
-pysqlite (SQLite interface for Python < 2.5, http://www.initd.org/tracker/pysqlite)
-dTree 2.05 (Javascript tree, http://www.destroydrop.com/javascripts/tree/) is also included in distribution. 
5) By default database is sqlite. For python versions prior to 2.5 install pysqlite3. 

For using mysql database (strongly recommended):
1) Edit constants.py DBLIB="mysql"
2) Edit ~/.my.cnf (c:\my.cnf) file with content:
[client]
user="XXXXXXX"
password="XXXXXXXXX"
3) Edit constants.py and put the path to .my.cnf , and the desired DBLIB from list ['mysql', 'sqlite', 'postgres']
4) Create a new database called "cubulus" (and have a user who can access it)
5) Initialize the database with ONE of the following command lines (Read to the end for loading your star schema)
	python gen.py | mysql -v
	python gen.py | sqlite3 -echo cubulus.db
	python gen.py | psql  cubulus -e
	python gen.py > 1.sql ; mclient -lsql -umonetdb 1.sql
 
 There is dbSize paramater; leave it as "medium" initially, so you can run the tests 
 Database initialization may take a long time; try tuning the SPARSITY in genFigures(60...)
 Bigger SPARSITY = less rows
 There is a cartesian product, to speed it up lower nr children when calling gen2LevelTable(..x1,x2,y1,y2..)

 If you plan to "scale out" with more database servers, be careful to generate database ONCE and then replicate it ! Otherwise you will get garbage results because of random-initialized database in each server.


SQLite
======
Default database for Cubulus is SQLite. Main reason is because Python 2.5 has builtin support for SQLite. Also that databases files are portable. 

One shortcoming of SQLite is to return 0 instead of NULL when doing SUMs. 

Generate database:

python gen.py | sqlite3 -echo cubulus.db

PostgreSQL
==========

Since partitioning syntax is different in PostgreSQL , it is easier (for the moment) to create a clusterred index.

Generate database:

python gen.py | psql  cubulus -e

Quick fixes:
update metadata set tbl_name='f' where dim=-1;
alter table fact_1_1 rename to f_1_1;
alter table fact_1_2 rename to f_1_2;
..
alter table fact_3_3 rename to f_3_3;


Clusterred index also allows tuning. Well, the target with Cubulus was to eliminate tuning, but it would be a shame not to use the good features in Postgres.
The python DB API-2.0 interface is bpgsql (http://barryp.org/software/bpgsql/), because it is Python-only, and hence portable. It is quite stable, holding well against Apache Bench stress test (without memcached )

MonetDB
=======

Monet is a columnar database, which means in practice that it's more than 10 times faster than equivalent MySQL database (partitioned explicitly by 3 dimensions).

Compilation of MonetDB on Mac OS with builtin Python2.3 : 

env EXTRA_ECONF="--with-python=python2.3" EXTRA_ECONF="--with-python-library=/usr/lib" EXTRA_ECONF="--with-python-incdir=/usr/include/python2.3/" ./monetdb-install.sh --prefix=~/MonetDB --enable-sql --nightly=current 

Generate database:
python gen.py > monet.sql
mclient -lsql -umonetdb monet.sql

Exporting data from MySQL
=========================
MySQL was the first backend for Cubulus, and is quite popular, so it is used as benchmark. Here is how to export data out of it. Depending on the destination SQL dialect, db1.sql file migth still need some manual editing.

mysqldump --databases cubulus --compact --compatible=ansi --skip-extended-insert --add-drop-table --skip-quote-names --skip-create-options > db0.sql 

cat db0.sql | sed 's/IF EXISTS//g' |  sed 's/"//g' | sed 's/int(..)/int /g' > db1.sql

Running
=======
1) Start mysql
2) Start memcached (optional, strongly recommended)
3) Start python site.py
4) -broken on v0.52 ! Run tests with: python test.py . Remember: works only with "medium" mySQL generated database, and needs memcached 
5) Browse http://localhost:8080

Tuning MySQL database
=====================
-indexing probably won't help much: there can be only one clustered index, filtering by columns that are at the end of PK (or any other secondary=non clustered indexes) means unusable indexes 
-PARTITION BY helps a lot, and you can create hundreds of partitions (before hitting OS and mysql open files limits; both tunable). 
-when doing such big SUMs the tolerable time-limit comes from CPU, with database size smaller that memory size.

Sample lines in my.cnf file:
#otherwise PARTITION BY runs out of file descriptors
open_files_limit = 8192
table_cache = 2048
# Try number of CPU's*2 for thread_concurrency
thread_concurrency = 2
#this needs more measurement; sometimes degrades performance
myisam_use_mmap=1
# Recommended for Mac OS
skip-thread-priority


Scaling up horizontally: database failover+load balancing
=========================================================
Cubulus can connect to multiple database servers and calculate reports in parallel. If one database server goes down, there is failover with "graceful degradation" (performance penalty). As long as there is one database server up, Cubulus will continue to work

Testing the fail-over
Stop memcached
Start Python and the databases
Run Apache Bench for ex: 
	ab -n 200 -c 4 http://localhost:8080/data/default
Check CPU usage on database servers, they should get similar load
Stop database_server_1. See load migrates to database_server_2.
Restart database_server_1. See load balances
Stop database_server_2. See load migrates to database_server_1. Start database_server_2. See load balances

Web filtering
=============
It's not a bad idea to put apache (mod_security), squid, or some other reverse proxy in front of CherryPy. This will protect CherryPy from buffer overflows, malformed URLs, fragments etc...


Authentication
==============
Authentication should normally be the deployed using LDAP / Kerberos / MS Active Directory. It is also easier and better to configure it in the web server rather than code it in CherryPy. 

If you don't deploy apache/lighttpd/squid/IIS, than all users are "anonymous"

Even for digest passwords, it is possible to _try_ replay attacks, so use SSL !!

Quick-and-dirty solution with lighttpd. Relevant lines from lighttpd.conf are :server.modules = (	"mod_access",	"mod_auth",	"mod_proxy",	"mod_accesslog" )server.port = 8090proxy.server = ( "" => ( ( 
	"host" => "127.0.0.1", 
	"port" => 8080 ) ) )auth.backend = "plain"auth.backend.plain.userfile = "/opt/local/etc/lighttpd/lighttpd.user"auth.require = ( "/" => (	"method" => "digest",	"realm" => "cubulus",	"require" => "valid-user") )

Don't forget to edit lighttpd.user file.

Apache mod_proxy
================
It is possible to put apache with mod_proxy in front. Edit MOD_PROXY_ROOT in constants.py. 
Example: for URL http://localhost:8080/xxx   MOD_PROXY_ROOT='/xxx'


Authorization
=============
Currently there is one table with usernames (users_01). It MUST contain user "anonymous", in case there is no external authentication provider

Auth_01 table contains the nodes as text (rather than ID). Reason is that adding a node in "Order Preserving Encoding of Hierarchies" will likely change some ID's. Therefore it seems more user-friendly to set something like "Europe" or "Sales". For the moment authorization in database is sufficient, but in future makes sense to move it ex to LDAP directory.

Scaling up
==========
If you happen to have a multiple core / multiple CPU server, edit constants.py THREADPOOL_SECONDARY. Set it to the number of available CPU cores. Otherwise leave it =1, in order to avoid context switching.

Stress testing
==============
It's good to do sanity check on the infrastructure. Python has the "global interpreter lock", and lots of partitions will make mySQL run out of file descriptors. In order to really stress the machine:
-stop memcached (yes, it works without..)
-in /etc/my.cnf set query_cache_size= 0M
-run Apache Bench for ex: 
	ab -n 200 -c 4 http://localhost:8080/data/default

Generating random star schema
=============================
Edit etl.py and set DATABASE = 'star' (different than default 'cubulus')
	python etl.py | mysql -v

If you are happy with results, edit constants.py DATABASE to match generated database.

etl.py will generate a random star schema, and will transform it to "hierarchical range-clustering" style. Dimension tables can have one or two levels. 

First, etl.py will print unmodified contents of 'star_create.sql'. You can tune it, but be prepared for EXPONENTIAL RUNTIME INCREASE. Be warned to slowly add rows into the table called "nr".

Then, etl.py will generate the "hierarchical range-clustering" dimensions and fact table.  There is partitioning for Cubulus fact table, but not for the star schema. Recommended partitioning is by Month (range) and subpartitions by all "flat dimensions" ex: measure and scenario.

Star schema is not tuned: no index / no partitions. Please feel free to suggest, or send your database to me.


Importing your star schema
==========================
If you have your own star schema with max 2 levels, try editing the etl.py script. There are comments. 

Don't forget to set CREATESCRIPT=''; otherwise you execute 'star_create.sql', which will drop all tables first, then create random ones.

