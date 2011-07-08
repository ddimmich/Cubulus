from constants import *
from metadata import *
from model import *

meta = metadata.meta

INEXISTENT = '_inexistent_'

class MDXOutput:
	def __init__(self):
		self.model = Model()
		
	def formatLevel(self, dim, id, hierList):
		#return '[time].[all time].[time_2005].[time_2005_2]'
		res = []
		
		crtId = id
		while True:
			# (name, parent_id, gen)
			crtLst = [(x[1],x[2],x[5]) for x in hierList if x[0] == crtId]
			if len(crtLst) != 1:
				return INEXISTENT
			
			crtNode = crtLst[0]
			res.append( "[%s]" % crtNode[0] )
			crtId = crtNode[1]
			if crtNode[2] == 0:
				break
		res.append( "[%s]" % meta.dimensionNames[dim] )
		res.reverse()
		return ".".join(res)
		
	def formatLevelList(self, dim, idList, user):
		res = [] #"[%s]." % meta.tableNames[dim]
		
		hierList = self.model.getHier(dim, user)
		#print hierList
		return [self.formatLevel(dim, abs(n), hierList) for n in idList]			 
		
	def getNodeFromFilters(self, dim, filters, user):
		start = filters[2*dim]
		end = filters[2*dim+1]
		
		hierList = self.model.getHier(dim, user)
		l = [x[0] for x in hierList if x[3] == start and x[4] == end]
		if len(l) != 1:
			return INEXISTENT
		nodeId = l[0]
		if meta.defNode[dim] != nodeId:
			return self.formatLevel(dim, nodeId, hierList)
		else:
			return ''
		
	
	def getMDX(self, onrows, oncols, rList, cList, filters, user):
		#contains all members
		rowAxis = self.formatLevelList(onrows, rList, user)
		colAxis = self.formatLevelList(oncols, cList, user)
		allSlicers = [self.getNodeFromFilters(x, filters, user) \
			for x in xrange(meta.NRDIMS) \
			if x not in [onrows, oncols]]
		slicers = [x for x in allSlicers if x != '']
		sl = ''
		if len(slicers) > 0:
			sl = "where (%s)" % ",".join(slicers)
		
		return "Select {%s} on rows, {%s} on columns from %s %s" % \
			(",".join(rowAxis), ",".join(colAxis), DATABASE, sl)
			
	def getMDXChildren(self, onrows, oncols, rList, cList, filters, user):
		#opened node list , similar with hiers
		rowAxis = self.formatLevelList(onrows, rList, user)
		colAxis = self.formatLevelList(oncols, cList, user)
		allSlicers = [self.getNodeFromFilters(x, filters, user) \
			for x in xrange(meta.NRDIMS) \
			if x not in [onrows, oncols]]
		slicers = [x for x in allSlicers if x != '']
		sl = ''
		if len(slicers) > 0:
			sl = "where (%s)" % ",".join(slicers)
		
		return "Select {%s} on rows, {%s} on columns from %s %s" % \
			(",".join([x+".children" for x in rowAxis]), \
			",".join([x+".children" for x in colAxis]), \
			DATABASE, sl)
		


#mo = MDXOutput()
#print mo.formatLevelList(0,[0,2,4], ANONYMOUS)

