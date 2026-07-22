#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop フック: LLM-Wiki inbox の当日スタブ確保 ＋ 過去の空スタブ自動クリーンアップ.

- 当日 `{date}-{project}.md` の足場（テンプレヘッダ）を用意する。
- 併せて「今日より前の日付」の空スタブ（中身なし）を削除する。
  当日ファイルはアクティブセッション／別プロジェクト並行作業と競合し得るため触らない。

vault ルートは argv[1] → 環境変数の順で解決。フック定義から
  args: ["${CLAUDE_PLUGIN_ROOT}/scripts/save_learnings.py", "${user_config.vault_root}"]
のように渡す。解決できなければ何もせず終了（セッションを止めない）。
stdin からフック JSON（cwd を含む）を受け取る。
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault import resolve_vault  # noqa: E402

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def is_stub(text: str) -> bool:
    body = text
    if body.lstrip().startswith("---"):
        parts = body.split("---", 2)
        if len(parts) == 3:
            body = parts[2]
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    lines = [ln for ln in body.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")
             and not ln.strip().startswith("project:")]
    return len(lines) == 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    cwd = data.get("cwd", "")
    project = Path(cwd).name if cwd else "unknown"
    date = datetime.now().strftime("%Y-%m-%d")

    vault = resolve_vault()
    if vault is None:
        return 0                      # vault 未設定なら黙って終了（セッションを止めない）
    inbox = vault / "inbox"
    try:
        inbox.mkdir(parents=True, exist_ok=True)
    except Exception:
        return 0

    # --- 過去日の空スタブを掃除（当日は残す） ---
    try:
        for f in inbox.glob("*.md"):
            m = DATE_RE.match(f.name)
            if not m or m.group(1) >= date:
                continue
            try:
                if f.stat().st_size == 0 or is_stub(f.read_text(encoding="utf-8")):
                    f.unlink()
            except Exception:
                pass
    except Exception:
        pass

    # --- 当日スタブの確保 ---
    outfile = inbox / f"{date}-{project}.md"
    if not outfile.exists():
        try:
            with open(outfile, "w", encoding="utf-8") as f:
                f.write(f"# {date} — {project}\n\n")
                f.write(f"project: `{cwd}`\n\n")
                f.write("## 学んだこと・解決したこと\n\n")
                f.write("<!-- この下にClaude Codeが追記します -->\n\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
