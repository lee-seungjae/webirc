/**
 * ClevisURL class
 *
 * URL 주소를 문자열에서 검색 및 URL 을 분석
 *
 * - 사용시 new 키워드로 객체를 생성하지 않고, ClevisURL.collect() 메소드와
 *   ClevisURL.parse() 메소드를 바로 호출하면 됩니다.
 * - parse() 메소드는 필요가 없을 경우 삭제하여 사용해도 무방합니다.
 * - LGPL 라이센스에 동의하에 얼마든지 수정하여 사용하실 수 있습니다.
 * - 단, 다른 사람이 개작된 소스의 재배포를 원할 경우 그 내용까지 포함하여 원시코드를
 *   공개해야 합니다.
 * - 또한, 재배포시 저작권 정보를 삭제해서는 안됩니다. 이 외에 수정 사항이 있을 경우
 *   저작권 정보를 덪붙일 수 있습니다.
 *
 * @author      KAi  (http://kais.tistory.com/)
 * @version     v0.2 (10-03-13)
 * @license     LPGL (http://korea.gnu.org/people/chsong/copyleft/lgpl.ko.html)
 */
/**
 * @usage
 *
 *   array   ClevisURL.collect( string );
 *     입력된 문자열에서 URL들을 찾아서 배열로 리턴
 *
 *   object  ClevisURL.parse( string );
 *     입력된 문자열(URL)을 분석하여 각 부분별 항목으로 리턴해줌
 *
 *
 * @history
 *
 *   v 0.2
 *     [10-03-13] 기존에 공개했던 정규식의 문제점을 개선하고 정확도를 높임
 *        [added] 클래스로 작성하고 URL 검출과 URL 분석할 수 있는 함수 추가
 *        [added] 로컬주소(file:///)도 검출하도록 추가
 *        [fixed] URL 도메인과 DOM 객체가 구분 안되는 문제 수정 (ccTLD 추가)
 *        [fixed] HTTP인증정보가 제대로 캡쳐 안되는 문제 수정
 *        [fixed] 쿼리스트링에 &*; 형식의 HTML 엔티티 문자도 포함되도록 수정
 *
 *   v 0.1
 *     [09-04-10] 간단히 URL 주소를 검색할 수 있는 코드 공개
 */
var ClevisURL = {
    // URL Pattern
    _patterns : {
        url : '(?:\\b(?:(?:(?:(ftp|https?|mailto|telnet):\\/\\/)?(?:((?:[\\w$\\-'
            + '_\\.\\+\\!\\*\\\'\\(\\),;\\?&=]|%[0-9a-f][0-9a-f])+(?:\\:(?:[\\w$'
            + '\\-_\\.\\+\\!\\*\\\'\\(\\),;\\?&=]|%[0-9a-f][0-9a-f])+)?)\\@)?((?'
            + ':[\\d]{1,3}\\.){3}[\\d]{1,3}|(?:[a-z0-9]+\\.|[a-z0-9][a-z0-9\\-]+'
            + '[a-z0-9]\\.)+(?:biz|com|info|name|net|org|pro|aero|asia|cat|coop|'
            + 'edu|gov|int|jobs|mil|mobi|museum|tel|travel|ero|gov|post|geo|cym|'
            + 'arpa|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|'
            + 'bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bw|by|bz|ca|cc|cd|cf|cg|ch'
            + '|ci|ck|cl|cm|cn|co|cr|cu|cv|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|e'
            + 'r|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|'
            + 'gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it'
            + '|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|l'
            + 't|lu|lv|ly|ma|mc|me|md|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|'
            + 'mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph'
            + '|pk|pl|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|s'
            + 'i|sk|sl|sm|sn|sr|st|sv|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tr|'
            + 'tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|za|zm'
            + '|zw)|localhost)\\b(?:\\:([\\d]+))?)|(?:(file):\\/\\/\\/?)?([a-z]:'
            + '))(?:\\/((?:(?:[\\w$\\-\\.\\+\\!\\*\\(\\),;:@=ㄱ-ㅎㅏ-ㅣ가-힣]|%['
            + '0-9a-f][0-9a-f]|&(?:nbsp|lt|gt|amp|cent|pound|yen|euro|sect|copy|'
            + 'reg);)*\\/)*)([^\\s\\/\\?:\\"\\\'<>\\|#]*)(?:[\\?:;]((?:\\b[\\w]+'
            + '(?:=(?:[\\w\\$\\-\\.\\+\\!\\*\\(\\),;:=ㄱ-ㅎㅏ-ㅣ가-힣]|%[0-9a-f]'
            + '[0-9a-f]|&(?:nbsp|lt|gt|amp|cent|pound|yen|euro|sect|copy|reg);)*'
            + ')?\\&?)*))*(#[\\w\\-ㄱ-ㅎㅏ-ㅣ가-힣]+)?)?)',
        querystring: new RegExp('(\\b[\\w]+(?:=(?:[\\w\\$\\-\\.\\+\\!\\*\\(\\),;'
            + ':=ㄱ-ㅎㅏ-ㅣ가-힣]|%[0-9a-f][0-9a-f]|&(?:nbsp|lt|gt|amp|cent|poun'
            + 'd|yen|euro|sect|copy|reg);)*)?)\\&?', 'gi')
    },

    /**
     * _process : 정규식 컴파일 후 검색
     * @param   (string)        string          문자열
     * @param   (string)        modifiers       정규식 수식어
     * @return  (mixed)                         정규식 결과 = [ array | null ]
     */
    _process : function (string, modifiers)
    {
        if ( ! string) throw new Error(1, '입력값이 비어 있습니다.');

        var p = new RegExp(ClevisURL._patterns.url, modifiers);
        return string.match(p);
    },

    /**
     * collect : 문장에서 여러 URL 주소 검색
     * @param   (string)        text            URL 을 찾을 문장
     * @return  (array)                         배열로 리턴
     */
    collect : function (text)
    {
        var r = ClevisURL._process(text, 'gmi');
        return (r) ? r : [];
    },

    /**
     * parse : 하나의 URL 주소를 분석
     * @param   (string)        url             URL 주소
     * @return  (object)                        객체로 리턴
     */
    parse : function (url, type)
    {
        var r = ClevisURL._process(url, 'mi');

        if ( ! r) return {};

        // HTTP 인증정보
        if (r[2]) r[2] = r[2].split(':');

        // 쿼리스트링 분석
        if (r[9]) {
            r[9] = r[9].match(ClevisURL._patterns.querystring);
            for (var n = 0; n < r[9].length; n++) {
                r[9][n] = (r[9][n] ? r[9][n].replace(/\&$/, '').split('=') : []);
                if (r[9][n].length == 1)
                    r[9][n][1] = '';
            }
        }

        // 프로토콜이 없을 경우 추가
        if ( ! r[1] && ! r[5]) {
            // 도메인이 없는 경우 로컬 파일 주소로 설정
            if ( ! r[3]) r[5] = 'file';

            // E-Mail 인지 체크
            else if (r[0].match(new RegExp('^('+ r[2][0] +'@'+ r[3] +')$')))
                r[1] = 'mailto';

            // 기타 기본 포트를 기준으로 프로토콜 설정.
            // 포트가 없을 경우 기본적으로 http 로 설정
            else {
                switch (r[4]) {
                    case 21:    r[1] = 'ftp'; break;
                    case 23:    r[1] = 'telnet'; break;
                    case 443:   r[1] = 'https'; break;
                    case 80:
                    default:    r[1] = 'http'; break;
                }
            }

            r[0] = (r[1] ? r[1] +'://' : r[5] +':///')
                + r[0];
        }

        return {
            'url'       : r[0],                     // 전체 URL
            'protocol'  : (r[1] ? r[1] : r[5]),     // [ftp|http|https|mailto|telnet] | [file]
            'userid'    : (r[2] ? r[2][0] : ''),    // 아이디 : HTTP 인증 정보
            'userpass'  : (r[2] ? r[2][1] : ''),    // 비밀번호
            'domain'    : (r[3] ? r[3] : ''),       // 도메인주소
            'port'      : (r[4] ? r[4] : ''),       // 포트
            'drive'     : (r[6] ? r[6] : ''),       // 'file' 프로토콜인 경우
            'directory' : (r[7] ? r[7] : ''),       // 하위 디렉토리
            'filename'  : (r[8] ? r[8] : ''),       // 파일명
            'querys'    : (r[9] ? r[9] : ''),       // 쿼리스트링
            'anchor'    : (r[10] ? r[10] : '')      // Anchor
        };
    }
};// END: ClevisURL;
