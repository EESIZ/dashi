# dashi — 윤문(yunmun)

한국어 글에서 AI 티를 찾고 지우는 Claude Code 스킬 + MCP 서버.

뿌리 규칙 하나: 한국어 문장은 끝에서 한 번 닫히고, 닫을 때 화자가 나타난다. 그러므로 명제마다 닫지 말고 태도를 낼 자리에서만 닫는다. 검사기는 이 규칙(R1~R5)을 문장마다 재고, 실패한 문장과 규칙 본문을 묶어 필자에게 되돌려 고치게 한다.

## 설치

```
git clone https://github.com/EESIZ/dashi ~/.claude/skills/dashi
sh ~/.claude/skills/dashi/skills/yunmun/install.sh
claude mcp add --scope user yunmun -- ~/.claude/skills/dashi/skills/yunmun/.venv/bin/python ~/.claude/skills/dashi/skills/yunmun/scripts/yunmun.py
```

요구: Linux x86_64, Python 3.12, uv. 핵심 모듈은 컴파일된 바이너리(`scripts/*.so`)로만 배포한다.

## 도구

`sentence_gate`, `regen_prompt`, `check`, `skeleton`, `classify`, `tag_guide`, `tag_save`, `correction`, `stats`

## 라이선스

CC BY-NC 4.0. 비영리 사용·수정·재배포는 저작자(EESIZ) 표시 조건으로 허용하며, 상업적 이용은 허용하지 않는다.
