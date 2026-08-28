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


def workflow_job(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        text,
    )
    return match.group(0) if match is not None else ""


def audit_ci_contract(text: str) -> list[str]:
    errors: list[str] = []
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
        "uses: actions/upload-artifact@v7",
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
        "uses: actions/download-artifact@v8",
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
        "uses: actions/download-artifact@v8",
        "scripts/distribution_binding.py check",
        "scripts/verify_packaged_contracts.py",
    )
    positions = [portability_job.find(token) for token in ordered_portability_tokens]
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        errors.append("the bound artifact must be downloaded and rechecked before execution")
    return errors


class CiContractTests(unittest.TestCase):
    def test_current_workflow_satisfies_hardening_contract(self) -> None:
        self.assertEqual(audit_ci_contract(WORKFLOW.read_text(encoding="utf-8")), [])

    def test_unpinned_uv_mutation_is_detected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        mutated = text.replace(EXACT_UV_INSTALL, "run: python -m pip install uv", 1)
        self.assertNotEqual(mutated, text)
        self.assertTrue(
            any("uv installations" in error for error in audit_ci_contract(mutated))
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
