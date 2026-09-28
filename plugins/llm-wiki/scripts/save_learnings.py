#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop フック: LLM-Wiki inbox の当日スタブ確保 ＋ 過去の空スタブ自動クリーンアップ.

- 当日 `{date}-{project}.md` の足場（テンプレヘッダ）を用意する（SessionStart でも同じものを作る）。
- 併せて「今日より前の日付」の空スタブ（中身なし）を削除する。
  当日ファイルはアクティブセッション／別プロジェクト並行作業と競合し得るため触らない。

vault ルートは argv[1] → 環境変数の順で解決。hooks.json は引数を渡さないため、通常は
userConfig 由来の環境変数 CLAUDE_PLUGIN_OPTION_VAULT_ROOT で解決される。
解決できなければ何もせず終了（セッションを止めない）。
stdin からフック JSON（cwd を含む）を受け取る。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault import (  # noqa: E402
    ensure_today_stub, is_before_today, is_stub, read_hook_cwd, read_text, resolve_vault,
)


def main() -> int:
    cwd = read_hook_cwd()

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
            if not is_before_today(f.name):
                continue
            try:
                if f.stat().st_size == 0 or is_stub(read_text(f)):
                    f.unlink()
            except Exception:
                pass
    except Exception:
        pass

    # --- 当日スタブの確保 ---
    ensure_today_stub(vault, cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
