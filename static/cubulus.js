function iframedrill(ve, di, it) {
	window.parent.document.cubulus.verb.value = ve;
	window.parent.document.cubulus.dim.value = di;
	window.parent.document.cubulus.item.value = it;	
	window.parent.document.cubulus.submit();
};
function drill(ve, di, it) {
	document.cubulus.verb.value = ve;
	document.cubulus.dim.value = di;
	document.cubulus.item.value = it;	
	document.cubulus.submit();
};
function setR(x) {
	document.cubulus.verb.value = '0';
	document.cubulus.dim.value = '0'
	document.cubulus.item.value = '0';
	document.cubulus.onrows.value = x;
	document.cubulus.submit();
};
function setC(x) {
	document.cubulus.verb.value = '0';
	document.cubulus.dim.value = '0'
	document.cubulus.item.value = '0';
	document.cubulus.oncols.value = x;
	document.cubulus.submit();
};