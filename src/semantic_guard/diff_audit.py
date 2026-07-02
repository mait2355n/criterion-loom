from __future__ import annotations

import re

from semantic_guard.audit_common import BASIS, _blocker, _has_implementation_evidence, _normalize_input_kind, _result, _security_signal
from semantic_guard.models import Finding
from semantic_guard.result_builder import next_actions as _next_actions, score_from_findings as _score_from_findings
from semantic_guard.text_utils import (
    combine as _combine,
    compact_snippet as _compact_snippet,
    excerpt_around as _excerpt_around,
    first_match as _first_match,
    has_any as _has_any,
    unique_nonempty as _unique_nonempty,
)

def audit_diff(diff: str, intent: str = "", context: str = "", strict: bool = True, input_kind: str = "diff-summary") -> dict[str, object]:
    input_kind = _normalize_input_kind(input_kind)
    combined = _combine(diff, intent, context)
    findings: list[Finding] = []
    missing: list[str] = []
    changed_files = _changed_files(diff)

    if not diff.strip():
        findings.append(_blocker("evidence", "差分が空。", "unified diff または変更要約を渡す。", BASIS["implementation"]))
        missing.append("diff")

    if not intent.strip():
        findings.append(
            Finding(
                severity="major",
                category="traceability",
                basis=BASIS["implementation"] + BASIS["requirements"],
                finding="変更意図が渡されていない。",
                suggested_fix="要求または計画を `intent` として渡し、差分との対応を見る。",
            )
        )
        missing.append("intent")

    security_evidence = _security_signal(diff)
    if security_evidence:
        findings.append(
            Finding(
                severity="major",
                category="security",
                basis=BASIS["security"],
                finding="安全性に関わる差分の可能性がある。",
                evidence=security_evidence,
                suggested_fix="入力、出力、認証、認可、秘密、ログ、依存、構成の確認証拠を残す。",
            )
        )

    implementation_signals = _implementation_change_signals(diff, changed_files)
    _add_implementation_findings(implementation_signals, findings, missing, strict)

    source_changed = any(_is_source_file(path) for path in changed_files)
    test_changed = any(_is_test_file(path) for path in changed_files)
    if source_changed and not test_changed:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="quality",
                basis=BASIS["implementation"],
                finding="ソース変更に対する試験差分または確認証拠が見えない。",
                evidence=", ".join(changed_files[:5]),
                suggested_fix="試験を追加・更新するか、不要な理由と実行した確認を finish_check に残す。",
                rule_id="diff.test_obligation.source_without_tests",
            )
        )
        missing.append("test_obligation")

    semantic_boundaries = _semantic_boundaries(diff)
    document_only_boundaries: list[dict[str, object]] = []
    reportable_boundaries: list[dict[str, str]] = []
    if semantic_boundaries:
        for boundary in semantic_boundaries:
            if _is_document_only_boundary(boundary, changed_files):
                document_only_boundaries.append(
                    {
                        **boundary,
                        "emission_status": "document_only",
                        "reason": "docs_only_evidence_language",
                    }
                )
            else:
                reportable_boundaries.append(boundary)

    if reportable_boundaries:
        boundary_names = [boundary["boundary"] for boundary in reportable_boundaries]
        boundary_evidence = _unique_nonempty([str(boundary["evidence"]) for boundary in reportable_boundaries])
        findings.append(
            Finding(
                severity="minor",
                category="meaning",
                basis=BASIS["meaning"],
                finding="名前、表示、識別子、保管、所属、正典に関わる差分の可能性がある。",
                evidence="; ".join(boundary_evidence[:3]),
                suggested_fix=_semantic_boundary_fix(boundary_names),
                warning_class="generic caution",
                semantic_boundaries=boundary_names,
                rule_id="diff.meaning.identity_boundary_change",
            )
        )

    complexity_growth = _complexity_growth_signal(diff)
    if complexity_growth:
        finding = (
            Finding(
                severity="minor",
                category="minimality",
                basis=BASIS["implementation"] + BASIS["minimality"],
                finding="差分で複雑性が増えている可能性がある。",
                evidence=complexity_growth,
                suggested_fix="必要な安全・証跡・失敗処理を残したまま、不要な抽象、分岐、将来対応、新規依存、標準機能の手製実装を削れないか確認する。",
                warning_class="generic caution",
            )
        )
        finding.rule_id = "diff.implementation.complexity_growth"
        findings.append(finding)

    filename_content_scope = _filename_content_scope_signals(diff, changed_files)
    if filename_content_scope:
        findings.append(
            Finding(
                severity="minor",
                category="minimality",
                basis=BASIS["implementation"] + BASIS["minimality"] + BASIS["meaning"],
                finding="ファイル名が示す責務に対して、追加内容が複数の別責務へ広がっている可能性がある。",
                evidence="; ".join(_filename_content_scope_evidence(signal) for signal in filename_content_scope[:3]),
                suggested_fix="ファイルを分ける、ファイル名を広げる、または同居が必要な理由と確認証拠を finish_check に残す。",
                warning_class="generic caution",
                rule_id="diff.implementation.filename_content_overbreadth",
            )
        )
        missing.append("filename_scope_alignment")

    filename_naming_scope = _filename_naming_scope_signals(diff, changed_files, intent, context)
    if filename_naming_scope:
        findings.append(
            Finding(
                severity="minor",
                category="scope",
                basis=BASIS["implementation"] + BASIS["minimality"] + BASIS["meaning"],
                finding="ファイル名による機能範囲管理が弱く、膨張を抑える命名または補助管理線が見えない。",
                evidence="; ".join(_filename_naming_scope_evidence(signal) for signal in filename_naming_scope[:3]),
                suggested_fix="可能なら basename をより具体的な機能範囲へ絞る。main/core など名前で絞りづらい場合は、責務、対象外、同居条件、分割条件を明示する。",
                warning_class="generic caution",
                rule_id="diff.implementation.filename_scope_underspecified",
            )
        )
        missing.append("filename_scope_management")

    if changed_files and not any(_is_doc_file(path) for path in changed_files) and _has_any(intent + context, ["仕様", "README", "docs", "運用", "設定", "migration", "移行"]):
        findings.append(
            Finding(
                severity="minor",
                category="documentation",
                basis=BASIS["implementation"],
                finding="文書更新が必要そうな意図に対して文書差分が見えない。",
                suggested_fix="仕様、README、設定例、移行手順の更新要否を finish_check で明記する。",
            )
        )

    return _result(
        phase="audit_diff",
        findings=findings,
        missing=sorted(set(missing)),
        score=_score_from_findings(findings),
        details={
            "changed_files": changed_files[:50],
            "changed_file_count": len(changed_files),
            "input_kind": input_kind,
            "semantic_boundaries": semantic_boundaries,
            "document_only_boundaries": document_only_boundaries,
            "implementation_signals": implementation_signals,
            "complexity_growth": complexity_growth,
            "filename_content_scope": filename_content_scope,
            "filename_naming_scope": filename_naming_scope,
        },
        next_actions=_next_actions(findings, "差分の根拠、試験、文書、安全確認を補完する。"),
    )


def _implementation_change_signals(diff: str, changed_files: list[str]) -> dict[str, str]:
    change_text = _change_text(diff)
    source_changed = any(_is_source_file(path) for path in changed_files)
    signals: dict[str, str] = {}

    public_contract = _public_contract_signal(change_text, changed_files)
    if public_contract:
        signals["public_contract"] = public_contract

    failure_prone = _failure_prone_operation_signal(change_text)
    if source_changed and failure_prone and not _has_failure_handling_evidence(change_text):
        signals["failure_prone_operation"] = failure_prone

    operational = _operational_change_signal(change_text)
    if source_changed and operational and not _has_observability_evidence(change_text):
        signals["operational_observability"] = operational

    dependency = _dependency_runtime_signal(change_text, changed_files)
    if dependency:
        signals["dependency_runtime"] = dependency

    return signals


def _add_implementation_findings(
    signals: dict[str, str],
    findings: list[Finding],
    missing: list[str],
    strict: bool,
) -> None:
    if "public_contract" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="compatibility",
                basis=BASIS["implementation"],
                finding="CLI/API/MCP/出力契約など公開面の変更の可能性がある。",
                evidence=signals["public_contract"],
                suggested_fix="互換性、既定値、移行要否、文書、代表実行、出力契約確認を finish_check に残す。",
                warning_class="generic caution",
            )
        )
        missing.append("public_contract_evidence")

    if "failure_prone_operation" in signals:
        findings.append(
            Finding(
                severity="major" if strict else "minor",
                category="reliability",
                basis=BASIS["implementation"],
                finding="失敗しやすい実行・入出力・解析処理に対する失敗処理の証拠が薄い。",
                evidence=signals["failure_prone_operation"],
                suggested_fix="timeout、例外処理、戻り値確認、入力不正時の扱い、fallback、または意図的に不要な理由を明示する。",
                warning_class="generic caution",
            )
        )
        missing.append("failure_handling")

    if "operational_observability" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="operations",
                basis=BASIS["implementation"],
                finding="運用中に失敗し得る処理に対する状態報告や観測性の証拠が薄い。",
                evidence=signals["operational_observability"],
                suggested_fix="log、status、returncode、通知、監視、retry 記録、または不要理由を残す。",
                warning_class="generic caution",
            )
        )
        missing.append("observability_evidence")

    if "dependency_runtime" in signals:
        findings.append(
            Finding(
                severity="minor",
                category="dependency",
                basis=BASIS["implementation"] + BASIS["security"],
                finding="依存、実行環境、構成、CI に関わる変更の可能性がある。",
                evidence=signals["dependency_runtime"],
                suggested_fix="依存更新、実行環境、互換性、安全性、lockfile、CI 影響の確認結果を残す。",
                warning_class="generic caution",
            )
        )
        missing.append("dependency_runtime_evidence")


PUBLIC_CONTRACT_FILES = (
    "cli.py",
    "mcp_server.py",
    "__init__.py",
    ".schema.json",
    "openapi",
    "api/",
    "schemas/",
)

DEPENDENCY_RUNTIME_FILES = (
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Dockerfile",
    "docker-compose",
    ".github/workflows/",
)


GENERIC_FILENAME_SCOPE_TOKENS = frozenset(
    {
        "core",
        "common",
        "constant",
        "constants",
        "helper",
        "helpers",
        "index",
        "main",
        "manager",
        "misc",
        "model",
        "models",
        "shared",
        "type",
        "types",
        "util",
        "utils",
    }
)


BROAD_FILENAME_SCOPE_TOKENS = GENERIC_FILENAME_SCOPE_TOKENS | frozenset(
    {
        "adapter",
        "adapters",
        "base",
        "client",
        "clients",
        "controller",
        "controllers",
        "coordinator",
        "coordinators",
        "engine",
        "engines",
        "facade",
        "handler",
        "handlers",
        "orchestration",
        "orchestrator",
        "orchestrators",
        "processor",
        "processors",
        "provider",
        "providers",
        "registry",
        "service",
        "services",
        "workflow",
        "workflows",
    }
)


BROAD_FILENAME_SCOPE_TERMS_JA = (
    "管理",
    "共通",
    "汎用",
    "補助",
    "中核",
    "基盤",
    "処理",
    "機能",
    "サービス",
)


RESPONSIBILITY_DOMAIN_TERMS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "request_audit": (
        ("audit request", "request audit", "audit requests", "requirement audit", "requirements audit", "requirement", "requirements"),
        ("要求監査", "要求"),
    ),
    "plan_audit": (
        ("audit plan", "plan audit", "planning audit", "audit plans", "work breakdown", "rollback"),
        ("計画監査", "計画", "作業分解", "復旧"),
    ),
    "diff_audit": (
        ("audit diff", "diff audit", "audit diffs", "changed files", "changed file", "patch", "hunk"),
        ("差分監査", "差分", "変更ファイル"),
    ),
    "finish_check": (
        ("finish check", "finish checks", "completion evidence", "residual risk"),
        ("完了確認", "完了証拠", "残リスク"),
    ),
    "auth": (
        ("auth", "authentication", "authorization", "login", "logout", "oauth", "permission", "role", "session", "credential"),
        ("認証", "認可", "権限", "ロール"),
    ),
    "billing": (
        ("billing", "bill", "payment", "payments", "invoice", "invoices", "checkout", "subscription", "refund", "charge", "stripe", "price", "tax"),
        ("請求", "決済", "支払", "価格", "返金"),
    ),
    "notification": (
        ("notify", "notifier", "notification", "notifications", "email", "mail", "sms", "webhook", "slack", "discord", "message", "alert"),
        ("通知", "メール", "警告"),
    ),
    "scheduling": (
        ("schedule", "scheduler", "cron", "daemon", "background", "job", "queue", "worker", "retry", "timer"),
        ("定期", "常駐", "再試行", "予約"),
    ),
    "persistence": (
        ("database", "db", "sql", "sqlite", "postgres", "storage", "store", "save", "load", "loader", "repository", "migration", "migrate"),
        ("永続", "保存", "読込", "読み込み", "移行", "格納"),
    ),
    "api": (
        ("api", "http", "endpoint", "route", "router", "server"),
        ("エンドポイント", "経路"),
    ),
    "cli": (
        ("cli", "argparse", "argument", "option", "flag", "stdout", "stderr", "command"),
        ("コマンド", "引数", "標準出力", "標準エラー"),
    ),
    "ui": (
        ("ui", "view", "screen", "page", "component", "render", "template", "display"),
        ("画面", "表示"),
    ),
    "scoring": (
        ("score", "scoring", "rank", "ranking", "weight", "metric"),
        ("スコア", "評価値", "順位", "指標"),
    ),
    "parsing": (
        ("parse", "parser", "token", "lexer", "regex", "json", "yaml", "csv", "xml"),
        ("解析", "字句", "正規表現"),
    ),
    "security": (
        ("security", "secure", "encrypt", "crypto", "hash", "sanitize", "secret", "csrf", "xss"),
        ("安全", "秘密", "暗号"),
    ),
}


def _change_text(diff: str) -> str:
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    return "\n".join(added) if added else diff


def _public_contract_signal(text: str, changed_files: list[str]) -> str:
    public_file = next((path for path in changed_files if _matches_suffix_or_part(path, PUBLIC_CONTRACT_FILES)), "")
    public_terms = [
        "--",
        "command",
        "option",
        "flag",
        "argument",
        "api",
        "mcp",
        "tool",
        "schema",
        "json",
        "output",
        "contract",
        "default",
        "互換",
        "移行",
        "出力",
        "契約",
        "既定",
    ]
    if public_file and _has_any(text, public_terms):
        return public_file
    if _has_any(text, ["breaking", "public api", "output schema", "出力契約", "公開 API", "公開面"]):
        return _first_match(text, public_terms)
    return ""


def _failure_prone_operation_signal(text: str) -> str:
    patterns = [
        r"\bsubprocess\.",
        r"\bshell=True\b",
        r"\bjson\.loads\b",
        r"\bjson\.load\b",
        r"\bopen\(",
        r"\bread_text\(",
        r"\bwrite_text\(",
        r"\brequests\.",
        r"\bhttpx\.",
        r"\burllib\.",
        r"\bsocket\.",
        r"\bexec\(",
        r"\beval\(",
        r"\bPath\(",
        r"\bos\.environ\b",
        r"\bdatabase\b",
        r"(?:database|data|schema)[_\s]+migration\b",
        r"\bmigration[_\s]+(?:script|command|runner|job|step|tool|operation)\b",
        r"\bmigrate[_\s]+(?:database|data|schema)\b",
        r"外部実行",
        r"入出力",
        r"ファイル",
        r"(?:DB|データ|スキーマ)移行",
        r"移行(?:処理|スクリプト|ジョブ|実行)",
        r"解析",
    ]
    return _first_regex_match(text, patterns)


def _has_failure_handling_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "timeout",
            "try",
            "except",
            "catch",
            "fallback",
            "returncode",
            "check=True",
            "raise_for_status",
            "validate",
            "validation",
            "schema",
            "FileNotFoundError",
            "JSONDecodeError",
            "失敗",
            "例外",
            "タイムアウト",
            "検証",
            "戻り値",
            "異常",
        ],
    )


def _operational_change_signal(text: str) -> str:
    terms = [
        "daemon",
        "scheduler",
        "cron",
        "launchd",
        "background",
        "webhook",
        "notification",
        "discord",
        "monitor",
        "watchdog",
        "retry",
        "codex exec",
        "subprocess",
        "常駐",
        "定期実行",
        "通知",
        "監視",
        "再試行",
        "外部実行",
    ]
    return _first_match(text, terms)


def _has_observability_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            "log",
            "logger",
            "logging",
            "status",
            "returncode",
            "stderr",
            "stdout",
            "metric",
            "monitor",
            "alert",
            "report",
            "record",
            "ログ",
            "状態",
            "通知",
            "記録",
            "報告",
            "監視",
        ],
    )


def _dependency_runtime_signal(text: str, changed_files: list[str]) -> str:
    file_match = next((path for path in changed_files if _matches_suffix_or_part(path, DEPENDENCY_RUNTIME_FILES)), "")
    if file_match:
        return file_match
    return _first_word_or_phrase_match(
        text,
        ["dependency", "dependencies", "runtime", "lockfile", "container", "ci"],
        ["依存", "実行環境", "構成"],
    )


def _filename_content_scope_signals(diff: str, changed_files: list[str]) -> list[dict[str, object]]:
    added_text_by_file = _added_text_by_file(diff, changed_files)
    signals: list[dict[str, object]] = []
    for path in changed_files:
        if not _is_source_file(path) or _is_test_file(path):
            continue
        filename_tokens = _filename_scope_tokens(path)
        if not filename_tokens:
            continue
        filename_domains = _responsibility_domain_hits(" ".join(filename_tokens))
        if not filename_domains:
            continue
        added_text = added_text_by_file.get(path, "")
        if not added_text.strip():
            continue
        content_domains = _responsibility_domain_hits(added_text)
        extra_domains = [domain for domain in content_domains if domain not in filename_domains]
        if len(extra_domains) < 2:
            continue
        signals.append(
            {
                "path": path,
                "filename_tokens": filename_tokens,
                "filename_domains": sorted(filename_domains),
                "extra_domains": [
                    {"domain": domain, "evidence": content_domains[domain]}
                    for domain in sorted(extra_domains)
                ],
                "evidence": _compact_snippet(added_text),
            }
        )
    return signals


def _filename_content_scope_evidence(signal: dict[str, object]) -> str:
    extra_domains = signal.get("extra_domains", [])
    domain_names = []
    if isinstance(extra_domains, list):
        for item in extra_domains:
            if isinstance(item, dict) and item.get("domain"):
                domain_names.append(str(item["domain"]))
    path = str(signal.get("path", ""))
    filename_domains = ", ".join(str(item) for item in signal.get("filename_domains", []))
    return f"{path}: filename_scope={filename_domains}; extra_content={', '.join(domain_names)}"


def _filename_naming_scope_signals(diff: str, changed_files: list[str], intent: str, context: str) -> list[dict[str, object]]:
    scope_management_present = _filename_scope_management_present(_combine(diff, intent, context))
    actions = _changed_file_actions(diff, changed_files)
    signals: list[dict[str, object]] = []
    for path in changed_files:
        action = actions.get(path)
        if action not in {"added", "renamed"}:
            continue
        if not _is_source_file(path) or _is_test_file(path):
            continue
        filename_tokens = _filename_name_tokens(path)
        risk_tokens = _filename_scope_risk_tokens(path, filename_tokens)
        if not risk_tokens:
            continue
        specific_tokens = [token for token in filename_tokens if token not in BROAD_FILENAME_SCOPE_TOKENS]
        if len(specific_tokens) >= 2:
            continue
        if scope_management_present:
            continue
        management_expectation = "fallback_scope_management_for_generic_name"
        if specific_tokens:
            management_expectation = "narrow_filename_preferred"
        signals.append(
            {
                "path": path,
                "action": action,
                "filename_tokens": filename_tokens,
                "risk_tokens": risk_tokens,
                "management_expectation": management_expectation,
                "evidence": f"{path}: {action} filename includes broad token(s) {', '.join(risk_tokens)}",
            }
        )
    return signals


def _filename_naming_scope_evidence(signal: dict[str, object]) -> str:
    path = str(signal.get("path", ""))
    action = str(signal.get("action", ""))
    risk_tokens = ", ".join(str(item) for item in signal.get("risk_tokens", []))
    expectation = str(signal.get("management_expectation", ""))
    return f"{path}: action={action}; broad_name={risk_tokens}; expectation={expectation}"


def _filename_scope_management_present(text: str) -> bool:
    return _has_any(
        text,
        [
            "responsibility",
            "responsibilities",
            "scope",
            "boundary",
            "boundaries",
            "out of scope",
            "non-goal",
            "non-goals",
            "split condition",
            "co-location condition",
            "narrow name",
            "scope management",
            "naming scope",
            "責務",
            "対象外",
            "非対象",
            "機能範囲",
            "適用範囲",
            "境界",
            "同居条件",
            "分割条件",
            "命名厳密化",
            "命名",
            "厳密化",
            "範囲管理",
            "命名管理",
            "限定責務",
            "専用",
        ],
    )


def _changed_file_actions(diff: str, changed_files: list[str]) -> dict[str, str]:
    actions: dict[str, str] = {}
    current_path = ""
    previous_line = ""
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            current_path = _changed_file_path_from_header(line)
        elif line.startswith("new file mode ") and current_path:
            actions[current_path] = "added"
        elif line.startswith("rename to "):
            path = _changed_file_path_from_header(line)
            if path:
                actions[path] = "renamed"
                current_path = path
        elif line.startswith("*** Add File: "):
            path = _changed_file_path_from_header(line)
            if path:
                actions[path] = "added"
                current_path = path
        elif line.startswith("+++ b/"):
            path = _changed_file_path_from_header(line)
            if path:
                current_path = path
                if previous_line.startswith("--- /dev/null"):
                    actions[path] = "added"
        previous_line = line

    for line in diff.splitlines():
        lowered = line.lower()
        if not _line_can_list_changed_files(line):
            continue
        action = ""
        if _has_any(lowered, ["rename", "renamed", "改名", "名称変更"]):
            action = "renamed"
        elif _has_any(lowered, ["add", "added", "create", "created", "new", "追加", "新規", "作成"]):
            action = "added"
        if not action:
            continue
        for match in SUMMARY_FILE_PATH_PATTERN.finditer(line):
            path = _clean_changed_file_candidate(match.group(0))
            if path in changed_files:
                actions.setdefault(path, action)

    return actions


def _added_text_by_file(diff: str, changed_files: list[str]) -> dict[str, str]:
    lines_by_file: dict[str, list[str]] = {path: [] for path in changed_files}
    current_path = ""
    for line in diff.splitlines():
        path = _changed_file_path_from_header(line)
        if path:
            current_path = path
            lines_by_file.setdefault(current_path, [])
            continue
        if current_path and line.startswith("+") and not line.startswith("+++"):
            lines_by_file.setdefault(current_path, []).append(line[1:])

    if any(lines_by_file.values()):
        return {path: "\n".join(lines) for path, lines in lines_by_file.items()}

    if len(changed_files) == 1:
        return {changed_files[0]: _change_text(diff)}

    for path in changed_files:
        path_lines = [line for line in diff.splitlines() if path in line]
        if path_lines:
            lines_by_file[path] = path_lines
    return {path: "\n".join(lines) for path, lines in lines_by_file.items()}


def _changed_file_path_from_header(line: str) -> str:
    if line.startswith("+++ b/"):
        return _clean_changed_file_candidate(line[6:])
    if line.startswith("diff --git "):
        match = re.search(r"\sb/(\S+)$", line)
        if match:
            return _clean_changed_file_candidate(match.group(1))
    if line.startswith("rename to "):
        return _clean_changed_file_candidate(line.removeprefix("rename to ").strip())
    if line.startswith("*** Update File: "):
        return _clean_changed_file_candidate(line.removeprefix("*** Update File: ").strip())
    if line.startswith("*** Add File: "):
        return _clean_changed_file_candidate(line.removeprefix("*** Add File: ").strip())
    return ""


def _filename_scope_tokens(path: str) -> list[str]:
    return [token for token in _filename_name_tokens(path) if token not in GENERIC_FILENAME_SCOPE_TOKENS]


def _filename_name_tokens(path: str) -> list[str]:
    filename = path.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    normalized = _responsibility_match_text(stem).lower()
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+|[\u3040-\u30ff\u3400-\u9fff]+", normalized)
        if token
    ]
    return _unique_nonempty(tokens)


def _filename_scope_risk_tokens(path: str, filename_tokens: list[str]) -> list[str]:
    risks = [token for token in filename_tokens if token in BROAD_FILENAME_SCOPE_TOKENS]
    stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    risks.extend(term for term in BROAD_FILENAME_SCOPE_TERMS_JA if term in stem)
    return _unique_nonempty(risks)


def _responsibility_domain_hits(text: str) -> dict[str, str]:
    normalized_text = _responsibility_match_text(text).lower()
    hits: dict[str, str] = {}
    for domain, (english_terms, other_terms) in RESPONSIBILITY_DOMAIN_TERMS.items():
        evidence = _responsibility_term_match(normalized_text, english_terms, other_terms)
        if evidence:
            hits[domain] = evidence
    return hits


def _responsibility_match_text(text: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[_./:+-]+", " ", spaced)


def _responsibility_term_match(normalized_text: str, english_terms: tuple[str, ...], other_terms: tuple[str, ...]) -> str:
    for term in english_terms:
        normalized_term = _responsibility_match_text(term).lower()
        escaped = re.escape(normalized_term)
        pattern = rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"
        if re.search(pattern, normalized_text, re.IGNORECASE):
            return term
    for term in other_terms:
        if term in normalized_text:
            return term
    return ""


def _matches_suffix_or_part(path: str, needles: tuple[str, ...]) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(needle.lower()) or needle.lower() in lowered for needle in needles)


def _first_regex_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start, end = match.span()
            return text[max(0, start - 45): min(len(text), end + 45)].strip()
    return ""


def _first_word_or_phrase_match(text: str, english_terms: list[str], other_terms: list[str]) -> str:
    for term in english_terms:
        escaped = re.escape(term)
        pattern = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start, end = match.span()
            return text[max(0, start - 45): min(len(text), end + 45)].strip()
    return _first_match(text, other_terms)


def _implemented_public_behavior(text: str) -> bool:
    implementation_terms = ["実装", "implemented", "added", "changed", "更新", "追加"]
    public_terms = ["cli", "api", "mcp", "command", "tool", "schema", "json", "出力", "コマンド", "公開"]
    return _has_any(text, implementation_terms) and _has_any(text, public_terms)


def _has_behavior_evidence(text: str) -> bool:
    if _has_any(
        text,
        [
            "smoke",
            "manual",
            "representative",
            "end-to-end",
            "e2e",
            "stdout",
            "returncode",
            "screenshot",
            "実地",
            "手動",
            "代表",
            "出力確認",
            "実行例",
            "挙動確認",
        ],
    ):
        return True
    return bool(re.search(r"\bsemantic-guard\s+(audit|review|finish|understand|llm|acceptance|validate)", text))


SEMANTIC_BOUNDARY_TERMS: dict[str, list[str]] = {
    "identity": ["identity", "identifier", "uuid", "primary key", "識別子", "同一性", "実体", "ID"],
    "display_identifier": ["display", "label", "title", "rename", "表示名", "表示", "ラベル", "名称", "名前"],
    "persistence": ["file path", "storage path", "save path", "directory", "folder", "永続化", "保存先", "保管", "格納", "配置"],
    "membership": ["membership", "belongs", "collection", "group", "所属", "分類", "包含", "メンバー"],
    "source_of_truth": ["source of truth", "canonical", "canon", "正本", "正典", "唯一の正", "参照元"],
    "permission": ["permission", "authorization", "authz", "role", "権限", "認可", "ロール"],
    "evidence": ["evidence", "proof", "acceptance", "verification", "証拠", "証跡", "根拠", "受入", "検証"],
}


def _semantic_boundaries(diff: str) -> list[dict[str, str]]:
    boundaries: list[dict[str, str]] = []
    for boundary, terms in SEMANTIC_BOUNDARY_TERMS.items():
        evidence = _semantic_boundary_evidence(diff, terms)
        if evidence:
            boundaries.append({"boundary": boundary, "evidence": evidence})
    return boundaries


def _semantic_boundary_evidence(text: str, terms: list[str]) -> str:
    lowered = text.lower()
    ignored_phrases = ["audit path", "document audit path", "code path", "path through"]
    for term in terms:
        term_lower = term.lower()
        if term_lower == "id":
            pattern = r"\b(id|ids)\b"
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            start, end = match.span()
        else:
            index = lowered.find(term_lower)
            if index < 0:
                continue
            start, end = index, index + len(term)
        excerpt = _excerpt_around(text, start, end)
        if any(ignored in excerpt.lower() for ignored in ignored_phrases):
            continue
        return excerpt
    return ""


def _semantic_boundary_fix(boundaries: list[str]) -> str:
    guidance = {
        "identity": "名前変更と実体識別子変更を分け、移行や参照解決の証拠を残す。",
        "display_identifier": "表示名、ラベル、識別子のどれを変えたのか明示する。",
        "persistence": "物理保存先、永続化形式、意味上の所属を混同していないか確認する。",
        "membership": "所属、分類、包含関係が変わるなら影響する参照と移行を確認する。",
        "source_of_truth": "正本、正典、参照元が変わるなら旧正本との関係を明示する。",
        "permission": "権限、認可、役割への影響と確認証拠を残す。",
        "evidence": "証拠、受入、検証の主張が成果物と対応しているか確認する。",
    }
    return " ".join(guidance.get(boundary, "") for boundary in boundaries).strip()


SUMMARY_FILE_CONTEXT_TERMS = (
    "changed",
    "changes",
    "updated",
    "modified",
    "added",
    "removed",
    "deleted",
    "touched",
    "files",
    "file",
    "変更",
    "更新",
    "修正",
    "追加",
    "削除",
    "変更ファイル",
    "変更対象",
)

SUMMARY_FILE_PATH_PATTERN = re.compile(
    r"""
    (?<![\w./-])
    (?:
        (?:[A-Za-z0-9_.@()+-]+/)+[A-Za-z0-9_.@()+-]+\.
            (?:py|js|ts|tsx|jsx|swift|go|rs|java|kt|c|cc|cpp|h|sh|css|html|sql|md|rst|txt|adoc|json|ya?ml|toml|lock)
        |
        (?:README|CHANGELOG|CONTRIBUTING|LICENSE)\.(?:md|txt)
        |
        pyproject\.toml
        |
        uv\.lock
        |
        requirements(?:-dev)?\.txt
        |
        package(?:-lock)?\.json
        |
        pnpm-lock\.yaml
        |
        yarn\.lock
        |
        Dockerfile
    )
    (?![\w./-])
    """,
    re.VERBOSE,
)


def _changed_files(diff: str) -> list[str]:
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
        elif line.startswith("diff --git "):
            match = re.search(r"\sb/(\S+)$", line)
            if match:
                files.append(match.group(1))
        elif line.startswith("rename to "):
            files.append(line.removeprefix("rename to ").strip())
        elif line.startswith("*** Update File: "):
            files.append(line.removeprefix("*** Update File: ").strip())
        elif line.startswith("*** Add File: "):
            files.append(line.removeprefix("*** Add File: ").strip())
        elif line.startswith("*** Delete File: "):
            files.append(line.removeprefix("*** Delete File: ").strip())
    header_files = _unique_nonempty([_clean_changed_file_candidate(path) for path in files])
    if header_files:
        return header_files
    return _summary_changed_files(diff)


def _summary_changed_files(text: str) -> list[str]:
    files: list[str] = []
    for line in text.splitlines():
        if not _line_can_list_changed_files(line):
            continue
        for match in SUMMARY_FILE_PATH_PATTERN.finditer(line):
            files.append(_clean_changed_file_candidate(match.group(0)))
    return _unique_nonempty(files)


def _line_can_list_changed_files(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r"^(?:uv|python|pytest|git|semantic-guard|codex)\b", stripped):
        return False
    if _has_any(stripped, SUMMARY_FILE_CONTEXT_TERMS):
        return True
    return bool(re.match(r"^[-*]?\s*" + SUMMARY_FILE_PATH_PATTERN.pattern, stripped, re.VERBOSE))


def _clean_changed_file_candidate(path: str) -> str:
    cleaned = path.strip().strip("'\"`<>()[]{}")
    return cleaned.removeprefix("a/").removeprefix("b/")


def _is_source_file(path: str) -> bool:
    return path.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".swift", ".go", ".rs", ".java", ".kt", ".c", ".cc", ".cpp", ".h"))


def _is_test_file(path: str) -> bool:
    lowered = path.lower()
    return "/test" in lowered or "test_" in lowered or lowered.endswith((".spec.ts", ".test.ts", ".spec.js", ".test.js"))


def _is_doc_file(path: str) -> bool:
    return path.endswith((".md", ".rst", ".txt", ".adoc"))


def _is_document_only_boundary(boundary: dict[str, str], changed_files: list[str]) -> bool:
    return (
        boundary.get("boundary") == "evidence"
        and bool(changed_files)
        and all(_is_doc_file(path) for path in changed_files)
    )


def _complexity_signal(diff: str) -> int:
    added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    patterns = [" if ", " for ", " while ", " try", " except", " catch", " class ", " enum ", " switch ", " async ", " await "]
    return sum(sum(pattern in line for pattern in patterns) for line in added)


def _complexity_growth_signal(diff: str) -> str:
    if _complexity_signal(diff) < 8:
        return ""
    added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    return _compact_snippet("\n".join(added[:8]))
