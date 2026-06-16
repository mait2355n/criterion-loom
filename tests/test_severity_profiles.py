from __future__ import annotations

import unittest

from semantic_guard.core import audit_plan
from semantic_guard.severity_profiles import apply_severity_profile


class SeverityProfileTests(unittest.TestCase):
    def test_release_profile_upgrades_governance_gap(self) -> None:
        result = audit_plan(
            "目的: 設定を公開する。対象外: UI。成果物: config。手順: 調査、実装、検証。"
            "依存: 既存 config。リスク: 運用が壊れる。検証: unittest。"
            "妥当性: 利用者が判断する。判断主体: 利用者。確認点: 実装後。"
            "戻し方: backup を戻す。証拠: コマンド結果。未確定: なし。",
            strict=True,
        )

        profiled = apply_severity_profile(result, "release")

        governance = [finding for finding in profiled["findings"] if finding["category"] == "governance"]
        self.assertTrue(governance)
        self.assertEqual(governance[0]["severity"], "major")
        self.assertTrue(profiled["details"]["severity_profile"]["adjustments"])
        self.assertEqual(profiled["details"]["severity_profile"]["base_score"], result["score"])
        self.assertLess(profiled["details"]["severity_profile"]["profiled_score"], result["score"])


if __name__ == "__main__":
    unittest.main()
