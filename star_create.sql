#helper table for self joins. Used for creating prod_0, prod_1, prod_2...
#
#
#COMPLEXITY IS NOT LINEAR!!
#
drop table if exists nr;
create table nr (id int(5));
insert into nr values(0);
insert into nr values(1);
insert into nr values(2);
insert into nr values(3); 
#insert into nr values(4); #cca 2 mil rows,
#insert into nr values(5); 
#insert into nr values(6); #cca 5.5 mil rows, 
#insert into nr values(7); #cca 8 mil rows, 30 mins

drop table if exists fact;
drop table if exists time;
drop table if exists prod;
drop table if exists customer;
drop table if exists packaging;
drop table if exists scenario;
drop table if exists measure;
drop table if exists t1;
drop table if exists t2;
drop table if exists t3;
drop table if exists t4;

#time corresponds to dim_0
#trying unordered PK's so JOIN has to do it's job
create table time(t_id int(10),t_year int(5), t_month int(5), 
 PRIMARY KEY (t_id));
insert into time values (10,2007,1);
insert into time values (20,2007,2);
insert into time values (30,2007,3);
insert into time values (40,2007,4);
insert into time values (50,2007,5);
insert into time values (60,2007,6);
insert into time values (1,2007,7);
insert into time values (2,2007,8);
insert into time values (3,2007,9);
insert into time values (4,2007,10);
insert into time values (5,2007,11);
insert into time values (6,2007,12);
insert into time values (101,2006,1);
insert into time values (102,2006,2);
insert into time values (103,2006,3);
insert into time values (104,2006,4);
insert into time values (105,2006,5);
insert into time values (106,2006,6);
insert into time values (107,2006,7);
insert into time values (108,2006,8);
insert into time values (109,2006,9);
insert into time values (110,2006,10);
insert into time values (111,2006,11);
insert into time values (112,2006,12);

#prod corresponds to dim_1
#
#keep format 'PARENT_CHILD' otherwise etl.py can't find the relationships !!
#
create table prod(p_id int(10) NOT NULL AUTO_INCREMENT, p_cat varchar(20), p_prod varchar(20), 
 PRIMARY KEY (p_id));
insert into prod (p_cat, p_prod) select 'food', concat('food','_',nr.id) from nr;
insert into prod (p_cat, p_prod) select 'electro', concat('electro','_',nr.id) from nr;
insert into prod (p_cat, p_prod) select 'car', concat('car','_',nr.id) from nr;
insert into prod (p_cat, p_prod) select 'fashion', concat('fashion','_',nr.id) from nr;
insert into prod (p_cat, p_prod) select 'sport', concat('sport','_',nr.id) from nr;
insert into prod (p_cat, p_prod) select 'books', concat('books','_',nr.id) from nr;
insert into prod (p_cat, p_prod) select 'cosmetic', concat('cosmetic','_',nr.id) from nr;

#prod corresponds to dim_2
create table customer(c_id int(10) NOT NULL AUTO_INCREMENT, c_type varchar(20), c_cust varchar(20), 
 PRIMARY KEY (c_id));
insert into customer (c_type, c_cust) select 'small', concat('small','_',nr.id) from nr;
insert into customer (c_type, c_cust) select 'medium', concat('medium','_',nr.id) from nr;
insert into customer (c_type, c_cust) select 'big', concat('big','_',nr.id) from nr;
insert into customer (c_type, c_cust) select 'huge', concat('huge','_',nr.id) from nr;
insert into customer (c_type, c_cust) select 'global', concat('global','_',nr.id) from nr;

#prod corresponds to dim_3
create table packaging(pck_id int(10) NOT NULL AUTO_INCREMENT, pck_type varchar(20), pck_pack varchar(20), 
 PRIMARY KEY (pck_id));
insert into packaging (pck_type, pck_pack) select 'box', concat('box','_',nr.id) from nr;
insert into packaging (pck_type, pck_pack) select 'can', concat('can','_',nr.id) from nr;
insert into packaging (pck_type, pck_pack) select 'bottle', concat('bottle','_',nr.id) from nr;
insert into packaging (pck_type, pck_pack) select 'pallet', concat('pallet','_',nr.id) from nr;
insert into packaging (pck_type, pck_pack) select 'deluxe', concat('deluxe','_',nr.id) from nr;
insert into packaging (pck_type, pck_pack) select 'cardboard', concat('cardboard','_',nr.id) from nr;

#prod corresponds to dim_4, flat, "root non-aggregatable" (currently calculated measures are not supported)
create table measure(m_id int(10), m_measure varchar(20), 
 PRIMARY KEY (m_id));
insert into measure values (15, 'sales');
insert into measure values (99, 'expenses');

#prod corresponds to dim_5, flat, "root non-aggregatable"
create table scenario(s_id int(10), s_scenario varchar(20), 
 PRIMARY KEY (s_id));
insert into scenario values (1, 'actual');
insert into scenario values (2, 'plan');

#gradually do cartesian product, otherwise it takes forever
create temporary table t1 (t_id int(10), p_id int(10));
insert into t1 select time.t_id, prod.p_id from time, prod;

create temporary table t2 (t_id int(10), p_id int(10), c_id int(10));
insert into t2 select t1.t_id, t1.p_id, customer.c_id from t1, customer;

create temporary table t3 (t_id int(10), p_id int(10), c_id int(10), pck_id int(10));
insert into t3 select t2.t_id, t2.p_id, t2.c_id, packaging.pck_id from t2, packaging;

create temporary table t4 (t_id int(10), p_id int(10), c_id int(10), pck_id int(10), m_id int(10));
insert into t4 select t3.t_id, t3.p_id, t3.c_id, t3.pck_id, measure.m_id from t3, measure;

create table fact (
 t_id int(10), p_id int(10), c_id int(10), pck_id int(10), m_id int(10), s_id int(10),
 figure decimal (10,4)); 
 #,PRIMARY KEY (t_id,p_id,c_id,pck_id,m_id, s_id));

#faster to add columns to empty table (before etl.py did this) 
alter table fact add column dim_0 int(10);
alter table fact add column dim_1 int(10);
alter table fact add column dim_2 int(10);
alter table fact add column dim_3 int(10);
alter table fact add column dim_4 int(10);
alter table fact add column dim_5 int(10);

#sparse cartesian product
insert into fact (t_id,p_id,c_id,pck_id,m_id, s_id, figure) select t4.t_id, t4.p_id, t4.c_id, t4.pck_id, t4.m_id, scenario.s_id, 
 rand()*1000 
 from t4, scenario
 where rand()*100 > 10;

drop table t1;
drop table t2;
drop table t3;
drop table t4;
