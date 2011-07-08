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

from model import *

################################
import metadata
meta = metadata.meta
NRDIMS = meta.NRDIMS
DEFHIER = meta.DEFHIER
DEFFILTER = meta.DEFFILTER

################################		
class DrillView:
	def renderDesigner(self, onrows, oncols):
		assert onrows != oncols
		
		model = Model()
		res = ['<table border="1">\n']
		for i in xrange(NRDIMS):
			res.append('<tr><td>')
			if i == onrows:
				res.append(meta.dimensionNames[i] + ' on rows')
			elif i != oncols:
				res.append('''<a href="javascript:set_r('%d')">%s on rows</a>'''
					% (i, meta.dimensionNames[i]))
			else:
				res.append(' ')
			res.append('</td>\n<td>')
			if i == oncols:
				res.append(meta.dimensionNames[i] + ' on cols')
			elif i != onrows:
				res.append('''<a href="javascript:set_c('%d')">%s on cols</a>'''
					% (i, meta.dimensionNames[i]))
			else:
				res.append(' ')
			res.append('</td>\n<td>')
			if i==i: # not in [onrows, oncols]:
				res.append( 
					("""<b onclick="javascript:i_frame_show('hier_',%(i)d,""" + 
					"""%(nrdims)d, '200px','200px', """ + 
					"""'%(modProxyRoot)s/data/hiers?dim=%(i)d')"> drill here </b>""") %
					{'i': i, 'nrdims' : NRDIMS, 'modProxyRoot' : MOD_PROXY_ROOT_2} )
				res.append(
					("""<iframe id="hier_%(i)d" src="/data/hiers?dim=%(i)d" """ + 
					"""width="200px" height="200px" frameborder="0" """ + 
					"""style="display:none ;position:absolute" """ + 
					"""onmouseout="i_frame_resize('%(i)d', '0px','0px', """ + 
					"""'%(modProxyRoot)s/data/hiers?dim=%(i)d')"> </iframe>""") % 
				 {'i': i, 'modProxyRoot' : MOD_PROXY_ROOT_2})
			else:
				res.append(' ')
			res.append('</td></tr>\n\n')
		res.append('</table>')
		return ' '.join(res)

	def genCellQueryStr(self, onrows, oncols, filters, rowelem, colelem ):
		assert onrows != oncols
		q = []
		for f in xrange(len(filters)/2):
			if f == onrows:
				q.append( str(rowelem[2]) )
				q.append( str(rowelem[3]) )
			elif f == oncols:
				q.append( str(colelem[2]) )
				q.append( str(colelem[3]) )
			else:
				q.append( str(filters[2*f] ))
				q.append( str(filters[2*f+1]))
		return q

				
	def genCellRowDict(self, onrows, oncols, filters, rowelem, \
			rownr, rows, cols, qDict):
		res = []
		dictIdx = 0
		for y in cols:
			q = self.genCellQueryStr(onrows, oncols, filters, rowelem, y)
			k =  '''%d%s%d''' % (rownr, MINORSEP, dictIdx)
			res.append('''<td id="k_%s">'''%k + '%' + \
				'(%s)s</td>' % k)	#do later % subst
			qDict[k] = q
			dictIdx += 1
			
		return res
		
	def genCellRowFormulaDict(self, onrows, oncols, filters, rowelem, \
			rownr, rows, cols, qDict):
		#same as genCellRowDict
		#but calculates row total instead of running SQL
		res = []
		dictIdx = 0
		
		for c in xrange(len(cols)):
			y = cols[c]
			q = ''
			if c == 0:
				#row total sum of cells of gen+1
				if (meta.selectableRoot[oncols] == 0 and cols[0][4] == 0) or \
					(rownr == 0 and meta.selectableRoot[onrows] == 0 and \
						rowelem[4] == 0):
					#except when 'all *' has non selectable root   ..OR..
					# OR same on first row
					#print '*'*5, 'EMTYCELL oncols', rownr, c
					q = EMPTYCELL
				else:
					q = '+'.join( \
						["float(q['%d%s%d'])" % (rownr, MINORSEP, i) \
							for i in xrange(1,len(cols)) \
							if cols[0][4] == cols[i][4] - 1 ])
					
			elif rownr == 0 :
				#first row = sum of other rows
				if meta.selectableRoot[onrows] == 0 and rowelem[4] == 0:
					#except when 'all *' has non selectable root 
					#print '*'*5, 'EMTYCELL onrows', rownr, c, rowelem
					q = EMPTYCELL
				else:
					q = '+'.join( \
						["float(q['%d%s%d'])" % (i, MINORSEP, c) 
							for i in xrange(1,len(rows)) \
							if rows[i][4] == 1])

			if q == '':
				#ex: flat dimensions
				q = self.genCellQueryStr(onrows, oncols, filters, rowelem, y)
									
			k =  '''%d%s%d''' % (rownr, MINORSEP, dictIdx)
			res.append('''<td id="k_%s">'''%k + '%' + \
				'(%s)s</td>' % k)	#do later % subst

			qDict[k] = q
			dictIdx += 1
			
		return res

	def genHierDrillLinks(self, verb, elem, dim, gen=0):
		if elem[4] == gen:
			return self.genDrillLinks(verb, elem, dim)
		else:
			return ' '

	def genDrillLinks(self, verb, elem, dim):
		return """<a href="javascript:drill('%s','%s','%s')"> %s </a>""" % \
			(verb, dim, elem[0], elem[1])

	def genFilterLinks(self, elem, dim, filters):
		return """<td %s><a href="javascript:drill('%s','%s','%s')"> %s </a></td>""" % \
			(FILTERHIGHLIGHT * (tuple(filters[2*dim:2*dim+2]) == elem[2:4]), \
			VERBSETFILTER, dim, elem[0], 'F')
			
	def genCachedCells(self, cachedDict):
		cachedCells = {}
		for (k,v) in cachedDict.items():
			cachedCells[k] = str(round(v))
		return cachedCells
	
	def renderRowColFiltersTable(self, onrows, oncols, filters, rows, cols, \
			rowWeaveExtra = 0, colWeaveExtra = 0):
						
		qDict = {}
		dictIdx = 0
		try:
			maxRowGen = max( [x[4] for x in rows] )
		except:
			maxRowGen = 1
		try:
			maxColGen = max( [x[4] for x in cols] )
		except:
			maxColGen = 1
			
		cw = '<td>' + C_WEAVE + '</td>'
		rw = '<td>' + R_WEAVE + '</td>'
		res = ['<table border="1" id="zebratable">']
		for cg in xrange(maxColGen+1 + colWeaveExtra):
			res.append('<tr>' + '<td class="nwcorner"> </td>' * \
				(maxRowGen + rowWeaveExtra + 1) )
			if cg >= maxColGen+1:
				res.extend([cw] * len(cols))
			else:
				res.extend( ['<td class="col_header">' + \
					self.genHierDrillLinks(VERBDRILL, x, oncols, cg) +'</td>' \
					for x in cols] )
			res.append('</tr>')
				
			
		iframeCount = 0
		rownr = 0
		for x in rows:
			res.append('<tr %s>' % 'class="odd"'[:11*(rownr % 2)] )
			for cr in xrange(maxRowGen+1):
				res.extend(['<td class="row_header">'] + \
					[self.genHierDrillLinks(VERBDRILL, x, onrows, cr)] +\
					['</td>'] )
					
			for iii in xrange(rowWeaveExtra):
				res.append(rw)
			cellrow = \
				self.genCellRowFormulaDict( \
					onrows, oncols, filters, x, rownr, rows, cols, qDict)
			res.extend(cellrow + ['</tr>'])
			rownr += 1

		res.append('</table>')
			
		return (res, qDict)
		