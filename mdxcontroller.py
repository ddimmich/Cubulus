from constants import *
from metadata import *
from model import *
from drillform import *
from mdx import *
import auth


meta = metadata.meta

class MDXController:
	def __init__(self):
		self.model = Model()
		self.df = DrillForm()
		
	def lookupDim(self, str):
		tmp = [i for i in xrange(meta.NRDIMS) \
			if str == meta.dimensionNames[i]]
		print str, meta.dimensionNames
		assert len(tmp) == 1
		return tmp[0]
		
	def lookupLevel(self, elems, allHiers):
		"""elemsWithBraces = str.split('.')
		elems = []
		for x in elemsWithBraces:
			assert x[0] == '[';
			assert x[-1] == ']'
			elems.append(x[1:-1])
			assert elems[-1] != ''"""
					
		dim = self.lookupDim(elems[0])
		
		elems = elems[1:]
		assert len(elems) > 0
		
		res = []
		for gen in xrange(len(elems)):
			#(id,name,parent_id,start,end,gen)
			node = [x for x in allHiers[dim] \
				if x[5] == gen and x[1] == elems[gen] ]
			assert len(node) == 1
			node = node[0]
			if gen > 1:
				#check parent
				assert node[2] == res[gen-1]
			res.append(node)
			
		return (dim, res[-1])
			
		
	def lookupLevelList(self, lst, user):
		allHiers = [self.model.getHier(i, user) for i in xrange(meta.NRDIMS)]
		tmp = [self.lookupLevel(x, allHiers) for x in lst]
		res = [x[1] for x in tmp if x[0] == tmp[0][0]]
		#assert same dim
		assert len(res) == len(tmp)
		
		return (tmp[0][0], res)
		
	@cherrypy.expose	
	def index(self, mdxQuery=''):
		return self.indexNoSecurity(mdxQuery, auth.getAuthUser())
		
	def indexNoSecurity(self, mdxQuery='', user=''):
		#try:
		table = ''
		if mdxQuery != '':
			tokens = mdxParser(mdxQuery)
			print tokens
			(onrows, rList) = self.lookupLevelList(tokens.onrows, user)
			#rList = [x[0] for x in rList]
			(oncols, cList) = self.lookupLevelList(tokens.oncols, user)
			#cList = [x[0] for x in cList]
			slicers = [self.lookupLevelList(x,user) for x in tokens.slicers]
			slicers = [(x[0], x[1][3],x[1][4]) for x in slicers]
			filters = meta.DEFFILTER.split(MAJORSEP)
			for f in slicers:
				filters[2*f[0]] = f[1]
				filters[2*f[0]+1] = f[2]
			print '*', onrows, oncols, filters, rList, cList
			table = self.df.renderTable(onrows, oncols, filters, rList, cList)
		#except:
		#	pass
		
		return """ <html>
		<form name="mdx" action="index" method="%(method)s">
			<input type="text" name="mdxQuery" value="%(mdx)s"></p>
			<p><input type="submit"></p>
		</form><br><br>
		%(table)s
		</html>""" % \
		{'mdx' : mdxQuery, 'method' : SUBMITMETHOD, 'table': table}
				
if __name__ == "__main__":
	mc = MDXController()
	print mc.lookupLevelList(['time.all time.time_2005.time_2005_2',
		'time.all time.time_2006.time_2006_4'],ANONYMOUS)
		