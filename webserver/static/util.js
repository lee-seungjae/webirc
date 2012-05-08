/*
   Utility Functions
   일단 utility 성격을 띠는 함수들을 모아둠.
   나중에 정리 필요함.
*/

function fill0(num, digit) 
{ 
	return (num/Math.pow(10, digit)).toFixed(digit).slice(digit); 
}

Date.prototype.toLocalHHMMString = function () 
{ 
	return fill0(this.getHours(), 2) + ":" + fill0(this.getMinutes(), 2);
}

function escapeHTML(s) {
	if( s.replace ) {
		return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
	}
	else
	{
		return s;
	}
}

