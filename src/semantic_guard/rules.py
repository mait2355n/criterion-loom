from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["blocker", "major", "minor", "info"]
Phase = Literal["understand_target", "audit_request", "audit_plan", "audit_diff", "finish_check"]
Discipline = Literal[
    "requirements_engineering",
    "project_planning",
    "software_engineering",
    "secure_development",
    "semantic_preservation",
]


@dataclass(frozen=True)
class SeverityPolicy:
    mode: str
    severity: Severity

    def as_dict(self) -> dict[str, str]:
        return {"mode": self.mode, "severity": self.severity}


@dataclass(frozen=True)
class Rule:
    id: str
    discipline: Discipline
    phase: Phase
    engineering_basis: tuple[str, ...]
    concern: str
    applies_when: tuple[str, ...]
    does_not_apply_when: tuple[str, ...]
    evidence_required: tuple[str, ...]
    severity_policy: tuple[SeverityPolicy, ...]
    finding: str
    remediation: str

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "discipline": self.discipline,
            "phase": self.phase,
            "engineering_basis": list(self.engineering_basis),
            "concern": self.concern,
            "applies_when": list(self.applies_when),
            "does_not_apply_when": list(self.does_not_apply_when),
            "evidence_required": list(self.evidence_required),
            "severity_policy": [policy.as_dict() for policy in self.severity_policy],
            "finding": self.finding,
            "remediation": self.remediation,
        }


RULES: tuple[Rule, ...] = (
    Rule(
        id="req.verifiability.acceptance_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: requirement quality and verifiability",
            "BABOK: requirements acceptance criteria and traceability",
            "NASA SEH: verification planning for technical requirements",
        ),
        concern="要求が達成確認不能なまま実装へ進むこと。",
        applies_when=(
            "入力が要求または要求候補である。",
            "達成確認、受入条件、試験、検査、実演、解析、証拠の記述が見えない。",
        ),
        does_not_apply_when=(
            "入力種別が説明文書、計画、差分、完了報告である。",
            "文脈側に明示的な受入条件または検証経路がある。",
        ),
        evidence_required=(
            "受入条件",
            "検証方法",
            "完了証拠の種類",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="blocker"),
            SeverityPolicy(mode="relaxed", severity="major"),
        ),
        finding="要求の達成確認方法が見えない。",
        remediation="試験、解析、検査、実演、受入条件のいずれかを明示する。",
    ),
    Rule(
        id="req.scope.non_goals_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: requirement scope and constraints",
            "BABOK: scope modeling and change impact analysis",
        ),
        concern="暗黙の対象外が実装範囲へ紛れ込むこと。",
        applies_when=(
            "入力が要求または要求候補である。",
            "対象外、非要求、非目標、制約、禁止事項が見えない。",
        ),
        does_not_apply_when=(
            "要求が単一で、周辺範囲が既存文脈に明示されている。",
            "探索、調査、質問など、範囲確定前の入力である。",
        ),
        evidence_required=(
            "対象外",
            "非要求",
            "変更禁止領域",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="非要求または対象外が明示されていない。",
        remediation="今回やらないこと、誤って含めてはいけないことを追加する。",
    ),
    Rule(
        id="req.achievement.criteria_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: requirement verification and acceptance information",
            "BABOK: verify requirements and validate requirements",
            "NASA SEH: measures of effectiveness and product validation",
        ),
        concern="要求が、何をもって達成されたと言えるか不明なまま実装されること。",
        applies_when=(
            "入力が検証、確認、試験、受入に触れている。",
            "受入基準、合格条件、完了条件、成功状態、Definition of Done が見えない。",
        ),
        does_not_apply_when=(
            "要求が探索質問や調査依頼で、達成条件を作る前段階である。",
            "文脈側に達成条件、成功状態、受入基準、または測定可能な品質基準がある。",
        ),
        evidence_required=(
            "受入基準",
            "合格条件",
            "成功状態",
            "完了条件",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="要求が何を以て達成されたと言えるかが薄い。",
        remediation="受入基準、合格条件、完了条件、成功状態、または Definition of Done を明示する。",
    ),
    Rule(
        id="req.verification.method_detail_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: verification methods and requirement quality",
            "BABOK: verify requirements",
            "NASA SEH: verification planning and verification methods",
        ),
        concern="確認する、動作確認する、とだけ書かれ、試験か解析か検査か実演か分からないこと。",
        applies_when=(
            "入力が検証、確認、試験、受入に触れている。",
            "試験、解析、検査、実演、測定、レビュー、代表実行などの具体的方法が見えない。",
        ),
        does_not_apply_when=(
            "文脈側に具体的な検証方法または実行コマンドがある。",
            "要求が検証方法を別計画へ委譲していることを明示している。",
        ),
        evidence_required=(
            "検証方法",
            "実行コマンドまたは試験種類",
            "測定またはレビュー方法",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="検証または確認の方法が具体化されていない。",
        remediation="試験、解析、検査、実演、測定、レビュー、代表 CLI 実行など、どの方法で確かめるかを明示する。",
    ),
    Rule(
        id="req.evidence.artifact_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: requirements information items and verification evidence",
            "BABOK: requirements lifecycle management and traceability",
            "NASA SEH: validation report and objective evidence",
        ),
        concern="達成確認が口頭や内心で終わり、後から確認できる証拠が残らないこと。",
        applies_when=(
            "要求に受入基準または検証方法がある。",
            "コマンド結果、試験結果、ログ、スクリーンショット、出力 JSON、レビュー記録などの証拠成果物が見えない。",
        ),
        does_not_apply_when=(
            "証拠が完了報告または試験計画に記録されることが明示されている。",
            "作業が会話回答のみで、永続証拠を残す必要がない。",
        ),
        evidence_required=(
            "証拠成果物",
            "試験結果または実行結果",
            "記録の保存先または形式",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="達成確認に使う証拠成果物が見えない。",
        remediation="コマンド結果、試験結果、ログ、スクリーンショット、出力 JSON、レビュー記録など、残す証拠を明示する。",
    ),
    Rule(
        id="req.acceptance.rejection_condition_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "BABOK: validate requirements and solution evaluation",
            "PMBOK: quality acceptance and change control",
            "NASA SEH: anomaly identification and corrective action in validation",
        ),
        concern="安全、権限、移行、公開、運用などの要求で、未達や差し戻しの条件が無いこと。",
        applies_when=(
            "要求が安全、権限、削除、移行、公開、運用、永続化など失敗時影響が大きい対象に触れる。",
            "不合格、棄却、差し戻し、保留、rollback 条件が見えない。",
        ),
        does_not_apply_when=(
            "要求が低リスクな局所改善で、失敗時の扱いが通常の未完了で足りる。",
            "文脈側に未達条件、差し戻し条件、rollback、または保留判断がある。",
        ),
        evidence_required=(
            "不合格条件",
            "差し戻し条件",
            "保留または rollback 条件",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="不合格、棄却、戻しが必要になる条件が見えない。",
        remediation="どの結果なら未達、差し戻し、保留、または rollback とするかを明示する。",
    ),
    Rule(
        id="req.context.scenario_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "NASA SEH: use cases, scenarios, concept of operations, and stakeholder expectations",
            "BABOK: specify and model requirements",
            "ISO/IEC/IEEE 29148: operational concepts and requirements context",
        ),
        concern="利用者操作や入力出力を含む要求が、どの場面で満たすべきか不明なまま実装されること。",
        applies_when=(
            "要求が画面、UI、利用者、入力、表示、検索、通知、workflow などに触れる。",
            "利用場面、入力条件、操作文脈、期待出力が見えない。",
        ),
        does_not_apply_when=(
            "要求が内部処理のみで、利用場面が意味を左右しない。",
            "文脈側にシナリオ、ユースケース、Given/When/Then、入力、期待出力がある。",
        ),
        evidence_required=(
            "利用場面",
            "入力条件",
            "操作文脈",
            "期待出力",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="利用場面、入力条件、操作文脈が見えない。",
        remediation="誰が、どの状態で、何を入力または操作し、何が返ればよいかを短いシナリオで明示する。",
    ),
    Rule(
        id="req.structure.observable_behavior_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: construct and characteristics of a good requirement",
            "BABOK: specify and model requirements",
            "NASA SEH: technical requirements definition",
        ),
        concern="改善、対応、サポートなどの語だけで、観測可能な振る舞いが定義されないこと。",
        applies_when=(
            "要求が改善、対応、サポート、最適化、強化などの抽象動詞で述べられている。",
            "返す、表示する、保存する、拒否する、通知する、記録するなどの観測可能な振る舞いが見えない。",
        ),
        does_not_apply_when=(
            "要求が調査、相談、設計方針の段階で、振る舞いをまだ固定しないことが明示されている。",
            "文脈側に観測可能な振る舞い、期待出力、状態変化、または検査可能な結果がある。",
        ),
        evidence_required=(
            "観測可能な振る舞い",
            "期待出力または状態変化",
            "対象操作または入力",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="要求が観測可能な振る舞いへ落ちていない。",
        remediation="誰または何が、どの操作や入力に対して、何を返す、保存する、表示する、拒否する、通知するのかを明示する。",
    ),
    Rule(
        id="req.context.precondition_trigger_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "NASA SEH: scenarios, use cases, and concept of operations",
            "BABOK: specify and model requirements",
            "ISO/IEC/IEEE 29148: requirements context and operational concepts",
        ),
        concern="利用者操作や公開面の要求で、いつその要求が発火するか不明なこと。",
        applies_when=(
            "要求が UI、画面、入力、検索、通知、API、CLI、JSON などに触れる。",
            "前提状態、入力条件、操作、発火条件、対象データが見えない。",
        ),
        does_not_apply_when=(
            "要求が常時成立すべき制約で、発火条件を持たない。",
            "文脈側に Given/When、前提条件、入力条件、操作、発火条件、対象データがある。",
        ),
        evidence_required=(
            "前提条件",
            "発火条件",
            "入力条件または対象データ",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="要求が満たされる前提条件または発火条件が見えない。",
        remediation="Given/When、前提状態、入力条件、操作、発火条件、対象データを明示する。",
    ),
    Rule(
        id="req.result.expected_result_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: verifiable requirement statements",
            "BABOK: verify requirements",
            "NASA SEH: validation against stakeholder expectations",
        ),
        concern="操作や入力に対して、何が返る、表示される、変化するのか不明なこと。",
        applies_when=(
            "要求が入力、操作、検索、通知、画面、UI、API、CLI、JSON などに触れる。",
            "期待する出力、表示、状態変化、エラー、拒否、通知、保存結果が見えない。",
        ),
        does_not_apply_when=(
            "品質要求だけで、期待結果が数値基準として十分に表現されている。",
            "文脈側に期待出力、状態変化、エラー、拒否、通知、保存結果がある。",
        ),
        evidence_required=(
            "期待出力",
            "期待状態",
            "エラーまたは拒否の扱い",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="操作や入力に対する期待結果が見えない。",
        remediation="期待する出力、表示、状態変化、エラー、拒否、通知、保存結果を明示する。",
    ),
    Rule(
        id="req.interface.contract_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: interface and software requirements information",
            "BABOK: requirements architecture and specify requirements",
            "ISO/IEC 25010: compatibility and interoperability",
        ),
        concern="API、CLI、JSON、設定などの公開面が、項目や形式なしに要求化されること。",
        applies_when=(
            "要求が API、CLI、MCP、JSON、YAML、CSV、Webhook、設定、環境変数、ファイル形式に触れる。",
            "入力項目、出力項目、形式、状態コード、エラー、既定値、例、schema が見えない。",
        ),
        does_not_apply_when=(
            "公開契約の詳細を別仕様へ委譲していることが明示されている。",
            "文脈側に schema、項目、状態コード、エラー、形式、例、既定値、引数がある。",
        ),
        evidence_required=(
            "入力項目",
            "出力項目",
            "形式または schema",
            "エラーまたは状態コード",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="入出力または公開面に触れているが、契約の項目が薄い。",
        remediation="入力項目、出力項目、形式、状態コード、エラー、既定値、例、schema のいずれかを明示する。",
    ),
    Rule(
        id="req.stakeholder.source_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: stakeholder requirements and requirements information items",
            "BABOK: elicitation, stakeholder needs, and requirements lifecycle management",
            "NASA SEH: stakeholder expectations definition",
        ),
        concern="誰の要求か、誰が使い、誰が受け入れるのか不明なまま実装へ進むこと。",
        applies_when=(
            "入力が要求または要求候補である。",
            "利害関係者、利用者、依頼元、受入者、運用者、保守者、判断主体が見えない。",
        ),
        does_not_apply_when=(
            "入力種別が説明文書、計画、差分、完了報告である。",
            "文脈側に要求元、利用者、受入者、判断主体、または不要理由がある。",
        ),
        evidence_required=(
            "利害関係者",
            "要求出所",
            "受入者または判断主体",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="要求の利害関係者または出所が見えない。",
        remediation="誰の要求か、誰が使うか、誰が受け入れるか、または出所が不要な理由を明示する。",
    ),
    Rule(
        id="req.quality.measurable_constraint_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: requirement characteristics and verification",
            "ISO/IEC 25010: software product quality characteristics",
            "BABOK: validate requirements and analyze potential value",
        ),
        concern="速い、安全、安定、使いやすいなどの品質要求が、測定不能な願望として残ること。",
        applies_when=(
            "入力が性能、安全性、可用性、信頼性、保守性、使いやすさなどの品質要求に触れる。",
            "閾値、測定方法、受入基準、判断主体が見えない。",
        ),
        does_not_apply_when=(
            "品質語が一般説明や対象外理由にだけ現れる。",
            "測定方法、閾値、受入基準、ベンチマーク、手動判断主体、または未定扱いが明示されている。",
        ),
        evidence_required=(
            "品質特性",
            "測定方法",
            "閾値または受入基準",
            "判断主体",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="品質要求らしき記述があるが、測定条件や受入基準が薄い。",
        remediation="性能、信頼性、安全性、使いやすさなどを、閾値、測定方法、受入基準、判断主体へ落とす。",
    ),
    Rule(
        id="req.priority.multiple_requirements_unprioritized",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "BABOK: requirements prioritization and backlog management",
            "PMBOK: scope and value delivery planning",
            "ISO/IEC/IEEE 29148: requirements management and traceability",
        ),
        concern="複数要求が同列に束ねられ、実装順序や保留判断が曖昧になること。",
        applies_when=(
            "入力が複数の要求を一つに束ねている可能性がある。",
            "必須、任意、優先度、実施順序、採用、保留が見えない。",
        ),
        does_not_apply_when=(
            "入力が単一要求である。",
            "文脈側に優先度、実施順序、保留、段階化、または一括実施の根拠がある。",
        ),
        evidence_required=(
            "優先度",
            "実施順序",
            "必須/任意",
            "保留判断",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="複数要求らしき入力に優先度または実施順序が見えない。",
        remediation="必須/任意、先にやる/後でやる、採用/保留などの優先度を分ける。",
    ),
    Rule(
        id="req.uncertainty.unclassified_uncertainty",
        discipline="semantic_preservation",
        phase="audit_request",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: requirements information items and assumptions",
            "BABOK: assumptions, constraints, and requirements lifecycle management",
            "semantic-implementation: preserve unknowns, hypotheses, and pending decisions",
        ),
        concern="推測や不確実性が要求本文へ混ざり、事実または確定要求として扱われること。",
        applies_when=(
            "入力に、たぶん、おそらく、かもしれない、maybe、probably などの不確実表現がある。",
            "未確定、仮説、判断待ち、保留、片側観測、時点差などの分類が見えない。",
        ),
        does_not_apply_when=(
            "不確実性が明示的に仮説、未確定、判断待ち、保留、時点差として分類されている。",
            "入力が探索質問や相談で、まだ要求化していないことが明らかである。",
        ),
        evidence_required=(
            "未確定分類",
            "仮説または判断待ち",
            "確定要求との分離",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="不確実な表現があるが、未確定、仮説、判断待ちなどの扱いが分かれていない。",
        remediation="推測を要求に混ぜず、未確定、仮説、判断待ち、片側観測、時点差のいずれかへ分類する。",
    ),
    Rule(
        id="req.solution.problem_mechanism_fit_missing",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "BABOK: analyze current state, define future state, and assess solution options",
            "ISO/IEC/IEEE 29148: requirement rationale, constraints, and validation information",
            "NASA SEH: problem definition, root-cause analysis, and validation against stakeholder expectations",
            "semantic-implementation: separate observed symptom, cause hypothesis, solution, and evidence",
        ),
        concern="解決策が観測症状を消すだけで、問題の原因、発生機構、制約、責務構造へどう作用するか不明なまま採用されること。",
        applies_when=(
            "入力が問題または症状と解決策を含む要求候補である。",
            "原因、発生機構、再現条件、制約、根拠、または解決策が効く理由が見えない。",
        ),
        does_not_apply_when=(
            "要求が純粋な新機能追加で、観測済み問題や症状の解消を目的にしていない。",
            "文脈側に原因仮説、機構説明、再現条件、制約、または解決策と問題の対応根拠がある。",
            "探索や調査依頼で、原因や解決策の候補をこれから作る段階だと明示されている。",
        ),
        evidence_required=(
            "原因または発生機構",
            "解決策が問題へ作用する根拠",
            "再現条件、制約、または責務構造",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="解決策が問題の原因構造または発生機構へどう作用するかが見えない。",
        remediation="観測症状、原因仮説、発生条件、制約、解決策が効く理由、または調査で確かめる項目を分けて明示する。",
    ),
    Rule(
        id="req.acceptance.symptom_only_success_criteria",
        discipline="requirements_engineering",
        phase="audit_request",
        engineering_basis=(
            "BABOK: solution evaluation and root cause analysis",
            "ISO/IEC/IEEE 29148: verifiable requirement acceptance information",
            "NASA SEH: validation criteria and anomaly resolution",
            "semantic-implementation: avoid treating disappearance of a signal as proof of problem resolution",
        ),
        concern="成功条件が、警告、失敗、停止、拒否、遅延などの観測症状が消えたことだけになり、本来の目的達成や異常時挙動を測れないこと。",
        applies_when=(
            "要求が問題または症状の解消を扱っている。",
            "受入条件が症状の消失、停止しないこと、エラーが出ないこと、警告が出ないことなどに偏っている。",
            "原因、制約、異常時挙動、副作用確認、または反証条件が見えない。",
        ),
        does_not_apply_when=(
            "症状の消失が、測定可能な根本原因、品質閾値、異常時挙動、または安全側条件と一緒に定義されている。",
            "要求が低影響の表示文言や一回限りの作業で、症状消失そのものが妥当な完了条件である。",
        ),
        evidence_required=(
            "目的達成に対応する受入条件",
            "原因または制約に対する確認",
            "反証条件または異常時挙動",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="受入条件が観測症状の消失だけに寄っている。",
        remediation="症状が出ないことだけでなく、原因または制約が解けた証拠、目的達成、異常時挙動、差し戻し条件を足す。",
    ),
    Rule(
        id="plan.risk.rollback_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: risk responses and change control",
            "ISO 21502: planning, control, and risk management",
            "NASA SEH: technical risk management and recovery planning",
        ),
        concern="失敗時の復旧経路がない計画で変更へ進むこと。",
        applies_when=(
            "入力が実装、移行、設定変更、文書正本更新を含む計画である。",
            "戻し方、復旧、退避、fallback、rollback が見えない。",
        ),
        does_not_apply_when=(
            "読み取り専用の調査または設計相談だけである。",
            "変更対象が破棄可能な一時成果物だけである。",
        ),
        evidence_required=(
            "戻し方",
            "復旧手順",
            "退避またはbackupの有無",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="blocker"),
            SeverityPolicy(mode="relaxed", severity="major"),
        ),
        finding="計画に復旧またはrollback経路が見えない。",
        remediation="戻し方、退避、fallback、または失敗時の containment を明示する。",
    ),
    Rule(
        id="plan.validation.problem_fit_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: benefits and value delivery",
            "ISO 21502: objectives, stakeholder needs, and quality",
            "NASA SEH: validation against stakeholder expectations",
        ),
        concern="作ったものが要求を満たしても、そもそもの問題を解いていないこと。",
        applies_when=(
            "入力が実装または変更計画である。",
            "妥当性確認、受入、目的に合うかの確認が見えない。",
        ),
        does_not_apply_when=(
            "要求元が検証可能な修正一点だけで、目的適合が自明な保守作業である。",
            "計画ではなく実行済み結果の完了報告である。",
        ),
        evidence_required=(
            "妥当性確認方法",
            "受入者または判断主体",
            "目的との対応",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="blocker"),
            SeverityPolicy(mode="relaxed", severity="major"),
        ),
        finding="計画に妥当性確認が見えない。",
        remediation="成果物が目的に合うことを誰が何で確認するか明示する。",
    ),
    Rule(
        id="plan.validation.owner_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: stakeholder engagement, governance, and quality acceptance",
            "ISO 21502: stakeholder, governance, and quality planning",
            "NASA SEH: validation against stakeholder expectations",
        ),
        concern="受入判断の主体が曖昧なまま、完了条件だけが書かれること。",
        applies_when=(
            "計画が妥当性確認、受入、validation、acceptance に触れている。",
            "誰が受け入れるか、誰が修正要求を判断するかが見えない。",
        ),
        does_not_apply_when=(
            "読み取り専用の調査で、受入判断が回答本文そのものに限定される。",
            "計画または文脈に受入者、判断主体、査読者、承認者、利用者が明示されている。",
        ),
        evidence_required=(
            "受入者",
            "判断主体",
            "判断材料",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="妥当性確認または受入判断の主体が見えない。",
        remediation="誰が、何を見て、受け入れまたは修正要求を判断するか明示する。",
    ),
    Rule(
        id="plan.control.progress_control_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: planning, monitoring, and controlling",
            "ISO 21502: monitoring, controlling, and reporting",
            "NASA SEH: technical assessment and progress control",
        ),
        concern="複数段階の計画が、途中の状態確認なしに最後まで流れること。",
        applies_when=(
            "計画が複数段階、工程、手順、フェーズ、作業分解を含む。",
            "中間確認、進捗報告、状態更新、停止条件が見えない。",
        ),
        does_not_apply_when=(
            "単発の小作業で、中間確認が過剰である。",
            "計画または文脈に進捗確認、状態報告、節目、レビュー、停止条件、または不要理由がある。",
        ),
        evidence_required=(
            "確認点",
            "進捗または状態報告",
            "停止条件または不要理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="複数段階の計画だが、進捗確認点または状態報告の方法が見えない。",
        remediation="中間確認、進捗報告、状態更新、停止条件、または不要理由を足す。",
    ),
    Rule(
        id="plan.control.change_control_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: scope management, change control, and governance",
            "ISO 21502: change control and project control",
            "NASA SEH: technical baseline and change control",
        ),
        concern="移行、公開、運用、設定変更などが、追加要求や範囲変更の扱いなしに進むこと。",
        applies_when=(
            "計画が移行、公開、運用、設定、API、MCP、全体変更、複数領域に触れる。",
            "範囲変更、追加要求、逸脱、後続化、判断待ちの扱いが見えない。",
        ),
        does_not_apply_when=(
            "計画が読み取り専用または局所的な一ファイル修正である。",
            "計画または文脈に変更統制、範囲変更、追加要求、後続化、保留、対象外、再計画が明示されている。",
        ),
        evidence_required=(
            "変更統制",
            "追加要求の扱い",
            "範囲変更の扱い",
            "後続化または保留基準",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="範囲変更や追加要求が起きやすい計画だが、変更統制が見えない。",
        remediation="追加要求、範囲変更、逸脱、後続化、判断待ちの扱いを決める。",
    ),
    Rule(
        id="plan.structure.work_package_decomposition_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMI WBS: deliverable-oriented decomposition of project scope",
            "ISO 21511: work breakdown structures for project and programme management",
            "NASA SEMP: technical program planning and control",
        ),
        concern="成果物や作業が粗い名目のまま残り、進捗、責任、検証、変更影響を追えないこと。",
        applies_when=(
            "計画が複数成果物、実装、移行、公開、運用、設定変更を含む。",
            "WBS、成果物分解、作業パッケージ、ファイル別/機能別/担当別の分解が見えない。",
        ),
        does_not_apply_when=(
            "単一成果物の小修正で、分解するとかえって過剰である。",
            "計画または文脈に成果物別、機能別、ファイル別、担当別の作業単位が明示されている。",
        ),
        evidence_required=(
            "成果物分解",
            "作業パッケージ",
            "分解単位と対象成果物の対応",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="成果物や作業が、管理可能な作業パッケージへ分解されていない。",
        remediation="WBS、成果物分解、ファイル別/機能別/担当別の作業パッケージを明示する。",
    ),
    Rule(
        id="plan.schedule.dependency_sequence_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: schedule planning and activity sequencing",
            "ISO 21502: schedule and project control practices",
            "NASA SEH: technical planning across life cycle phases",
        ),
        concern="複数作業の順序や並行可否が曖昧なまま、後続作業が誤った前提で進むこと。",
        applies_when=(
            "計画が複数段階、複数成果物、または実装と検証を含む。",
            "先行、後続、依存関係、並行可否、ブロッカー、critical path が見えない。",
        ),
        does_not_apply_when=(
            "単発作業で順序が意味を持たない。",
            "計画または文脈に作業順序、先行条件、並行可否、または依存順序が明示されている。",
        ),
        evidence_required=(
            "先行作業",
            "後続作業",
            "並行可否",
            "ブロッカー",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="複数作業の先行関係、依存順序、並行可否が見えない。",
        remediation="先に終える作業、後続作業、並行できる作業、ブロッカーを明示する。",
    ),
    Rule(
        id="plan.resource.estimate_or_capacity_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "ISO 21502: resource, cost, and schedule planning",
            "PMBOK: resource and estimate planning",
            "NASA SEMP: resources required for technical activities",
        ),
        concern="計画の規模や必要資源が見えず、実行不能または過剰な計画を検出できないこと。",
        applies_when=(
            "計画が複数段階の実装、検証、文書化、移行、公開、設定変更を含む。",
            "工数、所要時間、担当、資源、容量、追加依存なし、または見積不要理由が見えない。",
        ),
        does_not_apply_when=(
            "短い読み取り専用調査で、資源見積が目的に対して過剰である。",
            "計画または文脈に担当、所要時間、容量制約、追加依存なし、または見積不要理由がある。",
        ),
        evidence_required=(
            "担当または実施主体",
            "所要時間、工数、または容量前提",
            "追加依存の有無",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="作業量、所要時間、担当、資源、容量の前提が見えない。",
        remediation="工数、所要時間、担当、追加依存なし、容量制約、または見積不要な理由を明示する。",
    ),
    Rule(
        id="plan.risk.response_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: risk identification, analysis, response planning, and monitoring",
            "ISO 21502: risk management practices",
            "NASA SEH: technical risk management integration with planning",
        ),
        concern="リスクを列挙しただけで、検知、緩和、代替、保留、責任者が決まらないこと。",
        applies_when=(
            "計画にリスク、懸念、失敗条件、hazard がある。",
            "回避、低減、対策、検知、退避、再試行、contingency、fallback、責任者が見えない。",
        ),
        does_not_apply_when=(
            "読み取り専用の短い調査でリスク対応が通常の完了報告に含まれる。",
            "計画または文脈にリスク対応、代替策、検知方法、退避、保留、責任者が明示されている。",
        ),
        evidence_required=(
            "リスク事象",
            "対応方針",
            "検知または代替策",
            "責任者または判断主体",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="リスクは挙がっているが、対応方針が見えない。",
        remediation="リスク事象ごとに、回避、低減、検知、代替、退避、再試行、保留、責任者のいずれかを明示する。",
    ),
    Rule(
        id="plan.risk.hazard_transfer_analysis_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "PMBOK: risk identification and response planning",
            "ISO 21502: risk, change, and benefit control",
            "NASA SEH: technical risk management and hazard analysis",
            "semantic-implementation: expose where risk tolerance and incompleteness are being accepted",
        ),
        concern="解決策が症状、制限、閾値、拒否、警告、失敗処理を変えるのに、危険、負荷、費用、責任、故障様式がどこへ移るか確認しないこと。",
        applies_when=(
            "計画が問題または症状を抑える解決策、制限値変更、緩和、無効化、回避、リトライ増加、上限変更などに触れる。",
            "副作用、危険移転、負荷移転、下流影響、上流影響、制約確認、または不要理由が見えない。",
        ),
        does_not_apply_when=(
            "計画が読み取り専用の調査または原因切分けだけで、まだ解決策を実施しない。",
            "計画または文脈に影響分析、副作用確認、負荷確認、危険移転、互換性確認、または制約確認が明示されている。",
        ),
        evidence_required=(
            "副作用または危険移転の確認",
            "上流、下流、隣接対象への影響",
            "制約、容量、負荷、費用、責任、故障様式の確認",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="解決策が危険、負荷、費用、責任、故障様式をどこへ移すかが見えない。",
        remediation="副作用、危険移転、負荷移転、上流下流影響、制約確認、または対象外理由を計画へ足す。",
    ),
    Rule(
        id="plan.system.idempotency_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "SWEBOK: reliability, fault tolerance, and recovery",
            "ISO/IEC 25010: reliability, recoverability, and integrity",
            "Distributed Systems: retry safety and idempotent operations",
        ),
        concern="再実行、再試行、同期、定期実行などの反復処理が、二重作成や重複送信を起こすこと。",
        applies_when=(
            "計画が再実行、再試行、リトライ、再送、同期処理、定期実行、queue/job などに触れる。",
            "冪等性、重複防止、一意制約、冪等キー、upsert、排他、transaction、または重複検知が見えない。",
        ),
        does_not_apply_when=(
            "計画が読み取り専用、dry-run、調査のみ、または副作用なしの処理である。",
            "計画または文脈に冪等性、重複防止、一意制約、冪等キー、upsert、排他、transaction、または対象外理由が明示されている。",
        ),
        evidence_required=(
            "再実行または再試行される処理",
            "二重作成、重複送信、重複更新の防止策",
            "冪等性、重複検知、排他、または対象外理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="再実行、再試行、同期、定期実行などの反復処理だが、冪等性や重複副作用の扱いが見えない。",
        remediation="再実行時の二重作成、重複送信、重複更新をどう防ぐか、冪等キー、一意制約、upsert、排他、重複検知、または対象外理由を明示する。",
    ),
    Rule(
        id="plan.control.baseline_or_metric_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "ISO 21502: monitoring, controlling, and reporting",
            "PMBOK: scope, schedule, cost baselines and project control",
            "NASA SEH: technical assessment and corrective action",
        ),
        concern="進捗や完了を何と比較して判断するか不明なこと。",
        applies_when=(
            "計画が複数工程、進捗確認、検証、証拠、状態報告を含む。",
            "基準線、節目条件、完了基準、測定指標、判定基準、baseline が見えない。",
        ),
        does_not_apply_when=(
            "単発回答や読み取り専用調査で進捗制御が不要である。",
            "計画または文脈に基準線、完了基準、測定指標、節目条件、または不要理由がある。",
        ),
        evidence_required=(
            "基準線",
            "節目条件",
            "完了または進捗の判定基準",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="進捗や完了を測る基準線、指標、節目条件が見えない。",
        remediation="scope/schedule baseline、節目、完了基準、測定指標、判定基準、または不要理由を足す。",
    ),
    Rule(
        id="plan.governance.decision_gate_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "ISO 21502: governance, decision-making, and project control",
            "PMBOK: governance and phase gate decision practices",
            "NASA SEMP: reviews, approval, and technical authority coordination",
        ),
        concern="移行、公開、運用、設定変更などの高影響作業が、停止条件や承認なしに進むこと。",
        applies_when=(
            "計画が移行、公開、本番、運用、設定、権限、安全、削除に触れる。",
            "go/no-go、判断ゲート、承認、停止条件、保留条件、人間判断への回付条件が見えない。",
        ),
        does_not_apply_when=(
            "変更が読み取り専用または破棄可能な試作物に限定される。",
            "計画または文脈に判断ゲート、承認、停止条件、保留条件、または不要理由がある。",
        ),
        evidence_required=(
            "判断ゲート",
            "承認または受入判断",
            "停止条件または保留条件",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="移行、公開、運用、設定変更などの高影響作業に対する判断ゲートが見えない。",
        remediation="go/no-go、承認、停止条件、保留条件、または人間判断へ回す条件を明示する。",
    ),
    Rule(
        id="plan.release.provenance_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "SLSA: provenance and build integrity for released artifacts",
            "ISO/IEC/IEEE 12207: release and configuration management",
            "SWEBOK: software configuration management and release management",
        ),
        concern="公開または配布する成果物の版、出所、変更履歴、再現手順が曖昧なまま外へ出ること。",
        applies_when=(
            "計画が公開、配布、release、publish、package、wheel、sdist、PyPI、npm、GitHub 公開に触れる。",
            "版、tag/commit、checksum、変更履歴、生成物の由来、build/release 手順、照合方法が見えない。",
        ),
        does_not_apply_when=(
            "計画が非公開、配布しない、公開しない、または読み取り専用の確認である。",
            "計画または文脈に版、tag/commit、変更履歴、生成物の由来、再現手順、build/release 手順、checksum、署名、または不要理由がある。",
        ),
        evidence_required=(
            "公開物の版またはtag/commit",
            "変更履歴またはrelease note",
            "生成物の由来、build/release 手順、または照合方法",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="公開または配布を扱う計画だが、版、変更履歴、生成物の由来、または再現手順が見えない。",
        remediation="公開物の版、tag/commit、変更履歴、生成物の出所、build/release 手順、照合方法、または不要理由を明示する。",
    ),
    Rule(
        id="plan.minimality.justification_missing",
        discipline="project_planning",
        phase="audit_plan",
        engineering_basis=(
            "Value Engineering: function-to-cost justification for added elements",
            "Lean Engineering: eliminate work and inventory that do not add value",
            "SWEBOK: software design simplicity, reuse, and maintainability",
            "ISO/IEC 25010: maintainability and modifiability trade-offs",
        ),
        concern="新規依存、抽象、層、wrapper、schema などを足す計画が、既存機能や最小案で足りない理由なしに肥大化すること。",
        applies_when=(
            "計画が新規依存、抽象、層、wrapper、factory、adapter、plugin、schema などの追加に触れる。",
            "既存機能、標準機能、平台機能、既存依存、再利用、追加依存なし、後続化、または採用理由が見えない。",
        ),
        does_not_apply_when=(
            "計画が読み取り専用の調査や文書化だけで、実装構造を増やさない。",
            "計画または文脈に既存機能、標準機能、平台機能、既存依存、再利用、追加依存なし、または最小案の採用理由がある。",
            "追加要素が入力検証、権限境界、証跡、再現性、復旧、安全性など削減してはいけない境界を守るためのものだと明示されている。",
        ),
        evidence_required=(
            "既存機能または標準機能で足りない理由",
            "新規依存、抽象、層、schema などの採用理由",
            "後続化できる範囲または削減しない安全・証跡境界",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="新規依存、抽象、層、wrapper、schema などを足す計画だが、既存機能や最小案で足りない理由が見えない。",
        remediation="既存機能、標準機能、平台機能、既存依存で足りるかを確認し、新規要素が必要な根拠、後続化できる範囲、削減してはいけない安全・証跡境界を明示する。",
    ),
    Rule(
        id="diff.test_obligation.source_without_tests",
        discipline="software_engineering",
        phase="audit_diff",
        engineering_basis=(
            "ISO/IEC/IEEE 12207: software verification and validation",
            "SWEBOK: software testing and maintenance",
            "ISO/IEC 25010: reliability and maintainability",
        ),
        concern="ソース変更に対する回帰確認が無いまま完了扱いになること。",
        applies_when=(
            "差分に実行コードの変更がある。",
            "対応する試験、手動確認、または試験不要理由が見えない。",
        ),
        does_not_apply_when=(
            "変更がコメント、文書、型注釈、整形だけで挙動を変えない。",
            "finish_check 側に実行した確認と未実行理由が記録されている。",
        ),
        evidence_required=(
            "追加または更新した試験",
            "実行した確認コマンド",
            "試験不要理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="ソース変更に対する試験差分または確認証拠が見えない。",
        remediation="試験を追加・更新するか、不要な理由と実行した確認を finish_check に残す。",
    ),
    Rule(
        id="diff.security.sensitive_surface_change",
        discipline="secure_development",
        phase="audit_diff",
        engineering_basis=(
            "NIST SSDF: secure software development practices",
            "OWASP: authentication, authorization, secrets, and input handling",
            "CWE: weakness-oriented implementation review",
        ),
        concern="安全性に関わる面の変更が通常差分として見過ごされること。",
        applies_when=(
            "差分が入力、出力、認証、認可、秘密、暗号、依存、権限、ログ、構成に触れる。",
            "安全性確認、秘密情報確認、依存確認、手動確認の証拠が見えない。",
        ),
        does_not_apply_when=(
            "該当語が説明文書や例示だけに現れ、挙動や構成を変えていない。",
            "安全性確認の結果または対象外理由が finish_check に記録されている。",
        ),
        evidence_required=(
            "秘密情報の確認",
            "入力出力境界の確認",
            "認証認可または権限影響の確認",
            "依存または構成影響の確認",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="安全性に関わる差分の可能性がある。",
        remediation="入力、出力、認証、認可、秘密、ログ、依存、構成の確認証拠を残す。",
    ),
    Rule(
        id="diff.implementation.public_contract_change",
        discipline="software_engineering",
        phase="audit_diff",
        engineering_basis=(
            "SWEBOK: software construction, configuration management, and maintenance",
            "ISO/IEC/IEEE 12207: software implementation and transition processes",
            "ISO/IEC 25010: compatibility, usability, and maintainability",
        ),
        concern="CLI、API、MCP、出力 schema など公開契約の変更が通常の実装差分として見過ごされること。",
        applies_when=(
            "差分が CLI、API、MCP tool、出力 schema、既定値、構成、公開 import に触れる。",
            "互換性、移行要否、文書、代表実行、出力契約確認の証拠が見えない。",
        ),
        does_not_apply_when=(
            "変更が内部実装だけで、公開された呼び出し面や出力形式を変えない。",
            "finish_check 側に互換性、移行、文書、代表実行、出力契約確認の結果がある。",
        ),
        evidence_required=(
            "互換性確認",
            "既定値または移行影響",
            "代表 CLI/API/MCP 実行",
            "出力契約確認",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="CLI/API/MCP/出力契約など公開面の変更の可能性がある。",
        remediation="互換性、既定値、移行要否、文書、代表実行、出力契約確認を finish_check に残す。",
    ),
    Rule(
        id="diff.implementation.failure_handling_gap",
        discipline="software_engineering",
        phase="audit_diff",
        engineering_basis=(
            "SWEBOK: software construction, error handling, and construction testing",
            "ISO/IEC/IEEE 12207: software verification and integration",
            "ISO/IEC 25010: reliability, fault tolerance, and recoverability",
        ),
        concern="外部実行、入出力、通信、解析、環境参照など失敗しやすい処理が成功経路だけで実装されること。",
        applies_when=(
            "差分が subprocess、shell、file I/O、JSON parse、network、database、migration、environment に触れる。",
            "timeout、例外処理、戻り値確認、入力不正時の扱い、fallback の証拠が見えない。",
        ),
        does_not_apply_when=(
            "該当処理が文書例だけで実行経路を変えていない。",
            "差分または finish_check に timeout、例外処理、戻り値確認、fallback、または不要理由がある。",
        ),
        evidence_required=(
            "timeout",
            "例外処理",
            "戻り値確認",
            "不正入力時の扱い",
            "fallback または不要理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="失敗しやすい実行・入出力・解析処理に対する失敗処理の証拠が薄い。",
        remediation="timeout、例外処理、戻り値確認、入力不正時の扱い、fallback、または意図的に不要な理由を明示する。",
    ),
    Rule(
        id="diff.implementation.operational_observability_gap",
        discipline="software_engineering",
        phase="audit_diff",
        engineering_basis=(
            "SWEBOK: software engineering operations",
            "ISO/IEC/IEEE 12207: operation and maintenance processes",
            "ISO/IEC 25010: operability, reliability, and maintainability",
        ),
        concern="常駐、定期実行、外部実行、通知、監視、再試行などが失敗しても観測できないこと。",
        applies_when=(
            "差分が daemon、scheduler、cron、launchd、background、webhook、notification、monitor、retry、external execution に触れる。",
            "log、status、returncode、通知、監視、report、record などの観測証拠が見えない。",
        ),
        does_not_apply_when=(
            "変更が手動一回実行の補助だけで、継続運用や通知経路を持たない。",
            "差分または finish_check に log、status、returncode、通知、監視、report、record、または不要理由がある。",
        ),
        evidence_required=(
            "状態報告",
            "log または記録",
            "失敗通知または returncode",
            "監視または不要理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="運用中に失敗し得る処理に対する状態報告や観測性の証拠が薄い。",
        remediation="log、status、returncode、通知、監視、retry 記録、または不要理由を残す。",
    ),
    Rule(
        id="diff.implementation.dependency_runtime_change",
        discipline="secure_development",
        phase="audit_diff",
        engineering_basis=(
            "NIST SSDF: secure software development practices for dependencies and release integrity",
            "ISO/IEC/IEEE 12207: configuration management and software implementation",
            "ISO/IEC 25010: portability, compatibility, and security",
        ),
        concern="依存、実行環境、構成、CI の変更が、互換性や安全性への影響確認なしに流れること。",
        applies_when=(
            "差分が pyproject、lockfile、package manifest、Dockerfile、workflow、runtime config に触れる。",
            "依存更新、実行環境、互換性、安全性、lockfile、CI 影響の確認が見えない。",
        ),
        does_not_apply_when=(
            "変更が説明文書だけで、実際の依存や実行環境を変えていない。",
            "finish_check 側に依存、互換性、安全性、lockfile、CI 影響の確認結果または不要理由がある。",
        ),
        evidence_required=(
            "依存更新の意図",
            "lockfile 整合",
            "互換性確認",
            "安全性確認",
            "CI または実行環境影響",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="依存、実行環境、構成、CI に関わる変更の可能性がある。",
        remediation="依存更新、実行環境、互換性、安全性、lockfile、CI 影響の確認結果を残す。",
    ),
    Rule(
        id="diff.implementation.complexity_growth",
        discipline="software_engineering",
        phase="audit_diff",
        engineering_basis=(
            "SWEBOK: software design simplicity and maintainability",
            "ISO/IEC 25010: maintainability, analyzability, and modifiability",
            "Lean Engineering: reduce non-value-adding complexity",
            "Value Engineering: added function should justify added cost",
        ),
        concern="実装差分が安全や証跡に必要でない複雑性を増やし、保守、試験、説明の負担を増やすこと。",
        applies_when=(
            "差分で分岐、loop、例外処理、class、async などの構造要素がまとまって増える。",
            "責務、標準機能、既存機能、削減候補、試験や証跡との対応が見えない。",
        ),
        does_not_apply_when=(
            "複雑性が入力検証、失敗処理、安全性、証跡、可観測性、復旧など削減してはいけない境界を守るために必要である。",
            "差分または finish_check に、なぜその複雑性が必要か、または何を削ったかの根拠がある。",
        ),
        evidence_required=(
            "追加複雑性の必要理由",
            "標準機能、既存機能、削減候補の確認",
            "安全・証跡・失敗処理として残す必要の有無",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="差分で複雑性が増えている可能性がある。",
        remediation="必要な安全・証跡・失敗処理を残したまま、不要な抽象、分岐、将来対応、新規依存、標準機能の手製実装を削れないか確認する。",
    ),
    Rule(
        id="diff.implementation.filename_content_overbreadth",
        discipline="software_engineering",
        phase="audit_diff",
        engineering_basis=(
            "SWEBOK: software design cohesion and maintainability",
            "ISO/IEC 25010: maintainability, analyzability, and modifiability",
            "semantic-implementation: name versus identity and scope preservation",
            "Lean Engineering: avoid carrying unrelated responsibility in a narrow work unit",
        ),
        concern="狭いファイル名の中へ複数の別責務が追加され、名が示す保守単位より中身が過剰になること。",
        applies_when=(
            "差分が source file を変更し、その basename が特定責務を示している。",
            "追加内容に、ファイル名の責務領域に含まれない別責務領域が複数見える。",
            "ファイル分割、命名変更、同居理由、確認証拠が見えない。",
        ),
        does_not_apply_when=(
            "変更対象が docs/test だけである。",
            "ファイル名が core/utils/common など意図的に広い保守単位である。",
            "追加内容がファイル名と同じ責務領域、または一つの補助責務に留まる。",
            "finish_check 側に、同居が必要な理由、分割不要理由、または命名変更の判断がある。",
        ),
        evidence_required=(
            "ファイル名が示す責務",
            "追加内容の責務領域",
            "分割、命名変更、または同居理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="ファイル名が示す責務に対して、追加内容が複数の別責務へ広がっている可能性がある。",
        remediation="ファイルを分ける、ファイル名を広げる、または同居が必要な理由と確認証拠を finish_check に残す。",
    ),
    Rule(
        id="diff.implementation.filename_scope_underspecified",
        discipline="software_engineering",
        phase="audit_diff",
        engineering_basis=(
            "SWEBOK: software design cohesion and modularity",
            "ISO/IEC 25010: maintainability, analyzability, and modifiability",
            "semantic-implementation: name versus identity and scope preservation",
            "Lean Engineering: avoid premature catch-all work units",
        ),
        concern="追加または改名された source file の名前だけでは機能範囲を管理しづらく、main/core などの汎用名へ責務が膨らむこと。",
        applies_when=(
            "差分が source file を追加または改名している。",
            "basename に manager、service、utils、core、common、handler、controller などの広い責務語が見える。",
            "basename が複数の具体語で機能範囲を絞れておらず、命名厳密化または補助的な機能範囲管理が diff、intent、context に見えない。",
        ),
        does_not_apply_when=(
            "変更対象が docs/test だけである。",
            "既存ファイルの通常更新であり、命名時点ではない。",
            "ファイル名が複数の具体語で十分に絞られている。",
            "main/core など名前で絞りづらい場合に、責務範囲、対象外、同居条件、分割条件などの補助管理線が明示されている。",
        ),
        evidence_required=(
            "追加または改名されたファイル path",
            "膨らみやすい filename token",
            "名前による範囲管理、または汎用名に対する補助管理線",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="ファイル名による機能範囲管理が弱く、膨張を抑える命名または補助管理線が見えない。",
        remediation="可能なら basename をより具体的な機能範囲へ絞る。main/core など名前で絞りづらい場合は、責務、対象外、同居条件、分割条件を明示する。",
    ),
    Rule(
        id="diff.meaning.identity_boundary_change",
        discipline="semantic_preservation",
        phase="audit_diff",
        engineering_basis=(
            "semantic-implementation: name versus identity and storage versus membership",
            "SWEBOK: software design, maintenance, and configuration management",
        ),
        concern="名前、表示、識別子、保管場所、所属、正典の違いが混同されること。",
        applies_when=(
            "差分が名前、表示、識別子、file path、storage path、folder、alias、canonical に触れる。",
            "変更意図に意味保存または対応関係の説明が無い。",
        ),
        does_not_apply_when=(
            "単なる文言修正で、実体識別子や保存先を変えていない。",
            "移行、別名、参照解決、正典扱いの対応が明示されている。",
        ),
        evidence_required=(
            "名前と実体の対応",
            "表示と識別子の対応",
            "物理配置と意味所属の対応",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="minor"),
            SeverityPolicy(mode="relaxed", severity="info"),
        ),
        finding="名前、表示、識別子、保管、所属、正典に関わる差分の可能性がある。",
        remediation="名前と実体、表示と識別子、物理配置と意味所属を混同していないか確認する。",
    ),
    Rule(
        id="finish.evidence.tests_missing",
        discipline="software_engineering",
        phase="finish_check",
        engineering_basis=(
            "ISO/IEC/IEEE 12207: verification evidence",
            "SWEBOK: testing and quality assurance",
            "ISO/IEC 25010: reliability evidence",
        ),
        concern="完了主張が実行証拠なしに受理されること。",
        applies_when=(
            "入力が完了報告である。",
            "実行した試験、確認コマンド、未実行理由が見えない。",
        ),
        does_not_apply_when=(
            "作業が質問応答や設計相談のみで、検証対象の成果物が無い。",
            "証拠欄または文脈欄に実行結果、未実行理由、または確認済み成果物がある。",
        ),
        evidence_required=(
            "実行コマンド",
            "試験結果",
            "未実行理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="blocker"),
            SeverityPolicy(mode="relaxed", severity="major"),
        ),
        finding="検証証拠が見えない。",
        remediation="実行したコマンド、結果、または未実行理由を記録する。",
    ),
    Rule(
        id="finish.implementation.behavior_evidence_missing",
        discipline="software_engineering",
        phase="finish_check",
        engineering_basis=(
            "SWEBOK: construction testing, software testing, and operations",
            "ISO/IEC/IEEE 12207: verification, validation, and transition",
            "ISO/IEC 25010: functional suitability and reliability evidence",
        ),
        concern="単体試験だけで、実際の公開挙動や出力契約を確認せずに完了宣言されること。",
        applies_when=(
            "完了報告が CLI、API、MCP、command、tool、schema、JSON output など公開挙動の実装を述べている。",
            "代表実行、smoke test、出力確認、手動確認、未実行理由が見えない。",
        ),
        does_not_apply_when=(
            "変更が内部関数や文書だけで、利用者から見える挙動を変えていない。",
            "証拠欄に代表 CLI/API/MCP 実行、smoke test、出力契約確認、または未実行理由がある。",
        ),
        evidence_required=(
            "代表実行",
            "smoke test",
            "出力契約確認",
            "未実行理由",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="実装した公開挙動に対する代表実行証拠が見えない。",
        remediation="単体試験だけでなく、代表 CLI/API/MCP 実行、smoke test、出力契約確認、または未実行理由を記録する。",
    ),
    Rule(
        id="finish.validation.acceptance_evidence_missing",
        discipline="requirements_engineering",
        phase="finish_check",
        engineering_basis=(
            "ISO/IEC/IEEE 29148: requirements validation and acceptance",
            "BABOK: solution validation and acceptance",
            "PMBOK: quality acceptance and value delivery",
        ),
        concern="作業完了が、要求または目的との対応なしに宣言されること。",
        applies_when=(
            "入力が完了報告である。",
            "受入条件、完了条件、目的、証拠の対応が見えない。",
        ),
        does_not_apply_when=(
            "依頼が単純な情報取得で、受入条件が回答本文そのもので満たされる。",
            "証拠欄に要求項目ごとの結果対応がある。",
        ),
        evidence_required=(
            "受入条件",
            "完了条件",
            "要求と証拠の対応",
        ),
        severity_policy=(
            SeverityPolicy(mode="strict", severity="major"),
            SeverityPolicy(mode="relaxed", severity="minor"),
        ),
        finding="受入条件と証拠の対応が薄い。",
        remediation="要求または目的に対して、何をもって完了としたかを明記する。",
    ),
)

RULES_BY_ID: dict[str, Rule] = {rule.id: rule for rule in RULES}


def get_rule(rule_id: str) -> Rule:
    return RULES_BY_ID[rule_id]


def rules_for_phase(phase: Phase) -> tuple[Rule, ...]:
    return tuple(rule for rule in RULES if rule.phase == phase)


def rules_for_discipline(discipline: Discipline) -> tuple[Rule, ...]:
    return tuple(rule for rule in RULES if rule.discipline == discipline)
