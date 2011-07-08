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
import re, random, time

import cherrypy
import threadpool

from constants import *
from model import *
from drillview import *
import auth

from mdxinput import *
from mdxoutput import *

import hierchart

###############################
import metadata
meta = metadata.meta
NRDIMS = meta.NRDIMS
DEFHIER = meta.DEFHIER
DEFFILTER = meta.DEFFILTER


################################
class DrillForm:
	mins=[]
	maxs=[]
	def __init__(self):
		self.model = Model()
		(self.mins, self.maxs) = self.model.getMinMax()
		self.mdxInput = MDXInput()
		self.mdxOutput = MDXOutput()
		
		f = open('html_templates/drillform.tmpl','r')
		self.defaultTmpl = f.read()
		f.close()

		f = open('html_templates/drillform_hier.tmpl','r')
		self.hierTmpl = f.read()
		f.close()
				
	#
	#if you have parameter 'user', it allows USERNAME SPOOFING ATTACK
	#instead, read the validated headers 
	#	
	def default(self, onrows='0', oncols='1',hiers=DEFHIER, \
			filters=DEFFILTER, verb=VERBDRILL, dim='0', item='0', mdx=''):
			
		return self.defaultNoSecurity(\
			\
			auth.getAuthUser(), \
			\
			onrows, oncols, hiers, \
			filters, verb, dim, item, mdx)
	default.exposed = True
	#
	# DON*T EXPOSE !!		
	def defaultNoSecurity(self, user=ANONYMOUS, onrows='0', oncols='1',\
			hiers=DEFHIER, filters=DEFFILTER, verb=VERBDRILL, \
			dim='0', item='0', mdx=''):
		#renders the form with the hiers & figures
			
		(r,c) = ([],[])
		(myonrows, myoncols, myhiers, myfilters, myverb, mydim, myitem, err) = \
			self.sanitizeInput(onrows, oncols, hiers, filters, \
				verb, dim, item)
			
		myfilters = self.filterStr2List(filters) #self.getDefFilters(filters)
		
		#cherrypy.request.login DOES NOT WORK !!! 
		myfilters = self.model.securityByUser(myfilters, user)
		
		if myfilters[0] == -1:
			return 'insufficient permissions for user "%s"' % user
		

		if err == '':
			(myonrows, myoncols, myhiers_l, myhiers_s, myfilters_1, myfilters_s, \
					myverb, mydim, myitem, err, r, c, \
					nestOnRows, nestOnCols, nrId, ncId) = \
				self.performVerb(myonrows, myoncols, myhiers, myfilters, myverb, \
					mydim, myitem, mdx, user)
		else:
			#print '*'*5, 'error=', err, ';'
			(myonrows, myoncols, myhiers_l, myhiers_s, myfilters_s, \
					myverb, mydim, myitem) = \
				(myonrows, myoncols, myhiers, self.hierList2Str(myhiers), \
					self.filterList2Str(myfilters), VERBDRILL, 0, 0)
			(nestOnRows, nestOnCols, nrId, ncId) = (-1, -1, 0, 0)
				
		cherrypy.response.headers['Content-Type'] = CONTENT_TYPE
		cherrypy.response.headers['cache-control'] = CACHEABLE

		"""mdxQry = self.mdxOutput.getMDX(myonrows, myoncols, \
			[x[0] for x in r], [x[0] for x in c], \
			myfilters_1, user)"""
			
		resultHiers = self.hierStr2List(myhiers_s)
		
		if (myverb == VERBMDX) or (nestOnRows != -1 or nestOnCols != -1):
			mdxQry = mdx
		else:
			mdxQry = self.mdxOutput.getMDXChildren(myonrows, myoncols, \
				resultHiers[myonrows], \
				resultHiers[myoncols],\
				myfilters_1, user)
				
		d = {'modProxyRoot' : MOD_PROXY_ROOT_2,
			'method' : SUBMITMETHOD, 'hidden' : FORMFIELDS,
			'js' : JAVASCRIPT, 'err' : err, 
			'mdx_out': mdxQry,
			'table' : self.renderTable(myonrows, myoncols, myfilters_1, r, c, \
				nestOnRows, nestOnCols, nrId, ncId), 
			'onrows' : myonrows, 'oncols' : myoncols,
			'hiers' : myhiers_s, 'filters' : myfilters_s,
			'verb' : myverb, 'dim' : mydim, 
			'item' : myitem,
			'r' : r, 'c': c}
		return self.defaultTmpl % d
		
	#
	#if you have parameter 'user', it allows USERNAME SPOOFING ATTACK
	#instead, read the validated headers 
	#	
	def hiers(self, dim=0):
		return self.hiersNoSecurity(dim,
			\
			auth.getAuthUser(),
		)
	hiers.exposed = True
			
		
	#
	#DON*T EXPOSE !!
	def hiersNoSecurity(self, dim=0, user=ANONYMOUS ):
		#renders the hierarchy "menus"
		cherrypy.response.headers['cache-control']=CACHEABLE
		res = [self.hierTmpl % (MOD_PROXY_ROOT_2, MOD_PROXY_ROOT_2)]
		nodes = self.model.getHier(int(dim), user)
		#if user has limited authorisation, hier root != "all XXX"
		rootID = int(nodes[0][0])
		for n in nodes:
			id = n[0]	#ID in database
			treeID = n[0] - rootID	#ID in Javascript
			treeP_ID = n[2] - rootID	#ID in Javascript
			g = n[5]
			if (g==0):
				#dtree expects parent of root node=-1
				treeP_ID=-1
			rootName = n[1]
			if (g==0) and meta.selectableRoot[int(dim)] != 1:
				defNode = meta.defNode[int(dim)]
				rootName += '''( slicer = %s )''' % \
					self.model.getNode(int(dim), int(defNode))[1]  
				
			res.append(\
				"""a.add(%s,%s,'%s',"javascript:iframedrill('%s','%s','%s')");""" % \
				(treeID, treeP_ID, rootName, VERBSETFILTER, dim, id) )
		res.append("document.write(a);")
		#not needed in Safari , Camino, FFox, 
		#res.append("a.openTo(%s,true,true);" % meta.defNode[int(dim)]-rootID)
		res.append("</script></body></html>")
		return '\n'.join(res)
			
	
	def hierStr2List(self, h):
		return [[int(x) for x in y.split(MINORSEP)] for y in h.split(MAJORSEP)]
		
	def hierList2Str(self, h):
		return MAJORSEP.join( [ MINORSEP.join([str(e) for e in x]) for x in h])
		
	def filterStr2List(self, f):
		return [int(x) for x in f.split(MAJORSEP)]
		
	def filterList2Str(self, f):
		return MAJORSEP.join([str(abs(x)) for x in f])
		
	def sanitizeInput(self, onrows_s, oncols_s, hiers_s, filters_s, verb_s, \
			dim_s, item_s):
		(myonrows, myoncols, myhiers, myfilters, myverb, mydim, myitem, err) = \
			(DEFROW, DEFCOL, \
			self.hierStr2List(DEFHIER), \
			self.filterStr2List(DEFFILTER), \
			VERBDRILL, 0, 0, '')
		while True: #try:
			while True:
				if onrows_s == oncols_s:
					err='onrows=oncols'
					break
				myonrows = int(onrows_s)
				if myonrows not in xrange(0, NRDIMS):
					err = 'not numerical onrows'
					break
				myoncols = int(oncols_s)
				if myoncols not in xrange(0, NRDIMS):
					err = 'not numerical oncols'
					break				
				
				myhiers = self.hierStr2List(hiers_s)
				if len(myhiers) != NRDIMS:
					err = 'wrong hiers'
					myhiers = self.hierStr2List(DEFHIER)
					break
					
				myfilters = self.filterStr2List(filters_s)
				if len(myfilters) != 2*NRDIMS:
					err = 'wrong filters'
					myfilters = self.filterStr2List(DEFFILTER)
					break
					
				myverb = verb_s
				if verb_s not in [VERBDRILL, VERBFILTER, VERBSETFILTER, VERBMDX]:
					err = 'bad verb'
					break
					
				mydim = int(dim_s)
				if mydim not in xrange(NRDIMS):
					err = 'bad dim'
					break
					
				myitem = int(item_s)
				if (self.mins[mydim] < 0) or (myitem > self.maxs[mydim]):
					err = repr(['bad item', item_s, \
						self.mins[mydim] , self.maxs[mydim]])
					
				break
			break
		while False: #except:
			err = sys.exc_info()[0]

		return (myonrows, myoncols, myhiers, myfilters, myverb,mydim,myitem,err)
		
	def fixSelectableRoot(self, onrows, oncols, filters):
		#Non -selectable Root hier menus must display all hier
		#	for having all nodes as rows/columns captions
		#when is slicer replace root with default
		res = [x for x in filters]
		for d in xrange(NRDIMS):
			if d not in [onrows, oncols] and meta.selectableRoot[d] == 0:
				s = filters[2*d]
				e = filters[2*d+1]
				if (s,e) == self.model.getRoot(d)[2:4] :
					x = self.model.getNode(d, meta.defNode[d])
					res[2*d] = x[2]
					res[2*d+1] = x[3]
		return map(int, res)

	def performVerb(self, onrows, oncols, hiers, filters, verb, dim, item, \
			mdx, user):
		(myonrows, myoncols, myhiers, myfilters, myverb, mydim, myitem, err) = \
			   (onrows, oncols, hiers, filters, verb, dim, item, '')
			   
		(nestOnRows, nestOnCols, nrId, ncId) = (-1, -1, 0, 0)

		rChildren = []
		cChildren = []
		model = self.model
		
		if verb == VERBDRILL:
			mh = myhiers[dim]
									
			if item in mh:	#'drill up'
				"""error: 0-1-2 possible to drill up 1 and leave 
					2(child of 1)"""							
				if item != 0:						
					mh.remove(item)
				children = model.getAuthChildren(dim, mh, filters)
			else:	#'drill down'
				mh.append(item)
				mh.sort()		
				children = model.getAuthChildren(dim, mh, filters)
				#bug: don't accumulate level-0 memebers in hier !!!
				
			if 0 not in mh:
				#root always, first
				mh.insert(0,0)
			
			if dim == onrows:
				rChildren = children
			else:
				rChildren = model.getAuthChildren(onrows, myhiers[onrows], filters)
			if dim == oncols:
				cChildren = children
			else:
				cChildren = model.getAuthChildren(oncols, myhiers[oncols], filters)
		elif verb == VERBSETFILTER:
			node = model.getNode(dim, item)
			myfilters[2*dim] = node[2]
			myfilters[2*dim+1] = node[3]
			rChildren = model.getAuthChildren(onrows, myhiers[onrows], filters)
			cChildren = model.getAuthChildren(oncols, myhiers[oncols], filters)
		elif verb == VERBMDX:
			(myonrows, myoncols, myhiers, myfilters, \
					nestOnRows, nestOnCols, nrId, ncId, err) = \
				self.mdxInput.parse(mdx, user)
			myhiers = self.hierStr2List(myhiers)
			myfilters = self.filterStr2List(myfilters)
			rChildren = model.getAuthChildren(myonrows, myhiers[myonrows], filters)
			cChildren = model.getAuthChildren(myoncols, myhiers[myoncols], filters)
		
		myfilters2 = self.fixSelectableRoot(myonrows, myoncols, myfilters)
			
		return (myonrows, myoncols,  myhiers, self.hierList2Str(myhiers), \
			myfilters2, self.filterList2Str(myfilters2), myverb, mydim, myitem, err, \
			rChildren, cChildren, nestOnRows, nestOnCols, nrId, ncId)
			
	def workerCallback(self, request, result):
		#cherrypy.thread_data.threadpool.resultsQueue.get() hangs
		#need to use callback
		cherrypy.thread_data.result.extend(result)
		
	def runWorkers(self, uncachedQueryL, oncols, filters):
	
		cherrypy.thread_data.result = []
		
		n = len(uncachedQueryL)
		if n==0:
			return []
		
		if THREADPOOL_SECONDARY <= 1:
			# don't create threads for one-CPU database
			return self.model.runPipelinedQueriesFromDict( \
				(uncachedQueryL, oncols, filters, 0))

		p = THREADPOOL_SECONDARY
		args = []
		#
		#
		#split equally to workers; good only for ROW-based pipelined execution
		#
		#
		#
		[args.append( \
			(uncachedQueryL[threadNr*n/p:(threadNr+1)*n/p],oncols, filters, threadNr)) \
			for threadNr in xrange(p)]
			
		requests = threadpool.makeRequests(\
			self.model.runPipelinedQueriesFromDict, args, self.workerCallback)
		[cherrypy.thread_data.threadpool.putRequest(req) for req in requests]
		cherrypy.thread_data.threadpool.wait()
		
		return cherrypy.thread_data.result
	
	#nest DESCENDANTS of nestRowsId , nestColsId
	def renderTable(self, onrows, oncols, filters, rows, cols, \
			nestOnRows=-1, nestOnCols=2, nestRowsId=0, nestColsId=0):
		#none of the inner functions are used elsewhere
		#so don't pollute drillview namespace
			
		def filterWeaver(dim, mins, maxs, filters):
			#returns list of filters for nesting 
			assert len(mins) == len(maxs)
			res = []
			for i in xrange(len(mins)):
				#"shallow copy" ??
				res.append(eval(repr(filters)))
				res[-1][2*dim] = mins[i]
				res[-1][2*dim+1] = maxs[i]
			return res
			
		def colWeaver(idx, weaverL, resultSets):
			#nesting on columns a list of dv.renderRowColFiltersTable() results
			weaverCells = ''.join(['<td>'+x+'</td>' for x in weaverL])[:-5]
			colHeaderEnd = "</td>" + '<td> </td>'*(len(weaverL)-1)
			colHeaderEnd = colHeaderEnd[:-5]
			cell = resultSets[0][idx]
			if 'td class="nwcorner"' in cell:
				#some header
				return cell
			if 'td class="col_header"' in cell:
				#col header cell
				return cell + colHeaderEnd
			elif C_WEAVE in cell:
				return weaverCells
			elif 'td id' in cell:
				#figures
				return cell + \
					''.join(["</td>" + resultSets[i][idx] \
						for i in xrange(1,len(weaverL))])
			else:
				#row headers, runtime
				return cell
				
		def rowWeaver(idx, weaverL, resultSets):
			#nesting on rows a list woven on columns and split by <R_WEAVE>
			def getLastRowPos(s):
				lastRowPos = -1
				while True:
					try:
						lastRowPos = s.index('</tr>', lastRowPos+1)
					except ValueError:
						break
				return lastRowPos
				
			def rowHeaderSubstitute(hdr):
				#don't repeat row headers
				try:
					xx = hdr.index('class="odd"')
					bgn = '<tr class="odd">'
				except ValueError:
					bgn = '<tr>'
					
				cnt = 0
				pos = -1
				while True:
					try:
						pos = hdr.index('<td',pos+1)
						cnt += 1
					except ValueError:
						break
					
				return bgn + '<td> </td>' * cnt
					
		
			#rowWeaver begins here
			res = []		
			#header part
			lastRowPos = getLastRowPos(resultSets[0][idx])
			if idx == 0:
				#include columns headers for first one
				res.append(resultSets[0][idx][:lastRowPos+5])
			rowHeader = resultSets[0][idx][lastRowPos+5:]
			for rw in xrange(len(weaverL)):
				if rw == 0:
					hdr = rowHeader
				else:
					hdr = rowHeaderSubstitute(rowHeader)
				res.append(hdr + '<td>' + weaverL[rw] + '</td>')
				lrp = getLastRowPos(resultSets[rw][idx+1])				
				res.append(resultSets[rw][idx+1][:lrp+5])

			return ' '.join(res)
			
		#renderTable begins here	
		assert nestOnCols != oncols
		assert nestOnCols != onrows
		if nestOnCols != -1 and nestOnRows != -1:
			assert nestOnCols != nestOnRows
		assert nestOnRows != onrows
		assert nestOnRows != oncols
		
		startT = time.time()	#time measurement
		
		if nestOnCols != -1:
			cn = self.model.getNode(nestOnCols, nestColsId)
			colsNestHier = self.model.getAuthChildren(nestOnCols, [int(cn[0])], filters)
			colsNestChildren = [x for x in colsNestHier if x[4] == cn[4]+1]
			cNames = [x[1] for x in colsNestChildren]
			cMins = [x[2] for x in colsNestChildren]
			cMaxs = [x[3] for x in colsNestChildren]
			extraC = 1
		else:
			cNames = ['']
			extraC = 0
			
		if nestOnRows != -1:
			rn = self.model.getNode(nestOnRows, nestRowsId)
			rowsNestHier = \
				self.model.getAuthChildren(nestOnRows, [int(rn[0])], filters)
			rowsNestChildren = [x for x in rowsNestHier if x[4] == rn[4]+1]
			rNames = [x[1] for x in rowsNestChildren]
			rMins = [x[2] for x in rowsNestChildren]
			rMaxs = [x[3] for x in rowsNestChildren]
			rowWeavedFilters = filterWeaver(nestOnRows, rMins, rMaxs, filters)
			extraR = 1
		else:
			rowWeavedFilters = [filters]
			rNames = ['']
			extraR = 0

		rowRes=[]		
		for rwf in rowWeavedFilters:
			if nestOnCols != -1:
				weavedFilters = filterWeaver(nestOnCols, cMins, cMaxs, rwf)
			else:
				weavedFilters = [rwf]
	
			resultSets = [self.renderTableTransposer(
					onrows, oncols, f, rows, cols, \
					extraR, extraC).split("</td>") \
				for f in weavedFilters]
		
			x = [colWeaver(i, cNames, resultSets) \
				for i in xrange(len(resultSets[0]))]
			rowRes.append("</td>".join(x))
			
		if extraR > 0:
			rowResSets = [x.split('<td>' + R_WEAVE + '</td>') for x in rowRes]
			return "".join([rowWeaver(i, rNames, rowResSets) \
				for i in xrange(len(rowResSets[0])-1)] + \
				['</table> <p> <br />runtime: %4.2f secods<br /></p>'  
					% (time.time() - startT)])
		else:
			return rowRes[0] + \
				'<p><br />runtime: %4.2f secods<br /></p>'  % (time.time() - startT)
		
		
	def renderTableTransposer(self, onrows, oncols, filters, rows, cols, \
			extraR, extraC):
		print '*'*5, 'transpose also for TABLES'
		if meta.isPartition[onrows] != 0 and meta.isPartition[oncols] == 0:
			#evaluate transposed table, faster
			#this fills the cache
			self.renderTableRunner(oncols, onrows, filters, cols, rows,\
				extraR, extraC)
		
		return self.renderTableRunner(onrows, oncols, filters, rows, cols, \
			extraR, extraC)
						
		
	def renderTableRunner(self, onrows, oncols, filters, rows, cols, \
			extraR, extraC):	
		#also SVG chart here
		
		dv = DrillView()
		(htmlList, qDict) = \
			dv.renderRowColFiltersTable(onrows, oncols, filters, rows, cols, \
				extraR, extraC)
			
		(cachedCellsL, uncachedQueryL, toCalculateL) = \
			self.model.lookupCache(qDict)
		uncachedCellsL = self.runWorkers(uncachedQueryL, oncols, filters)
		
		readyL = cachedCellsL + uncachedCellsL
		
		calculatedL = self.model.calculateFormulas(toCalculateL, readyL)
		#print '*'*5, rows
		#print '*'*5, cols 
		#print '*'*5, calculatedL + readyL
		qDict = dict( calculatedL + readyL )
		
		#and chart
		h=400
		w=800
		(rl, d) = hierchart.computeChartData(rows, cols, qDict)
		
		return ' '.join(htmlList) % qDict
