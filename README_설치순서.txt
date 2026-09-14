해피아이 알리미 Cloud v1
=======================

목표
- PC를 켜두지 않아도 약 10분 간격으로 유치원 홈페이지 확인
- 사랑반 / 가정통신문 / 오늘의 식단 새 글 감지
- 새 글이 있으면 iPhone 홈 화면 PWA '해피아이 알리미'에 웹 푸시
- 알림을 누르면 해당 유치원 글로 이동

사용하는 무료 서비스
1) GitHub Pages: 아이폰에 설치할 해피아이 알리미 화면
2) GitHub Actions: 약 10분마다 새 글 검사
3) OneSignal: 아이폰 웹 푸시 전송

중요 보안
- 유치원 아이디/비밀번호를 코드에 절대 적지 않습니다.
- GitHub의 Repository Secrets에만 저장합니다.
- 공개 저장소에 저장되는 상태 파일에는 게시글 제목이나 아이디 원문 대신 SHA-256 해시만 남습니다.
- 유치원 사이트 자체가 HTTP이므로 원문을 열 때는 해당 사이트의 기존 보안 수준을 그대로 따릅니다.

준비할 계정
- GitHub 계정 1개
- OneSignal 무료 계정 1개

GitHub 저장소 이름 추천
- happiyi-alimi

설치 큰 순서
A. GitHub에 새 PUBLIC 저장소를 만든다.
B. 이 압축파일 안의 모든 파일/폴더를 저장소에 업로드한다.
C. GitHub Pages를 'Deploy from a branch' / main / docs 폴더로 켠다.
D. 만들어진 Pages 주소를 확인한다.
   예: https://내아이디.github.io/happiyi-alimi/

E. OneSignal에서 Web Push 앱을 만든다.
   Site URL에는 위 GitHub Pages 주소를 넣는다.
   Custom Code 방식으로 설정한다.
   App ID와 App API Key를 확인한다.

F. PC에서 configure_pwa.bat을 실행하고 OneSignal App ID를 입력한다.
   변경된 docs/config.js를 GitHub에 다시 업로드/덮어쓴다.

G. GitHub 저장소 > Settings > Secrets and variables > Actions > New repository secret에서 아래 5개를 만든다.
   HAPPI_ID
   HAPPI_PASSWORD
   ONESIGNAL_APP_ID
   ONESIGNAL_API_KEY
   PAGES_URL

   PAGES_URL 예:
   https://내아이디.github.io/happiyi-alimi

H. GitHub > Actions > Happy-I checker > Run workflow를 한 번 수동 실행한다.
   첫 실행은 현재 게시글을 기준점으로 저장하므로 알림을 보내지 않는다.

I. 아이폰에서 GitHub Pages 주소 접속
   공유 > 홈 화면에 추가
   홈 화면의 '해피아이' 아이콘으로 다시 실행
   '알림 켜기' 버튼을 누르고 허용

그 이후
- GitHub Actions가 매시 03,13,23,33,43,53분에 검사합니다.
- GitHub 스케줄 작업은 정확히 그 분에 시작되지 않고 지연될 수 있습니다.
- 새 글이 있으면 OneSignal이 구독된 아이폰으로 전송합니다.

비용
- 이 설계는 GitHub PUBLIC 저장소 + GitHub Pages + OneSignal 무료 플랜을 기준으로 월 0원으로 시작할 수 있게 구성했습니다.
- 서비스 정책은 변경될 수 있습니다.

문제가 생기면
- GitHub Actions 실행 화면의 빨간 오류 부분을 캡처해서 ChatGPT에 보여주세요.
- 아이디, 비밀번호, OneSignal API Key는 절대 캡처에 노출하지 마세요.
