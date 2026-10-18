from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
UV_VERSION = "0.10.10"
EXACT_UV_INSTALL = 'run: python -m pip install "uv==${{ env.UV_VERSION }}"'
EXACT_PYTHON_RUNTIME_CHECK = (
    "python -c \"import os, sys; expected = tuple(map(int, "
    "os.environ['EXPECTED_PYTHON'].split('.'))); actual = sys.version_info[:2]; "
    "sys.exit(f'Python runtime mismatch: {actual!r} != {expected!r}') if actual != "
    "expected else None\""
)
EXACT_UV_RUNTIME_CHECK = (
    "python -c \"import os, subprocess, sys; observed = "
    "subprocess.check_output(['uv', '--version'], text=True).split(); expected = "
    "os.environ['UV_VERSION']; sys.exit(f'uv runtime mismatch: {observed!r}; expected uv "
    "{expected}') if observed[:2] != ['uv', expected] else None\""
)
FULL_CONTRACT_COMMANDS = (
    "uv run --locked python -m compileall -q src tests workflow_tests candidate_tests scripts",
    "uv run --locked python -m unittest discover -s tests -v",
    "uv run --locked python -m unittest discover -s workflow_tests -t . -v",
    "uv run --locked python -m unittest discover -s candidate_tests -t . -v",
    "uv run --locked semantic-guard workflow evaluate-fixtures",
    "uv run --locked semantic-guard workflow evaluate-metamorphic",
)
EXPECTED_TRIGGERS = (
    "on:\n"
    "  push:\n"
    '    branches: ["main"]\n'
    "  pull_request:\n"
    '    branches: ["main"]\n'
    "  workflow_dispatch:\n"
)
EXPECTED_PERMISSIONS = "permissions:\n  contents: read\n"
PACKAGE_NEEDS = "needs: [v1-contract, legacy-smoke]"
PACKAGED_CONTRACTS_COMMAND = (
    'uv run --locked python scripts/verify_packaged_contracts.py --wheel "$WHEEL" --sdist "$SDIST"'
)
ACTION_USES = {
    "actions/checkout": (
        "d23441a48e516b6c34aea4fa41551a30e30af803",
        "v6",
        4,
    ),
    "actions/setup-python": (
        "ece7cb06caefa5fff74198d8649806c4678c61a1",
        "v6",
        4,
    ),
    "actions/upload-artifact": (
        "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        "v7",
        1,
    ),
    "actions/download-artifact": (
        "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
        "v8",
        1,
    ),
}


def action_ref(action: str) -> str:
    return f"uses: {action}@{ACTION_USES[action][0]}"


def action_line(action: str) -> str:
    return f"{action_ref(action)} # {ACTION_USES[action][1]}"


def workflow_job(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        text,
    )
    return match.group(0) if match is not None else ""


def audit_ci_contract(text: str) -> list[str]:
    errors: list[str] = []
    uses_lines = [line.strip() for line in text.splitlines() if "uses:" in line]
    expected_uses = {
        action_line(action): count for action, (_, _, count) in ACTION_USES.items()
    }
    for expected, count in expected_uses.items():
        if uses_lines.count(expected) != count:
            errors.append(
                "action must use the reviewed commit pin exactly "
                f"{count} times: {expected}"
            )
    if any(line not in expected_uses for line in uses_lines):
        errors.append("workflow contains an unreviewed action reference")
    if not re.search(rf"(?m)^  UV_VERSION: [\"']{re.escape(UV_VERSION)}[\"']$", text):
        errors.append("UV_VERSION must be fixed at the reviewed version")

    uv_install_lines = [
        line.strip()
        for line in text.splitlines()
        if "python -m pip install" in line and re.search(r"\buv(?:==|\s|$)", line)
    ]
    if uv_install_lines != [EXACT_UV_INSTALL] * 3:
        errors.append("all three uv installations must use the exact reviewed pin")
    if text.count(EXACT_UV_RUNTIME_CHECK) != 3:
        errors.append("each uv installation must be followed by a runtime version assertion")

    if 'python-version: ["3.11", "3.12", "3.13"]' not in text:
        errors.append("the full v1 contract matrix must cover Python 3.11, 3.12, and 3.13")
    if text.count(EXACT_PYTHON_RUNTIME_CHECK) != 3 or text.count("sys.version_info[:2]") < 4:
        errors.append("all contract, package, and portability jobs must assert the Python runtime")

    contract_job = workflow_job(text, "v1-contract")
    contract_run_lines = [line.strip() for line in contract_job.splitlines()]
    for command in FULL_CONTRACT_COMMANDS:
        if f"run: {command}" not in contract_run_lines:
            errors.append(f"missing full canonical/workflow/candidate contract command: {command}")

    package_job = workflow_job(text, "package")
    if not package_job:
        errors.append("the package job is missing")
    required_distribution_tokens = (
        'marker = Path("dist/.gitignore")',
        "marker.unlink()",
        "scripts/distribution_binding.py create",
        "scripts/distribution_binding.py check",
        "dist/distribution-binding.json",
        "dist/SHA256SUMS",
        "wheel_filename: ${{ steps.distribution.outputs.wheel_filename }}",
        "sdist_filename: ${{ steps.distribution.outputs.sdist_filename }}",
        "name: ${{ steps.distribution.outputs.artifact_name }}",
    )
    for token in required_distribution_tokens:
        if token not in package_job:
            errors.append(f"missing bound-distribution contract token: {token}")
    ordered_distribution_tokens = (
        "uv build --out-dir dist",
        "marker.unlink()",
        "scripts/distribution_binding.py create",
        "scripts/distribution_binding.py check",
        action_ref("actions/upload-artifact"),
    )
    positions = [package_job.find(token) for token in ordered_distribution_tokens]
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        errors.append("the distribution must be normalized, bound, checked, then uploaded")
    if "find dist" in text or "dist/*.whl" in text or "dist/*.tar.gz" in text:
        errors.append("artifact selection must not accept the first match or an unchecked glob")

    portability_job = workflow_job(text, "package-portability")
    if not portability_job:
        errors.append("the package-portability job is missing")
    required_portability_tokens = (
        "runs-on: ${{ matrix.os }}",
        "needs: package",
        "os: [macos-latest, windows-latest]",
        "ref: ${{ github.sha }}",
        'python-version: "3.12"',
        'raise SystemExit(f"Python runtime mismatch:',
        action_ref("actions/download-artifact"),
        "name: ${{ needs.package.outputs.artifact_name }}",
        "scripts/distribution_binding.py check",
        '--expected-commit "${{ github.sha }}"',
        "scripts/verify_packaged_contracts.py",
        'dist/${{ needs.package.outputs.wheel_filename }}',
        'dist/${{ needs.package.outputs.sdist_filename }}',
        "--timeout-seconds 300",
    )
    for token in required_portability_tokens:
        if token not in portability_job:
            errors.append(f"missing same-wheel portability contract token: {token}")
    ordered_portability_tokens = (
        action_ref("actions/download-artifact"),
        "scripts/distribution_binding.py check",
        "scripts/verify_packaged_contracts.py",
    )
    positions = [portability_job.find(token) for token in ordered_portability_tokens]
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        errors.append("the bound artifact must be downloaded and rechecked before execution")

    # The workflow's own trust boundary: who can trigger it, with which token
    # rights, and whether any step may fail without failing the run.
    trigger_block = re.search(r"(?ms)^on:\n.*?(?=^\S)", text)
    if trigger_block is None or trigger_block.group(0) != EXPECTED_TRIGGERS + "\n":
        errors.append("the workflow must run only on push and pull_request to main and on workflow_dispatch")
    if "pull_request_target" in text:
        errors.append("pull_request_target runs untrusted code with repository secrets and must not be used")
    if "continue-on-error" in text:
        errors.append("no step or job may continue on error")
    if text.count("permissions:") != 1 or EXPECTED_PERMISSIONS not in text:
        errors.append("permissions must be exactly one top-level block granting contents: read")
    if re.search(r"(?m)^\s+[A-Za-z-]+:\s*write(?:-all)?\s*$", text) or "write-all" in text or "read-all" in text:
        errors.append("no permission may be widened beyond contents: read")

    if package_job and PACKAGE_NEEDS not in package_job:
        errors.append("the package job must depend on both the contract and the legacy smoke jobs")
    if package_job and (
        "- name: Verify packaged contracts" not in package_job
        or PACKAGED_CONTRACTS_COMMAND not in package_job
    ):
        errors.append("the package job must verify packaged contracts before it uploads")
    elif package_job and package_job.find(PACKAGED_CONTRACTS_COMMAND) > package_job.find(action_ref("actions/upload-artifact")):
        errors.append("the package job must verify packaged contracts before it uploads")
    return errors


class CiContractTests(unittest.TestCase):
    def test_trust_boundary_mutations_are_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        step = "      - name: Check workflow rule invariance and sensitivity\n        run: uv run --locked semantic-guard workflow evaluate-metamorphic\n\n"
        verify = (
            "      - name: Verify packaged contracts\n"
            "        run: |\n"
            '          WHEEL="dist/${{ steps.distribution.outputs.wheel_filename }}"\n'
            '          SDIST="dist/${{ steps.distribution.outputs.sdist_filename }}"\n'
            f"          {PACKAGED_CONTRACTS_COMMAND}\n\n"
        )
        self.assertIn(step, text)
        self.assertIn(verify, text)
        mutations = {
            "remove the evaluate-metamorphic step": (text.replace(step, "", 1), "evaluate-metamorphic"),
            "permissions: write-all": (text.replace(EXPECTED_PERMISSIONS, "permissions: write-all\n", 1), "permissions"),
            "widen contents to write": (text.replace("  contents: read\n", "  contents: write\n", 1), "permissions"),
            "add id-token write": (text.replace(EXPECTED_PERMISSIONS, EXPECTED_PERMISSIONS + "  id-token: write\n", 1), "permission"),
            "add pull_request_target": (text.replace("  workflow_dispatch:\n", "  pull_request_target:\n  workflow_dispatch:\n", 1), "pull_request_target"),
            "add continue-on-error": (text.replace("    runs-on: ubuntu-latest\n", "    runs-on: ubuntu-latest\n    continue-on-error: true\n", 1), "continue on error"),
            "drop the package job needs": (text.replace(PACKAGE_NEEDS, "needs: [v1-contract]", 1), "package job must depend"),
            "remove the packaged contracts step": (text.replace(verify, "", 1), "verify packaged contracts"),
        }
        for name, (mutated, expected) in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(mutated, text)
                errors = audit_ci_contract(mutated)
                self.assertTrue(any(expected in error for error in errors), (expected, errors))

    def test_trigger_set_is_fixed(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n  schedule:\n    - cron: '0 0 * * *'\n", 1)

        self.assertNotEqual(mutated, text)
        self.assertTrue(any("must run only on" in error for error in audit_ci_contract(mutated)))


    def test_current_workflow_satisfies_hardening_contract(self) -> None:
        self.assertEqual(audit_ci_contract(WORKFLOW.read_text(encoding="utf-8")), [])

    def test_unpinned_uv_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace(EXACT_UV_INSTALL, "run: python -m pip install uv", 1)
        self.assertNotEqual(mutated, text)
        self.assertTrue(
            any("uv installations" in error for error in audit_ci_contract(mutated))
        )

    def test_action_tag_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        exact = action_line("actions/checkout")
        mutations = (
            text.replace(exact, "uses: actions/checkout@v6", 1),
            text.replace(exact, f'{action_ref("actions/checkout")}-suffix # v6', 1),
        )
        for mutated in mutations:
            with self.subTest(mutated=mutated):
                self.assertNotEqual(mutated, text)
                self.assertTrue(
                    any(
                        "reviewed commit pin" in error
                        for error in audit_ci_contract(mutated)
                    )
                )

    def test_unreviewed_action_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace(
            "      - name: Compile canonical source and tests\n",
            "      - name: Unreviewed action\n"
            "        uses: example/unreviewed@0123456789abcdef0123456789abcdef01234567\n\n"
            "      - name: Compile canonical source and tests\n",
            1,
        )
        self.assertNotEqual(mutated, text)
        self.assertIn(
            "workflow contains an unreviewed action reference",
            audit_ci_contract(mutated),
        )

    def test_uv_runtime_assertion_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace(EXACT_UV_RUNTIME_CHECK, "uv --version", 1)
        self.assertNotEqual(mutated, text)
        self.assertTrue(any("runtime version" in error for error in audit_ci_contract(mutated)))

    def test_python_312_matrix_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace(
            'python-version: ["3.11", "3.12", "3.13"]',
            'python-version: ["3.11", "3.13"]',
            1,
        )
        self.assertNotEqual(mutated, text)
        self.assertTrue(any("Python 3.11" in error for error in audit_ci_contract(mutated)))

    def test_python_runtime_assertion_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace("sys.version_info[:2]", "sys.version_info[:1]", 1)
        self.assertNotEqual(mutated, text)
        self.assertTrue(any("assert the Python runtime" in error for error in audit_ci_contract(mutated)))

    def test_full_contract_commands_must_remain_in_the_contract_job(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        job = workflow_job(text, "v1-contract")
        for command in FULL_CONTRACT_COMMANDS:
            with self.subTest(command=command):
                mutated_job = job.replace(f"run: {command}", "run: true", 1)
                self.assertNotEqual(mutated_job, job)
                mutated = text.replace(job, mutated_job, 1)
                # A copy in another job must not hide a missing contract step.
                mutated += f"\n  unrelated:\n    steps:\n      - run: {command}\n"
                self.assertTrue(
                    any(
                        "canonical/workflow/candidate" in error
                        for error in audit_ci_contract(mutated)
                    )
                )

    def test_unbound_artifact_upload_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace("            dist/SHA256SUMS\n", "", 1)
        self.assertNotEqual(mutated, text)
        self.assertTrue(any("SHA256SUMS" in error for error in audit_ci_contract(mutated)))

    def test_uv_build_marker_must_be_removed_before_binding(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace("          marker.unlink()\n", "", 1)
        self.assertNotEqual(mutated, text)
        self.assertTrue(any("marker.unlink" in error for error in audit_ci_contract(mutated)))

    def test_portability_job_must_consume_package_artifact(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace(
            "name: ${{ needs.package.outputs.artifact_name }}",
            "name: independently-built-distribution",
            1,
        )
        self.assertNotEqual(mutated, text)
        self.assertTrue(
            any("same-wheel portability" in error for error in audit_ci_contract(mutated))
        )

    def test_portability_job_must_run_on_the_os_matrix(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        job = workflow_job(text, "package-portability")
        mutated_job = job.replace("runs-on: ${{ matrix.os }}", "runs-on: ubuntu-latest", 1)
        self.assertNotEqual(mutated_job, job)
        mutated = text.replace(job, mutated_job, 1)
        self.assertTrue(
            any("runs-on" in error for error in audit_ci_contract(mutated))
        )

    def test_portability_job_must_recheck_the_exact_checked_out_source(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        job = workflow_job(text, "package-portability")
        mutations = (
            job.replace("ref: ${{ github.sha }}", "ref: main", 1),
            job.replace(
                "scripts/distribution_binding.py check",
                "scripts/distribution_binding.py --help",
                1,
            ),
            job.replace(
                '--expected-commit "${{ github.sha }}"',
                '--expected-commit "0000000000000000000000000000000000000000"',
                1,
            ),
        )
        for mutated_job in mutations:
            with self.subTest(mutated_job=mutated_job):
                self.assertNotEqual(mutated_job, job)
                mutated = text.replace(job, mutated_job, 1)
                self.assertTrue(
                    any(
                        "same-wheel portability" in error
                        for error in audit_ci_contract(mutated)
                    )
                )


if __name__ == "__main__":
    unittest.main()
