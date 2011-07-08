
import sqlalchemy as sa
import sqlahelper

Base = sqlahelper.get_base()
Session = sqlahelper.get_session()

def create_temp_table(nr):
    pass    

class Nr(Base):
    __tablename__ = "nr"
    id = sa.Column(sa.Integer(5), primary_key=True)
    
class Fact(Base):
    __tablename__ = "fact"
    fact_id = sa.Column(sa.Integer(10), primary_key=True)
    t_id = sa.Column(sa.Integer(10))
    p_id = sa.Column(sa.Integer(10))
    c_id = sa.Column(sa.Integer(10))
    pck_id = sa.Column(sa.Integer(10))
    m_id = sa.Column(sa.Integer(10))
    s_id = sa.Column(sa.Integer(10))
    figure = sa.Column(sa.Decimal(10,4))
    
    dim_0 = sa.Column(sa.Integer(10))
    dim_1 = sa.Column(sa.Integer(10))
    dim_2 = sa.Column(sa.Integer(10))
    dim_3 = sa.Column(sa.Integer(10))
    dim_4 = sa.Column(sa.Integer(10))
    dim_5 = sa.Column(sa.Integer(10))


class Time(Base):
    __tablename__ = "time"
    t_id = sa.Column(sa.Integer(10), primary_key=True)
    t_year = sa.Column(sa.Integer(5))
    t_month = sa.Column(sa.Integer(5))
    
class Prod(Base):
    __tablename__ = "prod"
    p_id = sa.Column(sa.Integer(10), primary_key=True)
    p_cat = sa.Column(sa.Unicode(20))
    p_prod = sa.Column(sa.Unicode(20))
    
class Customer(Base):
    __tablename__ = "customer"
    c_id = sa.Column(sa.Integer(10), primary_key=True)
    c_type = sa.Column(sa.Unicode(20))
    c_cust = sa.Column(sa.Unicode(20)) 

class Packaging(Base):
    __tablename__ = "packaging"
    pck_id = sa.Column(sa.Integer(10), primary_key=True)
    pck_type = sa.Column(sa.Unicode(20))
    pck_cust = sa.Column(sa.Unicode(20)) 
class Scenario(Base):
    __tablename__ = "scenario"
    s_id = sa.Column(sa.Integer(10), primary_key=True)
    s_scenario = sa.Column(sa.Unicode(20))
    
class Measure(Base):
    __tablename__ = "measure"
    m_id = sa.Column(sa.Integer(10), primary_key=True)
    m_measure = sa.Column(sa.Unicode(20))