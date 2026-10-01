from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

from semantic_guard_workflow.models import Finding
from semantic_guard_workflow.result_builder import build_result, score_from_findings
from semantic_guard_workflow.text_utils import compact_snippet

SCHEMA_VERSION = "artifact-membership-audit/v0"
CONTRACT_SCHEMA_VERSION = "artifact-membership-contract/v0"
NOTATION_PROFILE = "entity-reference-notation/v0"

MEMBERSHIP_STATUSES = ("belongs", "does_not_belong", "mixed", "unknown")
TARGET_ROLES = ("body", "appendix", "audit_bundle", "none", "undecided")
DISPOSITIONS = (
    "retain_direct",
    "retain_transformed",
    "relocate_to_appendix",
    "relocate_to_audit_bundle",
    "exclude_from_artifact",
    "hold_for_human_review",
)

DISPOSITION_TARGET_ROLES: dict[str, tuple[str, ...]] = {
    "retain_direct": ("body",),
    "retain_transformed": ("body",),
    "relocate_to_appendix": ("appendix",),
    "relocate_to_audit_bundle": ("audit_bundle",),
    "exclude_from_artifact": ("none",),
    "hold_for_human_review": ("undecided",),
}

RULE_IDS = (
    "artifact.membership.contract_missing",
    "artifact.membership.contract_conflict",
    "artifact.membership.required_element_missing",
    "artifact.membership.non_exportable_context",
    "artifact.membership.prohibited_content",
    "artifact.membership.production_residue",
    "artifact.membership.production_guidance",
    "artifact.membership.audit_material_in_body",
    "artifact.membership.supplemental_detail",
    "artifact.membership.unresolved",
)

_BASIS = ["semantic-implementation", "artifact-membership-audit/v0"]

# Conditional operating contracts describe durable behavior, not an observed delivery state.
_RUNTIME_DELIVERY_CONDITION = r"(?:(?:場合|とき|際)(?:は|に|、|,|\s)|\b(?:if|when)\b)"

_SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "conversation_dependency": (
        r"\b(?:as|per)\s+(?:(?:you|the user)\s+)?requested\b",
        r"\b(?:the\s+)?user\s+(?:asked|wanted|requested|told)\b",
        r"\b(?:prompt|conversation|chat|earlier message|previous response)\b",
        r"^\s*(?:そうだね|そうですね)(?:[、。,.!?！？]|\s|$)",
        (
            r"(?:前に|以前|前回)(?:も)?"
            r"(?:話した|話していた|述べた|確認した)(?:とおり|通り)"
        ),
        (
            r"(?:その|この)(?:方針|方向性|進め方)で"
            r"(?:進める|進めます|進めていく|進めていきます)"
        ),
        (
            r"(?:こっち|こちら)で"
            r"(?:確認した|確認してみた|調べた|検証した)(?:感じ|ところ)"
        ),
        r"(?:依頼|指示)(?:どおり|通り|に従)",
        r"(?:ユーザー|利用者|アナタ|あなた)が(?:望|求|言|指摘)",
        r"(?:会話中|前の回答|前回の回答|先ほど|さっき)",
    ),
    "runtime_delivery_context": (
        (
            rf"^(?!.*{_RUNTIME_DELIVERY_CONDITION})"
            r"(?=.{0,320}(?:実行環境|指定(?:出力|保存)?先|(?:出力|保存)先|"
            r"読み取り専用|読取り専用|読取専用|(?:書き?込み?|権限)制約))"
            r"(?=.{0,320}(?:保存|書き?込み?|上書き))"
            r"(?=.{0,320}(?:"
            r"拒否され(?:、|て(?:いる|いた)|た(?:[。、「『]|$)|ました)"
            r"|未保存(?:である|です|[。、]|$)"
            r"|未実施(?:だった|である|です|[。、]|$)"
            r"|未完了(?:だった|である|です|[。、]|$)"
            r"|(?:保存|書き?込み?)(?:が|は)?不能(?:[。、]|$)"
            r"|できなかった|できませんでした|行えなかった|実施できなかった))"
            r".*$"
        ),
        (
            rf"^(?!.*{_RUNTIME_DELIVERY_CONDITION})"
            r"(?=.{0,320}(?:この|本)(?:応答|回答|チャット|会話))"
            r"(?=.{0,320}(?:Markdown)?(?:本文|成果物|内容|生成成果))"
            r"(?=.{0,320}(?:保持|記載|掲載|載せ|返|提示|置|生成成果))"
            r".*$"
        ),
    ),
    "corrective_history": (
        r"\b(?:unlike|compared with)\s+(?:the\s+)?previous\s+version\b",
        r"\b(?:based on|in response to)\s+(?:your|the)\s+feedback\b",
        r"\bI\s+(?:fixed|changed|added|removed|rewrote)\b",
        r"(?:前版|旧版|前回)(?:と異な|から変)",
        r"(?:指摘|フィードバック)(?:を受け|に合わせ|に従)",
        r"(?:直した|修正した|追加した|削除した)",
    ),
    "production_guidance": (
        r"\b(?:written|rewritten|formatted)\s+(?:for|to be)\b",
        r"\b(?:natural|friendly|concise|beginner-friendly)\s+tone\b",
        r"\b(?:avoid|avoiding)\s+jargon\b",
        r"(?:初心者向け|自然な口調|簡潔な文体|専門用語を避け)",
        r"(?:この文書|この節|本文)(?:を|は).{0,24}(?:書いた|構成した|整えた)",
    ),
    "incidental_scaffolding": (
        r"\b(?:TODO|TBD|FIXME|placeholder|insert here|draft note)\b",
        r"(?:仮置き|下書き|ここに挿入|あとで書く|後で書く|例示用)",
    ),
    "audit_evidence": (
        r"\b(?:audit evidence|verification evidence|test results?|tool choice|implementation constraint|reasoning trace)\b",
        r"\b(?:unittest|pytest)\b.{0,48}\b(?:pass|passed|ok|failed)\b",
        r"(?:監査証拠|検証証拠|試験結果|テスト結果|実行コマンド|工具選択|実装制約|推論過程)",
    ),
    "supplemental_detail": (
        r"\b(?:supplemental material|background detail|appendix candidate|migration table)\b",
        r"(?:補足資料|詳細な背景|参考資料|付録候補|移行対応表)",
    ),
    "safety_or_legal": (
        r"\b(?:must|shall|required|warning|caution|safety|legal|compliance|privacy)\b",
        r"\b(?:credential|secret|token)s?\b.{0,48}\b(?:must not|never|do not|redact|withhold)\b",
        r"\b(?:must not|never|do not|redact|withhold)\b.{0,48}\b(?:credential|secret|token)s?\b",
        r"(?:必須|警告|危険|安全|法令|法的|規制|準拠|免責|してはならない|含めない)",
        r"(?:秘密|資格情報|トークン|個人情報).{0,24}(?:禁止|伏せ|秘匿|出力しない|含めない)",
    ),
    "reproducibility": (
        r"\b(?:reproduce|reproducibility|checksum|sha256|version pin|execution steps)\b",
        r"(?:再現|再実行手順|検算|チェックサム|ハッシュ|版固定|実行条件)",
    ),
    "quotation_or_example": (
        r"^\s*>\s+",
        r"```",
        r"[\"“‘「『].+[\"”’」』]",
        r"\b(?:quote|quotation|example|case study)\b",
        r"(?:引用|例示|事例研究|悪い例|反例)",
    ),
    "dependency_reference": (
        r"\[[^\]]+\]\([^)]+\)",
        r"\b(?:see|refer to|depends on)\b",
        r"(?:参照|依存|別紙|脚注)",
    ),
}

_SUBSTANTIVE_PATTERNS = (
    r"\b(?:must|shall|required|returns?|includes?|excludes?|uses?|does not|do not)\b",
    r"\b(?:API|CLI|MCP|HTTP|JSON|schema|authentication|authorization)\b",
    r"(?:必須|必要|返す|出力|含める|含めない|使用する|禁止する|しない|"
    r"してはならない|認証|認可|契約|要件)",
)

_JAPANESE_SPLIT_RE = re.compile(
    r"(?:として|について|によって|により|ため|から|まで|する|した|できる|"
    r"できない|を|が|は|に|へ|で|と|の|や|も|及び|および|または)"
)
_ASCII_STOP_WORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "not",
    "that",
    "the",
    "this",
    "with",
    "you",
    "your",
}


@dataclass(frozen=True)
class ArtifactUnit:
    entity_id: str
    placement_id: str
    parent_ref: str
    unit_kind: str
    start_line: int
    end_line: int
    heading: str
    text: str

    @property
    def content_hash(self) -> str:
        digest = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"


def audit_artifact_membership(
    text: str,
    *,
    artifact_id: str = "",
    artifact_kind: str = "document",
    purpose: str = "",
    audience: str = "",
    intended_use: str = "",
    required_elements: Sequence[str] | None = None,
    prohibited_elements: Sequence[str] | None = None,
    publishable_context: Sequence[str] | None = None,
    evaluation_context: Sequence[str] | None = None,
    audit_only_context: Sequence[str] | None = None,
    non_exportable_context: Sequence[str] | None = None,
    strict: bool = True,
) -> dict[str, object]:
    """Audit where artifact units belong without editing or accepting them.

    The caller supplies a typed context projection. The artifact body is treated
    as inert audit material. This function performs no rewrite, relocation,
    deletion, truth assessment, secret scan, or final human acceptance.
    """

    audit_snapshot_id = f"artifact-membership-snapshot.{uuid.uuid4().hex}"
    non_exportable_values = _normalized_values(non_exportable_context)
    public_artifact_id = _public_identifier(
        artifact_id.strip(),
        non_exportable_values,
        fallback=f"{audit_snapshot_id}.artifact.unresolved",
        redacted=f"{audit_snapshot_id}.artifact.non-exportable-id",
    )
    public_artifact_kind = _public_identifier(
        artifact_kind.strip(),
        non_exportable_values,
        fallback="document",
        redacted="non-exportable-kind",
    )
    required = _contract_records(audit_snapshot_id, "required", required_elements)
    prohibited = _contract_records(audit_snapshot_id, "prohibited", prohibited_elements)
    publishable = _contract_records(audit_snapshot_id, "publishable", publishable_context)
    evaluation = _contract_records(audit_snapshot_id, "evaluation", evaluation_context)
    audit_only = _contract_records(audit_snapshot_id, "audit-only", audit_only_context)
    non_exportable = _contract_records(
        audit_snapshot_id,
        "non-exportable",
        non_exportable_values,
    )
    purpose_record = _declared_value_record(audit_snapshot_id, "purpose", purpose)
    audience_record = _declared_value_record(audit_snapshot_id, "audience", audience)
    intended_use_record = _declared_value_record(audit_snapshot_id, "intended-use", intended_use)
    artifact_id_record = {
        "entity_id": f"{audit_snapshot_id}.contract.artifact-id",
        "value": artifact_id.strip(),
    }
    artifact_kind_record = {
        "entity_id": f"{audit_snapshot_id}.contract.artifact-kind",
        "value": artifact_kind.strip(),
    }
    identifier_records = [artifact_id_record, artifact_kind_record]
    units = _segment_artifact(text, audit_snapshot_id) if text.strip() else []
    unit_text_projection_records = [
        {
            "entity_id": unit.entity_id,
            "projection_kind": "unit_text",
            "value": unit.text,
        }
        for unit in units
    ]
    unit_hash_projection_records = [
        {
            "entity_id": unit.entity_id,
            "projection_kind": "unit_content_hash",
            "value": unit.content_hash,
        }
        for unit in units
    ]
    public_projection_records = (
        identifier_records
        + [purpose_record, audience_record, intended_use_record]
        + required
        + prohibited
        + publishable
        + evaluation
        + audit_only
        + unit_text_projection_records
        + unit_hash_projection_records
    )
    projection_taint_map = _non_exportable_projection_taints(
        public_projection_records,
        non_exportable,
    )
    projection_tainted_ids = set(projection_taint_map)
    if str(artifact_id_record["entity_id"]) in projection_tainted_ids:
        public_artifact_id = f"{audit_snapshot_id}.artifact.non-exportable-id"
    if str(artifact_kind_record["entity_id"]) in projection_tainted_ids:
        public_artifact_kind = "non-exportable-kind"
    if not artifact_id.strip():
        artifact_identity_status = "unresolved"
    elif public_artifact_id != artifact_id.strip():
        artifact_identity_status = "withheld_non_exportable"
    else:
        artifact_identity_status = "caller_asserted_not_verified"
    contract_fields = {
        "artifact_id": artifact_id.strip(),
        "purpose": purpose.strip(),
        "audience": audience.strip(),
        "intended_use": intended_use.strip(),
    }
    missing = [field for field, value in contract_fields.items() if not value]
    findings: list[Finding] = []

    if not text.strip():
        missing.append("artifact_text")
        findings.append(
            Finding(
                severity="blocker",
                category="membership",
                basis=_BASIS,
                finding="成果物本文が空で、所属を監査できない。",
                suggested_fix="被監査成果物の本文を渡す。",
                rule_id="artifact.membership.contract_missing",
                match_status="missing",
                confidence="high",
            )
        )

    if missing:
        findings.append(
            Finding(
                severity="blocker" if strict else "major",
                category="membership",
                basis=_BASIS,
                finding="成果物所属監査に必要な契約項目が不足している。",
                evidence=", ".join(sorted(set(missing))),
                suggested_fix="artifact_id、purpose、audience、intended_use と成果物本文を明示する。",
                needs_human_decision=True,
                rule_id="artifact.membership.contract_missing",
                match_status="missing",
                confidence="high",
            )
        )

    contract_conflicts = _contract_conflicts(
        required,
        publishable,
        prohibited,
        audit_only,
        non_exportable,
    )
    contract_conflicts.extend(
        _identifier_conflicts(
            artifact_id=artifact_id.strip(),
            artifact_kind=artifact_kind.strip(),
            artifact_id_ref=str(artifact_id_record["entity_id"]),
            artifact_kind_ref=str(artifact_kind_record["entity_id"]),
            non_exportable=non_exportable,
            projection_taint_map=projection_taint_map,
        )
    )
    if contract_conflicts:
        findings.append(
            Finding(
                severity="blocker" if strict else "major",
                category="membership",
                basis=_BASIS,
                finding="保持要求と公開禁止文脈が競合している。監査器は優先順位を推測できない。",
                evidence="; ".join(item["summary"] for item in contract_conflicts[:3]),
                suggested_fix="契約の権威と優先順位を人間が確定し、競合を解消する。",
                needs_human_decision=True,
                rule_id="artifact.membership.contract_conflict",
                match_status="unknown",
                confidence="high",
            )
        )

    contract_ready = not missing and not contract_conflicts
    assessments: list[dict[str, object]] = []
    human_review_points: list[dict[str, object]] = []
    for unit in units:
        assessment = _assess_unit(
            unit,
            artifact_id=public_artifact_id,
            contract_ready=contract_ready,
            required=required,
            prohibited=prohibited,
            publishable=publishable,
            evaluation=evaluation,
            audit_only=audit_only,
            non_exportable=non_exportable,
            split_non_exportable_matches=projection_taint_map.get(
                unit.entity_id,
                [],
            ),
        )
        assessments.append(assessment)
        review_point = _human_review_point(assessment)
        if review_point:
            human_review_points.append(review_point)
        finding = _finding_for_assessment(assessment)
        if finding is not None:
            findings.append(finding)

    missing_required = _missing_required_elements(text, required)
    for item in missing_required:
        findings.append(
            Finding(
                severity="major",
                category="membership",
                basis=_BASIS,
                finding="成果物契約で保持必須とされた要素が本文に見えない。",
                evidence=_safe_contract_evidence(item, non_exportable, projection_tainted_ids),
                suggested_fix="欠落が意図的かを確認し、必要なら成果物へ戻して再監査する。",
                needs_human_decision=True,
                rule_id="artifact.membership.required_element_missing",
                match_status="missing",
                confidence="high",
            )
        )

    disposition_counts = Counter(str(item["recommended_disposition"]) for item in assessments)
    membership_counts = Counter(str(item["membership_status"]) for item in assessments)
    context_dependency_candidates = [
        item["unit_ref"]
        for item in assessments
        if any(
            reason
            in {
                "conversation_dependency",
                "runtime_delivery_context",
                "corrective_history",
                "production_guidance",
                "evaluation_context_match",
            }
            for reason in item["reason_codes"]
        )
    ]
    non_direct = [
        item
        for item in assessments
        if item["recommended_disposition"] != "retain_direct"
    ]
    if missing_required or not contract_ready:
        standalone_status = "not_supported"
    elif non_direct:
        standalone_status = "not_supported"
    elif assessments:
        standalone_status = "supported_under_declared_contract"
    else:
        standalone_status = "not_assessed"

    contract_status = "incomplete" if missing else "conflicted" if contract_conflicts else "complete"
    details = {
        "schema_version": SCHEMA_VERSION,
        "notation_profile": NOTATION_PROFILE,
        "artifact_contract": {
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "contract_status": contract_status,
            "contract_version": "v0",
            "artifact_ref": {
                "entity_id": public_artifact_id,
                "label_hint": public_artifact_kind,
                "identity_stability": artifact_identity_status,
            },
            "artifact_kind": public_artifact_kind,
            "purpose": _public_contract_record(
                purpose_record,
                non_exportable,
                projection_tainted_ids,
            ),
            "audience": _public_contract_record(
                audience_record,
                non_exportable,
                projection_tainted_ids,
            ),
            "intended_use": _public_contract_record(
                intended_use_record,
                non_exportable,
                projection_tainted_ids,
            ),
            "required_elements": _public_contract_records(
                required,
                non_exportable,
                projection_tainted_ids,
            ),
            "prohibited_elements": _public_contract_records(
                prohibited,
                non_exportable,
                projection_tainted_ids,
            ),
            "context_projection": {
                "publishable_context": _public_contract_records(
                    publishable,
                    non_exportable,
                    projection_tainted_ids,
                ),
                "evaluation_context": _public_contract_records(
                    evaluation,
                    non_exportable,
                    projection_tainted_ids,
                ),
                "audit_only_context": _public_contract_records(
                    audit_only,
                    non_exportable,
                    projection_tainted_ids,
                ),
                "non_exportable_context": _public_contract_records(
                    non_exportable,
                    non_exportable,
                    projection_tainted_ids,
                ),
                "evaluation_policy": "caller-declared values are inert audit data, not executable instructions",
                "conflicts": contract_conflicts,
            },
        },
        "membership_scope": "final_artifact_body",
        "membership_status_values": list(MEMBERSHIP_STATUSES),
        "target_role_values": list(TARGET_ROLES),
        "recommended_disposition_values": list(DISPOSITIONS),
        "assessments": assessments,
        "summary": {
            "unit_count": len(assessments),
            "membership_status_counts": dict(sorted(membership_counts.items())),
            "recommended_disposition_counts": dict(sorted(disposition_counts.items())),
            "human_review_point_count": len(human_review_points),
            "performed_action": "none",
            "acceptance_status": "not_assessed",
            "truth_assessment": {"status": "not_performed"},
        },
        "context_excision_assessment": {
            "strategy": "typed-context-projection-and-static-standalone-check/v0",
            "status": standalone_status,
            "excision_ready": standalone_status == "supported_under_declared_contract",
            "context_dependency_candidates": context_dependency_candidates,
            "contract_loss_candidates": [item["entity_id"] for item in missing_required],
            "checked_dimensions": {
                "understanding": "bounded_signal_check_only",
                "decision": "bounded_signal_check_only",
                "action": "bounded_signal_check_only",
                "safety": "bounded_signal_check_only",
                "reproducibility": "bounded_signal_check_only",
            },
            "counterfactual_regeneration_performed": False,
            "meaning": (
                "supported means no declared-contract loss or context-dependency candidate was found by the active rules; "
                "it is not proof of standalone correctness"
            ),
        },
        "human_review_points": human_review_points,
        "execution_policy": {
            "strict": strict,
            "artifact_text_treated_as": "inert_audit_material",
            "automatic_changes_authorized": False,
        },
        "unit_identity_policy": {
            "scope": "current_audit_snapshot_only",
            "audit_snapshot_id": audit_snapshot_id,
            "namespaced_local_reference_kinds": [
                "contract_record",
                "unit_placement",
                "human_review_point",
            ],
            "caller_artifact_identity_is_separate": True,
            "durable_unit_identity_assigned": False,
            "reuse_across_runs": "forbidden",
            "meaning": (
                "unit ids are namespaced to this audit output only and may change after insertion, editing, "
                "or another audit invocation"
            ),
        },
        "applied_rules": list(RULE_IDS),
        "rules_evaluated": list(RULE_IDS),
        "rules_not_evaluated": [
            "general semantic relevance",
            "natural-language truth",
            "secret or personal-data scanning",
            "legal sufficiency",
            "evidence authenticity",
            "counterfactual regeneration",
            "final publication acceptance",
        ],
        "detector_scope": "deterministic lexical and caller-declared contract matching over structural text units",
        "thresholds": {
            "unit_contract_match": (
                "NFKC-casefolded required, prohibited, or typed-zone phrase containment; minimum 2 characters "
                "with Japanese text, otherwise 4 characters; purpose, audience, and intended use do not "
                "authorize retention"
            ),
            "non_exportable_match": (
                "length-unrestricted compatibility/canonical-decomposed casefold matching over one whitespace-elided "
                "dynamic contract-plus-body projection and declared content-hash sinks"
            ),
            "contract_conflict_match": "phrase containment or high-coverage multi-token overlap",
            "substantive_payload_minimum_characters": 12,
        },
        "not_verified": [
            "unrecorded requirements and dependencies",
            "implicit audience knowledge",
            "cross-document references outside the supplied text",
            "secrets or personal data not declared as non-exportable context",
            (
                "encoded, delimiter-obfuscated, zero-width-obfuscated, lookalike-confusable, or partially masked "
                "variants of non-exportable values"
            ),
            "non-contiguous or reverse-order reconstruction of non-exportable fragments",
            (
                "coincidental equality between a declared non-exportable value and fixed or generated audit protocol "
                "metadata other than content hashes"
            ),
            "downstream editor compliance",
            "stability or uniqueness of the caller-declared artifact id",
        ],
        "limitations": [
            "No finding does not mean no production residue exists.",
            "A disposition is non-binding audit material and is not an edit command.",
            "Content equality, placement identity, and artifact identity are separate.",
            "Strict mode increases contract blockers; it never authorizes automatic exclusion.",
            (
                "Non-exportable withholding prevents contiguous source-derived reproduction and declared content-hash "
                "collisions; it cannot remove other fixed or generated protocol metadata that coincidentally equals a "
                "declared value."
            ),
        ],
        "non_decisions": [
            "does not rewrite, move, redact, or delete artifact content",
            "does not assess truth",
            "does not approve publication",
            "does not decide final human acceptance",
        ],
        "score_semantics": "score reflects emitted finding severity only, not membership accuracy or publication readiness",
    }
    return build_result(
        phase="audit_artifact_membership",
        findings=findings,
        missing=sorted(set(missing + ["required_element:" + str(item["entity_id"]) for item in missing_required])),
        score=score_from_findings(findings),
        details=details,
        next_actions=_next_actions(assessments, missing_required, contract_status),
    )


def _segment_artifact(text: str, audit_snapshot_id: str) -> list[ArtifactUnit]:
    lines = text.splitlines()
    raw_units: list[tuple[int, int, str, int, str, str]] = []
    heading = ""
    heading_line = 0
    pending_heading_line = 0
    buffer: list[tuple[int, str]] = []
    in_fence = False

    def flush(*, preserve_heading_only: bool = True) -> None:
        nonlocal buffer, pending_heading_line
        body = "\n".join(line for _, line in buffer).strip()
        content = body
        start_line = buffer[0][0] if buffer else pending_heading_line
        end_line = buffer[-1][0] if buffer else pending_heading_line
        if pending_heading_line and body:
            content = f"{lines[pending_heading_line - 1]}\n{body}"
            start_line = pending_heading_line
        elif pending_heading_line and preserve_heading_only:
            content = lines[pending_heading_line - 1].strip()
        if content:
            kind = _unit_kind(body, has_pending_heading=bool(pending_heading_line))
            raw_units.append((start_line, end_line, heading, heading_line, content, kind))
        buffer = []
        pending_heading_line = 0

    for line_number, line in enumerate(lines, start=1):
        heading_match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
        if heading_match and not in_fence:
            flush()
            heading = heading_match.group(1).strip()
            heading_line = line_number
            pending_heading_line = line_number
            continue
        if not line.strip() and not in_fence:
            if buffer:
                flush()
            continue
        buffer.append((line_number, line))
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
    flush()

    units: list[ArtifactUnit] = []
    for index, (start, end, unit_heading, section_heading_line, content, kind) in enumerate(raw_units, start=1):
        unit_id = f"{audit_snapshot_id}.unit.{index:04d}"
        placement_id = f"{audit_snapshot_id}.placement.body.lines-{start}-{end}"
        parent_ref = (
            f"{audit_snapshot_id}.section.line-{section_heading_line}"
            if unit_heading and section_heading_line
            else ""
        )
        units.append(
            ArtifactUnit(
                entity_id=unit_id,
                placement_id=placement_id,
                parent_ref=parent_ref,
                unit_kind=kind,
                start_line=start,
                end_line=end,
                heading=unit_heading,
                text=content,
            )
        )
    return units


def _unit_kind(body: str, *, has_pending_heading: bool) -> str:
    stripped = body.lstrip()
    if stripped.startswith("```"):
        return "code_block"
    if re.match(r"^\[\^[^\]]+\]:", stripped):
        return "footnote"
    nonempty_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(nonempty_lines) >= 2 and all("|" in line for line in nonempty_lines[:2]):
        return "table"
    if re.match(r"^(?:[-*+] |\d+[.)] )", stripped):
        return "list_block"
    if has_pending_heading:
        return "section_block"
    return "paragraph"


def _assess_unit(
    unit: ArtifactUnit,
    *,
    artifact_id: str,
    contract_ready: bool,
    required: list[dict[str, object]],
    prohibited: list[dict[str, object]],
    publishable: list[dict[str, object]],
    evaluation: list[dict[str, object]],
    audit_only: list[dict[str, object]],
    non_exportable: list[dict[str, object]],
    split_non_exportable_matches: list[dict[str, object]],
) -> dict[str, object]:
    required_matches = _matching_records(unit.text, required)
    prohibited_matches = _matching_records(unit.text, prohibited)
    publishable_matches = _matching_records(unit.text, publishable)
    evaluation_matches = _matching_records(unit.text, evaluation)
    audit_only_matches = _matching_records(unit.text, audit_only)
    local_non_exportable_matches = _matching_non_exportable_records(unit.text, non_exportable)
    derived_non_exportable_matches = _matching_non_exportable_records(
        unit.content_hash,
        non_exportable,
    )
    non_exportable_matches = _merge_records(
        local_non_exportable_matches,
        derived_non_exportable_matches,
        split_non_exportable_matches,
    )
    directly_accounted_non_exportable_ids = {
        str(item.get("entity_id", ""))
        for item in local_non_exportable_matches + derived_non_exportable_matches
    }
    split_variant_detected = any(
        str(item.get("entity_id", "")) not in directly_accounted_non_exportable_ids
        for item in split_non_exportable_matches
    )
    signals = [name for name in _SIGNAL_PATTERNS if _has_signal(unit.text, name)]
    signal_set = set(signals)
    retention_required = bool(
        required_matches
        or publishable_matches
        or signal_set.intersection({"safety_or_legal", "reproducibility", "quotation_or_example", "dependency_reference"})
    )
    explicit_body_prohibition = bool(prohibited_matches)
    residue = bool(
        signal_set.intersection(
            {
                "conversation_dependency",
                "runtime_delivery_context",
                "corrective_history",
                "production_guidance",
                "incidental_scaffolding",
            }
        )
    )
    substantive_payload = _has_substantive_payload(unit.text)
    material_beyond_non_exportable = bool(non_exportable_matches) and _has_material_beyond_non_exportable(
        unit.text,
        local_non_exportable_matches,
    )

    reason_codes: list[str] = []
    reason_codes.extend(signals)
    if required_matches:
        reason_codes.append("required_element_match")
    if prohibited_matches:
        reason_codes.append("prohibited_element_match")
    if publishable_matches:
        reason_codes.append("publishable_context_match")
    if evaluation_matches:
        reason_codes.append("evaluation_context_match")
    if audit_only_matches:
        reason_codes.append("audit_only_context_match")
    if non_exportable_matches:
        reason_codes.append("non_exportable_context_match")
    if derived_non_exportable_matches:
        reason_codes.append("non_exportable_derived_output_match")
    if split_variant_detected:
        reason_codes.append("non_exportable_split_variant_match")
    if substantive_payload:
        reason_codes.append("substantive_payload")

    ambiguity_reasons: list[str] = []
    if not contract_ready:
        status, target, disposition, confidence = "unknown", "undecided", "hold_for_human_review", "high"
        ambiguity_reasons.append("artifact_contract_not_ready")
    elif non_exportable_matches and retention_required:
        status, target, disposition, confidence = "unknown", "undecided", "hold_for_human_review", "high"
        ambiguity_reasons.append("non_exportable_content_has_retention_countercondition")
    elif non_exportable_matches and material_beyond_non_exportable:
        status, target, disposition, confidence = "mixed", "body", "retain_transformed", "high"
        ambiguity_reasons.append("non_exportable_value_mixed_with_potentially_retainable_content")
    elif non_exportable_matches:
        status, target, disposition, confidence = "does_not_belong", "none", "exclude_from_artifact", "high"
    elif audit_only_matches:
        status, target, disposition, confidence = "does_not_belong", "audit_bundle", "relocate_to_audit_bundle", "high"
    elif explicit_body_prohibition and retention_required:
        status, target, disposition, confidence = "unknown", "undecided", "hold_for_human_review", "high"
        ambiguity_reasons.append("retention_and_prohibition_conflict")
    elif prohibited_matches:
        status, target, disposition, confidence = "does_not_belong", "none", "exclude_from_artifact", "high"
    elif evaluation_matches and not required_matches and not publishable_matches:
        status, target, disposition, confidence = "unknown", "undecided", "hold_for_human_review", "high"
        ambiguity_reasons.append("evaluation_context_is_not_publication_authority")
    elif "audit_evidence" in signal_set and not publishable_matches and not required_matches:
        status, target, disposition, confidence = "does_not_belong", "audit_bundle", "relocate_to_audit_bundle", "medium"
    elif residue and "quotation_or_example" in signal_set and not publishable_matches and not required_matches:
        status, target, disposition, confidence = "unknown", "undecided", "hold_for_human_review", "medium"
        ambiguity_reasons.append("residue_like_text_may_be_quoted_evidence")
    elif residue and (retention_required or substantive_payload):
        status, target, disposition, confidence = "mixed", "body", "retain_transformed", "medium"
    elif residue:
        status, target, disposition, confidence = "does_not_belong", "none", "exclude_from_artifact", "medium"
    elif "supplemental_detail" in signal_set and not required_matches:
        status, target, disposition, confidence = "belongs", "appendix", "relocate_to_appendix", "medium"
    elif required_matches or publishable_matches:
        status, target, disposition, confidence = "belongs", "body", "retain_direct", "high"
    elif signal_set.intersection({"safety_or_legal", "reproducibility", "dependency_reference", "quotation_or_example"}):
        status, target, disposition, confidence = "unknown", "undecided", "hold_for_human_review", "medium"
        ambiguity_reasons.append("retention_countercondition_without_contract_match")
    else:
        status, target, disposition, confidence = "unknown", "undecided", "hold_for_human_review", "low"
        ambiguity_reasons.append("insufficient_membership_evidence")
        reason_codes.append("insufficient_membership_evidence")

    needs_human = status in {"mixed", "unknown"} or disposition in {
        "retain_transformed",
        "exclude_from_artifact",
        "relocate_to_appendix",
        "relocate_to_audit_bundle",
    }
    review_ref = f"human-review.{unit.entity_id}" if needs_human else ""
    counterconditions = {
        "required_element": "matched" if required_matches else "not_matched",
        "dependency_reference": "matched" if "dependency_reference" in signal_set else "not_matched",
        "safety_or_legal": "matched" if "safety_or_legal" in signal_set else "not_matched",
        "reproducibility": "matched" if "reproducibility" in signal_set else "not_matched",
        "quotation_or_example": "matched" if "quotation_or_example" in signal_set else "not_matched",
        "mixed_content": "matched" if status == "mixed" else "not_matched",
    }
    coverage_impact = {
        "understanding": "material_candidate" if required_matches or publishable_matches else "unknown",
        "decision": "material_candidate" if required_matches else "unknown",
        "action": "material_candidate" if required_matches or "reproducibility" in signal_set else "unknown",
        "safety": "material_candidate" if "safety_or_legal" in signal_set else "unknown",
        "reproducibility": "material_candidate" if "reproducibility" in signal_set else "unknown",
    }
    if disposition == "exclude_from_artifact" and not retention_required:
        loss_if_applied = "No declared retention countercondition was matched; unrecorded value remains possible."
    elif disposition == "retain_transformed":
        loss_if_applied = "Removing the whole unit could discard substantive content or a retention countercondition."
    elif disposition.startswith("relocate_"):
        loss_if_applied = "Deleting instead of relocating could discard supporting or audit material."
    elif disposition == "hold_for_human_review":
        loss_if_applied = "Membership evidence is insufficient or conflicted; applying a change could discard required meaning."
    else:
        loss_if_applied = "Removing this unit could discard content matched to the declared artifact contract."

    non_exportable_match = bool(non_exportable_matches)
    safe_excerpt = "[non-exportable matched content omitted]" if non_exportable_match else compact_snippet(unit.text, 220)
    unit_ref = {
        "notation_profile": NOTATION_PROFILE,
        "artifact_ref": {"entity_id": artifact_id, "label_hint": "artifact"},
        "entity_id": unit.entity_id,
        "unit_instance_id": unit.entity_id,
        "identity_scope": "current_audit_snapshot_only",
        "durable_identity": "not_assigned",
        "label_hint": "[non-exportable matched content omitted]" if non_exportable_match else compact_snippet(unit.text, 80),
        "unit_kind": unit.unit_kind,
        "placement": {
            "placement_id": unit.placement_id,
            "role": "body",
            "path": f"lines:{unit.start_line}-{unit.end_line}",
            "parent_ref": unit.parent_ref,
        },
        "source_range": {"start_line": unit.start_line, "end_line": unit.end_line},
        "content_hash": None if non_exportable_match else unit.content_hash,
        "content_hash_status": "withheld_non_exportable" if non_exportable_match else "available",
    }
    return {
        "finding_id": f"finding.{unit.entity_id}",
        "unit_ref": unit_ref,
        "excerpt": safe_excerpt,
        "membership_scope": "final_artifact_body",
        "membership_status": status,
        "target_role": target,
        "recommended_disposition": disposition,
        "performed_action": "none",
        "required_element_refs": [item["entity_id"] for item in required_matches],
        "context_refs": [
            item["entity_id"]
            for item in publishable_matches + evaluation_matches + audit_only_matches + non_exportable_matches
        ],
        "prohibited_element_refs": [item["entity_id"] for item in prohibited_matches],
        "counterconditions_checked": counterconditions,
        "coverage_impact": coverage_impact,
        "loss_if_applied": loss_if_applied,
        "truth_assessment": {"status": "not_performed"},
        "evidence_support_status": (
            "conflicted"
            if ambiguity_reasons
            and (explicit_body_prohibition or bool(non_exportable_matches))
            else "present"
            if reason_codes
            else "absent"
        ),
        "match_status": "matched" if confidence == "high" else "partial" if confidence == "medium" else "unknown",
        "confidence": confidence,
        "ambiguity_reasons": ambiguity_reasons,
        "reason_codes": _unique(reason_codes),
        "basis": _BASIS,
        "human_review_point_ref": review_ref,
        "acceptance_status": "not_assessed",
    }


def _finding_for_assessment(assessment: dict[str, object]) -> Finding | None:
    disposition = str(assessment["recommended_disposition"])
    if disposition == "retain_direct":
        return None
    excerpt = str(assessment["excerpt"])
    reasons = set(str(item) for item in assessment["reason_codes"])
    if disposition == "exclude_from_artifact":
        if "non_exportable_context_match" in reasons:
            rule_id = "artifact.membership.non_exportable_context"
        elif "prohibited_element_match" in reasons:
            rule_id = "artifact.membership.prohibited_content"
        else:
            rule_id = "artifact.membership.production_residue"
        message = "成果物本文に所属しない候補がある。"
        fix = "人間が反条件と損失を確認し、後続編集器で排除してから再監査する。"
        severity = "major"
    elif disposition == "retain_transformed":
        rule_id = "artifact.membership.production_guidance"
        message = "必要内容と制作文脈が同じ単位に混在している。"
        fix = "意味または制約を保持し、制作事情への言及だけを後続編集器で改稿して再監査する。"
        severity = "minor"
    elif disposition == "relocate_to_audit_bundle":
        rule_id = "artifact.membership.audit_material_in_body"
        message = "最終本文ではなく監査束へ所属する候補がある。"
        fix = "削除せず監査束へ移す判断材料として扱い、本文と監査証拠を分離する。"
        severity = "minor"
    elif disposition == "relocate_to_appendix":
        rule_id = "artifact.membership.supplemental_detail"
        message = "本文より付録へ所属する補足候補がある。"
        fix = "読者への必要性を確認し、付録へ移すか本文に残すかを人間が決める。"
        severity = "minor"
    else:
        rule_id = (
            "artifact.membership.contract_conflict"
            if assessment["evidence_support_status"] == "conflicted"
            else "artifact.membership.unresolved"
        )
        message = "成果物への所属を現在の契約と規則だけでは確定できない。"
        fix = "必要な文脈、依存、権威、損失を補い、人間判断後に再監査する。"
        severity = "minor"
    return Finding(
        severity=severity,
        category="membership",
        basis=_BASIS,
        finding=message,
        evidence=excerpt,
        suggested_fix=fix,
        needs_human_decision=True,
        warning_class="possible false positive" if disposition == "hold_for_human_review" else "actionable",
        rule_id=rule_id,
        match_status=str(assessment["match_status"]),
        confidence=str(assessment["confidence"]),
        ambiguity_reasons=[str(item) for item in assessment["ambiguity_reasons"]],
        semantic_boundaries=[
            "membership is separate from truth and importance",
            "recommended disposition is separate from performed action",
            "human acceptance remains pending",
        ],
    )


def _human_review_point(assessment: dict[str, object]) -> dict[str, object] | None:
    ref = str(assessment["human_review_point_ref"])
    if not ref:
        return None
    return {
        "entity_id": ref,
        "unit_ref": assessment["unit_ref"],
        "question": "Which disposition and resulting artifact role should a human record for this unit?",
        "why_it_matters": str(assessment["loss_if_applied"]),
        "disposition_options": [
            "retain_direct",
            "retain_transformed",
            "relocate_to_appendix",
            "relocate_to_audit_bundle",
            "exclude_from_artifact",
            "hold_for_human_review",
        ],
        "target_role_options": ["body", "appendix", "audit_bundle", "none", "undecided"],
        "allowed_outcomes": [
            {
                "disposition": disposition,
                "target_roles": list(target_roles),
            }
            for disposition, target_roles in DISPOSITION_TARGET_ROLES.items()
        ],
        "owner": "human",
        "needed_for": "artifact finalization",
        "blocking_status": "blocking_for_automatic_change",
        "next_action": (
            "Review evidence, counterconditions, and loss_if_applied; then record an allowed disposition and target-role pair."
        ),
        "review_at": None,
        "acceptance_status": "pending",
    }


def _contract_records(snapshot_namespace: str, kind: str, values: Sequence[str] | None) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, value in enumerate(_normalized_values(values), start=1):
        records.append(
            {
                "entity_id": f"{snapshot_namespace}.contract.{kind}.{index:03d}",
                "label": value,
                "value": value,
                "source": "caller",
                "authority": "caller_declared",
                "certainty": "declared",
                "precedence": "conflict_requires_human_review",
                "evidence_ref": "caller_input",
            }
        )
    return records


def _declared_value_record(snapshot_namespace: str, kind: str, value: str) -> dict[str, object]:
    return {
        "entity_id": f"{snapshot_namespace}.contract.{kind}",
        "value": value.strip(),
        "source": "caller",
        "authority": "caller_declared",
        "certainty": "declared" if value.strip() else "missing",
        "precedence": "conflict_requires_human_review",
        "evidence_ref": "caller_input",
    }


def _non_exportable_projection_taints(
    records: list[dict[str, object]],
    non_exportable: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Map whitespace-elided sensitive matches to dynamic source records.

    The ordered projection deliberately excludes fixed result keys, enum values,
    and messages. Those are protocol vocabulary, not caller-derived source data.
    """

    if not non_exportable:
        return {}

    projection_chars: list[str] = []
    record_ids_by_char: list[str] = []
    for record in records:
        entity_id = str(record.get("entity_id", ""))
        for character in str(record.get("value", "")):
            projection_chars.append(character)
            record_ids_by_char.append(entity_id)
    compact_chars, record_ids_by_char = _compact_folded_projection(
        projection_chars,
        record_ids_by_char,
    )
    compact_projection = "".join(compact_chars)
    taint_map: dict[str, list[dict[str, object]]] = {}
    if not compact_projection:
        return taint_map
    for sensitive_record in non_exportable:
        compact_sensitive = _compact_folded(str(sensitive_record.get("value", "")))
        if not compact_sensitive:
            continue
        search_start = 0
        while True:
            match_start = compact_projection.find(compact_sensitive, search_start)
            if match_start < 0:
                break
            match_end = match_start + len(compact_sensitive)
            for record_id in _unique(record_ids_by_char[match_start:match_end]):
                taint_map.setdefault(record_id, []).append(sensitive_record)
            search_start = match_start + 1
    return {
        record_id: _merge_records(matches)
        for record_id, matches in taint_map.items()
    }


def _public_contract_records(
    records: list[dict[str, object]],
    non_exportable: list[dict[str, object]],
    projection_tainted_ids: set[str],
) -> list[dict[str, object]]:
    return [
        _public_contract_record(item, non_exportable, projection_tainted_ids)
        for item in records
    ]


def _public_contract_record(
    record: dict[str, object],
    non_exportable: list[dict[str, object]],
    projection_tainted_ids: set[str],
) -> dict[str, object]:
    value = str(record.get("value", ""))
    sensitive = _contains_non_exportable_value(
        value,
        [str(item.get("value", "")) for item in non_exportable],
    ) or str(record.get("entity_id", "")) in projection_tainted_ids
    public = dict(record)
    if sensitive:
        public["label"] = "[non-exportable value omitted]"
        public["value"] = "[non-exportable value omitted]"
        public["value_exposure"] = "redacted_non_exportable"
    else:
        public["value_exposure"] = "included"
    return public


def _safe_contract_evidence(
    record: dict[str, object],
    non_exportable: list[dict[str, object]],
    projection_tainted_ids: set[str],
) -> str:
    public = _public_contract_record(record, non_exportable, projection_tainted_ids)
    return str(public.get("value", ""))


def _normalized_values(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []
    if isinstance(values, (str, bytes)):
        raise TypeError("contract value collections must be sequences of strings, not a bare string")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError("contract value collections must contain only strings")
        stripped = value.strip()
        if stripped:
            normalized.append(stripped)
    return _unique(normalized)


def _public_identifier(
    value: str,
    non_exportable_values: Sequence[str],
    *,
    fallback: str,
    redacted: str,
) -> str:
    if not value:
        return fallback
    if _contains_non_exportable_value(value, non_exportable_values):
        return redacted
    return value


def _contains_non_exportable_value(value: str, non_exportable_values: Sequence[str]) -> bool:
    return any(_non_exportable_value_matches(value, item) for item in non_exportable_values)


def _contract_conflicts(
    required: list[dict[str, object]],
    publishable: list[dict[str, object]],
    prohibited: list[dict[str, object]],
    audit_only: list[dict[str, object]],
    non_exportable: list[dict[str, object]],
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    conflict_pairs = (
        ("required_vs_prohibited", required, prohibited),
        ("required_vs_audit_only", required, audit_only),
        ("required_vs_non_exportable", required, non_exportable),
        ("publishable_vs_prohibited", publishable, prohibited),
        ("publishable_vs_audit_only", publishable, audit_only),
        ("publishable_vs_non_exportable", publishable, non_exportable),
        ("audit_only_vs_non_exportable", audit_only, non_exportable),
    )
    for conflict_kind, left_records, right_records in conflict_pairs:
        for left in left_records:
            for right in right_records:
                if not _contract_values_conflict(str(left["value"]), str(right["value"])):
                    continue
                conflicts.append(
                    {
                        "kind": conflict_kind,
                        "left_ref": str(left["entity_id"]),
                        "right_ref": str(right["entity_id"]),
                        "summary": f"{left['entity_id']} conflicts with {right['entity_id']}",
                    }
                )
    return conflicts


def _identifier_conflicts(
    *,
    artifact_id: str,
    artifact_kind: str,
    artifact_id_ref: str,
    artifact_kind_ref: str,
    non_exportable: list[dict[str, object]],
    projection_taint_map: dict[str, list[dict[str, object]]],
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    for field, value, entity_ref in (
        ("artifact_id", artifact_id, artifact_id_ref),
        ("artifact_kind", artifact_kind, artifact_kind_ref),
    ):
        matching_sensitive_records = _merge_records(
            _matching_non_exportable_records(value, non_exportable),
            projection_taint_map.get(entity_ref, []),
        )
        if not matching_sensitive_records:
            continue
        for sensitive_record in matching_sensitive_records:
            conflicts.append(
                {
                    "kind": "public_identifier_vs_non_exportable",
                    "left_ref": entity_ref,
                    "right_ref": str(sensitive_record.get("entity_id", "")),
                    "left_path": f"artifact_contract.{field}",
                    "right_zone": "non_exportable_context",
                    "summary": f"{field} conflicts with non-exportable context",
                }
            )
    return conflicts


def _missing_required_elements(text: str, required: list[dict[str, object]]) -> list[dict[str, object]]:
    return [item for item in required if not _record_matches_text(text, str(item["value"]))]


def _matching_records(text: str, records: list[dict[str, object]]) -> list[dict[str, object]]:
    return [item for item in records if _record_matches_text(text, str(item["value"]))]


def _matching_non_exportable_records(
    text: str,
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        item
        for item in records
        if _non_exportable_value_matches(text, str(item["value"]))
    ]


def _non_exportable_value_matches(text: str, value: str) -> bool:
    text_normalized = _normalize_text(text)
    value_normalized = _normalize_text(value)
    return bool(text_normalized and value_normalized and value_normalized in text_normalized)


def _has_material_beyond_non_exportable(
    text: str,
    local_matches: list[dict[str, object]],
) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if not local_matches:
        return True
    remainder = normalized
    sensitive_values = sorted(
        (_normalize_text(str(item.get("value", ""))) for item in local_matches),
        key=len,
        reverse=True,
    )
    for sensitive in sensitive_values:
        if sensitive:
            remainder = remainder.replace(sensitive, " ")
    return any(character.isalnum() for character in remainder)


def _merge_records(*record_groups: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[str] = set()
    for records in record_groups:
        for record in records:
            entity_id = str(record.get("entity_id", ""))
            if entity_id in seen:
                continue
            seen.add(entity_id)
            merged.append(record)
    return merged


def _record_matches_text(text: str, value: str) -> bool:
    text_normalized = _normalize_text(text)
    value_normalized = _normalize_text(value)
    if not text_normalized or not value_normalized:
        return False
    contains_japanese = bool(re.search(r"[一-龯ぁ-んァ-ヶ]", value_normalized))
    minimum_length = 2 if contains_japanese else 4
    if len(value_normalized) < minimum_length:
        return False
    return value_normalized in text_normalized


def _contract_values_conflict(left: str, right: str) -> bool:
    left_normalized = _normalize_text(left)
    right_normalized = _normalize_text(right)
    if not left_normalized or not right_normalized:
        return False
    if right_normalized in left_normalized or left_normalized in right_normalized:
        return True
    left_terms = _anchor_terms(left_normalized)
    right_terms = _anchor_terms(right_normalized)
    shared = left_terms & right_terms
    if len(shared) < 2:
        return False
    return len(shared) / len(left_terms) >= 0.8 and len(shared) / len(right_terms) >= 0.8


def _anchor_terms(text: str) -> set[str]:
    ascii_terms = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.lower())
        if token not in _ASCII_STOP_WORDS
    }
    japanese_terms: set[str] = set()
    for chunk in re.findall(r"[一-龯ぁ-んァ-ヶー]{2,}", text):
        for part in _JAPANESE_SPLIT_RE.split(chunk):
            cleaned = part.strip()
            if 2 <= len(cleaned) <= 24:
                japanese_terms.add(cleaned)
    return ascii_terms | japanese_terms


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", _unicode_fold(text).strip())


def _compact_folded(text: str) -> str:
    characters, _ = _compact_folded_projection(list(text), [""] * len(text))
    return "".join(characters)


def _compact_folded_projection(
    characters: list[str],
    source_ids: list[str],
) -> tuple[list[str], list[str]]:
    """Fold one source projection while preserving every output character's source id."""

    decomposed_characters: list[str] = []
    decomposed_source_ids: list[str] = []
    for character, source_id in zip(characters, source_ids, strict=True):
        for decomposed in unicodedata.normalize("NFKD", character):
            if decomposed.isspace():
                continue
            decomposed_characters.append(decomposed)
            decomposed_source_ids.append(source_id)
    decomposed_characters, decomposed_source_ids = _canonical_order_projection(
        decomposed_characters,
        decomposed_source_ids,
    )

    folded_characters: list[str] = []
    folded_source_ids: list[str] = []
    for character, source_id in zip(decomposed_characters, decomposed_source_ids, strict=True):
        for folded in character.casefold():
            for decomposed in unicodedata.normalize("NFKD", folded):
                if decomposed.isspace():
                    continue
                folded_characters.append(decomposed)
                folded_source_ids.append(source_id)
    return _canonical_order_projection(folded_characters, folded_source_ids)


def _canonical_order_projection(
    characters: list[str],
    source_ids: list[str],
) -> tuple[list[str], list[str]]:
    ordered_characters: list[str] = []
    ordered_source_ids: list[str] = []
    segment: list[tuple[str, str]] = []

    def flush() -> None:
        if not segment:
            return
        if unicodedata.combining(segment[0][0]) == 0:
            starter = segment[0]
            marks = sorted(segment[1:], key=lambda item: unicodedata.combining(item[0]))
            ordered = [starter, *marks]
        else:
            ordered = sorted(segment, key=lambda item: unicodedata.combining(item[0]))
        ordered_characters.extend(character for character, _ in ordered)
        ordered_source_ids.extend(source_id for _, source_id in ordered)
        segment.clear()

    for character, source_id in zip(characters, source_ids, strict=True):
        if unicodedata.combining(character) == 0 and segment:
            flush()
        segment.append((character, source_id))
    flush()
    return ordered_characters, ordered_source_ids


def _unicode_fold(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return unicodedata.normalize("NFKC", folded)


def _has_signal(text: str, name: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in _SIGNAL_PATTERNS[name])


def _has_substantive_payload(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) < 12:
        return False
    return any(re.search(pattern, compact, re.IGNORECASE) for pattern in _SUBSTANTIVE_PATTERNS)


def _next_actions(
    assessments: list[dict[str, object]],
    missing_required: list[dict[str, object]],
    contract_status: str,
) -> list[str]:
    if contract_status != "complete":
        return ["成果物契約の不足または競合を人間が解消してから再監査する。"]
    if missing_required:
        return ["保持必須要素の欠落が意図的かを確認し、必要なら本文へ戻す。"]
    if any(item["recommended_disposition"] == "hold_for_human_review" for item in assessments):
        return ["保留断片の文脈、依存、損失を人間が確認する。"]
    if any(item["recommended_disposition"] != "retain_direct" for item in assessments):
        return ["非拘束の処置勧告を人間が確認し、後続編集後に再監査する。"]
    return []


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
