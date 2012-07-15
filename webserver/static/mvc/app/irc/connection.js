connection = {}

// 서버에 XHR을 보낸다
// option.request : 요청으로 보낼 객체(JSON.stringify 할 객체)
// option.callback.success : 요청이 성공했을 때 불릴 Callback.
//                   function(response, textStatus, jqXHR)
// option.callback.error : 요청이 실패했을 때 불릴 Callback.
//                 function(jqXHR, textStatus, errorThrown)
// option.timemout : 타임아웃 시간(milliseconds)
// TODO: 여기에 이게 있어야 하는지 잘 모르겠다 -_- 나중에 다시 생각하자.
connection.request = function(option) {
    // TODO: error 처리 좀더 정밀(?) 하게
    // check input
    if( option.request == undefined )
    {
        console.log("unspecified request");
        return;
    }

    if( option.callback == undefined )
    {
        console.log("unspecified callback");
        option.callback = {}
    }
    // 나머지 인자는 undefined 로 넘겨도 잘 동작한다.

    return Ext.Ajax.request({
        url: '/xhr',
        method: 'GET',
        params: { 'req': Ext.JSON.encode(option.request) },
        success:function(result, request) {
            var r = Ext.JSON.decode(result.responseText, true);
            if( r !== null )
			{
				if( r.err == 'LOGIN_REQUIRED' )
				{
                    // TODO: 로그인 후 원래대로 돌아오기
					document.location = '/static/login.html';
				}
				else
				{
					return option.callback.success(r, request);
				}
			}
            else
			{
                return option.callback.error(result, request);
			}
        },
        failure: option.callback.error,
        timeout: option.timeout
    });
}

// rpc polling loop를 시작한다.
// ui 단에서 첫 요청 성공, 매 요청 성공시, 요청 실패시 호출할 callback을 등록한다.
connection.init = function(initCallback, updateCallback, errorCallback) {
	this.request({ request: { 'req': 'LOG_INIT'},
            callback: {
                success: function(response, request) {
                    initCallback(response, request);
                    this.polling(response, request, updateCallback);
                },
			    failed: function(response, opts) {
                    errorCallback(response, opts);
                    // TODO: 네트워크 에러면 몇 번 더 시도해보자.
                    // 더 해서 안되면 사용자 확인 후 페이지 리프레쉬!
                    // 근데 사용자 확인은 ui한테 맡겨야지...
                }
            },
            timeout: 60000});
}


// update polling function
connection.polling = function(response, request, updateCallback) {
}
