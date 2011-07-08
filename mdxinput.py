import traceback, sys

from constants import *
from metadata import *
from model import *
#from drillform import *
from mdx import *
import auth


meta = metadata.meta

class MDXInput:
	def __init__(self):
		self.model = Model()
		#self.df = DrillForm()
		
		f = open('html_templates/mdx_.tmpl','r')
		self.tmpl = f.read()
		f.close()
		
	def lookupDim(self, str):
		tmp = [i for i in xrange(meta.NRDIMS) \
			if str == meta.dimensionNames[i]]
		assert len(tmp) == 1
		
		return tmp[0]
		
	def lookupLevel(self, elems, allHiers, parseNoChildren = False):
		dim = self.lookupDim(elems[0])
		
		elems = elems[1:]
		assert len(elems) > 0
		
		res = []
		if elems[-1].lower() == 'children' :
			chDelta = -1
		else:
			chDelta = 0
		for gen in xrange(len(elems) + chDelta):
			#(id,name,parent_id,start,end,gen)
			node = [x for x in allHiers[dim] \
				if x[5] == gen and x[1] == elems[gen] ]
			if len(node) != 1:
				raise Exception("unknown member " + repr(elems))
			node = node[0]
			if gen >= 1:
				#check parent
				assert abs(node[2]) == abs(res[gen-1][0])
			if parseNoChildren and (chDelta == 0):
				#no .children
				node = (-node[0],) +  (node[1:])

			res.append(node)
		return (dim, res[-1])
			
		
	def lookupLevelList(self, lst, user, parseNoChildren = False):
		allHiers = [self.model.getHier(i, user) for i in xrange(meta.NRDIMS)]
		tmp = [self.lookupLevel(x, allHiers, parseNoChildren) for x in lst]
		res = [x[1] for x in tmp if x[0] == tmp[0][0]]
		#assert same dim		
		assert len(res) == len(tmp)
		
		return (tmp[0][0], res)
		
	def parse(self, mdxQuery, user):
		"""def hier2AuthChildren(x):
			#getHier() has one more field than getAuthChildren()
			#fix here
			return (x[0],x[1],x[3],x[4],x[5])"""

		try:
			tokens = mdxParser(mdxQuery)
			
			try:
				(nestOnRows, nrId) = self.lookupLevelList(tokens.rownest, user)
				assert nrId != ''
				nrId = nrId[0][0]
			except IndexError:
				nestOnRows = -1
				nrId = 0
			
			try:
				(nestOnCols, ncId) = self.lookupLevelList(tokens.colnest, user)
				assert ncId != ''
				ncId = ncId[0][0]
			except IndexError:
				nestOnCols = -1
				ncId = 0
				
			(onrows, rList) = self.lookupLevelList(tokens.onrows, user, True)
			rList = [str(x[0]) for x in rList]			
			(oncols, cList) = self.lookupLevelList(tokens.oncols, user, True)
			cList = [str(x[0]) for x in cList]
			hiers = ['0'] * meta.NRDIMS
			hiers[onrows] = MINORSEP.join(rList)
			hiers[oncols] = MINORSEP.join(cList)
			hiers = MAJORSEP.join(hiers)
			slicers = [self.lookupLevelList([x],user) for x in tokens.slicers]
			slicers = [(x[0], x[1][0][3],x[1][0][4]) for x in slicers]
			filters = meta.DEFFILTER.split(MAJORSEP)
			for f in slicers:
				filters[2*f[0]] = f[1]
				filters[2*f[0]+1] = f[2]
			filters = MAJORSEP.join([str(x) for x in filters])
			
			return (onrows, oncols, hiers, filters, \
				nestOnRows, nestOnCols, nrId, ncId, '')
		except:
			err = ''
			try:
				#exctype, value = sys.exc_info()[:2]
				err = traceback.format_exc() + " when parsing: " + mdxQuery
			finally:
				pass
		
			return (0,1,meta.DEFHIER, meta.DEFFILTER, -1,-1,0,0,err)
		
		
				
if __name__ == "__main__":
	mc = MDXInput()
	"""print mc.lookupLevelList(['[prod].[all prod]','[prod].[all prod].[prod_0]',\
		'[prod].[all prod].[prod_1]','[prod].[all prod].[prod_2]',\
		'[prod].[all prod].[prod_3]','[prod].[all prod].[prod_4]'],ANONYMOUS)"""
		
		
	q = "Select {[time].[all time].[time_2005],[time].[all time].[time_2006]} on rows, {[prod].[all prod].children} on columns from cubulus where ([campaign].[all campaign].[campaign_1],[scenario].[all scenario].[scenario_2])"
	print mdxParser(q)
	print mc.parse(q,ANONYMOUS)