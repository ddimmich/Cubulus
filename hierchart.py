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

from constants import *

def getMaxLevel(rowOrCol):
	#max level in row / col headers
	try:
		return max([x[4] for x in rowOrCol])
	except ValueError:
		return 0

def rowIndexGen(i, crtRowOrCol):
	return '''%d%s%d''' % (i, MINORSEP, crtRowOrCol)

def colIndexGen(i, crtRowOrCol):
	return '''%d%s%d''' % (crtRowOrCol, MINORSEP, i)
	
def getRelPos(rowOrCol, maxLevel, crtRowOrCol, qDict, rcFunc):
	#relative position of header row / data columns by summing their values
	res = []
	rStack = [0.0]*(maxLevel+1)
	prevLevel = maxLevel
	for i in xrange(len(rowOrCol)):
		crtLevel = rowOrCol[i][4]
		if crtLevel <= prevLevel:
			#shift all subsequent nodes when beginning new subtree
			newStart = rStack[prevLevel]
			rStack[crtLevel+1:] = [newStart for x in rStack[crtLevel+1:]]

		#dividing 'n/a' by whatever == 0
		numerator = 0.0
		try:
			numerator = float(qDict[rcFunc(i, crtRowOrCol)])
		except (ValueError, TypeError, KeyError):
			pass
			
		try:
			crtPos = numerator / \
				float(qDict[rcFunc(0, crtRowOrCol)])
		except (ZeroDivisionError, ValueError, TypeError, KeyError):
			crtPos = 0.0
		
		elem = (rowOrCol[i][0], rowOrCol[i][1], crtLevel, 
			rStack[crtLevel], rStack[crtLevel] + crtPos )
		res.append(elem)
		rStack[crtLevel] += crtPos		 
		prevLevel = crtLevel
	
	assert len(res) == len(rowOrCol)
	#[(id, name, level, start, end), ...]
	return res


def computeChartData(onrows, oncols, qDict):
	#start here
	maxlR = getMaxLevel(onrows)
	maxlC = getMaxLevel(oncols)
	rowLegend = getRelPos(onrows, maxlR, 0, qDict, rowIndexGen)
	data = []
	for i in xrange(len(onrows)):
		if i == (len(onrows)-1) or onrows[i][3] < onrows[i+1][3]:			
			#only for lower level == unmasked rowHeaders
			#2007 masks "all"; 2007_01 masks 2007
			data.append(getRelPos(oncols, maxlC, i, qDict, colIndexGen))
		else:
			#print '*'*5+ str(i) + rowLegend[i][1] + 'masked'
			pass
	assert len(rowLegend) == len(onrows)
	return (rowLegend, data)


def level2Coordinates(rowOrCol, barSize, spaceSize):
	#translate level to coords with space in between bars
	return [(id, name, level*(barSize+spaceSize), barSize, start, end) 
		for (id, name, level, start, end) in rowOrCol]
def relPos2Coordinates(rowOrCol, size):
	#translate relative coords to
	return [(id, name, level, int(start*size), int((end-start)*size))
		for (id, name, level, start, end) in rowOrCol]
	
def drawBars(rowOrCol, deltaX, deltaY):
	return [("""<svg:rect x="%d" y="%d" width="%d" height="%d" """ +
		"""style="fill:red;stroke:black;stroke-width:1;opacity:0.9"/> """) 
		% (x0 + deltaX, y0 + deltaY, x1, y1)
		for (id, name, x0, x1, y0, y1) in rowOrCol]

def swapXY(rowOrCol):
	return [(id, name, y0, y1, x0, x1)
		for (id, name, x0, x1, y0, y1) in rowOrCol]


def renderSVG(w, h, onrows, oncols, rowLegend, data, maxlR, maxlC):
	res = []

	barSize = spaceSize = w*0.25 / (maxlR * 2 + 1)
	res.extend(
		drawBars(level2Coordinates(
			relPos2Coordinates(rowLegend, h), 
				barSize, spaceSize),
			spaceSize, 0))
		
	idx = 0
	for i in xrange(len(onrows)):
		if i == (len(onrows)-1) or onrows[i][3] < onrows[i+1][3]:
			#only for lower level == unmasked rowHeaders
			r = rowLegend[i]
			barSize = spaceSize = h * (r[4]-r[3]) / (maxlC * 2 + 1)			
			res.extend(
				drawBars ( swapXY ( level2Coordinates(
						relPos2Coordinates(data[idx], w*0.75*(r[4]-r[3])), 
						barSize, spaceSize)),
					w*0.25, h*r[3]+spaceSize))
			idx += 1
	return res
	
if __name__ == '__main__':
	onrows=((0L, 'all time', 0L, 26L, 0L), (1L, 'time_2005', 3L, 14L, 1L), 
		(2L, 'time_2006', 15L, 26L, 1L), (15L, 'time_2006_1', 15L, 15L, 2L), 
		(16L, 'time_2006_2', 16L, 16L, 2L), (17L, 'time_2006_3', 17L, 17L, 2L), 
		(18L, 'time_2006_4', 18L, 18L, 2L), (19L, 'time_2006_5', 19L, 19L, 2L), 
		(20L, 'time_2006_6', 20L, 20L, 2L), (21L, 'time_2006_7', 21L, 21L, 2L), 
		(22L, 'time_2006_8', 22L, 22L, 2L), (23L, 'time_2006_9', 23L, 23L, 2L), 
		(24L, 'time_2006_10', 24L, 24L, 2L), (25L, 'time_2006_11', 25L, 25L, 2L), 
		(26L, 'time_2006_12', 26L, 26L, 2L))
	oncols=((0L, 'all region', 0L, 15L, 0L), (1L, 'region_0', 6L, 7L, 1L), 
		(2L, 'region_1', 8L, 9L, 1L), (8L, 'region_1_0', 8L, 8L, 2L), 
		(9L, 'region_1_1', 9L, 9L, 2L), (3L, 'region_2', 10L, 11L, 1L), 
		(4L, 'region_3', 12L, 13L, 1L), (5L, 'region_4', 14L, 15L, 1L)) 
	qDict={'1_7': '411959.16', '1_6': '402571.91', '1_5': '406292.37', 
		'1_4': '207438.53', '1_3': '198327.81', '1_2': '405766.33', 
		'1_1': '399949.81', '1_0': 2026539.5799999998, '0_6': 802003.79000000004, 
		'0_7': 815658.78000000003, '0_4': 408749.88, '0_5': 805474.75, 
		'0_2': 811376.97999999998, '0_3': 402627.10999999999, 
		'0_0': 4037773.4199999999, '0_1': 803259.12, '5_3': '17941.03', 
		'5_2': '35373.63', '5_1': '35625.16', '5_0': 170321.52000000002, 
		'5_7': '33124.23', '5_6': '34201.86', '5_5': '31996.64', 
		'5_4': '17432.60', '4_2': '34867.55', '4_3': '17039.61', '4_0': 168542.44, 
		'4_1': '33558.38', '4_6': '34135.75', '4_7': '33265.88', '4_4': '17827.94', 
		'4_5': '32714.88', '6_6': '32449.86', '6_1': '35125.23', '8_6': '31653.40', 
		'8_7': '35468.65', '8_4': '16588.76', '8_5': '32611.22', '8_2': '33788.05', 
		'8_3': '17199.29', '8_0': 166359.69, '8_1': '32838.37', '9_7': '34128.65', 
		'9_6': '34082.31', '9_5': '35209.80', '9_4': '15983.66', '9_3': '15001.10', 
		'9_2': '30984.75', '9_1': '34031.58', '9_0': 168437.09, '6_4': '16102.96', 
		'6_5': '35059.65', '13_1': '33211.11', '13_0': 165432.75, 
		'13_3': '17279.84', '13_2': '33426.85', '13_5': '32572.20', 
		'13_4': '16147.01', '13_7': '33102.67', '13_6': '33119.92', 
		'6_7': '35595.10', '11_7': '33373.20', '11_6': '34629.73', 
		'11_5': '33123.38', '11_4': '17540.71', '11_3': '17171.27', 
		'11_2': '34711.98', '11_1': '31071.33', '11_0': 166909.62, 
		'3_1': '33630.43', '3_0': 170566.90000000002, '3_3': '17527.38', 
		'3_2': '33130.62', '3_5': '36296.87', '3_4': '15603.25', '3_7': '34647.14', 
		'3_6': '32861.84', '2_0': 2011233.8399999999, '2_1': '403309.31', 
		'2_2': '405610.65', '2_3': '204299.30', '2_4': '201311.35', 
		'2_5': '399182.38', '2_6': '399431.88', '2_7': '403699.62', 
		'14_2': '32518.61', '14_3': '16189.73', '14_0': 163613.87, 
		'14_1': '30736.38', '14_6': '35447.76', '14_7': '31494.21', 
		'14_4': '16328.88', '14_5': '33416.91', '12_4': '16732.35', 
		'12_0': 165997.28, '12_1': '35106.00', '12_2': '34632.96', 
		'12_3': '17900.61', '6_0': 171867.53, '12_5': '30781.42', '6_2': '33637.69', 
		'6_3': '17534.73', '10_6': '33524.36', '10_7': '33510.48', 
		'10_4': '19002.55', '10_5': '32095.55', '10_2': '36655.27', 
		'10_3': '17652.73', '10_0': 169892.18000000002, '10_1': '34106.52', 
		'7_5': '33303.88', '7_4': '16020.69', '7_7': '32905.18', '7_6': '30932.42', 
		'7_1': '34268.82', '7_0': 163292.98999999999, '7_3': '15862.00', 
		'7_2': '31882.69', '12_7': '33084.23', '12_6': '32392.67'}

	(rl, d) = computeChartData(onrows, oncols, qDict)

	print """<?xml version="1.0" encoding="UTF-8"?>
	<!DOCTYPE html 
		  PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
		  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
	<html xmlns="http://www.w3.org/1999/xhtml" 
		  xmlns:svg="http://www.w3.org/2000/svg"
		  xmlns:xlink="http://www.w3.org/1999/xlink">
	<svg:svg version="1.1" baseProfile="full" width="300px" height="200px">"""
	print "\n".join(renderSVG(800, 500, onrows, oncols, rl, d, 3, 3))
	print '</svg:svg></html>'

		
		
	