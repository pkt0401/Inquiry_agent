## 파일 구조 설명
- inquiry.json: 문의하기 게시판에 올라온 문의 게시물 데이터 (DB에서 json으로 Export)
- inquiry_comment.json: 문의 댓글 데이터 (DB에서 json으로 Export)
- files.json: 문의 게시물에 첨부된 파일 데이터에 대한 DB 내 row (DB에서 json으로 Export)
- files/: 실제 파일 데이터 files.json의 filepath와 연계되어 있음

- 참고 : inquiry_comment의 user_id 2, 7, 61은 운영자들임

## 요구사항
- 문의 게시물에 대해 응대할 수 있는 agent, 다국어 대응 가능하도록 (일본어, 영어 지원)
- 보수적으로 응답할 수 있는지 여부를 판단해서 댓글 달기, 무조건 달면 안됨.
- 답변을 하기 위해 필요한 context 정보가 어떤 게 있는지 파악할 것, 시스템 상 이러이러한 정보는 agent가 접근 가능해야할 것 같다 이렇게 정리해주시면 되겠습니다.