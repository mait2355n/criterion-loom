目的: fixture/golden 退行検出を実装する。
対象外: 監査規則本体の大規模改変はしない。
成果物: fixture 入力、期待値 JSON、unittest 実行器、文書更新。
作業分解: fixture 入力、期待値 JSON、unittest 実行器、文書更新を作業パッケージに分ける。
手順: 形式設計、fixture 追加、実装、検証、文書化。
順序: 形式設計後に fixture を追加し、実装後に検証と文書化を行う。
依存: Python 標準 json/pathlib/unittest と既存 core API。
資源: Codex が一作業単位で実施し、追加依存なし。
リスク: 期待値を厳密にしすぎると有益な改善で壊れる。部分一致で抑える。
検証: unittest と compileall を実行する。
妥当性: 各 fixture の rationale が固定したい監査意味へ追跡できるか確認する。
判断主体: 保守者が受入を判断する。
確認点: fixture 追加後、実装後、文書更新後に進捗を確認する。
基準線: 既存 core API と fixture 期待値を判定基準にする。
戻し方: 追加 fixture と test_fixtures.py と文書差分を戻す。
証拠: 実行したコマンド結果を完了報告へ残す。
未確定: なし。
