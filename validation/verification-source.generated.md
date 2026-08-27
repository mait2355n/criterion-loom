# Verification Source Generated Projection

> GENERATED FILE. Edit `verification-source.json`, then regenerate this file.
> Exact equality is checked by `validate_verification_source.py`.

## Binding

| Field | Value |
| --- | --- |
| projection_version | `semantic-guard-verification-projection/v0` |
| source | `verification-source.json` |
| source_sha256 | `6a48d93e6800e145c9d4352d5d911cedaeb378697a2915d85b461119433b43ac` |
| canonical_json_sha256 | `af51759ef1143b1e5b11d1b4681c94e30807c0c4b5291bfedcb19b51159cb59a` |
| schema_version | `semantic-guard-verification-source/v0` |
| register_id | `verification-register.semantic-guard.r0` |
| recorded_at | `2026-08-27T15:43:40+09:00` |
| human_acceptance.status | `pending` |
| human_acceptance.owner | `human` |

## Collection Counts

| Collection | Count |
| --- | ---: |
| `state_profiles` | 10 |
| `evidence_observations` | 6 |
| `evidence_effects` | 27 |
| `verification_items` | 17 |
| `implementation_conformance_items` | 27 |
| `views` | 5 |
| `unresolved_items` | 17 |
| `resolution_obligations` | 52 |
| `resolution_paths` | 19 |

## Entity Inventory

| Collection | Stable ID | Navigation label |
| --- | --- | --- |
| `evidence_effects` | `effect.action-artifact.integrated-omission.contextualizes` |  |
| `evidence_effects` | `effect.action-occurrence.historical-review.refutes` |  |
| `evidence_effects` | `effect.artifact-authenticity.historical-review.refutes` |  |
| `evidence_effects` | `effect.bounded-claim.integrated-schema.contextualizes` |  |
| `evidence_effects` | `effect.bounded-claim.public-trust-basis.challenges` |  |
| `evidence_effects` | `effect.constitution.normative-items.contextualizes` |  |
| `evidence_effects` | `effect.dependency-analysis.real-nlp.contextualizes` |  |
| `evidence_effects` | `effect.discovery.integrated-record.contextualizes` |  |
| `evidence_effects` | `effect.discovery.real-nlp-missing-coreference.challenges` |  |
| `evidence_effects` | `effect.engineering-governance.historical-review.challenges` |  |
| `evidence_effects` | `effect.field.integrated-unverified.contextualizes` |  |
| `evidence_effects` | `effect.historical-review.governance-action-authenticity.contextualizes` |  |
| `evidence_effects` | `effect.human-boundary.integrated-acceptance.supports` |  |
| `evidence_effects` | `effect.legacy-baseline.integrated-record.supports` |  |
| `evidence_effects` | `effect.legacy-characterization.known-failures.challenges` |  |
| `evidence_effects` | `effect.lifecycle-surface.integrated-next-action.refutes` |  |
| `evidence_effects` | `effect.lifecycle.integrated-record.contextualizes` |  |
| `evidence_effects` | `effect.lifecycle.requirement-slice.integrated-suite.supports` |  |
| `evidence_effects` | `effect.local-conformance.integrated-suite.supports` |  |
| `evidence_effects` | `effect.operational-reverification.integrated-record.challenges` |  |
| `evidence_effects` | `effect.operational.integrated-unverified.contextualizes` |  |
| `evidence_effects` | `effect.origin-requirement.purpose-items.contextualizes` |  |
| `evidence_effects` | `effect.origin-requirement.rebased-verification-denominator.contextualizes` |  |
| `evidence_effects` | `effect.partial-conformance.integrated-record.contextualizes` |  |
| `evidence_effects` | `effect.real-nlp.discovery-field.contextualizes` |  |
| `evidence_effects` | `effect.real-nlp.provider-paths.supports` |  |
| `evidence_effects` | `effect.repair.integrated-acceptance.contextualizes` |  |
| `evidence_observations` | `evidence.constitution.snapshot.2026-08-24` | v1 憲法 snapshot |
| `evidence_observations` | `evidence.full-evaluation.2026-07-11` | 全体監査の歴史的観測 |
| `evidence_observations` | `evidence.integrated-verification.2026-07-16` | vNext 統合検証観測 |
| `evidence_observations` | `evidence.origin-requirement.snapshot.2026-08-27` | 原点要求 snapshot |
| `evidence_observations` | `evidence.public-trust-basis-inspection.2026-07-17` | 公開 provenance 信頼根拠欄の欠落観測 |
| `evidence_observations` | `evidence.real-nlp-smoke.2026-07-16` | 実 Sudachi/GiNZA 煙試験観測 |
| `implementation_conformance_items` | `conformance.INV-VN-001` | 未知・競合・無効・被覆不足を上位 pass が捨てない |
| `implementation_conformance_items` | `conformance.INV-VN-002` | 直接 satisfied は残余危険門まで provisional |
| `implementation_conformance_items` | `conformance.INV-VN-003` | terminal satisfaction の閉包条件 |
| `implementation_conformance_items` | `conformance.INV-VN-004` | 必須解析器障害を silent success にしない |
| `implementation_conformance_items` | `conformance.INV-VN-005` | 候補解析器は支持・解除不能 |
| `implementation_conformance_items` | `conformance.INV-VN-006` | 引用・例示等を肯定へ自動昇格しない |
| `implementation_conformance_items` | `conformance.INV-VN-007` | 開いた自由文から missing を断定しない |
| `implementation_conformance_items` | `conformance.INV-VN-008` | 人間の危険受容で監査事実を消さない |
| `implementation_conformance_items` | `conformance.INV-VN-009` | score を正しさ確率にしない |
| `implementation_conformance_items` | `conformance.INV-VN-010` | schema・digest・由来破損を pass にしない |
| `implementation_conformance_items` | `conformance.INV-VN-011` | 分野語共有だけを関係証明にしない |
| `implementation_conformance_items` | `conformance.INV-VN-012` | 解析器 ok は span 被覆と能力閉包を要する |
| `implementation_conformance_items` | `conformance.INV-VN-013` | 公開集約欄の矛盾を受理しない |
| `implementation_conformance_items` | `conformance.INV-VN-014` | 入力同一性と監査観測同一性を分ける |
| `implementation_conformance_items` | `conformance.completeness.provider-accounting` | 解析器実行会計 |
| `implementation_conformance_items` | `conformance.completeness.public-result` | 公開結果完全性 |
| `implementation_conformance_items` | `conformance.migration.legacy-baseline` | 旧版基線 |
| `implementation_conformance_items` | `conformance.migration.legacy-characterization` | 旧版特性試験 |
| `implementation_conformance_items` | `conformance.stage.decision-request-materialization` | 段階8 判断要求生成 |
| `implementation_conformance_items` | `conformance.stage.dependency-analysis-bundle` | 段階4 依存構造解析束 |
| `implementation_conformance_items` | `conformance.stage.input-boundary` | 段階0 入力契約と記録境界 |
| `implementation_conformance_items` | `conformance.stage.llm-candidate` | 段階6 LLM 候補 |
| `implementation_conformance_items` | `conformance.stage.morphology` | 段階3 形態素解析 |
| `implementation_conformance_items` | `conformance.stage.obligation-reaggregation` | 段階7 義務別再集約 |
| `implementation_conformance_items` | `conformance.stage.provisional-direct-audit` | 段階1 義務別仮判定 |
| `implementation_conformance_items` | `conformance.stage.residual-risk-gate` | 段階2 独立残余危険門 |
| `implementation_conformance_items` | `conformance.stage.versioned-lifting-rule` | 段階5 版付き決定論的導出 |
| `resolution_obligations` | `obligation.action-assurance.adversarial-review` | Challenge the mechanism with independent and adversarial observations appropriate to the selected assurance profile. |
| `resolution_obligations` | `obligation.action-assurance.human-trust-model` | Choose the bounded threat model, trust roots, acceptable claim strength, and residual-risk policy. |
| `resolution_obligations` | `obligation.action-assurance.implement-evidence-envelope` | Implement the action-evidence contract, runtime observation, authority snapshot, provenance, and replay controls with... |
| `resolution_obligations` | `obligation.analyzer-effectiveness.define-route-protocol` | Define one versioned subject-bound protocol, corpus split, route configuration, capability accounting, error taxonomy... |
| `resolution_obligations` | `obligation.analyzer-effectiveness.independent-route-review` | Independently review corpus isolation, labels and adjudication, resource and model binding, capability accounting, ea... |
| `resolution_obligations` | `obligation.analyzer-effectiveness.measure-dependency-coreference` | Measure dependency and coreference candidate accuracy, missing capability, attachment, role reversal, long-sentence, ... |
| `resolution_obligations` | `obligation.analyzer-effectiveness.measure-lifting-expansion` | Add candidate lifting families only through versioned governed mappings, then measure each family's coverage gain, fa... |
| `resolution_obligations` | `obligation.analyzer-effectiveness.measure-llm-incremental-value` | Measure the LLM candidate route's incremental discovery, false satisfaction, false defect, abstention, challenge capt... |
| `resolution_obligations` | `obligation.analyzer-effectiveness.measure-morphology-ablation` | Execute direct-only and morphology-enabled routes on identical bound cases and report incremental discovery, false sa... |
| `resolution_obligations` | `obligation.assurance-profile.human-policy` | Choose claim-strength profiles, required observer independence, acceptable trust roots, and downgrade behavior. |
| `resolution_obligations` | `obligation.assurance-profile.independent-challenge` | Challenge profile selection, observer independence, trust-root resolution, and downgrade behavior independently of th... |
| `resolution_obligations` | `obligation.assurance-profile.public-contract` | Implement a versioned profile registry and bind every elevated public provenance trust class to required, locally or ... |
| `resolution_obligations` | `obligation.field-policy.evaluation-protocol` | Construct the sampling, measurement, holdout, and uncertainty protocol within the accepted risk policy and governed r... |
| `resolution_obligations` | `obligation.field-policy.execute-evaluation` | Execute the versioned protocol on the selected, subject-bound holdout corpus within the accepted engineering, risk, a... |
| `resolution_obligations` | `obligation.field-policy.human-risk-choice` | Choose intended use, target population, catastrophic-error cost, and decision thresholds. |
| `resolution_obligations` | `obligation.field-policy.independent-labels` | Provide independent labels, disagreement records, and adjudication evidence. |
| `resolution_obligations` | `obligation.human-use.human-responsibility-policy` | Choose coding-agent and human role meanings, decision rights, escalation conditions, required context, unacceptable a... |
| `resolution_obligations` | `obligation.human-use.implement-responsibility-aware-material` | Implement versioned coding-agent and human projections that preserve subject, proposition, finding, evidence, limitat... |
| `resolution_obligations` | `obligation.human-use.independent-task-evaluation` | Independently evaluate representative coding-agent and human tasks, separately measuring correct routing, comprehensi... |
| `resolution_obligations` | `obligation.lifecycle-composition.human-semantics` | Accept or revise the cross-stage identity, transformation, obligation-carrying, authority, evidence, unresolved-remai... |
| `resolution_obligations` | `obligation.lifecycle-composition.implement-trace-and-rules` | Implement versioned cross-stage identities, source and target propositions, carried and discharged obligations, evide... |
| `resolution_obligations` | `obligation.lifecycle-composition.independent-cross-stage-review` | Independently review origin trace, identity and proposition preservation, allowed transformations, authority changes,... |
| `resolution_obligations` | `obligation.lifecycle-surfaces.human-profile-acceptance` | Accept or revise the meaning, engineering basis, scope, non-goals, and acceptance boundary of each of the nine curren... |
| `resolution_obligations` | `obligation.lifecycle-surfaces.implement-vertical-slices` | Implement each of the nine lifecycle profiles currently required by OR-01 as a versioned contract, fail-closed vertic... |
| `resolution_obligations` | `obligation.lifecycle-surfaces.independent-review` | Review every implemented surface remaining in the current versioned denominator for origin trace, engineering interpr... |
| `resolution_obligations` | `obligation.operational-qualification.execute-bound-profile` | Build and execute a versioned qualification protocol against a closed subject and environment manifest, covering the ... |
| `resolution_obligations` | `obligation.operational-qualification.human-envelope` | Choose the deployment profile, workload and duration envelope, providers and platforms, acceptable failure and recove... |
| `resolution_obligations` | `obligation.operational-qualification.independent-review` | Independently review and, where required, observe the qualification subject, environment, workload, failure injection... |
| `resolution_obligations` | `obligation.projection.generate-or-compare` | Generate the projection deterministically or check every projected state and evidence cell against an explicit mapping. |
| `resolution_obligations` | `obligation.proof-graph.human-migration-adoption` | Accept, revise, defer, or reject the proof-obligation profile and any v1 default, v0 support, retirement, and downgra... |
| `resolution_obligations` | `obligation.proof-graph.implement-replayable-contract` | Strengthen v0 cross-field validation and implement opt-in v1 typed proof obligations and an acyclic derivation graph ... |
| `resolution_obligations` | `obligation.proof-graph.independent-adversarial-review` | Independently challenge subject and proposition substitution, rule and evidence replacement, aggregate-state inconsis... |
| `resolution_obligations` | `obligation.register-completeness.human-denominator-adoption` | Accept, revise, defer, or reject the exact denominator, disposition vocabulary, non-applicability policy, reactivatio... |
| `resolution_obligations` | `obligation.register-completeness.implement-denominator-and-dispositions` | Implement the charter denominator and exactly-one disposition contract for declared unproven scope, residual risks, r... |
| `resolution_obligations` | `obligation.register-completeness.independent-denominator-review` | Independently review the denominator, source locators, disposition meanings, non-applicability boundary, handoff pres... |
| `resolution_obligations` | `obligation.repair-loop.human-outcome-policy` | Choose repair outcomes, error costs, escalation rules, acceptance boundary, and the evidence needed before a repair m... |
| `resolution_obligations` | `obligation.repair-loop.implement-and-reaudit` | Implement machine-readable repair targets, caller-owned execution handoff, before-after re-audit, regression detectio... |
| `resolution_obligations` | `obligation.repair-loop.independent-effect-review` | Evaluate repair effect, regression, unresolved remainder, and escalation correctness on independently reviewed and ad... |
| `resolution_obligations` | `obligation.requalification.human-validity-policy` | Choose deployment profiles, evidence validity periods, rerun thresholds, and rollback risk policy. |
| `resolution_obligations` | `obligation.requalification.implement-runbook` | Map subject changes to evidence invalidation and provide reproducible requalification procedures. |
| `resolution_obligations` | `obligation.rule-pack.construct-mappings` | Construct versioned criterion mappings with applicability, counterconditions, limitations, and review triggers. |
| `resolution_obligations` | `obligation.rule-pack.human-adoption` | Accept, revise, defer, or reject the selected sources, interpretations, and exception policy. |
| `resolution_obligations` | `obligation.rule-pack.independent-review` | Review the engineering interpretation independently of the implementation author. |
| `resolution_obligations` | `obligation.secure-operation.human-policy` | Adopt or revise the candidate secure-operation criterion and choose intended use, data classes, providers, egress, re... |
| `resolution_obligations` | `obligation.secure-operation.implement-controls` | Implement the adopted profile, fail-closed provider and privilege gates, minimization and redaction, retention contro... |
| `resolution_obligations` | `obligation.secure-operation.independent-review` | Review and challenge the adopted data, provider, privilege, provenance, adversarial-input, resource-exhaustion, reten... |
| `resolution_obligations` | `obligation.secure-operation.verify-nonapplicability-boundary` | Inspect and bind the selected subject, configuration, data classes, provider routes, privilege grants, evidence store... |
| `resolution_obligations` | `obligation.state-derivation.implement-assessment-record` | Add a versioned assessment-record contract that consumes typed evidence effects and records each asserted state-axis ... |
| `resolution_obligations` | `obligation.state-derivation.independent-observation` | Provide independent observations when the selected claim profile requires independence. |
| `resolution_obligations` | `obligation.transition.define-plan-and-prohibitions` | Define opt-in introduction, compatibility and shadow period, entry and abort criteria, public and stored-record migra... |
| `resolution_obligations` | `obligation.transition.human-cutover-decision` | Accept, revise, defer, or reject only the selected cutover, compatibility period, rollback authority, disposal, and r... |
| `resolution_obligations` | `obligation.transition.independent-rehearsal` | Independently observe representative shadow comparison, public and stored-record migration, compatibility, abort, rol... |
| `resolution_paths` | `resolution-path.action-assurance.implemented-and-challenged` |  |
| `resolution_paths` | `resolution-path.analyzer-effectiveness.common-holdout-and-independent-review` |  |
| `resolution_paths` | `resolution-path.assurance-profile.accepted-implemented-challenged` |  |
| `resolution_paths` | `resolution-path.engineering-rule-pack.governed-and-reviewed` |  |
| `resolution_paths` | `resolution-path.field-validation.accepted-and-independently-labeled` |  |
| `resolution_paths` | `resolution-path.human-use.policy-material-and-independent-evaluation` |  |
| `resolution_paths` | `resolution-path.lifecycle-composition.accepted-implemented-and-reviewed` |  |
| `resolution_paths` | `resolution-path.lifecycle-surfaces.current-or-revised-denominator` |  |
| `resolution_paths` | `resolution-path.operational-qualification.selected-profile` |  |
| `resolution_paths` | `resolution-path.projection.generated-or-value-compared` |  |
| `resolution_paths` | `resolution-path.proof-graph.implemented-reviewed-and-human-adopted` |  |
| `resolution_paths` | `resolution-path.register-completeness.implemented-reviewed-and-human-adopted` |  |
| `resolution_paths` | `resolution-path.repair-loop.full-cycle` |  |
| `resolution_paths` | `resolution-path.requalification.policy-and-runbook` |  |
| `resolution_paths` | `resolution-path.secure-operation.adopted-profile` |  |
| `resolution_paths` | `resolution-path.secure-operation.verified-nonapplicability` |  |
| `resolution_paths` | `resolution-path.state-derivation.profile-with-independence` |  |
| `resolution_paths` | `resolution-path.state-derivation.profile-without-independence` |  |
| `resolution_paths` | `resolution-path.transition.evidence-complete-human-decision` |  |
| `state_profiles` | `state.boundary-verified` | 境界局所検証済み |
| `state_profiles` | `state.field-not-evaluated` | 評価設計のみ・実務未評価 |
| `state_profiles` | `state.known-incomplete` | 既知の未充足 |
| `state_profiles` | `state.local-verified-not-validated` | 局所検証済み・実務未妥当化 |
| `state_profiles` | `state.missing-not-evaluated` | 欠落・未検証 |
| `state_profiles` | `state.missing-refuted` | 必要機構欠落により非充足 |
| `state_profiles` | `state.not-assessed` | 未評価 |
| `state_profiles` | `state.partial-challenged` | 部分実装・反証材料あり |
| `state_profiles` | `state.partial-inconclusive` | 部分実装・結論不能 |
| `state_profiles` | `state.stale-partial-evidence` | 旧観測による部分材料 |
| `unresolved_items` | `unresolved.action-evidence-and-authenticity-mechanism` | 行為証拠・真正性機構 |
| `unresolved_items` | `unresolved.analyzer-route-effectiveness-and-incremental-value` | 解析 route 別の発見性能・増分価値 |
| `unresolved_items` | `unresolved.assurance-profile-and-public-trust-basis` | 保証 profile と公開高信頼級の根拠契約 |
| `unresolved_items` | `unresolved.engineering-rule-pack-governance` | 体系知 rule pack の採用統治 |
| `unresolved_items` | `unresolved.evidence-expiry-and-requalification` | 証拠失効・再資格方針 |
| `unresolved_items` | `unresolved.field-population-and-thresholds` | 実務母集団・費用・閾値 |
| `unresolved_items` | `unresolved.human-operational-use` | coding agent・人間の責任適合利用と理解可能性 |
| `unresolved_items` | `unresolved.lifecycle-surface-vertical-slices` | 原点九工程面の profile・契約・縦断実装 |
| `unresolved_items` | `unresolved.lifecycle-trace-and-composition` | 工程横断 trace・意味合成機構 |
| `unresolved_items` | `unresolved.operational-qualification` | 運用 profile 資格確認の設計・実行・独立査読 |
| `unresolved_items` | `unresolved.projection-value-equivalence` | Markdown 投影の値級一致又は自動生成 |
| `unresolved_items` | `unresolved.proof-obligation-and-assurance-graph-soundness` | proof obligation・assurance graph の閉包と独立再集約 |
| `unresolved_items` | `unresolved.repair-loop-implementation-and-effect` | 修正循環の実装と効果評価 |
| `unresolved_items` | `unresolved.secure-information-handling-and-external-boundaries` | 安全な情報取扱い・外部送信・権限境界の採用 |
| `unresolved_items` | `unresolved.state-evidence-derivation-and-subject-binding` | 状態導出・対象 snapshot 拘束 |
| `unresolved_items` | `unresolved.transition-cutover-rollback-and-retirement` | 移行・cutover・rollback・retirement 証拠 |
| `unresolved_items` | `unresolved.verification-register-completeness` | 検証 register 分母・disposition の有界完全性 |
| `verification_items` | `verification.cross.field-validation` | 実務資料上の妥当性確認 |
| `verification_items` | `verification.cross.human-operational-use` | 人間・coding agent の責任適合利用 |
| `verification_items` | `verification.cross.lifecycle-trace-and-composition` | 工程横断 trace・意味合成 |
| `verification_items` | `verification.cross.operational-qualification` | 運用 profile 資格確認 |
| `verification_items` | `verification.cross.operational-reverification` | 運用・変更影響・再検証 |
| `verification_items` | `verification.cross.register-completeness` | 検証 register の有界完全性 |
| `verification_items` | `verification.cross.secure-and-responsible-operation` | 安全・責任ある情報取扱いと外部境界 |
| `verification_items` | `verification.cross.transition-and-cutover` | 移行・cutover・rollback・retirement 統治 |
| `verification_items` | `verification.or01.discovery-effectiveness` | OR-01 未解決・欠陥の発見性能 |
| `verification_items` | `verification.or01.engineering-knowledge-governance` | OR-01 体系知の根拠統治 |
| `verification_items` | `verification.or01.lifecycle-surface-coverage` | OR-01 工程横断被覆 |
| `verification_items` | `verification.or02.action-occurrence-and-procedure` | OR-02 行為発生・主体・権限・手続適合 |
| `verification_items` | `verification.or02.artifact-provenance-authenticity` | OR-02 成果物来歴・真正性・因果境界 |
| `verification_items` | `verification.or02.bounded-claim-model` | OR-02 限定的立証の主張模型 |
| `verification_items` | `verification.or02.proof-obligation-and-assurance-graph-soundness` | OR-02 proof obligation・assurance graph 健全性 |
| `verification_items` | `verification.or03.human-decision-boundary` | OR-03 人間判断境界 |
| `verification_items` | `verification.or03.repair-effect` | OR-03 修正循環の有効性 |
| `views` | `view.action-assurance` | 行為立証ビュー |
| `views` | `view.discovery-effectiveness` | 発見性能ビュー |
| `views` | `view.local-implementation-conformance` | 局所実装適合ビュー |
| `views` | `view.origin-purpose-coverage` | 原点要求被覆ビュー |
| `views` | `view.repair-and-human-decision` | 修正循環・人間判断ビュー |

## Complete JSON-Pointer Value Appendix

Every source node appears exactly once below. Object records expose their
sorted keys, array records expose their length, and scalar records expose the
complete JSON value. JSON Pointer escaping follows RFC 6901.

Node count: `6128`

```jsonl
{"keys":["$schema","authority_boundary","claim_effect_semantics","evidence_effects","evidence_observations","human_acceptance","implementation_conformance_items","non_goals","notation_profile","record_surface","recorded_at","register_id","schema_version","scope","state_axes","state_profiles","status","title","unresolved_items","upstream_sources","verification_items","views"],"member_count":22,"node_type":"object","pointer":"/"}
{"node_type":"string","pointer":"/$schema","value":"./verification-source.schema.json"}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/authority_boundary"}
{"node_type":"string","pointer":"/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":3,"node_type":"array","pointer":"/authority_boundary/source_may"}
{"node_type":"string","pointer":"/authority_boundary/source_may/0","value":"Define verification items and their relation to origin requirements."}
{"node_type":"string","pointer":"/authority_boundary/source_may/1","value":"Record bounded evidence observations, counterevidence, unproven scope, and revalidation conditions."}
{"node_type":"string","pointer":"/authority_boundary/source_may/2","value":"Expose material for repair and human review."}
{"item_count":4,"node_type":"array","pointer":"/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/authority_boundary/source_must_not/0","value":"Assign work priority or delegate execution."}
{"node_type":"string","pointer":"/authority_boundary/source_must_not/1","value":"Accept residual risk or make final acceptance."}
{"node_type":"string","pointer":"/authority_boundary/source_must_not/2","value":"Turn a test file, fixture pass, analyzer output, or score into unconditional correctness."}
{"node_type":"string","pointer":"/authority_boundary/source_must_not/3","value":"Override the origin requirement, constitution, or public audit-result schemas."}
{"keys":["blocks_claim","does_not_block_claim","partially_blocks_claim"],"member_count":3,"node_type":"object","pointer":"/claim_effect_semantics"}
{"node_type":"string","pointer":"/claim_effect_semantics/blocks_claim","value":"While unresolved, an affected verification or conformance claim cannot have satisfied assurance or terminal assurance."}
{"node_type":"string","pointer":"/claim_effect_semantics/does_not_block_claim","value":"The unresolved item remains visible but does not constrain the assurance state of affected claims."}
{"node_type":"string","pointer":"/claim_effect_semantics/partially_blocks_claim","value":"While unresolved, an affected verification or conformance claim cannot have terminal assurance."}
{"item_count":27,"node_type":"array","pointer":"/evidence_effects"}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/0"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/0/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/0/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/0/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/0/effect_id","value":"effect.origin-requirement.purpose-items.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/0/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/0/evidence_ref/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/evidence_effects/0/evidence_ref/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/evidence_effects/0/evidence_ref/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/0/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/0/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/0/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/0/label_hint","value":"OR-01 工程横断被覆"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/0/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/1/entity_id","value":"verification.or03.human-decision-boundary"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/1/label_hint","value":"人間判断境界"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/0/item_refs/2"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/2/entity_id","value":"verification.cross.secure-and-responsible-operation"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/2/label_hint","value":"安全・責任ある運用境界"}
{"node_type":"string","pointer":"/evidence_effects/0/item_refs/2/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/0/limitations"}
{"node_type":"string","pointer":"/evidence_effects/0/limitations/0","value":"The wording snapshot contextualizes the propositions only; it does not support their implementation, verification, validation, or assurance state."}
{"node_type":"string","pointer":"/evidence_effects/0/observation_locator","value":"../docs/prototypes/origin-requirement.md"}
{"node_type":"string","pointer":"/evidence_effects/0/proposition_scope","value":"The bound origin-requirement snapshot defines the lifecycle denominator, retained human decision ownership, and the authority and danger context from which the candidate secure-operation proposition is derived."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/1"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/1/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/1/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/1/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/1/effect_id","value":"effect.constitution.normative-items.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/1/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/1/evidence_ref/entity_id","value":"evidence.constitution.snapshot.2026-08-24"}
{"node_type":"string","pointer":"/evidence_effects/1/evidence_ref/label_hint","value":"v1 憲法 snapshot"}
{"node_type":"string","pointer":"/evidence_effects/1/evidence_ref/reference_kind","value":"ref"}
{"item_count":5,"node_type":"array","pointer":"/evidence_effects/1/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/1/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/0/entity_id","value":"verification.or01.engineering-knowledge-governance"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/0/label_hint","value":"OR-01 体系知の根拠統治"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/1/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/1/entity_id","value":"verification.or02.bounded-claim-model"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/1/label_hint","value":"限定的立証の主張模型"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/1/item_refs/2"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/2/entity_id","value":"verification.or03.repair-effect"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/2/label_hint","value":"修正効果"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/1/item_refs/3"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/3/entity_id","value":"verification.or03.human-decision-boundary"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/3/label_hint","value":"人間判断境界"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/1/item_refs/4"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/4/entity_id","value":"verification.cross.secure-and-responsible-operation"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/4/label_hint","value":"安全・責任ある運用境界"}
{"node_type":"string","pointer":"/evidence_effects/1/item_refs/4/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/1/limitations"}
{"node_type":"string","pointer":"/evidence_effects/1/limitations/0","value":"Normative wording is not implementation conformance, execution evidence, field validity, or final acceptance."}
{"node_type":"string","pointer":"/evidence_effects/1/observation_locator","value":"../constitution/semantic-guard-constitution.yaml"}
{"node_type":"string","pointer":"/evidence_effects/1/proposition_scope","value":"The bound constitution snapshot supplies the normative vocabulary, invariants, authority boundary, bounded-assurance dimensions, repair intent, and human-decision separation used to formulate these verification propositions."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/2"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/2/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/2/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/2/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/2/effect_id","value":"effect.historical-review.governance-action-authenticity.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/2/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/2/evidence_ref/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/evidence_effects/2/evidence_ref/label_hint","value":"全体監査の歴史的観測"}
{"node_type":"string","pointer":"/evidence_effects/2/evidence_ref/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/2/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/2/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/0/entity_id","value":"verification.or01.engineering-knowledge-governance"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/0/label_hint","value":"OR-01 体系知の根拠統治"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/2/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/1/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/1/label_hint","value":"行為発生・主体・権限・手続適合"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/2/item_refs/2"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/2/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/2/label_hint","value":"成果物来歴・真正性・因果境界"}
{"node_type":"string","pointer":"/evidence_effects/2/item_refs/2/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/2/limitations"}
{"node_type":"string","pointer":"/evidence_effects/2/limitations/0","value":"The old subject snapshot is unbound and stale; its separate challenge or refutation effects do not establish the current implementation state."}
{"node_type":"string","pointer":"/evidence_effects/2/observation_locator","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"node_type":"string","pointer":"/evidence_effects/2/proposition_scope","value":"The historical assessment supplies prior observed gaps that motivate governance, action-occurrence, and authenticity propositions in the current register."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/3"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/3/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/3/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/3/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/3/effect_id","value":"effect.lifecycle.integrated-record.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/3/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/3/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/3/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/3/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/3/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/3/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/3/item_refs/0/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"node_type":"string","pointer":"/evidence_effects/3/item_refs/0/label_hint","value":"OR-01 工程横断被覆"}
{"node_type":"string","pointer":"/evidence_effects/3/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/3/limitations"}
{"node_type":"string","pointer":"/evidence_effects/3/limitations/0","value":"It names only a subset of the current OR-01 denominator and is unbound to a closed tested-source manifest."}
{"node_type":"string","pointer":"/evidence_effects/3/observation_locator","value":"integrated-verification-2026-07-16.json#/next_actions/4"}
{"node_type":"string","pointer":"/evidence_effects/3/proposition_scope","value":"The dated next-action record identifies additional lifecycle vertical slices as future work and therefore supplies located implementation context for the lifecycle-coverage assessment."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/4"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/4/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/4/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/4/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/4/effect_id","value":"effect.discovery.integrated-record.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/4/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/4/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/4/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/4/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/4/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/4/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/4/item_refs/0/entity_id","value":"verification.or01.discovery-effectiveness"}
{"node_type":"string","pointer":"/evidence_effects/4/item_refs/0/label_hint","value":"OR-01 未解決・欠陥の発見性能"}
{"node_type":"string","pointer":"/evidence_effects/4/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/4/limitations"}
{"node_type":"string","pointer":"/evidence_effects/4/limitations/0","value":"The selected smoke cases and unbound source do not support target-population discovery effectiveness."}
{"node_type":"string","pointer":"/evidence_effects/4/observation_locator","value":"integrated-verification-2026-07-16.json#/real_nlp_verification"}
{"node_type":"string","pointer":"/evidence_effects/4/proposition_scope","value":"The integrated record locates the five-case NLP execution summary used to frame the bounded discovery implementation context."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/5"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/5/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/5/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/5/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/5/effect_id","value":"effect.real-nlp.discovery-field.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/5/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/5/evidence_ref/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/5/evidence_ref/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/evidence_effects/5/evidence_ref/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/evidence_effects/5/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/5/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/5/item_refs/0/entity_id","value":"verification.or01.discovery-effectiveness"}
{"node_type":"string","pointer":"/evidence_effects/5/item_refs/0/label_hint","value":"OR-01 未解決・欠陥の発見性能"}
{"node_type":"string","pointer":"/evidence_effects/5/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/5/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/5/item_refs/1/entity_id","value":"verification.cross.field-validation"}
{"node_type":"string","pointer":"/evidence_effects/5/item_refs/1/label_hint","value":"実務資料上の妥当性確認"}
{"node_type":"string","pointer":"/evidence_effects/5/item_refs/1/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/5/limitations"}
{"node_type":"string","pointer":"/evidence_effects/5/limitations/0","value":"Hand-selected smoke cases are neither an adjudicated target population nor an accuracy or practical-value estimate."}
{"node_type":"string","pointer":"/evidence_effects/5/observation_locator","value":"real-nlp-smoke-2026-07-16.json#/cases"}
{"node_type":"string","pointer":"/evidence_effects/5/proposition_scope","value":"The located five-case record provides bounded real-provider behavior relevant to discovery and field-evaluation design."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/6"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/6/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/6/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/6/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/6/effect_id","value":"effect.bounded-claim.integrated-schema.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/6/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/6/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/6/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/6/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/6/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/6/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/6/item_refs/0/entity_id","value":"verification.or02.bounded-claim-model"}
{"node_type":"string","pointer":"/evidence_effects/6/item_refs/0/label_hint","value":"OR-02 限定的立証の主張模型"}
{"node_type":"string","pointer":"/evidence_effects/6/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/6/limitations"}
{"node_type":"string","pointer":"/evidence_effects/6/limitations/0","value":"Schema self-validation does not support action occurrence, elevated trust basis, authenticity, or field validity."}
{"node_type":"string","pointer":"/evidence_effects/6/observation_locator","value":"integrated-verification-2026-07-16.json#/vnext_verification/json_schemas"}
{"node_type":"string","pointer":"/evidence_effects/6/proposition_scope","value":"The dated record reports public-schema self-validation and supplies context for the partial bounded-claim implementation assessment."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/7"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/7/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/7/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/7/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/7/effect_id","value":"effect.action-artifact.integrated-omission.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/7/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/7/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/7/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/7/evidence_ref/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/evidence_effects/7/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/7/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/7/item_refs/0/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"node_type":"string","pointer":"/evidence_effects/7/item_refs/0/label_hint","value":"行為発生・主体・権限・手続適合"}
{"node_type":"string","pointer":"/evidence_effects/7/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/7/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/7/item_refs/1/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"node_type":"string","pointer":"/evidence_effects/7/item_refs/1/label_hint","value":"成果物来歴・真正性・因果境界"}
{"node_type":"string","pointer":"/evidence_effects/7/item_refs/1/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/7/limitations"}
{"node_type":"string","pointer":"/evidence_effects/7/limitations/0","value":"The omission record is unbound and self-reported; the separate historical refutation effect supplies the current provisional refuted state."}
{"node_type":"string","pointer":"/evidence_effects/7/observation_locator","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/6"}
{"node_type":"string","pointer":"/evidence_effects/7/proposition_scope","value":"The dated record explicitly lists signatures, trusted time, actor identity, action occurrence, causal proof, and artifact authenticity as unimplemented or unverified context for both propositions."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/8"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/8/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/8/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/8/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/8/effect_id","value":"effect.repair.integrated-acceptance.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/8/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/8/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/8/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/8/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/8/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/8/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/8/item_refs/0/entity_id","value":"verification.or03.repair-effect"}
{"node_type":"string","pointer":"/evidence_effects/8/item_refs/0/label_hint","value":"修正効果"}
{"node_type":"string","pointer":"/evidence_effects/8/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/8/limitations"}
{"node_type":"string","pointer":"/evidence_effects/8/limitations/0","value":"The record contains no finding-to-repair effectiveness observation and therefore does not support repair implementation or effect."}
{"node_type":"string","pointer":"/evidence_effects/8/observation_locator","value":"integrated-verification-2026-07-16.json#/acceptance_state"}
{"node_type":"string","pointer":"/evidence_effects/8/proposition_scope","value":"The dated record separates implementation verification, human acceptance, production readiness, and cutover authorization, providing context for why repair effect must remain a separate proposition."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/9"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/9/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/9/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/9/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/9/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/9/effect","value":"supports"}
{"node_type":"string","pointer":"/evidence_effects/9/effect_id","value":"effect.human-boundary.integrated-acceptance.supports"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/9/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/9/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/9/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/9/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/9/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/9/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/9/item_refs/0/entity_id","value":"verification.or03.human-decision-boundary"}
{"node_type":"string","pointer":"/evidence_effects/9/item_refs/0/label_hint","value":"人間判断境界"}
{"node_type":"string","pointer":"/evidence_effects/9/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/9/limitations"}
{"node_type":"string","pointer":"/evidence_effects/9/limitations/0","value":"The observation is unbound, self-reported, and does not validate whether future human materials are understandable or complete; support remains provisional."}
{"node_type":"string","pointer":"/evidence_effects/9/observation_locator","value":"integrated-verification-2026-07-16.json#/acceptance_state"}
{"node_type":"string","pointer":"/evidence_effects/9/proposition_scope","value":"The dated record keeps human acceptance pending and default cutover unauthorized while separately reporting local implementation verification, supporting the bounded claim that automated audit status does not replace human acceptance."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/10"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/10/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/10/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/10/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/10/effect_id","value":"effect.field.integrated-unverified.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/10/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/10/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/10/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/10/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/10/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/10/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/10/item_refs/0/entity_id","value":"verification.cross.field-validation"}
{"node_type":"string","pointer":"/evidence_effects/10/item_refs/0/label_hint","value":"実務資料上の妥当性確認"}
{"node_type":"string","pointer":"/evidence_effects/10/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/10/limitations"}
{"node_type":"string","pointer":"/evidence_effects/10/limitations/0","value":"This records a known evidence gap and does not support a field-validity state."}
{"node_type":"string","pointer":"/evidence_effects/10/observation_locator","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/0"}
{"node_type":"string","pointer":"/evidence_effects/10/proposition_scope","value":"The dated record explicitly lists adjudicated real-work evaluation, statistical recall, precision, and catastrophic false-satisfaction measurement as unverified."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/11"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/11/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/11/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/11/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/11/effect_id","value":"effect.operational.integrated-unverified.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/11/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/11/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/11/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/11/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/11/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/11/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/11/item_refs/0/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/evidence_effects/11/item_refs/0/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/evidence_effects/11/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/11/limitations"}
{"node_type":"string","pointer":"/evidence_effects/11/limitations/0","value":"It does not supply a closed tested-source manifest, expiry policy, or operational qualification."}
{"node_type":"string","pointer":"/evidence_effects/11/observation_locator","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/7"}
{"node_type":"string","pointer":"/evidence_effects/11/proposition_scope","value":"The dated record's explicit operational-test omissions provide located context for the requalification proposition."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/12"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/12/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/12/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/12/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/12/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/12/effect","value":"supports"}
{"node_type":"string","pointer":"/evidence_effects/12/effect_id","value":"effect.local-conformance.integrated-suite.supports"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/12/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/12/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/12/evidence_ref/reference_kind","value":"ref"}
{"item_count":20,"node_type":"array","pointer":"/evidence_effects/12/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/0/entity_id","value":"conformance.INV-VN-001"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/0/label_hint","value":"未解決保存"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/1/entity_id","value":"conformance.INV-VN-002"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/1/label_hint","value":"仮通過"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/2"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/2/entity_id","value":"conformance.INV-VN-003"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/2/label_hint","value":"終局充足閉包"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/3"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/3/entity_id","value":"conformance.INV-VN-004"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/3/label_hint","value":"必須解析器障害"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/4"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/4/entity_id","value":"conformance.INV-VN-005"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/4/label_hint","value":"候補権限上限"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/5"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/5/entity_id","value":"conformance.INV-VN-006"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/5/label_hint","value":"引用等の非昇格"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/5/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/6"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/6/entity_id","value":"conformance.INV-VN-007"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/6/label_hint","value":"開いた自由文"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/6/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/7"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/7/entity_id","value":"conformance.INV-VN-009"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/7/label_hint","value":"score 非確率"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/7/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/8"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/8/entity_id","value":"conformance.INV-VN-010"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/8/label_hint","value":"schema/digest 閉包"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/8/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/9"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/9/entity_id","value":"conformance.INV-VN-011"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/9/label_hint","value":"語彙一致非証明"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/9/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/10"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/10/entity_id","value":"conformance.INV-VN-012"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/10/label_hint","value":"解析器能力・被覆"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/10/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/11"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/11/entity_id","value":"conformance.INV-VN-013"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/11/label_hint","value":"公開集約整合"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/11/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/12"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/12/entity_id","value":"conformance.INV-VN-014"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/12/label_hint","value":"入力・観測同一性分離"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/12/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/13"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/13/entity_id","value":"conformance.stage.input-boundary"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/13/label_hint","value":"入力境界"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/13/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/14"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/14/entity_id","value":"conformance.stage.provisional-direct-audit"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/14/label_hint","value":"直接仮判定"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/14/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/15"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/15/entity_id","value":"conformance.stage.residual-risk-gate"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/15/label_hint","value":"残余危険門"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/15/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/16"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/16/entity_id","value":"conformance.stage.obligation-reaggregation"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/16/label_hint","value":"義務別再集約"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/16/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/17"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/17/entity_id","value":"conformance.stage.decision-request-materialization"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/17/label_hint","value":"判断要求生成"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/17/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/18"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/18/entity_id","value":"conformance.completeness.provider-accounting"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/18/label_hint","value":"解析器実行会計"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/18/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/12/item_refs/19"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/19/entity_id","value":"conformance.completeness.public-result"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/19/label_hint","value":"公開結果完全性"}
{"node_type":"string","pointer":"/evidence_effects/12/item_refs/19/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/12/limitations"}
{"node_type":"string","pointer":"/evidence_effects/12/limitations/0","value":"The aggregate record does not locate each individual test result and lacks a closed tested-source manifest; support is provisional, unbound, and not field validation."}
{"node_type":"string","pointer":"/evidence_effects/12/observation_locator","value":"integrated-verification-2026-07-16.json#/vnext_verification/unit_and_contract_tests/0"}
{"node_type":"string","pointer":"/evidence_effects/12/proposition_scope","value":"The dated record reports a zero-failure v1 unit and contract suite that includes the named local invariant, stage, and completeness checks."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/13"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/13/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/13/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/13/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/13/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/13/effect","value":"supports"}
{"node_type":"string","pointer":"/evidence_effects/13/effect_id","value":"effect.real-nlp.provider-paths.supports"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/13/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/13/evidence_ref/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/13/evidence_ref/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/evidence_effects/13/evidence_ref/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/13/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/13/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/0/entity_id","value":"conformance.INV-VN-012"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/0/label_hint","value":"解析器能力・被覆"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/13/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/1/entity_id","value":"conformance.stage.morphology"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/1/label_hint","value":"形態素解析"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/13/item_refs/2"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/2/entity_id","value":"conformance.completeness.provider-accounting"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/2/label_hint","value":"解析器実行会計"}
{"node_type":"string","pointer":"/evidence_effects/13/item_refs/2/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/13/limitations"}
{"node_type":"string","pointer":"/evidence_effects/13/limitations/0","value":"The source and analyzer resources are unbound, GiNZA is partial, and five smoke cases do not establish semantic accuracy or field validity."}
{"node_type":"string","pointer":"/evidence_effects/13/observation_locator","value":"real-nlp-smoke-2026-07-16.json#/cases"}
{"node_type":"string","pointer":"/evidence_effects/13/proposition_scope","value":"The five located cases report real morphology execution plus explicit requested, fulfilled, and missing dependency capabilities, supporting the bounded provider-accounting and morphology-path claims."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/14"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/14/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/14/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/14/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/14/effect_id","value":"effect.partial-conformance.integrated-record.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/14/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/14/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/14/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/14/evidence_ref/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/evidence_effects/14/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/14/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/0/entity_id","value":"conformance.INV-VN-008"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/0/label_hint","value":"人間危険受容の非消去"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/14/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/1/entity_id","value":"conformance.stage.versioned-lifting-rule"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/1/label_hint","value":"版付き導出"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/14/item_refs/2"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/2/entity_id","value":"conformance.stage.llm-candidate"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/2/label_hint","value":"LLM候補"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/14/item_refs/3"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/3/entity_id","value":"conformance.migration.legacy-characterization"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/3/label_hint","value":"旧版特性試験"}
{"node_type":"string","pointer":"/evidence_effects/14/item_refs/3/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/14/limitations"}
{"node_type":"string","pointer":"/evidence_effects/14/limitations/0","value":"The aggregate record is not proposition-specific, is unbound, and does not close each item's remaining obligations."}
{"node_type":"string","pointer":"/evidence_effects/14/observation_locator","value":"integrated-verification-2026-07-16.json#/vnext_verification/unit_and_contract_tests/0"}
{"node_type":"string","pointer":"/evidence_effects/14/proposition_scope","value":"The dated aggregate test record supplies implementation context for these deliberately partial or challenged conformance items without supporting a satisfied assurance state."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/15"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/15/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/15/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/15/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/15/effect_id","value":"effect.dependency-analysis.real-nlp.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/15/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/15/evidence_ref/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/15/evidence_ref/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/evidence_effects/15/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/15/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/15/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/15/item_refs/0/entity_id","value":"conformance.stage.dependency-analysis-bundle"}
{"node_type":"string","pointer":"/evidence_effects/15/item_refs/0/label_hint","value":"依存構造解析束"}
{"node_type":"string","pointer":"/evidence_effects/15/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/15/limitations"}
{"node_type":"string","pointer":"/evidence_effects/15/limitations/0","value":"This supports a partial implementation context only and does not establish dependency-analysis accuracy or complete capability coverage."}
{"node_type":"string","pointer":"/evidence_effects/15/observation_locator","value":"real-nlp-smoke-2026-07-16.json#/provider_contract"}
{"node_type":"string","pointer":"/evidence_effects/15/proposition_scope","value":"The provider contract locates the requested dependency bundle and its explicitly missing coreference capability."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/16"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/16/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/16/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/16/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/16/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/16/effect","value":"supports"}
{"node_type":"string","pointer":"/evidence_effects/16/effect_id","value":"effect.legacy-baseline.integrated-record.supports"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/16/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/16/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/16/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/16/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/16/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/16/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/16/item_refs/0/entity_id","value":"conformance.migration.legacy-baseline"}
{"node_type":"string","pointer":"/evidence_effects/16/item_refs/0/label_hint","value":"旧版基線"}
{"node_type":"string","pointer":"/evidence_effects/16/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/16/limitations"}
{"node_type":"string","pointer":"/evidence_effects/16/limitations/0","value":"The record is unbound and does not make legacy behavior a correctness oracle or prove host and runtime authenticity."}
{"node_type":"string","pointer":"/evidence_effects/16/observation_locator","value":"integrated-verification-2026-07-16.json#/legacy_verification/baseline"}
{"node_type":"string","pointer":"/evidence_effects/16/proposition_scope","value":"The dated record reports a matched legacy baseline manifest and runtime asset count, supporting the bounded local baseline-conformance state."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","lifecycle_surfaces","limitations","observation_locator","proposition_scope"],"member_count":9,"node_type":"object","pointer":"/evidence_effects/17"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/17/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/17/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/17/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/17/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/17/effect","value":"supports"}
{"node_type":"string","pointer":"/evidence_effects/17/effect_id","value":"effect.lifecycle.requirement-slice.integrated-suite.supports"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/17/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/17/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/17/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/17/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/17/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/17/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/17/item_refs/0/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"node_type":"string","pointer":"/evidence_effects/17/item_refs/0/label_hint","value":"OR-01 工程横断被覆"}
{"node_type":"string","pointer":"/evidence_effects/17/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/17/lifecycle_surfaces"}
{"node_type":"string","pointer":"/evidence_effects/17/lifecycle_surfaces/0","value":"requirement"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/17/limitations"}
{"node_type":"string","pointer":"/evidence_effects/17/limitations/0","value":"The aggregate record is unbound and not surface-specific at individual-test granularity; support remains provisional and cannot override the parent refutation from nine missing surfaces."}
{"node_type":"string","pointer":"/evidence_effects/17/observation_locator","value":"integrated-verification-2026-07-16.json#/vnext_verification/unit_and_contract_tests/0"}
{"node_type":"string","pointer":"/evidence_effects/17/proposition_scope","value":"The dated zero-failure v1 suite supports only the local implemented and verified state assigned to the requirement lifecycle surface, not completion of the parent ten-surface proposition."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/18"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/18/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/18/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/18/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/18/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/18/effect","value":"refutes"}
{"node_type":"string","pointer":"/evidence_effects/18/effect_id","value":"effect.lifecycle-surface.integrated-next-action.refutes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/18/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/18/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/18/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/18/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/18/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/18/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/18/item_refs/0/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"node_type":"string","pointer":"/evidence_effects/18/item_refs/0/label_hint","value":"OR-01 工程横断被覆"}
{"node_type":"string","pointer":"/evidence_effects/18/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/18/limitations"}
{"node_type":"string","pointer":"/evidence_effects/18/limitations/0","value":"The record names only a subset of the nine missing OR-01 surfaces and is unbound to the current source snapshot; one missing surface is sufficient to refute universal completion, but not to enumerate the current denominator."}
{"node_type":"string","pointer":"/evidence_effects/18/observation_locator","value":"integrated-verification-2026-07-16.json#/next_actions/4"}
{"node_type":"string","pointer":"/evidence_effects/18/proposition_scope","value":"The dated record calls for additional plan, diff, convention, finish, and acceptance-material vertical slices before cutover, which is a counterexample to the proposition that every OR-01 lifecycle surface already has a v1 vertical slice."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/19"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/19/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/19/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/19/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/19/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/19/effect","value":"challenges"}
{"node_type":"string","pointer":"/evidence_effects/19/effect_id","value":"effect.engineering-governance.historical-review.challenges"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/19/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/19/evidence_ref/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/evidence_effects/19/evidence_ref/label_hint","value":"全体監査の歴史的観測"}
{"node_type":"string","pointer":"/evidence_effects/19/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/19/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/19/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/19/item_refs/0/entity_id","value":"verification.or01.engineering-knowledge-governance"}
{"node_type":"string","pointer":"/evidence_effects/19/item_refs/0/label_hint","value":"OR-01 体系知の根拠統治"}
{"node_type":"string","pointer":"/evidence_effects/19/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/19/limitations"}
{"node_type":"string","pointer":"/evidence_effects/19/limitations/0","value":"The assessment is stale and its subject snapshot is unbound; it cannot establish the current implementation state without reinspection."}
{"node_type":"string","pointer":"/evidence_effects/19/observation_locator","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"node_type":"string","pointer":"/evidence_effects/19/proposition_scope","value":"The historical assessment reports missing engineering-rule governance and therefore challenges completeness of the current engineering-knowledge proposition."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/20"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/20/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/20/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/20/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/20/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/20/effect","value":"challenges"}
{"node_type":"string","pointer":"/evidence_effects/20/effect_id","value":"effect.discovery.real-nlp-missing-coreference.challenges"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/20/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/20/evidence_ref/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/20/evidence_ref/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/evidence_effects/20/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/20/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/20/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/20/item_refs/0/entity_id","value":"verification.or01.discovery-effectiveness"}
{"node_type":"string","pointer":"/evidence_effects/20/item_refs/0/label_hint","value":"OR-01 未解決・欠陥の発見性能"}
{"node_type":"string","pointer":"/evidence_effects/20/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/20/limitations"}
{"node_type":"string","pointer":"/evidence_effects/20/limitations/0","value":"This is one declared capability gap in a five-case smoke record, not a target-population discovery estimate."}
{"node_type":"string","pointer":"/evidence_effects/20/observation_locator","value":"real-nlp-smoke-2026-07-16.json#/provider_contract/expected_missing_dependency_capabilities/0"}
{"node_type":"string","pointer":"/evidence_effects/20/proposition_scope","value":"The selected dependency provider explicitly lacks coreference_candidate, challenging discovery coverage for relations that depend on reference resolution."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/21"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/21/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/21/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/21/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/21/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/21/effect","value":"challenges"}
{"node_type":"string","pointer":"/evidence_effects/21/effect_id","value":"effect.bounded-claim.public-trust-basis.challenges"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/21/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/21/evidence_ref/entity_id","value":"evidence.public-trust-basis-inspection.2026-07-17"}
{"node_type":"string","pointer":"/evidence_effects/21/evidence_ref/label_hint","value":"公開 provenance 信頼根拠欄の欠落観測"}
{"node_type":"string","pointer":"/evidence_effects/21/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/21/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/21/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/21/item_refs/0/entity_id","value":"verification.or02.bounded-claim-model"}
{"node_type":"string","pointer":"/evidence_effects/21/item_refs/0/label_hint","value":"OR-02 限定的立証の主張模型"}
{"node_type":"string","pointer":"/evidence_effects/21/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/21/limitations"}
{"node_type":"string","pointer":"/evidence_effects/21/limitations/0","value":"The located provenance contract does not prove consumer misuse; the challenge concerns missing public contract constraints."}
{"node_type":"string","pointer":"/evidence_effects/21/observation_locator","value":"../schemas/common.schema.json#/$defs/provenance_record"}
{"node_type":"string","pointer":"/evidence_effects/21/proposition_scope","value":"The public trust_class enum admits independently_observed, signed, and formally_verified without conditional basis fields, challenging the acceptance criterion that elevated claims fail closed when their mechanism and trust basis are absent."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/22"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/22/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/22/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/22/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/22/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/22/effect","value":"refutes"}
{"node_type":"string","pointer":"/evidence_effects/22/effect_id","value":"effect.action-occurrence.historical-review.refutes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/22/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/22/evidence_ref/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/evidence_effects/22/evidence_ref/label_hint","value":"全体監査の歴史的観測"}
{"node_type":"string","pointer":"/evidence_effects/22/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/22/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/22/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/22/item_refs/0/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"node_type":"string","pointer":"/evidence_effects/22/item_refs/0/label_hint","value":"行為発生・主体・権限・手続適合"}
{"node_type":"string","pointer":"/evidence_effects/22/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/22/limitations"}
{"node_type":"string","pointer":"/evidence_effects/22/limitations/0","value":"The refutation is provisional for the current repository because the historical subject snapshot is stale and unbound."}
{"node_type":"string","pointer":"/evidence_effects/22/observation_locator","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"node_type":"string","pointer":"/evidence_effects/22/proposition_scope","value":"The historical assessment reports missing action-event, actor, authority, and independent-observer evidence, refuting the then-current occurrence-and-procedure capability claim."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/23"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/23/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/23/claim_dimensions/0","value":"implementation"}
{"node_type":"string","pointer":"/evidence_effects/23/claim_dimensions/1","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/23/claim_dimensions/2","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/23/effect","value":"refutes"}
{"node_type":"string","pointer":"/evidence_effects/23/effect_id","value":"effect.artifact-authenticity.historical-review.refutes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/23/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/23/evidence_ref/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/evidence_effects/23/evidence_ref/label_hint","value":"全体監査の歴史的観測"}
{"node_type":"string","pointer":"/evidence_effects/23/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/23/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/23/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/23/item_refs/0/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"node_type":"string","pointer":"/evidence_effects/23/item_refs/0/label_hint","value":"成果物来歴・真正性・因果境界"}
{"node_type":"string","pointer":"/evidence_effects/23/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/23/limitations"}
{"node_type":"string","pointer":"/evidence_effects/23/limitations/0","value":"The refutation is provisional for the current repository because the historical subject snapshot is stale and unbound."}
{"node_type":"string","pointer":"/evidence_effects/23/observation_locator","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"node_type":"string","pointer":"/evidence_effects/23/proposition_scope","value":"The historical assessment reports absent original-evidence rechecking, authenticity, and provenance mechanisms, refuting the then-current artifact-provenance and authenticity capability claim."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/24"}
{"item_count":3,"node_type":"array","pointer":"/evidence_effects/24/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/24/claim_dimensions/0","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/24/claim_dimensions/1","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/24/claim_dimensions/2","value":"freshness"}
{"node_type":"string","pointer":"/evidence_effects/24/effect","value":"challenges"}
{"node_type":"string","pointer":"/evidence_effects/24/effect_id","value":"effect.operational-reverification.integrated-record.challenges"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/24/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/24/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/24/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/24/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/24/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/24/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/24/item_refs/0/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/evidence_effects/24/item_refs/0/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/evidence_effects/24/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/24/limitations"}
{"node_type":"string","pointer":"/evidence_effects/24/limitations/0","value":"This located omission does not enumerate every manifest, evidence-expiry, or recovery gap; other unreferenced evidence may exist elsewhere."}
{"node_type":"string","pointer":"/evidence_effects/24/observation_locator","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/7"}
{"node_type":"string","pointer":"/evidence_effects/24/proposition_scope","value":"The dated execution record explicitly leaves long-duration, concurrency, load, denial-of-service, and cross-platform evidence unverified, challenging use of that record as current operational qualification."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/25"}
{"item_count":2,"node_type":"array","pointer":"/evidence_effects/25/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/25/claim_dimensions/0","value":"verification"}
{"node_type":"string","pointer":"/evidence_effects/25/claim_dimensions/1","value":"assurance"}
{"node_type":"string","pointer":"/evidence_effects/25/effect","value":"challenges"}
{"node_type":"string","pointer":"/evidence_effects/25/effect_id","value":"effect.legacy-characterization.known-failures.challenges"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/25/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/25/evidence_ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_effects/25/evidence_ref/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/evidence_effects/25/evidence_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/25/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/25/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/25/item_refs/0/entity_id","value":"conformance.migration.legacy-characterization"}
{"node_type":"string","pointer":"/evidence_effects/25/item_refs/0/label_hint","value":"旧版特性試験"}
{"node_type":"string","pointer":"/evidence_effects/25/item_refs/0/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/25/limitations"}
{"node_type":"string","pointer":"/evidence_effects/25/limitations/0","value":"Known legacy failures are not v1 conformance failures and do not make the legacy implementation a correctness oracle."}
{"node_type":"string","pointer":"/evidence_effects/25/observation_locator","value":"integrated-verification-2026-07-16.json#/legacy_verification/unit_tests"}
{"node_type":"string","pointer":"/evidence_effects/25/proposition_scope","value":"The legacy characterization reports two preserved failures, challenging any complete-success interpretation while supporting defect-preserving characterization."}
{"keys":["claim_dimensions","effect","effect_id","evidence_ref","item_refs","limitations","observation_locator","proposition_scope"],"member_count":8,"node_type":"object","pointer":"/evidence_effects/26"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/26/claim_dimensions"}
{"node_type":"string","pointer":"/evidence_effects/26/claim_dimensions/0","value":"proposition"}
{"node_type":"string","pointer":"/evidence_effects/26/effect","value":"contextualizes"}
{"node_type":"string","pointer":"/evidence_effects/26/effect_id","value":"effect.origin-requirement.rebased-verification-denominator.contextualizes"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/26/evidence_ref"}
{"node_type":"string","pointer":"/evidence_effects/26/evidence_ref/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/evidence_effects/26/evidence_ref/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/evidence_effects/26/evidence_ref/reference_kind","value":"ref"}
{"item_count":6,"node_type":"array","pointer":"/evidence_effects/26/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/26/item_refs/0"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/0/entity_id","value":"verification.or02.proof-obligation-and-assurance-graph-soundness"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/0/label_hint","value":"proof obligation・assurance graph 健全性"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/26/item_refs/1"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/1/entity_id","value":"verification.cross.register-completeness"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/1/label_hint","value":"検証 register の有界完全性"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/26/item_refs/2"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/2/entity_id","value":"verification.cross.lifecycle-trace-and-composition"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/2/label_hint","value":"工程横断 trace・意味合成"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/26/item_refs/3"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/3/entity_id","value":"verification.cross.operational-qualification"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/3/label_hint","value":"運用 profile 資格確認"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/26/item_refs/4"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/4/entity_id","value":"verification.cross.transition-and-cutover"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/4/label_hint","value":"移行・cutover 統治"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/evidence_effects/26/item_refs/5"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/5/entity_id","value":"verification.cross.human-operational-use"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/5/label_hint","value":"人間・coding agent の責任適合利用"}
{"node_type":"string","pointer":"/evidence_effects/26/item_refs/5/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/evidence_effects/26/limitations"}
{"node_type":"string","pointer":"/evidence_effects/26/limitations/0","value":"The origin wording contextualizes why these propositions belong in the denominator; it does not support their implementation, verification, validation, assurance, operational readiness, transition authorization, or human acceptance."}
{"node_type":"string","pointer":"/evidence_effects/26/observation_locator","value":"../docs/prototypes/origin-requirement.md"}
{"node_type":"string","pointer":"/evidence_effects/26/proposition_scope","value":"The bound origin requirement supplies the lifecycle denominator, bounded-proof meaning, repair and human-decision purpose, sidecar boundary, and prohibition on silent success from which the six rebased verification concerns are derived."}
{"item_count":6,"node_type":"array","pointer":"/evidence_observations"}
{"keys":["acquisition_method","content_digest","detail_refs","elevated_trust_basis","entity_id","evidence_kind","freshness","label","limitations","observation_locators","observed_at","result_summary","scope","source_path","subject_binding","trust_class"],"member_count":16,"node_type":"object","pointer":"/evidence_observations/0"}
{"node_type":"string","pointer":"/evidence_observations/0/acquisition_method","value":"file_read"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/0/content_digest"}
{"node_type":"string","pointer":"/evidence_observations/0/content_digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/0/content_digest/value","value":"6960dfbc79670712b45ea3b02da8a2f7239c770ec9bf861cd7aa652009b5d3fb"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/0/detail_refs"}
{"node_type":"string","pointer":"/evidence_observations/0/detail_refs/0","value":"../docs/prototypes/origin-requirement.md"}
{"keys":["formal_model_ref","formal_verification_result_ref","independence_basis_ref","observer_ref","signature_or_attestation_ref","signer_ref","trust_root_ref","verifier_ref"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/0/elevated_trust_basis"}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/formal_model_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/formal_verification_result_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/independence_basis_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/observer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/signature_or_attestation_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/signer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/trust_root_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/elevated_trust_basis/verifier_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/evidence_observations/0/evidence_kind","value":"source_snapshot"}
{"node_type":"string","pointer":"/evidence_observations/0/freshness","value":"current"}
{"node_type":"string","pointer":"/evidence_observations/0/label","value":"原点要求 snapshot"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/0/limitations"}
{"node_type":"string","pointer":"/evidence_observations/0/limitations/0","value":"A source snapshot proves recorded wording, not implementation or effectiveness."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/0/observation_locators"}
{"node_type":"string","pointer":"/evidence_observations/0/observation_locators/0","value":"../docs/prototypes/origin-requirement.md"}
{"node_type":"string","pointer":"/evidence_observations/0/observed_at","value":"2026-08-27T15:40:12+09:00"}
{"node_type":"string","pointer":"/evidence_observations/0/result_summary","value":"OR-01, OR-02, OR-03, non-goals, acceptance criteria, and hollow-success conditions are present."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/0/scope"}
{"node_type":"string","pointer":"/evidence_observations/0/scope/0","value":"Purpose and boundary text only."}
{"node_type":"string","pointer":"/evidence_observations/0/source_path","value":"../docs/prototypes/origin-requirement.md"}
{"keys":["command_or_log_refs","digest_bindings","environment_ref","limitations","manifest_digest","manifest_ref","status","subject_locators"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/0/subject_binding"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/0/subject_binding/command_or_log_refs"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/0/subject_binding/digest_bindings"}
{"keys":["digest","subject_locator"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/0/subject_binding/digest_bindings/0"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/0/subject_binding/digest_bindings/0/digest"}
{"node_type":"string","pointer":"/evidence_observations/0/subject_binding/digest_bindings/0/digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/0/subject_binding/digest_bindings/0/digest/value","value":"6960dfbc79670712b45ea3b02da8a2f7239c770ec9bf861cd7aa652009b5d3fb"}
{"node_type":"string","pointer":"/evidence_observations/0/subject_binding/digest_bindings/0/subject_locator","value":"../docs/prototypes/origin-requirement.md"}
{"node_type":"null","pointer":"/evidence_observations/0/subject_binding/environment_ref","value":null}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/0/subject_binding/limitations"}
{"node_type":"string","pointer":"/evidence_observations/0/subject_binding/limitations/0","value":"Binds the wording snapshot only, not implementation or runtime behavior."}
{"node_type":"null","pointer":"/evidence_observations/0/subject_binding/manifest_digest","value":null}
{"node_type":"null","pointer":"/evidence_observations/0/subject_binding/manifest_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/0/subject_binding/status","value":"bound"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/0/subject_binding/subject_locators"}
{"node_type":"string","pointer":"/evidence_observations/0/subject_binding/subject_locators/0","value":"../docs/prototypes/origin-requirement.md"}
{"node_type":"string","pointer":"/evidence_observations/0/trust_class","value":"locally_observed"}
{"keys":["acquisition_method","content_digest","detail_refs","elevated_trust_basis","entity_id","evidence_kind","freshness","label","limitations","observation_locators","observed_at","result_summary","scope","source_path","subject_binding","trust_class"],"member_count":16,"node_type":"object","pointer":"/evidence_observations/1"}
{"node_type":"string","pointer":"/evidence_observations/1/acquisition_method","value":"file_read"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/1/content_digest"}
{"node_type":"string","pointer":"/evidence_observations/1/content_digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/1/content_digest/value","value":"4f1662fa4ba00d866dbfd808dd02f57249bfddf87306762d107205d626b23337"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/1/detail_refs"}
{"node_type":"string","pointer":"/evidence_observations/1/detail_refs/0","value":"../constitution/semantic-guard-constitution.yaml"}
{"keys":["formal_model_ref","formal_verification_result_ref","independence_basis_ref","observer_ref","signature_or_attestation_ref","signer_ref","trust_root_ref","verifier_ref"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/1/elevated_trust_basis"}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/formal_model_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/formal_verification_result_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/independence_basis_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/observer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/signature_or_attestation_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/signer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/trust_root_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/elevated_trust_basis/verifier_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/1/entity_id","value":"evidence.constitution.snapshot.2026-08-24"}
{"node_type":"string","pointer":"/evidence_observations/1/evidence_kind","value":"source_snapshot"}
{"node_type":"string","pointer":"/evidence_observations/1/freshness","value":"current"}
{"node_type":"string","pointer":"/evidence_observations/1/label","value":"v1 憲法 snapshot"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/1/limitations"}
{"node_type":"string","pointer":"/evidence_observations/1/limitations/0","value":"Presence in the constitution does not establish runtime implementation or field validity."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/1/observation_locators"}
{"node_type":"string","pointer":"/evidence_observations/1/observation_locators/0","value":"../constitution/semantic-guard-constitution.yaml"}
{"node_type":"string","pointer":"/evidence_observations/1/observed_at","value":"2026-08-24T13:01:52+09:00"}
{"node_type":"string","pointer":"/evidence_observations/1/result_summary","value":"The constitution records bounded-correctness dimensions, separated claim classes, authority limits, invariants, pass preconditions, and evaluation metrics."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/1/scope"}
{"node_type":"string","pointer":"/evidence_observations/1/scope/0","value":"Normative v1 model pending human acceptance."}
{"node_type":"string","pointer":"/evidence_observations/1/source_path","value":"../constitution/semantic-guard-constitution.yaml"}
{"keys":["command_or_log_refs","digest_bindings","environment_ref","limitations","manifest_digest","manifest_ref","status","subject_locators"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/1/subject_binding"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/1/subject_binding/command_or_log_refs"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/1/subject_binding/digest_bindings"}
{"keys":["digest","subject_locator"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/1/subject_binding/digest_bindings/0"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/1/subject_binding/digest_bindings/0/digest"}
{"node_type":"string","pointer":"/evidence_observations/1/subject_binding/digest_bindings/0/digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/1/subject_binding/digest_bindings/0/digest/value","value":"4f1662fa4ba00d866dbfd808dd02f57249bfddf87306762d107205d626b23337"}
{"node_type":"string","pointer":"/evidence_observations/1/subject_binding/digest_bindings/0/subject_locator","value":"../constitution/semantic-guard-constitution.yaml"}
{"node_type":"null","pointer":"/evidence_observations/1/subject_binding/environment_ref","value":null}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/1/subject_binding/limitations"}
{"node_type":"string","pointer":"/evidence_observations/1/subject_binding/limitations/0","value":"Binds the normative wording snapshot only, not implementation conformance."}
{"node_type":"null","pointer":"/evidence_observations/1/subject_binding/manifest_digest","value":null}
{"node_type":"null","pointer":"/evidence_observations/1/subject_binding/manifest_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/1/subject_binding/status","value":"bound"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/1/subject_binding/subject_locators"}
{"node_type":"string","pointer":"/evidence_observations/1/subject_binding/subject_locators/0","value":"../constitution/semantic-guard-constitution.yaml"}
{"node_type":"string","pointer":"/evidence_observations/1/trust_class","value":"locally_observed"}
{"keys":["acquisition_method","content_digest","detail_refs","elevated_trust_basis","entity_id","evidence_kind","freshness","label","limitations","observation_locators","observed_at","result_summary","scope","source_path","subject_binding","trust_class"],"member_count":16,"node_type":"object","pointer":"/evidence_observations/2"}
{"node_type":"string","pointer":"/evidence_observations/2/acquisition_method","value":"file_read"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/2/content_digest"}
{"node_type":"string","pointer":"/evidence_observations/2/content_digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/2/content_digest/value","value":"1a5df685a46f1418f3413c505c65d147b20a7b5f0a41f743576a46394cc7590f"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/2/detail_refs"}
{"node_type":"string","pointer":"/evidence_observations/2/detail_refs/0","value":"../schemas/common.schema.json"}
{"keys":["formal_model_ref","formal_verification_result_ref","independence_basis_ref","observer_ref","signature_or_attestation_ref","signer_ref","trust_root_ref","verifier_ref"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/2/elevated_trust_basis"}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/formal_model_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/formal_verification_result_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/independence_basis_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/observer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/signature_or_attestation_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/signer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/trust_root_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/elevated_trust_basis/verifier_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/2/entity_id","value":"evidence.public-trust-basis-inspection.2026-07-17"}
{"node_type":"string","pointer":"/evidence_observations/2/evidence_kind","value":"source_snapshot"}
{"node_type":"string","pointer":"/evidence_observations/2/freshness","value":"current"}
{"node_type":"string","pointer":"/evidence_observations/2/label","value":"公開 provenance 信頼根拠欄の欠落観測"}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/2/limitations"}
{"node_type":"string","pointer":"/evidence_observations/2/limitations/0","value":"This is a deterministic schema inspection, not proof that a consumer will overclaim."}
{"node_type":"string","pointer":"/evidence_observations/2/limitations/1","value":"Changing the public contract is deliberately outside this verification-register revision."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/2/observation_locators"}
{"node_type":"string","pointer":"/evidence_observations/2/observation_locators/0","value":"../schemas/common.schema.json#/$defs/provenance_record"}
{"node_type":"string","pointer":"/evidence_observations/2/observed_at","value":"2026-07-17T01:44:51+09:00"}
{"node_type":"string","pointer":"/evidence_observations/2/result_summary","value":"The public provenance_record enumerates independently_observed, signed, and formally_verified trust classes but has no profile reference or conditional fields that bind those labels to observer independence, signature, trust-root, formal-model, or verifier evidence."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/2/scope"}
{"node_type":"string","pointer":"/evidence_observations/2/scope/0","value":"Public provenance_record schema trust-class contract."}
{"node_type":"string","pointer":"/evidence_observations/2/source_path","value":"../schemas/common.schema.json"}
{"keys":["command_or_log_refs","digest_bindings","environment_ref","limitations","manifest_digest","manifest_ref","status","subject_locators"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/2/subject_binding"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/2/subject_binding/command_or_log_refs"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/2/subject_binding/digest_bindings"}
{"keys":["digest","subject_locator"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/2/subject_binding/digest_bindings/0"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/2/subject_binding/digest_bindings/0/digest"}
{"node_type":"string","pointer":"/evidence_observations/2/subject_binding/digest_bindings/0/digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/2/subject_binding/digest_bindings/0/digest/value","value":"1a5df685a46f1418f3413c505c65d147b20a7b5f0a41f743576a46394cc7590f"}
{"node_type":"string","pointer":"/evidence_observations/2/subject_binding/digest_bindings/0/subject_locator","value":"../schemas/common.schema.json"}
{"node_type":"null","pointer":"/evidence_observations/2/subject_binding/environment_ref","value":null}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/2/subject_binding/limitations"}
{"node_type":"string","pointer":"/evidence_observations/2/subject_binding/limitations/0","value":"Binds only the inspected public schema bytes, not any runtime evidence mechanism."}
{"node_type":"null","pointer":"/evidence_observations/2/subject_binding/manifest_digest","value":null}
{"node_type":"null","pointer":"/evidence_observations/2/subject_binding/manifest_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/2/subject_binding/status","value":"bound"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/2/subject_binding/subject_locators"}
{"node_type":"string","pointer":"/evidence_observations/2/subject_binding/subject_locators/0","value":"../schemas/common.schema.json"}
{"node_type":"string","pointer":"/evidence_observations/2/trust_class","value":"locally_observed"}
{"keys":["acquisition_method","content_digest","detail_refs","elevated_trust_basis","entity_id","evidence_kind","freshness","label","limitations","observation_locators","observed_at","result_summary","scope","source_path","subject_binding","trust_class"],"member_count":16,"node_type":"object","pointer":"/evidence_observations/3"}
{"node_type":"string","pointer":"/evidence_observations/3/acquisition_method","value":"imported_record"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/3/content_digest"}
{"node_type":"string","pointer":"/evidence_observations/3/content_digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/3/content_digest/value","value":"c61681d5f73d767060730331e21e2093a776bbdbf0e44ace389d83faca8aa2f3"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/3/detail_refs"}
{"node_type":"string","pointer":"/evidence_observations/3/detail_refs/0","value":"integrated-verification-2026-07-16.json"}
{"keys":["formal_model_ref","formal_verification_result_ref","independence_basis_ref","observer_ref","signature_or_attestation_ref","signer_ref","trust_root_ref","verifier_ref"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/3/elevated_trust_basis"}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/formal_model_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/formal_verification_result_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/independence_basis_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/observer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/signature_or_attestation_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/signer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/trust_root_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/elevated_trust_basis/verifier_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/3/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/evidence_observations/3/evidence_kind","value":"test_execution"}
{"node_type":"string","pointer":"/evidence_observations/3/freshness","value":"unbound"}
{"node_type":"string","pointer":"/evidence_observations/3/label","value":"vNext 統合検証観測"}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/3/limitations"}
{"node_type":"string","pointer":"/evidence_observations/3/limitations/0","value":"The record has no dedicated record schema in the current repository."}
{"node_type":"string","pointer":"/evidence_observations/3/limitations/1","value":"It does not establish field performance, action authenticity, production readiness, or human acceptance."}
{"item_count":13,"node_type":"array","pointer":"/evidence_observations/3/observation_locators"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/0","value":"integrated-verification-2026-07-16.json#/acceptance_state"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/1","value":"integrated-verification-2026-07-16.json#/legacy_verification/baseline"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/2","value":"integrated-verification-2026-07-16.json#/legacy_verification/unit_tests"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/3","value":"integrated-verification-2026-07-16.json#/next_actions/4"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/4","value":"integrated-verification-2026-07-16.json#/real_nlp_verification"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/5","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/0"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/6","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/2"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/7","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/4"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/8","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/6"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/9","value":"integrated-verification-2026-07-16.json#/unverified_or_unimplemented/7"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/10","value":"integrated-verification-2026-07-16.json#/vnext_verification/conformance_corpus"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/11","value":"integrated-verification-2026-07-16.json#/vnext_verification/json_schemas"}
{"node_type":"string","pointer":"/evidence_observations/3/observation_locators/12","value":"integrated-verification-2026-07-16.json#/vnext_verification/unit_and_contract_tests/0"}
{"node_type":"string","pointer":"/evidence_observations/3/observed_at","value":"2026-07-16T00:00:00+09:00"}
{"node_type":"string","pointer":"/evidence_observations/3/result_summary","value":"147 v1 tests passed on Python 3.13 and 3.11; seven runtime schemas and local distribution/MCP paths were checked; declared legacy defects and unverified field/action-assurance scopes remain."}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/3/scope"}
{"node_type":"string","pointer":"/evidence_observations/3/scope/0","value":"Requirement-relation vertical slice local implementation."}
{"node_type":"string","pointer":"/evidence_observations/3/scope/1","value":"Dated local and isolated execution environments described in the record."}
{"node_type":"string","pointer":"/evidence_observations/3/source_path","value":"integrated-verification-2026-07-16.json"}
{"keys":["command_or_log_refs","digest_bindings","environment_ref","limitations","manifest_digest","manifest_ref","status","subject_locators"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/3/subject_binding"}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/3/subject_binding/command_or_log_refs"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/command_or_log_refs/0","value":"integrated-verification-2026-07-16.json#/vnext_verification/unit_and_contract_tests/0/command"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/command_or_log_refs/1","value":"integrated-verification-2026-07-16.json#/vnext_verification/unit_and_contract_tests/1/command"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/3/subject_binding/digest_bindings"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/environment_ref","value":"integrated-verification-2026-07-16.json#/vnext_verification/unit_and_contract_tests"}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/3/subject_binding/limitations"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/limitations/0","value":"The record does not bind the tested v1 source tree to a closed manifest or source digest set."}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/limitations/1","value":"Embedded command strings are not raw execution logs or independent observations."}
{"node_type":"null","pointer":"/evidence_observations/3/subject_binding/manifest_digest","value":null}
{"node_type":"null","pointer":"/evidence_observations/3/subject_binding/manifest_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/status","value":"unbound"}
{"item_count":4,"node_type":"array","pointer":"/evidence_observations/3/subject_binding/subject_locators"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/subject_locators/0","value":"../src/semantic_guard"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/subject_locators/1","value":"../tests"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/subject_locators/2","value":"../schemas"}
{"node_type":"string","pointer":"/evidence_observations/3/subject_binding/subject_locators/3","value":"../constitution/semantic-guard-constitution.yaml"}
{"node_type":"string","pointer":"/evidence_observations/3/trust_class","value":"tool_reported"}
{"keys":["acquisition_method","content_digest","detail_refs","elevated_trust_basis","entity_id","evidence_kind","freshness","label","limitations","observation_locators","observed_at","result_summary","scope","source_path","subject_binding","trust_class"],"member_count":16,"node_type":"object","pointer":"/evidence_observations/4"}
{"node_type":"string","pointer":"/evidence_observations/4/acquisition_method","value":"imported_record"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/4/content_digest"}
{"node_type":"string","pointer":"/evidence_observations/4/content_digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/4/content_digest/value","value":"55c49f802717ca0642fea087fb99145e0fda8754a655e4f8ec5191d6469d115c"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/4/detail_refs"}
{"node_type":"string","pointer":"/evidence_observations/4/detail_refs/0","value":"real-nlp-smoke-2026-07-16.json"}
{"keys":["formal_model_ref","formal_verification_result_ref","independence_basis_ref","observer_ref","signature_or_attestation_ref","signer_ref","trust_root_ref","verifier_ref"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/4/elevated_trust_basis"}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/formal_model_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/formal_verification_result_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/independence_basis_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/observer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/signature_or_attestation_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/signer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/trust_root_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/elevated_trust_basis/verifier_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/4/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/evidence_observations/4/evidence_kind","value":"test_execution"}
{"node_type":"string","pointer":"/evidence_observations/4/freshness","value":"unbound"}
{"node_type":"string","pointer":"/evidence_observations/4/label","value":"実 Sudachi/GiNZA 煙試験観測"}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/4/limitations"}
{"node_type":"string","pointer":"/evidence_observations/4/limitations/0","value":"Smoke cases are not a target-population accuracy estimate."}
{"node_type":"string","pointer":"/evidence_observations/4/limitations/1","value":"No blind labeling, adjudication, confidence interval, or repair-effect observation."}
{"item_count":3,"node_type":"array","pointer":"/evidence_observations/4/observation_locators"}
{"node_type":"string","pointer":"/evidence_observations/4/observation_locators/0","value":"real-nlp-smoke-2026-07-16.json#/cases"}
{"node_type":"string","pointer":"/evidence_observations/4/observation_locators/1","value":"real-nlp-smoke-2026-07-16.json#/provider_contract"}
{"node_type":"string","pointer":"/evidence_observations/4/observation_locators/2","value":"real-nlp-smoke-2026-07-16.json#/provider_contract/expected_missing_dependency_capabilities/0"}
{"node_type":"string","pointer":"/evidence_observations/4/observed_at","value":"2026-07-16T00:00:00+09:00"}
{"node_type":"string","pointer":"/evidence_observations/4/result_summary","value":"Five bounded real-provider cases ran; Sudachi fulfilled requested capabilities and GiNZA remained partial because coreference_candidate was missing."}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/4/scope"}
{"node_type":"string","pointer":"/evidence_observations/4/scope/0","value":"Five hand-selected structured requirement cases."}
{"node_type":"string","pointer":"/evidence_observations/4/scope/1","value":"Provider execution and public-contract behavior."}
{"node_type":"string","pointer":"/evidence_observations/4/source_path","value":"real-nlp-smoke-2026-07-16.json"}
{"keys":["command_or_log_refs","digest_bindings","environment_ref","limitations","manifest_digest","manifest_ref","status","subject_locators"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/4/subject_binding"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/4/subject_binding/command_or_log_refs"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/4/subject_binding/digest_bindings"}
{"node_type":"string","pointer":"/evidence_observations/4/subject_binding/environment_ref","value":"real-nlp-smoke-2026-07-16.json#/environment"}
{"item_count":2,"node_type":"array","pointer":"/evidence_observations/4/subject_binding/limitations"}
{"node_type":"string","pointer":"/evidence_observations/4/subject_binding/limitations/0","value":"The record does not bind the analyzer code, model resources, cases, or complete environment to a closed subject manifest."}
{"node_type":"string","pointer":"/evidence_observations/4/subject_binding/limitations/1","value":"No raw command or execution log locator is recorded."}
{"node_type":"null","pointer":"/evidence_observations/4/subject_binding/manifest_digest","value":null}
{"node_type":"null","pointer":"/evidence_observations/4/subject_binding/manifest_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/4/subject_binding/status","value":"unbound"}
{"item_count":3,"node_type":"array","pointer":"/evidence_observations/4/subject_binding/subject_locators"}
{"node_type":"string","pointer":"/evidence_observations/4/subject_binding/subject_locators/0","value":"../src/semantic_guard/japanese_morphology.py"}
{"node_type":"string","pointer":"/evidence_observations/4/subject_binding/subject_locators/1","value":"../src/semantic_guard/japanese_dependency.py"}
{"node_type":"string","pointer":"/evidence_observations/4/subject_binding/subject_locators/2","value":"../src/semantic_guard/engine.py"}
{"node_type":"string","pointer":"/evidence_observations/4/trust_class","value":"tool_reported"}
{"keys":["acquisition_method","content_digest","detail_refs","elevated_trust_basis","entity_id","evidence_kind","freshness","label","limitations","observation_locators","observed_at","result_summary","scope","source_path","subject_binding","trust_class"],"member_count":16,"node_type":"object","pointer":"/evidence_observations/5"}
{"node_type":"string","pointer":"/evidence_observations/5/acquisition_method","value":"file_read"}
{"keys":["algorithm","value"],"member_count":2,"node_type":"object","pointer":"/evidence_observations/5/content_digest"}
{"node_type":"string","pointer":"/evidence_observations/5/content_digest/algorithm","value":"sha256"}
{"node_type":"string","pointer":"/evidence_observations/5/content_digest/value","value":"e13e5a539372aff599b2c3c1241dce364b9962ad07eed6bc2047548b29ae2d37"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/5/detail_refs"}
{"node_type":"string","pointer":"/evidence_observations/5/detail_refs/0","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"keys":["formal_model_ref","formal_verification_result_ref","independence_basis_ref","observer_ref","signature_or_attestation_ref","signer_ref","trust_root_ref","verifier_ref"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/5/elevated_trust_basis"}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/formal_model_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/formal_verification_result_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/independence_basis_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/observer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/signature_or_attestation_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/signer_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/trust_root_ref","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/elevated_trust_basis/verifier_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/5/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/evidence_observations/5/evidence_kind","value":"historical_assessment"}
{"node_type":"string","pointer":"/evidence_observations/5/freshness","value":"stale"}
{"node_type":"string","pointer":"/evidence_observations/5/label","value":"全体監査の歴史的観測"}
{"item_count":3,"node_type":"array","pointer":"/evidence_observations/5/limitations"}
{"node_type":"string","pointer":"/evidence_observations/5/limitations/0","value":"Predates the current v1 snapshot and must not override newer direct observations."}
{"node_type":"string","pointer":"/evidence_observations/5/limitations/1","value":"The content digest binds the publication-sanitized derivative prepared on 2026-08-24; observed_at denotes the historical assessment event, not the derivative publication time."}
{"node_type":"string","pointer":"/evidence_observations/5/limitations/2","value":"A separate private original was recorded with sha256:788499cc5cb8c283cf130f9fd2c645733f18f6c63c5755a334973a83196a3159; current availability is not established by this public repository."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/5/observation_locators"}
{"node_type":"string","pointer":"/evidence_observations/5/observation_locators/0","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"node_type":"string","pointer":"/evidence_observations/5/observed_at","value":"2026-07-11T00:00:00+09:00"}
{"node_type":"string","pointer":"/evidence_observations/5/result_summary","value":"The audit found missing engineering-rule governance, action-event evidence, typed lifecycle edges, original-evidence rechecking, independent observers, authenticity, and coverage manifests."}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/5/scope"}
{"node_type":"string","pointer":"/evidence_observations/5/scope/0","value":"Repository state observed on 2026-07-11."}
{"node_type":"string","pointer":"/evidence_observations/5/source_path","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"keys":["command_or_log_refs","digest_bindings","environment_ref","limitations","manifest_digest","manifest_ref","status","subject_locators"],"member_count":8,"node_type":"object","pointer":"/evidence_observations/5/subject_binding"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/5/subject_binding/command_or_log_refs"}
{"item_count":0,"node_type":"array","pointer":"/evidence_observations/5/subject_binding/digest_bindings"}
{"node_type":"null","pointer":"/evidence_observations/5/subject_binding/environment_ref","value":null}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/5/subject_binding/limitations"}
{"node_type":"string","pointer":"/evidence_observations/5/subject_binding/limitations/0","value":"The assessed repository snapshot and environment were not closed by a manifest."}
{"node_type":"null","pointer":"/evidence_observations/5/subject_binding/manifest_digest","value":null}
{"node_type":"null","pointer":"/evidence_observations/5/subject_binding/manifest_ref","value":null}
{"node_type":"string","pointer":"/evidence_observations/5/subject_binding/status","value":"unbound"}
{"item_count":1,"node_type":"array","pointer":"/evidence_observations/5/subject_binding/subject_locators"}
{"node_type":"string","pointer":"/evidence_observations/5/subject_binding/subject_locators/0","value":"Repository state described by the 2026-07-11 assessment"}
{"node_type":"string","pointer":"/evidence_observations/5/trust_class","value":"locally_observed"}
{"keys":["decided_at","decision_record_ref","owner","status"],"member_count":4,"node_type":"object","pointer":"/human_acceptance"}
{"node_type":"null","pointer":"/human_acceptance/decided_at","value":null}
{"node_type":"null","pointer":"/human_acceptance/decision_record_ref","value":null}
{"node_type":"string","pointer":"/human_acceptance/owner","value":"human"}
{"node_type":"string","pointer":"/human_acceptance/status","value":"pending"}
{"item_count":27,"node_type":"array","pointer":"/implementation_conformance_items"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/0"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/0/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/entity_id","value":"conformance.INV-VN-001"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/0/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/0/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/label","value":"未知・競合・無効・被覆不足を上位 pass が捨てない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/0/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/limitations/0","value":"Preserves known unresolved states; does not establish discovery recall."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/0/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/0/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/0/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/procedure_refs/0","value":"src/semantic_guard/models.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/procedure_refs/1","value":"src/semantic_guard/aggregation.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/procedure_refs/2","value":"tests/test_models_and_aggregation.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/proposition","value":"Known unresolved required obligations prevent pass."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/0/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/remaining_obligations/0","value":"Measure catastrophic false satisfaction and silent coverage gaps on real artifacts."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/0/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/0/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/subject_ref/entity_id","value":"INV-VN-001"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/subject_ref/label_hint","value":"INV-VN-001"}
{"node_type":"string","pointer":"/implementation_conformance_items/0/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/1"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/1/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/entity_id","value":"conformance.INV-VN-002"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/1/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/1/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/label","value":"直接 satisfied は残余危険門まで provisional"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/1/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/limitations/0","value":"Parser-only and field recall remain unvalidated."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/1/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/1/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/implementation_conformance_items/1/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/procedure_refs/0","value":"src/semantic_guard/engine.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/procedure_refs/1","value":"src/semantic_guard/residual_risk.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/procedure_refs/2","value":"tests/test_engine.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/procedure_refs/3","value":"tests/test_residual_risk.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/proposition","value":"Direct-rule satisfaction cannot become pass before the independent residual-risk gate."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/1/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/remaining_obligations/0","value":"Evaluate conditional-mode misses on real artifacts."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/1/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/1/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/subject_ref/entity_id","value":"INV-VN-002"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/subject_ref/label_hint","value":"INV-VN-002"}
{"node_type":"string","pointer":"/implementation_conformance_items/1/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/2"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/2/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/entity_id","value":"conformance.INV-VN-003"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/2/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/2/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/label","value":"terminal satisfaction の閉包条件"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/2/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/limitations/0","value":"Supporting evidence may still lack authenticity or independent observation."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/2/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/2/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/implementation_conformance_items/2/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/procedure_refs/0","value":"src/semantic_guard/aggregation.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/procedure_refs/1","value":"src/semantic_guard/public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/procedure_refs/2","value":"tests/test_models_and_aggregation.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/procedure_refs/3","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/proposition","value":"Terminal satisfaction requires complete coverage, no challenge, no open hold, and supporting evidence."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/2/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/remaining_obligations/0","value":"Add artifact authenticity and signed provenance only where elevated claims require them."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/2/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/2/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/subject_ref/entity_id","value":"INV-VN-003"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/subject_ref/label_hint","value":"INV-VN-003"}
{"node_type":"string","pointer":"/implementation_conformance_items/2/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/3"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/3/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/entity_id","value":"conformance.INV-VN-004"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/3/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/3/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/label","value":"必須解析器障害を silent success にしない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/3/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/limitations/0","value":"Current tests do not establish long-duration resource exhaustion behavior."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/3/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/3/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/3/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/procedure_refs/0","value":"src/semantic_guard/providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/procedure_refs/1","value":"src/semantic_guard/engine.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/procedure_refs/2","value":"tests/test_providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/proposition","value":"Unavailable, failed, or invalid required providers produce visible failure or uncertainty and cannot silently pass."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/3/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/remaining_obligations/0","value":"Test latency, resource exhaustion, concurrency, and partial infrastructure failure."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/3/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/3/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/subject_ref/entity_id","value":"INV-VN-004"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/subject_ref/label_hint","value":"INV-VN-004"}
{"node_type":"string","pointer":"/implementation_conformance_items/3/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/4"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/4/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/entity_id","value":"conformance.INV-VN-005"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/4/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/4/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/label","value":"候補解析器は支持・解除不能"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/4/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/limitations/0","value":"External model identity and live API adapter are absent."}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/4/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/4/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/4/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/origin_requirement_refs/1/reference_kind","value":"ref"}
{"item_count":5,"node_type":"array","pointer":"/implementation_conformance_items/4/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/procedure_refs/0","value":"src/semantic_guard/providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/procedure_refs/1","value":"src/semantic_guard/lifting.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/procedure_refs/2","value":"src/semantic_guard/llm_candidates.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/procedure_refs/3","value":"tests/test_providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/procedure_refs/4","value":"tests/test_llm_candidates.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/proposition","value":"Candidate-only providers cannot directly support obligations or release holds."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/4/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/remaining_obligations/0","value":"Define external adapter and model-identity evidence without raising candidate authority."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/4/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/4/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/subject_ref/entity_id","value":"INV-VN-005"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/subject_ref/label_hint","value":"INV-VN-005"}
{"node_type":"string","pointer":"/implementation_conformance_items/4/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/5"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/5/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/entity_id","value":"conformance.INV-VN-006"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/5/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/5/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/label","value":"引用・例示等を肯定へ自動昇格しない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/5/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/limitations/0","value":"Real paraphrase and discourse coverage are not established."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/5/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/5/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/5/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/procedure_refs/0","value":"src/semantic_guard/residual_risk.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/procedure_refs/1","value":"tests/test_residual_risk.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/procedure_refs/2","value":"fixtures/requirement-relations/conformance.jsonl"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/proposition","value":"Quotation, example, history, hearsay, non-adoption, and negation do not automatically become current affirmative propositions."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/5/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/remaining_obligations/0","value":"Evaluate domain paraphrases, cross-sentence scope, and reporting structures."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/5/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/5/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/subject_ref/entity_id","value":"INV-VN-006"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/subject_ref/label_hint","value":"INV-VN-006"}
{"node_type":"string","pointer":"/implementation_conformance_items/5/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/6"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/6/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/entity_id","value":"conformance.INV-VN-007"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/6/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/6/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/label","value":"開いた自由文から missing を断定しない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/6/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/limitations/0","value":"Multiple-requirement segmentation is not implemented at practical quality."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/6/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/6/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/6/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/procedure_refs/0","value":"src/semantic_guard/records.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/procedure_refs/1","value":"tests/test_records.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/proposition","value":"Open text or unknown applicability yields undetermined rather than a fabricated missing fact."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/6/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/remaining_obligations/0","value":"Implement and validate multi-requirement record segmentation."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/6/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/6/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/subject_ref/entity_id","value":"INV-VN-007"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/subject_ref/label_hint","value":"INV-VN-007"}
{"node_type":"string","pointer":"/implementation_conformance_items/6/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/7"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/7/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/entity_id","value":"conformance.INV-VN-008"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/7/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/7/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/label","value":"人間の危険受容で監査事実を消さない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/7/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/limitations/0","value":"No append-only external human decision record is linked."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/7/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/7/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/origin_requirement_refs/0/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/origin_requirement_refs/0/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/7/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/procedure_refs/0","value":"schemas/audit-result.schema.json"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/procedure_refs/1","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/proposition","value":"External human acceptance is recorded without mutating audit findings, counterevidence, or unproven scope."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/7/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/remaining_obligations/0","value":"Integrate a human-owned external decision reference without moving ownership into semantic-guard."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/7/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/state_profile_ref/entity_id","value":"state.partial-inconclusive"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/state_profile_ref/label_hint","value":"部分実装・結論不能"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/7/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/subject_ref/entity_id","value":"INV-VN-008"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/subject_ref/label_hint","value":"INV-VN-008"}
{"node_type":"string","pointer":"/implementation_conformance_items/7/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/8"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/8/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/entity_id","value":"conformance.INV-VN-009"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/8/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/8/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/label","value":"score を正しさ確率にしない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/8/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/limitations/0","value":"External legacy consumers may still misread the score."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/8/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/8/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/8/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/procedure_refs/0","value":"src/semantic_guard/compat.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/procedure_refs/1","value":"tests/test_compat.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/proposition","value":"A legacy score is an explicitly non-probabilistic projection and is not used as correctness probability."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/8/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/remaining_obligations/0","value":"Monitor and document legacy consumer misuse during migration."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/8/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/8/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/subject_ref/entity_id","value":"INV-VN-009"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/subject_ref/label_hint","value":"INV-VN-009"}
{"node_type":"string","pointer":"/implementation_conformance_items/8/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/9"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/9/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/entity_id","value":"conformance.INV-VN-010"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/9/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/9/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/label","value":"schema・digest・由来破損を pass にしない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/9/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/limitations/0","value":"No signature, trusted time, or complete artifact-digest bundle."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/9/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/9/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/implementation_conformance_items/9/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/procedure_refs/0","value":"src/semantic_guard/public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/procedure_refs/1","value":"migration/legacy-baseline-2026-07-16.json"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/procedure_refs/2","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/procedure_refs/3","value":"tests/test_legacy_runner.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/proposition","value":"Schema violations, digest mismatches, or missing provenance become invalid or block and cannot pass."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/9/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/remaining_obligations/0","value":"Add elevated provenance mechanisms only for claims that require them."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/9/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/9/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/subject_ref/entity_id","value":"INV-VN-010"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/subject_ref/label_hint","value":"INV-VN-010"}
{"node_type":"string","pointer":"/implementation_conformance_items/9/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/10"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/10/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/entity_id","value":"conformance.INV-VN-011"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/10/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/10/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/label","value":"分野語共有だけを関係証明にしない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/10/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/limitations/0","value":"Anchor and action-family coverage over practical vocabulary and cross-sentence causality are unknown."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/10/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/10/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/10/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/procedure_refs/0","value":"src/semantic_guard/direct_rules.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/procedure_refs/1","value":"tests/test_direct_rules.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/procedure_refs/2","value":"fixtures/requirement-relations/conformance.jsonl"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/proposition","value":"Shared domain vocabulary alone cannot prove causal, constraint, verification-target, or evidence-generation relations."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/10/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/remaining_obligations/0","value":"Build engineering-grounded relation profiles and evaluate practical vocabulary coverage."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/10/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/10/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/subject_ref/entity_id","value":"INV-VN-011"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/subject_ref/label_hint","value":"INV-VN-011"}
{"node_type":"string","pointer":"/implementation_conformance_items/10/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/11"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/11/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/entity_id","value":"conformance.INV-VN-012"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/11/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/11/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/11/evidence_refs/1"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/evidence_refs/1/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/evidence_refs/1/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/label","value":"解析器 ok は span 被覆と能力閉包を要する"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/11/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/limitations/0","value":"Capability accounting does not prove semantic accuracy."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/11/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/11/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/implementation_conformance_items/11/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/procedure_refs/0","value":"src/semantic_guard/providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/procedure_refs/1","value":"src/semantic_guard/japanese_morphology.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/procedure_refs/2","value":"src/semantic_guard/japanese_dependency.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/procedure_refs/3","value":"tests/test_providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/proposition","value":"Provider ok requires requested capability accounting and full target-span coverage."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/11/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/remaining_obligations/0","value":"Evaluate long inputs, resource exhaustion, chunking, and semantic accuracy."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/11/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/11/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/subject_ref/entity_id","value":"INV-VN-012"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/subject_ref/label_hint","value":"INV-VN-012"}
{"node_type":"string","pointer":"/implementation_conformance_items/11/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/12"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/12/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/entity_id","value":"conformance.INV-VN-013"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/12/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/12/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/label","value":"公開集約欄の矛盾を受理しない"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/12/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/limitations/0","value":"Cross-version migration and external serializer interoperability are not established."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/12/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/12/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/12/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/procedure_refs/0","value":"src/semantic_guard/public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/procedure_refs/1","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/proposition","value":"Public conclusion, coverage, challenge, holds, unresolved items, and workflow can be reaggregated and contradictory payloads are rejected."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/12/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/remaining_obligations/0","value":"Add version-transition and independent serializer round-trip evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/12/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/12/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/subject_ref/entity_id","value":"INV-VN-013"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/subject_ref/label_hint","value":"INV-VN-013"}
{"node_type":"string","pointer":"/implementation_conformance_items/12/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/13"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/13/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/entity_id","value":"conformance.INV-VN-014"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/13/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/13/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/item_kind","value":"invariant"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/label","value":"入力同一性と監査観測同一性を分ける"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/13/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/limitations/0","value":"No signed time, replay defense, or actor authentication."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/13/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/13/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/13/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/procedure_refs/0","value":"src/semantic_guard/public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/procedure_refs/1","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/proposition","value":"Audit observation identity binds configuration and observation rather than input text alone."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/13/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/remaining_obligations/0","value":"Define elevated occurrence identity and replay protection where operational profiles require them."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/13/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/13/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/subject_ref/entity_id","value":"INV-VN-014"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/subject_ref/label_hint","value":"INV-VN-014"}
{"node_type":"string","pointer":"/implementation_conformance_items/13/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/14"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/14/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/entity_id","value":"conformance.stage.input-boundary"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/14/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/14/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/label","value":"段階0 入力契約と記録境界"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/14/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/limitations/0","value":"One structured functional-requirement profile only."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/14/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/14/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/14/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/procedure_refs/0","value":"src/semantic_guard/records.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/procedure_refs/1","value":"tests/test_records.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/proposition","value":"Closed structured records are distinguished from open text before audit claims are generated."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/14/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/remaining_obligations/0","value":"Add separately versioned profiles for other lifecycle artifacts."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/14/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/14/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/subject_ref/entity_id","value":"stage.input-boundary"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/subject_ref/label_hint","value":"入力契約と記録境界"}
{"node_type":"string","pointer":"/implementation_conformance_items/14/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/15"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/15/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/entity_id","value":"conformance.stage.provisional-direct-audit"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/15/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/15/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/label","value":"段階1 義務別仮判定"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/15/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/limitations/0","value":"Engineering rule provenance and practical detection coverage remain incomplete."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/15/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/15/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/15/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/procedure_refs/0","value":"src/semantic_guard/direct_rules.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/procedure_refs/1","value":"src/semantic_guard/profiles.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/procedure_refs/2","value":"tests/test_direct_rules.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/proposition","value":"Direct rules produce obligation-level provisional results under a versioned profile."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/15/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/remaining_obligations/0","value":"Adopt traceable rule packs and evaluate false satisfaction."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/15/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/15/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/subject_ref/entity_id","value":"stage.provisional-direct-audit"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/subject_ref/label_hint","value":"義務別仮判定"}
{"node_type":"string","pointer":"/implementation_conformance_items/15/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/16"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/16/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/entity_id","value":"conformance.stage.residual-risk-gate"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/16/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/16/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/label","value":"段階2 独立残余危険門"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/16/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/limitations/0","value":"Unknown-unknown discovery and field recall are not measured."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/16/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/16/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/16/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/procedure_refs/0","value":"src/semantic_guard/residual_risk.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/procedure_refs/1","value":"tests/test_residual_risk.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/proposition","value":"Residual-risk checks run independently of positive direct matching."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/16/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/remaining_obligations/0","value":"Build a denominator and target-population validation."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/16/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/16/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/subject_ref/entity_id","value":"stage.residual-risk-gate"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/subject_ref/label_hint","value":"独立残余危険門"}
{"node_type":"string","pointer":"/implementation_conformance_items/16/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/17"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/17/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/entity_id","value":"conformance.stage.morphology"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/17/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/17/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/evidence_refs/0/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/evidence_refs/0/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/label","value":"段階3 形態素解析"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/17/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/limitations/0","value":"Morphology is signal-only and does not prove semantic relations."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/17/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/17/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/17/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/procedure_refs/0","value":"src/semantic_guard/japanese_morphology.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/procedure_refs/1","value":"tests/test_providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/proposition","value":"Sudachi provides source-aligned tokenization, lemma, and part-of-speech signals without support authority."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/17/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/remaining_obligations/0","value":"Evaluate contribution to detection under ablation and field cases."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/17/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/17/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/subject_ref/entity_id","value":"stage.morphology"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/subject_ref/label_hint","value":"形態素解析"}
{"node_type":"string","pointer":"/implementation_conformance_items/17/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/18"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/18/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/entity_id","value":"conformance.stage.dependency-analysis-bundle"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/18/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/18/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/evidence_refs/0/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/evidence_refs/0/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/label","value":"段階4 依存構造解析束"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/18/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/limitations/0","value":"coreference_candidate is missing; semantic accuracy and long-document behavior are unvalidated."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/18/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/18/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/implementation_conformance_items/18/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/procedure_refs/0","value":"src/semantic_guard/japanese_dependency.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/procedure_refs/1","value":"src/semantic_guard/dependency_projection.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/procedure_refs/2","value":"tests/test_japanese_dependency.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/procedure_refs/3","value":"tests/test_dependency_projection.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/proposition","value":"GiNZA emits source-aligned dependency and scope candidates while missing capability remains visible."}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/18/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/remaining_obligations/0","value":"Provide coreference capability or revise the required bundle by human decision."}
{"node_type":"string","pointer":"/implementation_conformance_items/18/remaining_obligations/1","value":"Evaluate practical dependency and scope accuracy."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/18/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/state_profile_ref/entity_id","value":"state.partial-inconclusive"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/state_profile_ref/label_hint","value":"部分実装・結論不能"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/18/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/subject_ref/entity_id","value":"stage.dependency-analysis-bundle"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/subject_ref/label_hint","value":"依存構造解析束"}
{"node_type":"string","pointer":"/implementation_conformance_items/18/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/19"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/19/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/entity_id","value":"conformance.stage.versioned-lifting-rule"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/19/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/19/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/label","value":"段階5 版付き決定論的導出"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/19/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/limitations/0","value":"Only a bounded condition-attachment lifting rule exists."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/19/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/19/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/19/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/procedure_refs/0","value":"src/semantic_guard/lifting.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/procedure_refs/1","value":"tests/test_lifting.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/proposition","value":"Only versioned assertion-capable rules can lift candidates after consuming declared evidence and counterconditions."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/19/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/remaining_obligations/0","value":"Add engineering-grounded rules for negation, modality, quotation, reporting, and cross-field relations."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/19/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/state_profile_ref/entity_id","value":"state.partial-inconclusive"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/state_profile_ref/label_hint","value":"部分実装・結論不能"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/19/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/subject_ref/entity_id","value":"stage.versioned-lifting-rule"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/subject_ref/label_hint","value":"版付き決定論的導出規則"}
{"node_type":"string","pointer":"/implementation_conformance_items/19/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/20"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/20/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/entity_id","value":"conformance.stage.llm-candidate"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/20/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/20/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/label","value":"段階6 LLM 候補"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/20/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/limitations/0","value":"No automatic external API adapter, model identity, latency, retry, or field evaluation."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/20/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/20/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/20/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/procedure_refs/0","value":"src/semantic_guard/llm_candidates.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/procedure_refs/1","value":"schemas/llm-candidate-input.schema.json"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/procedure_refs/2","value":"tests/test_llm_candidates.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/proposition","value":"Caller-supplied LLM candidates are digest- and span-bound, run under declared modes, and remain candidate-only."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/20/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/remaining_obligations/0","value":"Define external invocation evidence and evaluate incremental value without authority escalation."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/20/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/state_profile_ref/entity_id","value":"state.partial-inconclusive"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/state_profile_ref/label_hint","value":"部分実装・結論不能"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/20/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/subject_ref/entity_id","value":"stage.llm-candidate"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/subject_ref/label_hint","value":"LLM候補"}
{"node_type":"string","pointer":"/implementation_conformance_items/20/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/21"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/21/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/entity_id","value":"conformance.stage.obligation-reaggregation"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/21/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/21/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/label","value":"段階7 義務別再集約"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/21/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/limitations/0","value":"Correct aggregation cannot compensate for missed upstream defects."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/21/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/21/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/21/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/procedure_refs/0","value":"src/semantic_guard/engine.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/procedure_refs/1","value":"src/semantic_guard/aggregation.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/procedure_refs/2","value":"tests/test_models_and_aggregation.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/proposition","value":"Obligation-level results are reaggregated without dropping challenge, coverage, holds, or unresolved obligations."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/21/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/remaining_obligations/0","value":"Bind aggregation evaluation to discovery-effectiveness evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/21/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/21/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/subject_ref/entity_id","value":"stage.obligation-reaggregation"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/subject_ref/label_hint","value":"義務別再集約"}
{"node_type":"string","pointer":"/implementation_conformance_items/21/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/22"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/22/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/entity_id","value":"conformance.stage.decision-request-materialization"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/22/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/22/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/item_kind","value":"pipeline_stage"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/label","value":"段階8 判断要求生成"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/22/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/limitations/0","value":"Decision-request generation is not proof of comprehension, correct routing, or repair effect."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/22/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/22/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/origin_requirement_refs/0/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/origin_requirement_refs/0/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/22/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/procedure_refs/0","value":"schemas/decision-request.schema.json"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/procedure_refs/1","value":"src/semantic_guard/public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/procedure_refs/2","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/proposition","value":"Unresolved or human-authority conditions produce bounded decision-request material without making the decision."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/22/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/remaining_obligations/0","value":"Validate agent usability, human comprehension, correct escalation, and repair outcomes."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/22/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/state_profile_ref/entity_id","value":"state.boundary-verified"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/state_profile_ref/label_hint","value":"境界局所検証済み"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/22/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/subject_ref/entity_id","value":"stage.decision-request-materialization"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/subject_ref/label_hint","value":"判断要求生成"}
{"node_type":"string","pointer":"/implementation_conformance_items/22/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/23"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/23/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/entity_id","value":"conformance.completeness.provider-accounting"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/23/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/23/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/23/evidence_refs/1"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/evidence_refs/1/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/evidence_refs/1/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/item_kind","value":"completeness"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/label","value":"解析器実行会計"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/23/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/limitations/0","value":"Declared capability execution is not semantic accuracy proof."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/23/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/23/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/23/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/procedure_refs/0","value":"src/semantic_guard/providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/procedure_refs/1","value":"tests/test_providers.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/proposition","value":"Requested, fulfilled, and missing capabilities, resource version, and target-span coverage are checked and published."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/23/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/remaining_obligations/0","value":"Add semantic performance evidence and operational failure cases."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/23/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/23/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/subject_ref/entity_id","value":"INV-VN-012"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/subject_ref/label_hint","value":"解析器実行会計の完全性"}
{"node_type":"string","pointer":"/implementation_conformance_items/23/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/24"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/24/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/entity_id","value":"conformance.completeness.public-result"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/24/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/24/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/item_kind","value":"completeness"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/label","value":"公開結果完全性"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/24/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/limitations/0","value":"Excerpt content is not reverified without source text; authenticity is absent."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/24/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/24/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":2,"node_type":"array","pointer":"/implementation_conformance_items/24/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/procedure_refs/0","value":"src/semantic_guard/public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/procedure_refs/1","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/proposition","value":"Public aggregate fields and source references are cross-checked against obligation entities and declared input identity."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/24/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/remaining_obligations/0","value":"Add original-source rechecking and elevated provenance only where required."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/24/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/24/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/subject_ref/entity_id","value":"INV-VN-013"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/subject_ref/label_hint","value":"公開結果完全性"}
{"node_type":"string","pointer":"/implementation_conformance_items/24/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/25"}
{"item_count":0,"node_type":"array","pointer":"/implementation_conformance_items/25/counterevidence_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/entity_id","value":"conformance.migration.legacy-baseline"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/25/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/25/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/item_kind","value":"migration"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/label","value":"旧版基線"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/25/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/limitations/0","value":"OS, host, dynamic libraries, time, and signed attestation are outside the baseline."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/25/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/25/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/25/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/procedure_refs/0","value":"migration/legacy-baseline-2026-07-16.json"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/procedure_refs/1","value":"src/semantic_guard/legacy_runner.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/procedure_refs/2","value":"tests/test_legacy_runner.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/proposition","value":"The legacy comparison target set, runner, adapter, and manifest are pinned and drift-checked."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/25/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/remaining_obligations/0","value":"Define environment qualification if legacy comparison becomes release evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/25/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/25/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/subject_ref/entity_id","value":"migration.legacy-baseline.v1"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/subject_ref/label_hint","value":"旧版基線 v1"}
{"node_type":"string","pointer":"/implementation_conformance_items/25/subject_ref/reference_kind","value":"ref"}
{"keys":["counterevidence_refs","entity_id","evidence_refs","item_kind","label","limitations","origin_requirement_refs","procedure_refs","proposition","remaining_obligations","state_profile_ref","subject_ref"],"member_count":12,"node_type":"object","pointer":"/implementation_conformance_items/26"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/26/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/26/counterevidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/counterevidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/counterevidence_refs/0/label_hint","value":"332 of 334 legacy tests passed with two known failures"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/entity_id","value":"conformance.migration.legacy-characterization"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/26/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/26/evidence_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/item_kind","value":"migration"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/label","value":"旧版特性試験"}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/26/limitations"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/limitations/0","value":"Legacy behavior is neither accepted truth nor evidence that v1 resolves the defects."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/26/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/26/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/origin_requirement_refs/0/reference_kind","value":"ref"}
{"item_count":3,"node_type":"array","pointer":"/implementation_conformance_items/26/procedure_refs"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/procedure_refs/0","value":"validation/legacy-shadow-known-defects-2026-07-16.json"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/procedure_refs/1","value":"src/semantic_guard/shadow.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/procedure_refs/2","value":"tests/test_shadow.py"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/proposition","value":"Legacy behavior is characterized with known defects preserved and is not used as a ground-truth oracle."}
{"item_count":1,"node_type":"array","pointer":"/implementation_conformance_items/26/remaining_obligations"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/remaining_obligations/0","value":"Classify each material old/new semantic difference under independent review."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/26/state_profile_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/state_profile_ref/entity_id","value":"state.partial-challenged"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/state_profile_ref/label_hint","value":"部分実装・反証材料あり"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/state_profile_ref/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/implementation_conformance_items/26/subject_ref"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/subject_ref/entity_id","value":"migration.legacy-characterization.2026-07-16"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/subject_ref/label_hint","value":"旧版特性試験"}
{"node_type":"string","pointer":"/implementation_conformance_items/26/subject_ref/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/non_goals"}
{"node_type":"string","pointer":"/non_goals/0","value":"Changing the v1 runtime, analyzer behavior, public CLI, MCP, or audit-result schemas."}
{"node_type":"string","pointer":"/non_goals/1","value":"Claiming standards conformance, field readiness, general natural-language accuracy, authenticity, or formal proof."}
{"node_type":"string","pointer":"/non_goals/2","value":"Owning execution control, work priority, delegation, durable management history, or human final acceptance."}
{"node_type":"string","pointer":"/non_goals/3","value":"Treating this source or its Markdown projection as execution evidence."}
{"node_type":"string","pointer":"/notation_profile","value":"entity-reference-notation/v0"}
{"keys":["action","context","current_state","detail_refs"],"member_count":4,"node_type":"object","pointer":"/record_surface"}
{"node_type":"string","pointer":"/record_surface/action","value":"Use every unresolved item's canonical resolution paths and their required obligations, including known gaps, as audit material for the next planning decision; do not infer path activation, priority, authorization, cutover, or final acceptance from this source."}
{"node_type":"string","pointer":"/record_surface/context","value":"The former verification matrix mixed implementation presence, test definitions, execution observations, field validity, assurance, freshness, and human acceptance. This source separates them while preserving the original purpose."}
{"node_type":"string","pointer":"/record_surface/current_state","value":"The canonical denominator now registers 17 verification concerns and 17 unresolved families. The six rebased concerns remain state.not-assessed, analyzer-route effectiveness remains a known gap, and whole lifecycle coverage, action occurrence and authenticity, repair effect, field validity, secure-operation boundaries, public elevated-trust bases, operational qualification and requalification, transition, and human operational use remain incomplete or unevaluated."}
{"item_count":12,"node_type":"array","pointer":"/record_surface/detail_refs"}
{"node_type":"string","pointer":"/record_surface/detail_refs/0","value":"./verification-source.schema.json"}
{"node_type":"string","pointer":"/record_surface/detail_refs/1","value":"./verification-validation-result.schema.json"}
{"node_type":"string","pointer":"/record_surface/detail_refs/2","value":"./verification-source.generated.md"}
{"node_type":"string","pointer":"/record_surface/detail_refs/3","value":"./verification-matrix.md"}
{"node_type":"string","pointer":"/record_surface/detail_refs/4","value":"../scripts/validate_verification_source.py"}
{"node_type":"string","pointer":"/record_surface/detail_refs/5","value":"../constitution/semantic-guard-constitution.yaml"}
{"node_type":"string","pointer":"/record_surface/detail_refs/6","value":"../docs/prototypes/origin-requirement.md"}
{"node_type":"string","pointer":"/record_surface/detail_refs/7","value":"../docs/prototypes/proof-obligation-assurance-graph-charter-2026-07-16.md"}
{"node_type":"string","pointer":"/record_surface/detail_refs/8","value":"../docs/prototypes/verification-register-completeness-charter-2026-07-16.md"}
{"node_type":"string","pointer":"/record_surface/detail_refs/9","value":"../docs/impact-and-execution-order-2026-07-16.md"}
{"node_type":"string","pointer":"/record_surface/detail_refs/10","value":"./integrated-verification-2026-07-16.json"}
{"node_type":"string","pointer":"/record_surface/detail_refs/11","value":"./real-nlp-smoke-2026-07-16.json"}
{"node_type":"string","pointer":"/recorded_at","value":"2026-08-27T15:43:40+09:00"}
{"node_type":"string","pointer":"/register_id","value":"verification-register.semantic-guard.r0"}
{"node_type":"string","pointer":"/schema_version","value":"semantic-guard-verification-source/v0"}
{"item_count":5,"node_type":"array","pointer":"/scope"}
{"node_type":"string","pointer":"/scope/0","value":"OR-01, OR-02, and OR-03 purpose coverage."}
{"node_type":"string","pointer":"/scope/1","value":"Discovery effectiveness, bounded action assurance, proof-obligation graph soundness, register completeness, lifecycle composition, repair effect, field validation, operational qualification, transition control, human operational use, and operational revalidation."}
{"node_type":"string","pointer":"/scope/2","value":"Secure and responsible handling of source artifacts, external analyzers or LLMs, dependencies, privileges, and incidents as a candidate cross-cutting engineering criterion pending human adoption."}
{"node_type":"string","pointer":"/scope/3","value":"The current requirement-relation vertical slice's invariant, pipeline, completeness, and migration conformance."}
{"node_type":"string","pointer":"/scope/4","value":"Relations between verification requirements and dated evidence observations."}
{"keys":["assurance","freshness","human_acceptance","implementation","independence_rule","validation","verification"],"member_count":7,"node_type":"object","pointer":"/state_axes"}
{"node_type":"string","pointer":"/state_axes/assurance","value":"The bounded proposition outcome, finality, challenge, and coverage under recorded assumptions and evidence."}
{"node_type":"string","pointer":"/state_axes/freshness","value":"Whether evidence is bound to the current subject snapshot and evaluation context."}
{"node_type":"string","pointer":"/state_axes/human_acceptance","value":"The human-owned accept, request_revision, or defer decision, kept separate from all technical states."}
{"node_type":"string","pointer":"/state_axes/implementation","value":"Whether a mechanism or contract exists in the declared scope."}
{"node_type":"string","pointer":"/state_axes/independence_rule","value":"No state axis may be inferred from another; implementation plus tests is not validation, assurance, freshness, or human acceptance."}
{"node_type":"string","pointer":"/state_axes/validation","value":"Whether the result was shown useful for the intended context and stakeholder purpose."}
{"node_type":"string","pointer":"/state_axes/verification","value":"Whether specified behavior was checked against a requirement by a declared method."}
{"item_count":10,"node_type":"array","pointer":"/state_profiles"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/0"}
{"node_type":"string","pointer":"/state_profiles/0/entity_id","value":"state.known-incomplete"}
{"node_type":"string","pointer":"/state_profiles/0/label","value":"既知の未充足"}
{"node_type":"string","pointer":"/state_profiles/0/meaning","value":"Repository inspection indicates missing implementation, but the assessment is not bound to a closed subject manifest."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/0/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/0/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/0/state/assurance/challenge","value":"open"}
{"node_type":"string","pointer":"/state_profiles/0/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/0/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/0/state/assurance/outcome","value":"refuted"}
{"node_type":"string","pointer":"/state_profiles/0/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/0/state/implementation","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/0/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/0/state/verification","value":"failed"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/1"}
{"node_type":"string","pointer":"/state_profiles/1/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/state_profiles/1/label","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/state_profiles/1/meaning","value":"Implementation and bounded local checks exist, while field validation and generality remain open."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/1/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/1/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/1/state/assurance/challenge","value":"none"}
{"node_type":"string","pointer":"/state_profiles/1/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/1/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/1/state/assurance/outcome","value":"satisfied"}
{"node_type":"string","pointer":"/state_profiles/1/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/1/state/implementation","value":"implemented"}
{"node_type":"string","pointer":"/state_profiles/1/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/1/state/verification","value":"passed"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/2"}
{"node_type":"string","pointer":"/state_profiles/2/entity_id","value":"state.partial-inconclusive"}
{"node_type":"string","pointer":"/state_profiles/2/label","value":"部分実装・結論不能"}
{"node_type":"string","pointer":"/state_profiles/2/meaning","value":"Some mechanism and observations exist, but the proposition is not closed under the required scope."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/2/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/2/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/2/state/assurance/challenge","value":"none"}
{"node_type":"string","pointer":"/state_profiles/2/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/2/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/2/state/assurance/outcome","value":"undetermined"}
{"node_type":"string","pointer":"/state_profiles/2/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/2/state/implementation","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/2/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/2/state/verification","value":"inconclusive"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/3"}
{"node_type":"string","pointer":"/state_profiles/3/entity_id","value":"state.partial-challenged"}
{"node_type":"string","pointer":"/state_profiles/3/label","value":"部分実装・反証材料あり"}
{"node_type":"string","pointer":"/state_profiles/3/meaning","value":"Some mechanism exists, while located counterevidence keeps the proposition challenged and incomplete."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/3/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/3/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/3/state/assurance/challenge","value":"open"}
{"node_type":"string","pointer":"/state_profiles/3/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/3/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/3/state/assurance/outcome","value":"undetermined"}
{"node_type":"string","pointer":"/state_profiles/3/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/3/state/implementation","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/3/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/3/state/verification","value":"inconclusive"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/4"}
{"node_type":"string","pointer":"/state_profiles/4/entity_id","value":"state.missing-not-evaluated"}
{"node_type":"string","pointer":"/state_profiles/4/label","value":"欠落・未検証"}
{"node_type":"string","pointer":"/state_profiles/4/meaning","value":"Located negative evidence indicates that the required mechanism is absent, while result-level verification and validation remain incomplete."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/4/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/4/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/4/state/assurance/challenge","value":"none"}
{"node_type":"string","pointer":"/state_profiles/4/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/4/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/4/state/assurance/outcome","value":"refuted"}
{"node_type":"string","pointer":"/state_profiles/4/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/4/state/implementation","value":"missing"}
{"node_type":"string","pointer":"/state_profiles/4/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/4/state/verification","value":"not_run"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/5"}
{"node_type":"string","pointer":"/state_profiles/5/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/state_profiles/5/label","value":"未評価"}
{"node_type":"string","pointer":"/state_profiles/5/meaning","value":"No evidence-bound assessment establishes whether the required mechanism exists or is absent."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/5/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/5/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/5/state/assurance/challenge","value":"none"}
{"node_type":"string","pointer":"/state_profiles/5/state/assurance/coverage","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/5/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/5/state/assurance/outcome","value":"undetermined"}
{"node_type":"string","pointer":"/state_profiles/5/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/5/state/implementation","value":"not_assessed"}
{"node_type":"string","pointer":"/state_profiles/5/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/5/state/verification","value":"not_run"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/6"}
{"node_type":"string","pointer":"/state_profiles/6/entity_id","value":"state.missing-refuted"}
{"node_type":"string","pointer":"/state_profiles/6/label","value":"必要機構欠落により非充足"}
{"node_type":"string","pointer":"/state_profiles/6/meaning","value":"Inspection indicates that a required mechanism is absent, but the assessment is not bound to a closed subject manifest."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/6/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/6/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/6/state/assurance/challenge","value":"open"}
{"node_type":"string","pointer":"/state_profiles/6/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/6/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/6/state/assurance/outcome","value":"refuted"}
{"node_type":"string","pointer":"/state_profiles/6/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/6/state/implementation","value":"missing"}
{"node_type":"string","pointer":"/state_profiles/6/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/6/state/verification","value":"failed"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/7"}
{"node_type":"string","pointer":"/state_profiles/7/entity_id","value":"state.boundary-verified"}
{"node_type":"string","pointer":"/state_profiles/7/label","value":"境界局所検証済み"}
{"node_type":"string","pointer":"/state_profiles/7/meaning","value":"A declared authority or fail-closed boundary is implemented and locally verified, without implying product acceptance."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/7/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/7/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/7/state/assurance/challenge","value":"none"}
{"node_type":"string","pointer":"/state_profiles/7/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/7/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/7/state/assurance/outcome","value":"satisfied"}
{"node_type":"string","pointer":"/state_profiles/7/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/7/state/implementation","value":"implemented"}
{"node_type":"string","pointer":"/state_profiles/7/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/7/state/verification","value":"passed"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/8"}
{"node_type":"string","pointer":"/state_profiles/8/entity_id","value":"state.field-not-evaluated"}
{"node_type":"string","pointer":"/state_profiles/8/label","value":"評価設計のみ・実務未評価"}
{"node_type":"string","pointer":"/state_profiles/8/meaning","value":"Metrics or evaluation intent exist, but no target-population field validation has been completed."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/8/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/8/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/8/state/assurance/challenge","value":"none"}
{"node_type":"string","pointer":"/state_profiles/8/state/assurance/coverage","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/8/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/8/state/assurance/outcome","value":"undetermined"}
{"node_type":"string","pointer":"/state_profiles/8/state/freshness","value":"unbound"}
{"node_type":"string","pointer":"/state_profiles/8/state/implementation","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/8/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/8/state/verification","value":"not_run"}
{"keys":["entity_id","label","meaning","state"],"member_count":4,"node_type":"object","pointer":"/state_profiles/9"}
{"node_type":"string","pointer":"/state_profiles/9/entity_id","value":"state.stale-partial-evidence"}
{"node_type":"string","pointer":"/state_profiles/9/label","value":"旧観測による部分材料"}
{"node_type":"string","pointer":"/state_profiles/9/meaning","value":"The observation remains useful as historical material but is not bound to the current snapshot."}
{"keys":["assurance","freshness","implementation","validation","verification"],"member_count":5,"node_type":"object","pointer":"/state_profiles/9/state"}
{"keys":["challenge","coverage","finality","outcome"],"member_count":4,"node_type":"object","pointer":"/state_profiles/9/state/assurance"}
{"node_type":"string","pointer":"/state_profiles/9/state/assurance/challenge","value":"none"}
{"node_type":"string","pointer":"/state_profiles/9/state/assurance/coverage","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/9/state/assurance/finality","value":"provisional"}
{"node_type":"string","pointer":"/state_profiles/9/state/assurance/outcome","value":"undetermined"}
{"node_type":"string","pointer":"/state_profiles/9/state/freshness","value":"stale"}
{"node_type":"string","pointer":"/state_profiles/9/state/implementation","value":"partial"}
{"node_type":"string","pointer":"/state_profiles/9/state/validation","value":"not_evaluated"}
{"node_type":"string","pointer":"/state_profiles/9/state/verification","value":"inconclusive"}
{"node_type":"string","pointer":"/status","value":"active_draft"}
{"node_type":"string","pointer":"/title","value":"semantic-guard v1 verification requirement and evidence source"}
{"item_count":17,"node_type":"array","pointer":"/unresolved_items"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/0"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/0/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/0/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/0/affected_entity_refs/0/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"node_type":"string","pointer":"/unresolved_items/0/affected_entity_refs/0/label_hint","value":"OR-01 工程横断被覆"}
{"node_type":"string","pointer":"/unresolved_items/0/affected_entity_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/0/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/0/entity_id","value":"unresolved.lifecycle-surface-vertical-slices"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/0/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/0/evidence_gap/0","value":"Human-accepted per-surface purpose, engineering basis, scope, non-goals, and acceptance boundary."}
{"node_type":"string","pointer":"/unresolved_items/0/evidence_gap/1","value":"Nine versioned profiles, closed contracts, vertical implementations, and conformance suites."}
{"node_type":"string","pointer":"/unresolved_items/0/evidence_gap/2","value":"Independent cross-surface review and representative operational observations."}
{"node_type":"string","pointer":"/unresolved_items/0/label","value":"原点九工程面の profile・契約・縦断実装"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/0/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/0/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/authority_basis","value":"Adopting the meaning, scope, non-goals, and acceptance boundary of each lifecycle audit profile changes the authorized product purpose."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/decision_question","value":"For each of the nine currently required lifecycle surfaces, what meaning, engineering basis, scope, non-goals, and risk boundary shall its v1 profile use; if any surface is to leave the denominator, what separate versioned origin-requirement revision authorizes that change?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/0/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/evidence_needed/0","value":"Human per-surface profile adoption record, or a separate versioned human-approved origin-requirement revision that explicitly changes the denominator."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/obligation_id","value":"obligation.lifecycle-surfaces.human-profile-acceptance"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/0/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/0/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.rule-pack.human-adoption"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"体系知 rule pack の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/0/responsibility","value":"Accept or revise the meaning, engineering basis, scope, non-goals, and acceptance boundary of each of the nine currently missing OR-01 lifecycle profiles. Deferral changes timing only. Rejection may remove a surface from the denominator only through a separate, versioned, human-approved revision of the origin requirement; absence of adoption does not erase the present requirement."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/0/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/authority_basis","value":"Profiles, schemas, runtime paths, fixtures, and conformance suites are technical realization after their meaning is accepted."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/0/resolution_obligations/1/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/0/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/evidence_needed/0","value":"Per-surface profile and schema."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/evidence_needed/1","value":"Per-surface vertical implementation."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/evidence_needed/2","value":"Conformance, negative, metamorphic, and migration observations."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/obligation_id","value":"obligation.lifecycle-surfaces.implement-vertical-slices"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/0/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/0/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.lifecycle-surfaces.human-profile-acceptance"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"九工程面 profile の人間受理"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/1/responsibility","value":"Implement each of the nine lifecycle profiles currently required by OR-01 as a versioned contract, fail-closed vertical path, negative and metamorphic suite, evidence projection, and migration boundary, except where a separate versioned human-approved origin-requirement revision has changed that denominator."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/0/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/authority_basis","value":"Cross-surface omission and interpretation error require review that is not supplied solely by each implementation author."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/0/resolution_obligations/2/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/0/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/evidence_needed/0","value":"Independent cross-surface conformance and omission review."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/obligation_id","value":"obligation.lifecycle-surfaces.independent-review"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/0/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/0/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.lifecycle-surfaces.implement-vertical-slices"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"九工程面の縦断実装"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_obligations/2/responsibility","value":"Review every implemented surface remaining in the current versioned denominator for origin trace, engineering interpretation, omission, cross-surface consistency, and overclaiming, and review the trace and authorization of any origin-requirement revision that changed that denominator."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/0/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/0/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/activation_condition","value":"Applies to the current OR-01 denominator, or to a revised denominator only after a separate versioned human-approved origin-requirement revision."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/completion_rule","value":"Every surface remaining in the versioned denominator has an accepted engineering-grounded profile, closed contract, fail-closed vertical implementation, bounded conformance evidence, declared unproven scope, and independent omission review; any denominator change has separately reviewed origin authorization."}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/path_id","value":"resolution-path.lifecycle-surfaces.current-or-revised-denominator"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.lifecycle-surfaces.human-profile-acceptance"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/0/label_hint","value":"九工程面 profile の人間受理"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.lifecycle-surfaces.implement-vertical-slices"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/1/label_hint","value":"九工程面の縦断実装"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.lifecycle-surfaces.independent-review"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/2/label_hint","value":"工程横断の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/0/resolution_summary","value":"The current nine missing OR-01 surfaces remain required unless a separate human-approved origin revision changes the denominator; every surface in the resulting denominator must satisfy the same profile, implementation, evidence, and review closure."}
{"node_type":"string","pointer":"/unresolved_items/0/subject","value":"Candidate profiles now cover request, exploration-question, decision-state, plan, action, realization-policy, diff, verification, and completion-claim, and several local sidecar contracts exist; none of the nine profiles is human-adopted, resolved into public stage adapters, implemented as a complete vertical path, or supported by bounded conformance evidence."}
{"node_type":"string","pointer":"/unresolved_items/0/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/1"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/1/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/1/affected_entity_refs/0/entity_id","value":"verification.or03.repair-effect"}
{"node_type":"string","pointer":"/unresolved_items/1/affected_entity_refs/0/label_hint","value":"OR-03 修正循環の有効性"}
{"node_type":"string","pointer":"/unresolved_items/1/affected_entity_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/1/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/1/entity_id","value":"unresolved.repair-loop-implementation-and-effect"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/1/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/1/evidence_gap/0","value":"Human-accepted repair outcome, escalation, authority, and error-cost policy."}
{"node_type":"string","pointer":"/unresolved_items/1/evidence_gap/1","value":"Finding-to-repair and before-after re-audit implementation."}
{"node_type":"string","pointer":"/unresolved_items/1/evidence_gap/2","value":"Independent repair-effect, regression, and escalation observations."}
{"node_type":"string","pointer":"/unresolved_items/1/label","value":"修正循環の実装と効果評価"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/1/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/1/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/authority_basis","value":"What counts as useful repair, unacceptable regression, correct escalation, and retained human authority is a value and risk decision."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/decision_question","value":"Which before-after changes count as useful repair, unacceptable regression, or required human escalation, and who may authorize the resulting work?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/1/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/evidence_needed/0","value":"Human repair-effect and escalation policy decision record."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/obligation_id","value":"obligation.repair-loop.human-outcome-policy"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/1/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.field-policy.human-risk-choice"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"実務用途と危険費用の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/0/responsibility","value":"Choose repair outcomes, error costs, escalation rules, acceptance boundary, and the evidence needed before a repair may influence completion material."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/1/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/authority_basis","value":"Finding-to-repair mapping, bounded handoff, re-audit, and regression accounting are technical realization once outcome and authority policy is fixed."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/1/resolution_obligations/1/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/1/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/evidence_needed/0","value":"Finding-to-repair contract."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/evidence_needed/1","value":"Bounded repair handoff implementation."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/evidence_needed/2","value":"Before-after re-audit and regression suite."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/obligation_id","value":"obligation.repair-loop.implement-and-reaudit"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/1/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.repair-loop.human-outcome-policy"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"修正効果・移譲方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/1/responsibility","value":"Implement machine-readable repair targets, caller-owned execution handoff, before-after re-audit, regression detection, unresolved remainder, and escalation material without moving control into semantic-guard."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/1/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/authority_basis","value":"Repair improvement, regression, and escalation correctness cannot be validated only by the agent or audit implementation that produced the change."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/1/resolution_obligations/2/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/1/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/evidence_needed/0","value":"Independent before-after repair-effect and escalation review."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/obligation_id","value":"obligation.repair-loop.independent-effect-review"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.field-policy.evaluation-protocol"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"実務評価手順"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.repair-loop.implement-and-reaudit"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"修正循環・再監査の実装"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_obligations/2/responsibility","value":"Evaluate repair effect, regression, unresolved remainder, and escalation correctness on independently reviewed and adjudicated cases."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/1/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/1/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/activation_condition","value":"Applies whenever repair-effect completion is claimed for OR-03."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/completion_rule","value":"Located findings pass through caller-authorized repair, before-after re-audit, regression and remainder accounting, correct escalation, and independent adjudicated effect evaluation under the accepted human policy."}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/path_id","value":"resolution-path.repair-loop.full-cycle"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.repair-loop.human-outcome-policy"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/0/label_hint","value":"修正効果方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.repair-loop.implement-and-reaudit"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/1/label_hint","value":"修正循環の実装と再監査"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.repair-loop.independent-effect-review"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/2/label_hint","value":"修正効果の独立評価"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/1/resolution_summary","value":"A caller-controlled repair path must implement and independently evaluate the whole finding-to-repair-to-reaudit cycle under a human-owned outcome policy."}
{"node_type":"string","pointer":"/unresolved_items/1/subject","value":"A local v1 finding-to-repair, responsibility-material, re-audit, and regression-accounting contract now exists, but no human-adopted outcome policy, bound field execution, or independent repair-effect and escalation evaluation establishes practical improvement."}
{"node_type":"string","pointer":"/unresolved_items/1/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/2"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/2/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/2/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/2/affected_entity_refs/0/entity_id","value":"verification.or01.engineering-knowledge-governance"}
{"node_type":"string","pointer":"/unresolved_items/2/affected_entity_refs/0/label_hint","value":"体系知の根拠統治"}
{"node_type":"string","pointer":"/unresolved_items/2/affected_entity_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/2/claim_effect","value":"partially_blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/2/entity_id","value":"unresolved.engineering-rule-pack-governance"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/2/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/2/evidence_gap/0","value":"Versioned rule-pack source."}
{"node_type":"string","pointer":"/unresolved_items/2/evidence_gap/1","value":"Independent engineering review."}
{"node_type":"string","pointer":"/unresolved_items/2/evidence_gap/2","value":"Human adoption and exception policy."}
{"node_type":"string","pointer":"/unresolved_items/2/label","value":"体系知 rule pack の採用統治"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/2/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/2/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/0/authority_basis","value":"This constructs traceable audit material within already accepted purpose and does not adopt an engineering interpretation."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/0/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/2/resolution_obligations/0/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/2/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/0/evidence_needed/0","value":"Versioned rule-pack source."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/0/evidence_needed/1","value":"Criterion-to-source locator mapping."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/0/obligation_id","value":"obligation.rule-pack.construct-mappings"}
{"item_count":0,"node_type":"array","pointer":"/unresolved_items/2/resolution_obligations/0/precondition_obligation_refs"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/0/responsibility","value":"Construct versioned criterion mappings with applicability, counterconditions, limitations, and review triggers."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/2/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/authority_basis","value":"Independence from the implementation author is itself the required evidence property."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/2/resolution_obligations/1/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/2/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/evidence_needed/0","value":"Independent engineering review record."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/obligation_id","value":"obligation.rule-pack.independent-review"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/2/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/2/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.rule-pack.construct-mappings"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"版付き基準対応の構築"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/1/responsibility","value":"Review the engineering interpretation independently of the implementation author."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/2/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/authority_basis","value":"Adopting sources, interpretations, exceptions, and review cadence changes the authorized normative basis."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/decision_question","value":"Which rule-pack sources, interpretations, exceptions, and review cadence are authorized?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/2/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/evidence_needed/0","value":"Human adoption and exception decision record."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/obligation_id","value":"obligation.rule-pack.human-adoption"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.rule-pack.construct-mappings"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"版付き基準対応の構築"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.rule-pack.independent-review"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"体系知解釈の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_obligations/2/responsibility","value":"Accept, revise, defer, or reject the selected sources, interpretations, and exception policy."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/2/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/2/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/activation_condition","value":"Applies to every engineering criterion adopted into an audit profile."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/completion_rule","value":"The human adopts a versioned governance profile only after every criterion has traceable applicability, counterconditions, limitations, review triggers, and independent engineering-interpretation review evidence."}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/path_id","value":"resolution-path.engineering-rule-pack.governed-and-reviewed"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.rule-pack.construct-mappings"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/0/label_hint","value":"体系知対応表の構築"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.rule-pack.independent-review"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/1/label_hint","value":"体系知解釈の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.rule-pack.human-adoption"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/2/label_hint","value":"体系知 rule pack の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/2/resolution_summary","value":"Adopted engineering criteria require constructed trace mappings, independent interpretation review, and human adoption; naming a body of knowledge is insufficient."}
{"node_type":"string","pointer":"/unresolved_items/2/subject","value":"Source editions, clause or concept mappings, interpretations, adoption authority, exceptions, and review conditions for engineering-grounded audit rules."}
{"node_type":"string","pointer":"/unresolved_items/2/uncertainty_kind","value":"pending_decision"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/3"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/3/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/3/affected_entity_refs/0/entity_id","value":"verification.or01.discovery-effectiveness"}
{"node_type":"string","pointer":"/unresolved_items/3/affected_entity_refs/0/label_hint","value":"未解決・欠陥の発見性能"}
{"node_type":"string","pointer":"/unresolved_items/3/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/3/affected_entity_refs/1/entity_id","value":"verification.cross.field-validation"}
{"node_type":"string","pointer":"/unresolved_items/3/affected_entity_refs/1/label_hint","value":"実務資料上の妥当性確認"}
{"node_type":"string","pointer":"/unresolved_items/3/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/3/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/3/entity_id","value":"unresolved.field-population-and-thresholds"}
{"item_count":7,"node_type":"array","pointer":"/unresolved_items/3/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/3/evidence_gap/0","value":"Human risk and intended-use policy."}
{"node_type":"string","pointer":"/unresolved_items/3/evidence_gap/1","value":"Human-adopted engineering rule-pack meaning."}
{"node_type":"string","pointer":"/unresolved_items/3/evidence_gap/2","value":"Typed state derivation and closed subject binding."}
{"node_type":"string","pointer":"/unresolved_items/3/evidence_gap/3","value":"Human-selected secure-operation applicability boundary."}
{"node_type":"string","pointer":"/unresolved_items/3/evidence_gap/4","value":"Domain sampling frame."}
{"node_type":"string","pointer":"/unresolved_items/3/evidence_gap/5","value":"Independent labeling and adjudication design."}
{"node_type":"string","pointer":"/unresolved_items/3/evidence_gap/6","value":"Executed field evaluation with uncertainty and error-cost results."}
{"node_type":"string","pointer":"/unresolved_items/3/label","value":"実務母集団・費用・閾値"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/0/authority_basis","value":"Intended use, catastrophic-error cost, and acceptable thresholds are value and risk decisions."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/0/decision_question","value":"Which errors are intolerable, for whom, in which population, and at what decision threshold?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/0/evidence_needed/0","value":"Human risk and intended-use decision record."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/0/obligation_id","value":"obligation.field-policy.human-risk-choice"}
{"item_count":0,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/0/precondition_obligation_refs"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/0/responsibility","value":"Choose intended use, target population, catastrophic-error cost, and decision thresholds."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/authority_basis","value":"Sampling and measurement machinery can be engineered only after the human risk policy fixes its estimand and costs, the engineering meaning is adopted, state and subject binding is defined, and secure-operation applicability is selected."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/3/resolution_obligations/1/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/evidence_needed/0","value":"Domain sampling frame."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/evidence_needed/1","value":"Versioned evaluation protocol and cost matrix."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/obligation_id","value":"obligation.field-policy.evaluation-protocol"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.field-policy.human-risk-choice"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"実務用途と危険費用の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.rule-pack.human-adoption"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"体系知 rule pack の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/2/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/2/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/3/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/3/label_hint","value":"安全運用の適用性判断"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/precondition_obligation_refs/3/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/1/responsibility","value":"Construct the sampling, measurement, holdout, and uncertainty protocol within the accepted risk policy and governed rule-pack meaning, using typed state derivation and a closed subject manifest inside the selected secure-operation applicability boundary."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/authority_basis","value":"Reviewer independence and preserved disagreement cannot be supplied by the implementation author alone."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/3/resolution_obligations/2/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/evidence_needed/0","value":"Independent double-review and adjudication record."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/obligation_id","value":"obligation.field-policy.independent-labels"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.field-policy.evaluation-protocol"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"評価手順の構築"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/2/responsibility","value":"Provide independent labels, disagreement records, and adjudication evidence."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/3"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/authority_basis","value":"Executing the accepted protocol is bounded technical work only after the human risk policy, governed engineering basis, typed state and subject binding, secure-operation applicability, protocol, and independent labels are all available."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/3/resolution_obligations/3/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/3/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/evidence_needed/0","value":"Bound execution record and raw result locator."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/evidence_needed/1","value":"Stratified measures, uncertainty report, and accepted cost-matrix evaluation."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/obligation_id","value":"obligation.field-policy.execute-evaluation"}
{"item_count":6,"node_type":"array","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/0/entity_id","value":"obligation.field-policy.human-risk-choice"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/0/label_hint","value":"実務用途と危険費用の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/1/entity_id","value":"obligation.rule-pack.human-adoption"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/1/label_hint","value":"体系知 rule pack の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/2/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/2/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/3/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/3/label_hint","value":"安全運用の適用性判断"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/4"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/4/entity_id","value":"obligation.field-policy.evaluation-protocol"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/4/label_hint","value":"評価手順の構築"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/5"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/5/entity_id","value":"obligation.field-policy.independent-labels"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/5/label_hint","value":"独立標識と裁定証拠"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/precondition_obligation_refs/5/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_obligations/3/responsibility","value":"Execute the versioned protocol on the selected, subject-bound holdout corpus within the accepted engineering, risk, and secure-operation boundaries; preserve raw predictions and abstentions and calculate stratified error, catastrophic false-satisfaction, uncertainty, disagreement, and cost results without changing accepted meaning or thresholds."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/3/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/3/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/activation_condition","value":"Applies to any field-validity or practical-readiness claim for a selected use context."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/completion_rule","value":"A human accepts the intended use, error costs, target population, thresholds, governed rule-pack meaning, and secure-operation applicability; typed state derivation and subject binding is in place; a versioned sampling, holdout, measurement, and uncertainty protocol is executed; and independent labels, disagreements, and adjudications are preserved as located evidence."}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/path_id","value":"resolution-path.field-validation.accepted-and-independently-labeled"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.field-policy.human-risk-choice"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/0/label_hint","value":"実務用途と危険費用の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.field-policy.evaluation-protocol"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/1/label_hint","value":"実務評価手順の構築"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.field-policy.independent-labels"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/2/label_hint","value":"独立標識と裁定証拠"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/3/entity_id","value":"obligation.field-policy.execute-evaluation"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/3/label_hint","value":"実務評価の実行観測"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_paths/0/required_obligation_refs/3/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/3/resolution_summary","value":"Field evaluation cannot be designed or executed before human risk policy, governed rule-pack meaning, typed state and subject binding, and secure-operation applicability; the resulting protocol, independent labeling and adjudication, and bound execution are all required before field validity is closed."}
{"node_type":"string","pointer":"/unresolved_items/3/subject","value":"Target populations, sampling frames, label policy, catastrophic-error cost, decision thresholds, and uncertainty method for each lifecycle profile."}
{"node_type":"string","pointer":"/unresolved_items/3/uncertainty_kind","value":"value_judgment"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/4"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/4/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/4/affected_entity_refs/0/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"node_type":"string","pointer":"/unresolved_items/4/affected_entity_refs/0/label_hint","value":"行為発生・主体・権限・手続適合"}
{"node_type":"string","pointer":"/unresolved_items/4/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/4/affected_entity_refs/1/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"node_type":"string","pointer":"/unresolved_items/4/affected_entity_refs/1/label_hint","value":"成果物来歴・真正性・因果境界"}
{"node_type":"string","pointer":"/unresolved_items/4/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/4/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/4/entity_id","value":"unresolved.action-evidence-and-authenticity-mechanism"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/4/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/4/evidence_gap/0","value":"Threat and trust model."}
{"node_type":"string","pointer":"/unresolved_items/4/evidence_gap/1","value":"Action-evidence envelope."}
{"node_type":"string","pointer":"/unresolved_items/4/evidence_gap/2","value":"Runtime observer and provenance mechanism."}
{"node_type":"string","pointer":"/unresolved_items/4/evidence_gap/3","value":"Adversarial validation."}
{"node_type":"string","pointer":"/unresolved_items/4/label","value":"行為証拠・真正性機構"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/4/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/4/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/authority_basis","value":"Trusted actors, observers, clocks, roots, and acceptable claim strength define deployment risk acceptance."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/decision_question","value":"Which actors, observers, clocks, trust roots, and causal claims are trusted for this deployment profile?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/4/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/evidence_needed/0","value":"Human trust and threat-model decision record."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/obligation_id","value":"obligation.action-assurance.human-trust-model"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/4/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.assurance-profile.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"全体保証 profile 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/0/responsibility","value":"Choose the bounded threat model, trust roots, acceptable claim strength, and residual-risk policy."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/4/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/authority_basis","value":"The contract and mechanisms are technical realization work once their trust boundary is authorized."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/4/resolution_obligations/1/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/4/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/evidence_needed/0","value":"Action-evidence envelope."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/evidence_needed/1","value":"Runtime observer and provenance implementation."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/obligation_id","value":"obligation.action-assurance.implement-evidence-envelope"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/4/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.action-assurance.human-trust-model"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"信頼・脅威模型の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/1/responsibility","value":"Implement the action-evidence contract, runtime observation, authority snapshot, provenance, and replay controls within that model."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/4/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/authority_basis","value":"The requested independence and adversarial challenge cannot be established by the mechanism author alone."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/4/resolution_obligations/2/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/4/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/evidence_needed/0","value":"Adversarial evidence report."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/evidence_needed/1","value":"Independent observer record where required by the selected profile."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/obligation_id","value":"obligation.action-assurance.adversarial-review"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.action-assurance.human-trust-model"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"信頼・脅威模型の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.action-assurance.implement-evidence-envelope"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"行為証拠機構の実装"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_obligations/2/responsibility","value":"Challenge the mechanism with independent and adversarial observations appropriate to the selected assurance profile."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/4/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/4/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/activation_condition","value":"Applies to every bounded action-occurrence, authority, provenance, authenticity, or replay-resistance claim."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/completion_rule","value":"The human accepts a bounded threat and trust model, its evidence mechanisms are implemented, and independent adversarial observations support only the claim strength and semantics actually covered by those mechanisms."}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/path_id","value":"resolution-path.action-assurance.implemented-and-challenged"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.action-assurance.human-trust-model"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/0/label_hint","value":"信頼・脅威模型の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.action-assurance.implement-evidence-envelope"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/1/label_hint","value":"行為証拠機構の実装"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.action-assurance.adversarial-review"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/2/label_hint","value":"行為証拠機構の敵対査読"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/4/resolution_summary","value":"A human-owned trust model, implemented action-evidence mechanisms, and independent adversarial evidence must all close without semantic overclaiming."}
{"node_type":"string","pointer":"/unresolved_items/4/subject","value":"Runtime observation, actor and authority evidence, trusted time, artifact provenance, replay protection, signature or append-only trust mechanism, and causal model boundaries."}
{"node_type":"string","pointer":"/unresolved_items/4/uncertainty_kind","value":"pending_decision"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/5"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/5/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/5/affected_entity_refs/0/entity_id","value":"verification.cross.secure-and-responsible-operation"}
{"node_type":"string","pointer":"/unresolved_items/5/affected_entity_refs/0/label_hint","value":"安全・責任ある情報取扱いと外部境界"}
{"node_type":"string","pointer":"/unresolved_items/5/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/5/affected_entity_refs/1/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/unresolved_items/5/affected_entity_refs/1/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/unresolved_items/5/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/5/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/5/entity_id","value":"unresolved.secure-information-handling-and-external-boundaries"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/5/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/5/evidence_gap/0","value":"Human intended-use, data, egress, retention, privilege, and incident-risk policy."}
{"node_type":"string","pointer":"/unresolved_items/5/evidence_gap/1","value":"Versioned data-flow and threat model plus enforceable provider and evidence-store controls."}
{"node_type":"string","pointer":"/unresolved_items/5/evidence_gap/2","value":"Independent adversarial review for the selected deployment profile."}
{"node_type":"string","pointer":"/unresolved_items/5/label","value":"安全な情報取扱い・外部送信・権限境界の採用"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/0/authority_basis","value":"Allowed data classes, external transmission, retention, privileges, incident tolerance, and residual risk are organizational and human decisions."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/0/decision_question","value":"For which artifacts and deployment profiles may semantic-guard use external providers or privileged actions, and under which data, retention, incident, and residual-risk controls?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/0/evidence_needed/0","value":"Human secure-operation and data-handling decision record, or a versioned non-applicability record with a closed deployment boundary and re-evaluation triggers."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/0/obligation_id","value":"obligation.secure-operation.human-policy"}
{"item_count":0,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/0/precondition_obligation_refs"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/0/responsibility","value":"Adopt or revise the candidate secure-operation criterion and choose intended use, data classes, providers, egress, retention, privilege, incident, and residual-risk policy. Deferral leaves the claim blocked. A non-applicability decision is valid only as a versioned closed boundary excluding real or protected data, external providers, privileged actions, and durable operation, with explicit re-evaluation triggers."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/authority_basis","value":"Data-flow, threat-model, policy enforcement, provenance checks, and adversarial test machinery are technical realization after the human boundary is fixed."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/5/resolution_obligations/1/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/evidence_needed/0","value":"Versioned secure-operation profile."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/evidence_needed/1","value":"Data-flow and threat model."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/evidence_needed/2","value":"Enforcement and adversarial test records."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/obligation_id","value":"obligation.secure-operation.implement-controls"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"安全運用方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/1/responsibility","value":"Implement the adopted profile, fail-closed provider and privilege gates, minimization and redaction, retention controls, resource provenance, incident evidence, and adversarial conformance tests."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/authority_basis","value":"Whether the selected repository, configuration, data flow, provider graph, privilege grants, and storage paths actually remain inside a declared non-applicability boundary is an inspectable technical proposition, not a human value declaration."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/5/resolution_obligations/2/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/evidence_needed/0","value":"Closed subject and configuration manifest."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/evidence_needed/1","value":"Located data-flow, provider, privilege, and storage inspection record."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/evidence_needed/2","value":"Re-evaluation trigger conformance record."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/obligation_id","value":"obligation.secure-operation.verify-nonapplicability-boundary"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"安全運用方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/2/responsibility","value":"Inspect and bind the selected subject, configuration, data classes, provider routes, privilege grants, evidence stores, and execution path to demonstrate the absence of real or protected data, external providers, privileged actions, and durable operation, and test the declared re-evaluation triggers."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/3"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/authority_basis","value":"Independent challenge of exfiltration, injection, provenance, privilege, exhaustion, and recovery controls cannot be supplied by their implementation author alone."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/5/resolution_obligations/3/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/3/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/evidence_needed/0","value":"Independent secure-operation review and adversarial observation record."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/obligation_id","value":"obligation.secure-operation.independent-review"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/0/entity_id","value":"obligation.assurance-profile.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/0/label_hint","value":"保証 profile 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/1/entity_id","value":"obligation.assurance-profile.public-contract"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/1/label_hint","value":"公開高信頼根拠契約の実装"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/2/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/2/label_hint","value":"安全運用方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/3/entity_id","value":"obligation.secure-operation.implement-controls"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/3/label_hint","value":"安全運用制御の実装"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/precondition_obligation_refs/3/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_obligations/3/responsibility","value":"Review and challenge the adopted data, provider, privilege, provenance, adversarial-input, resource-exhaustion, retention, and incident controls independently."}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/5/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/5/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/activation_condition","value":"Selected only by the human secure-operation decision when real or protected data, an external provider, privileged action, or durable operation is in scope."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/completion_rule","value":"The human-approved profile has fail-closed information-flow and authority controls, and independent adversarial evidence supports the bounded deployment claim without presenting semantic-guard as a general security certifier."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/path_id","value":"resolution-path.secure-operation.adopted-profile"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/0/label_hint","value":"安全運用方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.secure-operation.implement-controls"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/1/label_hint","value":"安全運用制御の実装"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.secure-operation.independent-review"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/2/label_hint","value":"安全運用制御の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/5/resolution_paths/1"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/activation_condition","value":"Selected only by a versioned human non-applicability decision for a closed synthetic-public, local-only, unprivileged, non-durable deployment boundary."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/completion_rule","value":"A closed manifest and located configuration, data-flow, provider, privilege, and storage observations demonstrate the declared exclusions, and tested change triggers reactivate the adopted-profile path when the observed boundary changes."}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/path_id","value":"resolution-path.secure-operation.verified-nonapplicability"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/0/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/0/label_hint","value":"安全運用方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/1/entity_id","value":"obligation.secure-operation.verify-nonapplicability-boundary"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/1/label_hint","value":"非適用境界の拘束観測"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_paths/1/required_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/5/resolution_summary","value":"Secure-operation closes only through an implemented and independently challenged adopted profile, or through a human-declared non-applicability boundary whose factual exclusions and reactivation triggers are demonstrably verified."}
{"node_type":"string","pointer":"/unresolved_items/5/subject","value":"Whether and how a secure-operation criterion is adopted for real artifacts, external analyzers or LLMs, dependencies, privileges, evidence retention, adversarial inputs, and incidents."}
{"node_type":"string","pointer":"/unresolved_items/5/uncertainty_kind","value":"value_judgment"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/6"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/6/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/0/entity_id","value":"verification.or02.bounded-claim-model"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/0/label_hint","value":"限定的立証の主張模型"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/1/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/1/label_hint","value":"行為発生・主体・権限・手続適合"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/affected_entity_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/2/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/2/label_hint","value":"成果物来歴・真正性・因果境界"}
{"node_type":"string","pointer":"/unresolved_items/6/affected_entity_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/6/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/6/entity_id","value":"unresolved.assurance-profile-and-public-trust-basis"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/6/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/6/evidence_gap/0","value":"Human-approved assurance-profile taxonomy and independence policy."}
{"node_type":"string","pointer":"/unresolved_items/6/evidence_gap/1","value":"Public elevated-trust basis fields and conditional schema constraints."}
{"node_type":"string","pointer":"/unresolved_items/6/evidence_gap/2","value":"Adversarial profile-selection and trust-label tests."}
{"node_type":"string","pointer":"/unresolved_items/6/label","value":"保証 profile と公開高信頼級の根拠契約"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/6/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/6/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/0/authority_basis","value":"Claim strength, independence conditions, trusted roots, and downgrade policy determine accepted risk and normative meaning."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/0/decision_question","value":"Which claim classes and deployment risks require independent observation, signed attestation, or formal verification, and what downgrade is permitted when the basis is absent?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/6/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/0/evidence_needed/0","value":"Human assurance-profile and trust policy decision record."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/0/obligation_id","value":"obligation.assurance-profile.human-policy"}
{"item_count":0,"node_type":"array","pointer":"/unresolved_items/6/resolution_obligations/0/precondition_obligation_refs"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/0/responsibility","value":"Choose claim-strength profiles, required observer independence, acceptable trust roots, and downgrade behavior."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/6/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/authority_basis","value":"The profile registry and fail-closed schema constraints are technical realization within an accepted trust policy."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/6/resolution_obligations/1/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/6/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/evidence_needed/0","value":"Assurance-profile contract."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/evidence_needed/1","value":"Revised public provenance schema."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/evidence_needed/2","value":"Negative conformance tests for missing or unresolved basis."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/obligation_id","value":"obligation.assurance-profile.public-contract"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/6/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.assurance-profile.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"保証 profile 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/1/responsibility","value":"Implement a versioned profile registry and bind every elevated public provenance trust class to required, locally or externally resolvable basis records."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/6/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/authority_basis","value":"The independence and adversarial validity of elevated trust handling cannot be established by its implementation author alone."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/6/resolution_obligations/2/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/6/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/evidence_needed/0","value":"Independent and adversarial assurance-profile review record."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/obligation_id","value":"obligation.assurance-profile.independent-challenge"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.assurance-profile.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"保証 profile 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.assurance-profile.public-contract"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"公開高信頼根拠契約の実装"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_obligations/2/responsibility","value":"Challenge profile selection, observer independence, trust-root resolution, and downgrade behavior independently of the implementation author."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/6/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/6/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/activation_condition","value":"Applies before any elevated assurance profile or public trust label is used."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/completion_rule","value":"The human accepts claim-strength, independence, trust-root, and downgrade policy; the registry and public basis contract fail closed; and independent challenge evidence covers profile selection, observer independence, trust-root resolution, and downgrade behavior."}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/path_id","value":"resolution-path.assurance-profile.accepted-implemented-challenged"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.assurance-profile.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/0/label_hint","value":"保証 profile 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.assurance-profile.public-contract"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/1/label_hint","value":"公開高信頼根拠契約の実装"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.assurance-profile.independent-challenge"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/2/label_hint","value":"保証 profile の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/6/resolution_summary","value":"Elevated assurance requires a human-accepted profile, a fail-closed public basis contract, and independent challenge of its selection and trust mechanics."}
{"node_type":"string","pointer":"/unresolved_items/6/subject","value":"A versioned assurance-profile registry must decide when independence is required, and public provenance records must bind elevated trust labels to inspectable observer, signature, trust-root, formal-model, verifier, and result evidence."}
{"node_type":"string","pointer":"/unresolved_items/6/uncertainty_kind","value":"pending_decision"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/7"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/7/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/7/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/0/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/0/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/7/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/1/entity_id","value":"conformance.migration.legacy-baseline"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/1/label_hint","value":"旧版基線"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/7/affected_entity_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/2/entity_id","value":"conformance.migration.legacy-characterization"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/2/label_hint","value":"旧版特性試験"}
{"node_type":"string","pointer":"/unresolved_items/7/affected_entity_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/7/claim_effect","value":"partially_blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/7/entity_id","value":"unresolved.evidence-expiry-and-requalification"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/7/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/7/evidence_gap/0","value":"Deployment profile."}
{"node_type":"string","pointer":"/unresolved_items/7/evidence_gap/1","value":"Subject-snapshot manifest policy."}
{"node_type":"string","pointer":"/unresolved_items/7/evidence_gap/2","value":"Evidence validity policy."}
{"node_type":"string","pointer":"/unresolved_items/7/evidence_gap/3","value":"Operational risk tolerance and rollback criteria."}
{"node_type":"string","pointer":"/unresolved_items/7/label","value":"証拠失効・再資格方針"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/7/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/7/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/0/authority_basis","value":"Validity periods, rerun thresholds, deployment profiles, and rollback tolerance are operational risk decisions."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/0/decision_question","value":"Which changes or elapsed periods invalidate each claim for the selected deployment profile?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/7/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/0/evidence_needed/0","value":"Human evidence-validity and operational-risk policy."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/0/obligation_id","value":"obligation.requalification.human-validity-policy"}
{"item_count":0,"node_type":"array","pointer":"/unresolved_items/7/resolution_obligations/0/precondition_obligation_refs"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/0/responsibility","value":"Choose deployment profiles, evidence validity periods, rerun thresholds, and rollback risk policy."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/7/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/authority_basis","value":"Invalidation mapping and rerun automation are technical realization after validity policy is fixed."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/7/resolution_obligations/1/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/7/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/evidence_needed/0","value":"Subject-snapshot manifest contract."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/evidence_needed/1","value":"Change-to-rerun mapping."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/evidence_needed/2","value":"Executable requalification runbook."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/obligation_id","value":"obligation.requalification.implement-runbook"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/7/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/7/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.requalification.human-validity-policy"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"証拠有効性方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_obligations/1/responsibility","value":"Map subject changes to evidence invalidation and provide reproducible requalification procedures."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/7/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/7/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/activation_condition","value":"Applies to every deployment profile that reuses evidence beyond a single historical observation."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/completion_rule","value":"The human accepts validity periods, rerun thresholds, and rollback policy, and a reproducible runbook maps subject changes to invalidation and demonstrates the required requalification procedure."}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/path_id","value":"resolution-path.requalification.policy-and-runbook"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.requalification.human-validity-policy"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/0/label_hint","value":"証拠有効期間の人間方針"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.requalification.implement-runbook"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/1/label_hint","value":"再資格手順の実装"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/7/resolution_summary","value":"An accepted freshness policy is insufficient alone; a reproducible change-to-invalidation mapping and requalification runbook must also exist."}
{"node_type":"string","pointer":"/unresolved_items/7/subject","value":"Which changes invalidate which evidence, how long evidence remains current, and which release or operational profiles require rerun or requalification."}
{"node_type":"string","pointer":"/unresolved_items/7/uncertainty_kind","value":"time_dependent"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/8"}
{"item_count":15,"node_type":"array","pointer":"/unresolved_items/8/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/0/entity_id","value":"view.origin-purpose-coverage"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/0/label_hint","value":"原点要求被覆ビュー"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/1/entity_id","value":"view.local-implementation-conformance"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/1/label_hint","value":"局所実装適合ビュー"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/2/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/2/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/3/entity_id","value":"verification.or03.human-decision-boundary"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/3/label_hint","value":"人間判断境界"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/4"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/4/entity_id","value":"conformance.INV-VN-003"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/4/label_hint","value":"terminal satisfaction 閉包"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/5"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/5/entity_id","value":"conformance.INV-VN-005"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/5/label_hint","value":"候補 authority ceiling"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/5/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/6"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/6/entity_id","value":"conformance.INV-VN-008"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/6/label_hint","value":"人間受理と監査事実の分離"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/6/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/7"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/7/entity_id","value":"conformance.INV-VN-009"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/7/label_hint","value":"score 非確率境界"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/7/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/8"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/8/entity_id","value":"conformance.INV-VN-010"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/8/label_hint","value":"schema・digest・由来 fail-closed"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/8/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/9"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/9/entity_id","value":"conformance.INV-VN-013"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/9/label_hint","value":"公開集約再計算"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/9/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/10"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/10/entity_id","value":"conformance.INV-VN-014"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/10/label_hint","value":"入力・監査観測同一性の分離"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/10/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/11"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/11/entity_id","value":"conformance.stage.input-boundary"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/11/label_hint","value":"入力契約と記録境界"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/11/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/12"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/12/entity_id","value":"conformance.stage.obligation-reaggregation"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/12/label_hint","value":"義務別再集約"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/12/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/13"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/13/entity_id","value":"conformance.stage.decision-request-materialization"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/13/label_hint","value":"判断要求生成"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/13/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/affected_entity_refs/14"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/14/entity_id","value":"conformance.completeness.public-result"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/14/label_hint","value":"公開結果完全性"}
{"node_type":"string","pointer":"/unresolved_items/8/affected_entity_refs/14/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/8/claim_effect","value":"partially_blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/8/entity_id","value":"unresolved.state-evidence-derivation-and-subject-binding"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/8/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/8/evidence_gap/0","value":"Per-item, per-axis assessment records that consume the existing typed effects and state the asserted value, derivation rule, assessor, and assessment time."}
{"node_type":"string","pointer":"/unresolved_items/8/evidence_gap/1","value":"Proposition-specific raw result locators where aggregate suite records currently provide only provisional support."}
{"node_type":"string","pointer":"/unresolved_items/8/evidence_gap/2","value":"Closed tested-subject manifest and raw command or log locator."}
{"node_type":"string","pointer":"/unresolved_items/8/evidence_gap/3","value":"Typed resolution-path selection and completion-assessment records that bind the selected branch to a human decision or located observation and reject impossible, multiply selected, or unsupported closure."}
{"node_type":"string","pointer":"/unresolved_items/8/label","value":"状態導出・対象 snapshot 拘束"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/8/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/8/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/authority_basis","value":"Assessment-record contracts, locators, and subject manifests are bounded audit infrastructure work."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/8/resolution_obligations/0/decision_question","value":null}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/8/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/evidence_needed/0","value":"Versioned assessment-record schema and per-axis records."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/evidence_needed/1","value":"Closed subject manifest."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/evidence_needed/2","value":"Proposition-specific raw result, command, or log locators."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/evidence_needed/3","value":"Typed path-selection and completion-assessment schema with reachability, exclusivity, exhaustiveness, and unsupported-closure tests."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/obligation_id","value":"obligation.state-derivation.implement-assessment-record"}
{"item_count":0,"node_type":"array","pointer":"/unresolved_items/8/resolution_obligations/0/precondition_obligation_refs"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/0/responsibility","value":"Add a versioned assessment-record contract that consumes typed evidence effects and records each asserted state-axis value, derivation rule, assessor and time, proposition-specific result locators, and closed subject manifests. Add a typed resolution-path selection and completion record whose activation basis is a human decision or located observation rather than free text alone."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/8/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/authority_basis","value":"Where a selected assurance profile requires independence, the implementation author cannot self-supply that property."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/8/resolution_obligations/1/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/8/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/evidence_needed/0","value":"Profile-specific independent observation record."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/obligation_id","value":"obligation.state-derivation.independent-observation"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.assurance-profile.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"保証 profile 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.assurance-profile.public-contract"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"公開高信頼根拠契約の実装"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/2/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/2/label_hint","value":"状態導出記録の実装"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_obligations/1/responsibility","value":"Provide independent observations when the selected claim profile requires independence."}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/8/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/8/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/0/activation_condition","value":"Selected only when the accepted claim profile explicitly does not require independent observation for the item state."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/0/completion_rule","value":"Every nontrivial state is reproducibly derived from typed, located supporting and countervailing observations bound to the assessed subject, with derivation rule, assessor, time, and the profile's non-independence decision recorded. The selected path is also bound to a typed activation decision or observation and a completion assessment; no free-text condition alone closes the unresolved item."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/0/path_id","value":"resolution-path.state-derivation.profile-without-independence"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/8/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/0/required_obligation_refs/0/label_hint","value":"状態導出記録の実装"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/8/resolution_paths/1"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/activation_condition","value":"Selected whenever the accepted claim profile requires independent observation for the item state."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/completion_rule","value":"The complete reproducible state derivation is supplemented by profile-conformant independent observations whose independence basis and subject binding are inspectable. The selected path is also bound to a typed activation decision or observation and a completion assessment; no free-text condition alone closes the unresolved item."}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/path_id","value":"resolution-path.state-derivation.profile-with-independence"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/0/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/0/label_hint","value":"状態導出記録の実装"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/1/entity_id","value":"obligation.state-derivation.independent-observation"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/1/label_hint","value":"状態の独立観測"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_paths/1/required_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/8/resolution_summary","value":"All nontrivial states require typed reproducible derivation and subject binding; the selected assurance profile determines whether independent observation is also mandatory. Path structure is currently validated, but typed activation, selection, and completion assessment remain part of this unresolved gap."}
{"node_type":"string","pointer":"/unresolved_items/8/subject","value":"Local opt-in subject-manifest, evidence-validity, state-assessment, expiry, and requalification contracts now derive separate state axes under closed declared subjects, but this canonical register has no adopted validity policy or bound current-source assessment. Resolution-path activation conditions also remain human-readable, with no typed selection or completion-assessment record, so the validator does not decide reachability, exclusivity, exhaustiveness, selection, or completion."}
{"node_type":"string","pointer":"/unresolved_items/8/uncertainty_kind","value":"evidence_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/9"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/9/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/9/affected_entity_refs/0/entity_id","value":"verification.or02.proof-obligation-and-assurance-graph-soundness"}
{"node_type":"string","pointer":"/unresolved_items/9/affected_entity_refs/0/label_hint","value":"proof obligation・assurance graph 健全性"}
{"node_type":"string","pointer":"/unresolved_items/9/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/9/affected_entity_refs/1/entity_id","value":"verification.or02.bounded-claim-model"}
{"node_type":"string","pointer":"/unresolved_items/9/affected_entity_refs/1/label_hint","value":"限定的立証の主張模型"}
{"node_type":"string","pointer":"/unresolved_items/9/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/9/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/9/entity_id","value":"unresolved.proof-obligation-and-assurance-graph-soundness"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/9/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/9/evidence_gap/0","value":"Replayable v0 cross-field closure and opt-in v1 proof-obligation graph implementation."}
{"node_type":"string","pointer":"/unresolved_items/9/evidence_gap/1","value":"Bound mutation, graph-cycle, duplicate-evidence, authority, and reaggregation observations."}
{"node_type":"string","pointer":"/unresolved_items/9/evidence_gap/2","value":"Independent adversarial review."}
{"node_type":"string","pointer":"/unresolved_items/9/evidence_gap/3","value":"Human assurance-profile and migration adoption decision."}
{"node_type":"string","pointer":"/unresolved_items/9/label","value":"proof obligation・assurance graph の閉包と独立再集約"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/9/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/authority_basis","value":"A versioned contract, independent reaggregation logic, graph closure, and negative mutation checks are bounded technical work under an accepted normative and assurance profile."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/9/resolution_obligations/0/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/9/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/evidence_needed/0","value":"Versioned v0 closure and v1 proof-obligation/graph contracts."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/evidence_needed/1","value":"Independent reaggregation implementation."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/evidence_needed/2","value":"Positive, mutation, cycle, duplicate-accounting, unclosed-reference, authority, and migration test observations bound to a closed subject manifest."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/obligation_id","value":"obligation.proof-graph.implement-replayable-contract"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.rule-pack.human-adoption"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"体系知 rule pack の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/1/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/1/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/2/entity_id","value":"obligation.assurance-profile.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/2/label_hint","value":"保証 profile 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/0/responsibility","value":"Strengthen v0 cross-field validation and implement opt-in v1 typed proof obligations and an acyclic derivation graph that bind subject, proposition, rules, evidence, obligation results, authority, aggregate state, unproved scope, and residual risk; reject substitutions, unresolved endpoints, cycles, duplicate evidence accounting, and unfulfilled required obligations while keeping v0 available."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/authority_basis","value":"Subject, authority, evidence, aggregation, and graph-bypass resistance cannot be established solely by the contract and validator authors."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/9/resolution_obligations/1/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/9/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/evidence_needed/0","value":"Independent adversarial proof-graph and public-contract review record."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/obligation_id","value":"obligation.proof-graph.independent-adversarial-review"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.assurance-profile.public-contract"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"公開高信頼根拠契約の実装"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.proof-graph.implement-replayable-contract"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"再生可能な proof graph 契約実装"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/1/responsibility","value":"Independently challenge subject and proposition substitution, rule and evidence replacement, aggregate-state inconsistency, duplicate corroboration, graph closure, authority inheritance, downgrade behavior, and v0/v1 migration boundaries."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/authority_basis","value":"Adopting claim strength, default output, support period, retirement, and residual graph risk changes the public assurance and migration policy."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/decision_question","value":"Which proof-obligation profile, claim strength, v1 default policy, v0 support period, retirement rule, and downgrade behavior are authorized?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/9/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/evidence_needed/0","value":"Human proof-graph assurance and migration decision record."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/obligation_id","value":"obligation.proof-graph.human-migration-adoption"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.proof-graph.implement-replayable-contract"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"再生可能な proof graph 契約実装"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.proof-graph.independent-adversarial-review"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"proof graph の独立敵対査読"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_obligations/2/responsibility","value":"Accept, revise, defer, or reject the proof-obligation profile and any v1 default, v0 support, retirement, and downgrade policy after reviewing implementation and independent challenge evidence."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/9/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/9/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/activation_condition","value":"Applies before a public claim is treated as replayably derived or before v1 becomes a default or v0 is retired."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/completion_rule","value":"A bound implementation independently reaggregates and rejects every declared substitution and closure failure, independent review finds no bounded subject, authority, evidence, or aggregation bypass, and a located human decision adopts only the reviewed claim and migration profile."}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/path_id","value":"resolution-path.proof-graph.implemented-reviewed-and-human-adopted"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.proof-graph.implement-replayable-contract"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/0/label_hint","value":"再生可能な proof graph 契約実装"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.proof-graph.independent-adversarial-review"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/1/label_hint","value":"proof graph の独立敵対査読"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.proof-graph.human-migration-adoption"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/2/label_hint","value":"保証・移行方針の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/9/resolution_summary","value":"Implementation and local closure are insufficient alone; replayable graph evidence, independent adversarial review, and a separate human assurance and migration decision are all required."}
{"node_type":"string","pointer":"/unresolved_items/9/subject","value":"A local opt-in v1 graph and adversarial replay checks exist, but no current subject-bound execution record, independent review, or human assurance and migration decision establishes that public assurance claims close typed proof obligations, subject, proposition, rules, evidence, authority, and aggregate state without substitution or duplicate accounting."}
{"node_type":"string","pointer":"/unresolved_items/9/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/10"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/10/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/10/affected_entity_refs/0/entity_id","value":"verification.cross.register-completeness"}
{"node_type":"string","pointer":"/unresolved_items/10/affected_entity_refs/0/label_hint","value":"検証 register の有界完全性"}
{"node_type":"string","pointer":"/unresolved_items/10/affected_entity_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/10/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/10/entity_id","value":"unresolved.verification-register-completeness"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/10/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/10/evidence_gap/0","value":"Versioned denominator and disposition vocabulary."}
{"node_type":"string","pointer":"/unresolved_items/10/evidence_gap/1","value":"Omission, dangling-locator, duplicate, contradiction, unsupported-resolution, unsupported-non-applicability, and handoff-preservation observations."}
{"node_type":"string","pointer":"/unresolved_items/10/evidence_gap/2","value":"Independent denominator review."}
{"node_type":"string","pointer":"/unresolved_items/10/evidence_gap/3","value":"Human bounded-completeness and non-applicability policy decision."}
{"node_type":"string","pointer":"/unresolved_items/10/label","value":"検証 register 分母・disposition の有界完全性"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/10/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/10/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/authority_basis","value":"Stable registration, source locators, typed dispositions, negative omission checks, and projection identity coverage are bounded audit-infrastructure work and do not choose risk acceptance."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/10/resolution_obligations/0/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/10/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/evidence_needed/0","value":"Versioned denominator and disposition contract."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/evidence_needed/1","value":"Bound negative omission, locator, duplication, contradiction, unsupported-resolution, non-applicability, and handoff tests."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/evidence_needed/2","value":"Projection identity coverage record."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/obligation_id","value":"obligation.register-completeness.implement-denominator-and-dispositions"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/10/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/0/responsibility","value":"Implement the charter denominator and exactly-one disposition contract for declared unproven scope, residual risks, remaining obligations, unresolved and independent-review findings, transition prohibitions, measured hazards, and field outcomes; reject dangling, duplicate, contradictory, unsupported resolved/non-applicable, or uncertainty-erasing handoff records."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/10/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/authority_basis","value":"A self-selected denominator can validate itself while omitting a known concern; independent omission and disposition review is a required evidence property."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/10/resolution_obligations/1/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/10/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/evidence_needed/0","value":"Independent register-denominator and omission review record."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/obligation_id","value":"obligation.register-completeness.independent-denominator-review"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/10/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.register-completeness.implement-denominator-and-dispositions"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"register 分母・disposition 実装"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/1/responsibility","value":"Independently review the denominator, source locators, disposition meanings, non-applicability boundary, handoff preservation, and negative omission cases against the origin requirements and declared gap sources."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/10/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/authority_basis","value":"Adopting the bounded denominator and conditions for non-applicability determines what may enter completeness and completion claims."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/decision_question","value":"Which declared gap sources and disposition rules define the authorized bounded register denominator, and under what located conditions may non-applicability be used?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/10/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/evidence_needed/0","value":"Human register-denominator and non-applicability decision record."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/obligation_id","value":"obligation.register-completeness.human-denominator-adoption"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.register-completeness.implement-denominator-and-dispositions"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"register 分母・disposition 実装"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.register-completeness.independent-denominator-review"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"register 分母の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_obligations/2/responsibility","value":"Accept, revise, defer, or reject the exact denominator, disposition vocabulary, non-applicability policy, reactivation conditions, and bounded completeness meaning after independent review."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/10/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/10/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/activation_condition","value":"Applies before bounded register completeness is used in progress, completion, transition, or acceptance material."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/completion_rule","value":"The accepted denominator gives every declared gap-bearing source exactly one located, non-contradictory disposition; negative omission and unsupported-closure cases fail; handoff preserves uncertainty; independent review and the human decision bound the completeness meaning without claiming unknown-unknown discovery."}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/path_id","value":"resolution-path.register-completeness.implemented-reviewed-and-human-adopted"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.register-completeness.implement-denominator-and-dispositions"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/0/label_hint","value":"register 分母・disposition 実装"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.register-completeness.independent-denominator-review"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/1/label_hint","value":"register 分母の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.register-completeness.human-denominator-adoption"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/2/label_hint","value":"register 分母の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/10/resolution_summary","value":"A self-validating register is not complete; the denominator and dispositions require bounded implementation, independent omission review, and explicit human adoption."}
{"node_type":"string","pointer":"/unresolved_items/10/subject","value":"The local canonical denominator, gap register, omission checks, contradiction checks, typed dispositions, and exact generated projection are implemented, but the denominator is not human-adopted, resolved or non-applicable dispositions have no accepted current evidence, and independent omission review has not been performed."}
{"node_type":"string","pointer":"/unresolved_items/10/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/11"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/11/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/11/affected_entity_refs/0/entity_id","value":"verification.cross.lifecycle-trace-and-composition"}
{"node_type":"string","pointer":"/unresolved_items/11/affected_entity_refs/0/label_hint","value":"工程横断 trace・意味合成"}
{"node_type":"string","pointer":"/unresolved_items/11/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/11/affected_entity_refs/1/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"node_type":"string","pointer":"/unresolved_items/11/affected_entity_refs/1/label_hint","value":"OR-01 工程横断被覆"}
{"node_type":"string","pointer":"/unresolved_items/11/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/11/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/11/entity_id","value":"unresolved.lifecycle-trace-and-composition"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/11/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/11/evidence_gap/0","value":"Human-accepted cross-stage meaning and authority boundary."}
{"node_type":"string","pointer":"/unresolved_items/11/evidence_gap/1","value":"Typed identity and composition contract across all lifecycle profiles."}
{"node_type":"string","pointer":"/unresolved_items/11/evidence_gap/2","value":"Split, merge, revision, cancellation, supersession, repair, and orphan-detection observations."}
{"node_type":"string","pointer":"/unresolved_items/11/evidence_gap/3","value":"Independent cross-stage omission and semantic-substitution review."}
{"node_type":"string","pointer":"/unresolved_items/11/label","value":"工程横断 trace・意味合成機構"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/11/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/authority_basis","value":"Which identities, propositions, obligations, authorities, evidence, and transformations retain or change meaning across stages is part of the authorized product purpose and risk boundary."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/decision_question","value":"Which meanings and obligations must remain identical, which transformations are permitted, and which authority or evidence changes require human escalation across each lifecycle boundary?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/11/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/evidence_needed/0","value":"Human lifecycle-composition semantics and authority-boundary decision record."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/obligation_id","value":"obligation.lifecycle-composition.human-semantics"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.rule-pack.human-adoption"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"体系知 rule pack の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/1/entity_id","value":"obligation.lifecycle-surfaces.human-profile-acceptance"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/1/label_hint","value":"各工程 profile の人間受理"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/0/responsibility","value":"Accept or revise the cross-stage identity, transformation, obligation-carrying, authority, evidence, unresolved-remainder, split/merge, supersession, cancellation, and repair semantics for the current lifecycle denominator."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/authority_basis","value":"Typed identities, trace records, composition rules, and fail-closed checks are technical realization after lifecycle meanings are accepted."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/11/resolution_obligations/1/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/11/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/evidence_needed/0","value":"Versioned lifecycle trace and composition contract."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/evidence_needed/1","value":"Cross-stage vertical, mutation, split/merge, supersession, cancellation, repair, and orphan-detection observations bound to closed subjects."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/obligation_id","value":"obligation.lifecycle-composition.implement-trace-and-rules"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.lifecycle-composition.human-semantics"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"工程横断意味の人間受理"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.lifecycle-surfaces.implement-vertical-slices"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"OR-01 工程面の縦断実装"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/2/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/2/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/1/responsibility","value":"Implement versioned cross-stage identities, source and target propositions, carried and discharged obligations, evidence and authority transformations, unresolved remainder, and rules for split, merge, revision, cancellation, supersession, repair, and completion; reject orphaning, substitution, duplication, stale binding, and unsupported strengthening."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/authority_basis","value":"Cross-stage omissions and semantic substitutions require review outside the authors of individual stages and composition rules."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/11/resolution_obligations/2/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/11/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/evidence_needed/0","value":"Independent cross-stage trace, composition, omission, and overclaim review."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/obligation_id","value":"obligation.lifecycle-composition.independent-cross-stage-review"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/11/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.lifecycle-composition.implement-trace-and-rules"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"工程横断 trace・合成実装"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_obligations/2/responsibility","value":"Independently review origin trace, identity and proposition preservation, allowed transformations, authority changes, evidence freshness, unresolved obligation carriage, branching, merging, cancellation, supersession, and completion over representative full-lifecycle cases."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/11/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/11/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/activation_condition","value":"Applies to every claim that composes meaning or evidence across two or more OR-01 lifecycle surfaces."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/completion_rule","value":"Every transition in the accepted denominator preserves or explicitly transforms identity, proposition, obligation, authority, evidence, and unresolved scope under accepted rules; adversarial composition failures are rejected and independent full-lifecycle review finds no bounded omission or unsupported strengthening."}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/path_id","value":"resolution-path.lifecycle-composition.accepted-implemented-and-reviewed"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.lifecycle-composition.human-semantics"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/0/label_hint","value":"工程横断意味の人間受理"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.lifecycle-composition.implement-trace-and-rules"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/1/label_hint","value":"工程横断 trace・合成実装"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.lifecycle-composition.independent-cross-stage-review"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/2/label_hint","value":"工程横断の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/11/resolution_summary","value":"Per-surface completion does not close lifecycle purpose; accepted cross-stage semantics, typed composition, bound adversarial evidence, and independent full-lifecycle review are required."}
{"node_type":"string","pointer":"/unresolved_items/11/subject","value":"A local typed lifecycle trace and cross-stage composition validator preserves identity, proposition, obligation, authority, evidence, and unresolved scope, but the ten stage semantics are not human-adopted or integrated into vertical public paths and no bound independent full-lifecycle evidence closes the transformations."}
{"node_type":"string","pointer":"/unresolved_items/11/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/12"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/12/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/12/affected_entity_refs/0/entity_id","value":"verification.cross.operational-qualification"}
{"node_type":"string","pointer":"/unresolved_items/12/affected_entity_refs/0/label_hint","value":"運用 profile 資格確認"}
{"node_type":"string","pointer":"/unresolved_items/12/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/12/affected_entity_refs/1/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/unresolved_items/12/affected_entity_refs/1/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/unresolved_items/12/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/12/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/12/entity_id","value":"unresolved.operational-qualification"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/12/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/12/evidence_gap/0","value":"Human deployment envelope, failure thresholds, and operational risk policy."}
{"node_type":"string","pointer":"/unresolved_items/12/evidence_gap/1","value":"Closed subject, environment, provider, dependency, and configuration manifest."}
{"node_type":"string","pointer":"/unresolved_items/12/evidence_gap/2","value":"Bound long-duration, concurrency, load, exhaustion, failure, recovery, compatibility, platform, and incident observations."}
{"node_type":"string","pointer":"/unresolved_items/12/evidence_gap/3","value":"Independent operational qualification review."}
{"node_type":"string","pointer":"/unresolved_items/12/label","value":"運用 profile 資格確認の設計・実行・独立査読"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/12/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/authority_basis","value":"Deployment profiles, service expectations, failure thresholds, incident tolerance, and rollback triggers are operational value and risk choices."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/decision_question","value":"For which deployment, workload, duration, provider, platform, failure, recovery, incident, and rollback envelope may operational readiness be assessed?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/12/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/evidence_needed/0","value":"Human deployment-envelope and operational-risk decision record."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/obligation_id","value":"obligation.operational-qualification.human-envelope"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"安全運用の適用性判断"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/1/entity_id","value":"obligation.field-policy.human-risk-choice"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/1/label_hint","value":"実務用途と危険費用の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/0/responsibility","value":"Choose the deployment profile, workload and duration envelope, providers and platforms, acceptable failure and recovery thresholds, observability, incident, rollback, and residual-risk policy, and bind it to the selected secure-operation applicability branch."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/authority_basis","value":"Qualification harnesses and execution are technical work after the deployment, secure-use, and failure envelope is authorized."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/12/resolution_obligations/1/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/12/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/evidence_needed/0","value":"Versioned qualification protocol and closed manifests."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/evidence_needed/1","value":"Bound raw workload, failure, recovery, resource, platform, and incident execution records."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/evidence_needed/2","value":"Threshold and out-of-envelope report."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/obligation_id","value":"obligation.operational-qualification.execute-bound-profile"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.operational-qualification.human-envelope"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"運用 envelope の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/2/entity_id","value":"obligation.requalification.implement-runbook"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/2/label_hint","value":"証拠失効・再資格手順"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/1/responsibility","value":"Build and execute a versioned qualification protocol against a closed subject and environment manifest, covering the selected duration, concurrency, load, exhaustion, provider failure, restart, recovery, compatibility, platform, observability, incident, and rollback-trigger scenarios without generalizing outside the accepted envelope."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/authority_basis","value":"Operational envelope coverage, failure injection, recovery interpretation, and readiness limits cannot be established solely by the qualification authors."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/12/resolution_obligations/2/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/12/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/evidence_needed/0","value":"Independent operational qualification and boundary review record."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/obligation_id","value":"obligation.operational-qualification.independent-review"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/12/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.operational-qualification.execute-bound-profile"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"運用 profile 資格試験"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_obligations/2/responsibility","value":"Independently review and, where required, observe the qualification subject, environment, workload, failure injection, resource limits, recovery, compatibility, platforms, incidents, thresholds, exclusions, and readiness projection."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/12/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/12/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/activation_condition","value":"Applies before operational-readiness or default-route claims for the human-selected deployment profile."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/completion_rule","value":"The selected secure-use and deployment envelope has closed manifests and bound duration, concurrency, load, exhaustion, provider-failure, recovery, compatibility, platform, observability, incident, and threshold evidence, and independent review supports only the tested operational scope."}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/path_id","value":"resolution-path.operational-qualification.selected-profile"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.operational-qualification.human-envelope"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/0/label_hint","value":"運用 envelope の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.operational-qualification.execute-bound-profile"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/1/label_hint","value":"運用 profile 資格試験"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.operational-qualification.independent-review"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/2/label_hint","value":"運用資格の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/12/resolution_summary","value":"Operational qualification requires a human-selected deployment envelope, a subject-bound execution across its declared failure and recovery conditions, and independent boundary review; local tests do not substitute."}
{"node_type":"string","pointer":"/unresolved_items/12/subject","value":"No human-selected deployment envelope, bound qualification run, or independent observation establishes duration, concurrency, load, exhaustion, provider failure, recovery, compatibility, platform, observability, and incident behavior."}
{"node_type":"string","pointer":"/unresolved_items/12/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/13"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/13/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/13/affected_entity_refs/0/entity_id","value":"verification.cross.transition-and-cutover"}
{"node_type":"string","pointer":"/unresolved_items/13/affected_entity_refs/0/label_hint","value":"移行・cutover 統治"}
{"node_type":"string","pointer":"/unresolved_items/13/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/13/affected_entity_refs/1/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/unresolved_items/13/affected_entity_refs/1/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/unresolved_items/13/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/13/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/13/entity_id","value":"unresolved.transition-cutover-rollback-and-retirement"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/13/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/13/evidence_gap/0","value":"Versioned transition, compatibility, evidence-migration, rollback, disposal, and retirement plan."}
{"node_type":"string","pointer":"/unresolved_items/13/evidence_gap/1","value":"Bound shadow, migration, rollback, and recovery rehearsal."}
{"node_type":"string","pointer":"/unresolved_items/13/evidence_gap/2","value":"Independent transition observation."}
{"node_type":"string","pointer":"/unresolved_items/13/evidence_gap/3","value":"Located field, operational, human-use, register-completeness, and human cutover decision evidence."}
{"node_type":"string","pointer":"/unresolved_items/13/label","value":"移行・cutover・rollback・retirement 証拠"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/13/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/authority_basis","value":"A versioned transition plan, compatibility mapping, prohibitions, evidence migration, rollback protocol, and retirement checks are bounded audit and release material, not cutover authorization."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/13/resolution_obligations/0/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/13/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/evidence_needed/0","value":"Versioned transition, compatibility, migration, rollback, disposal, and retirement plan."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/evidence_needed/1","value":"Machine-checkable entry, abort, and no-cutover prohibitions."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/obligation_id","value":"obligation.transition.define-plan-and-prohibitions"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.lifecycle-composition.implement-trace-and-rules"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"工程横断 trace・合成実装"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/1/entity_id","value":"obligation.proof-graph.implement-replayable-contract"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/1/label_hint","value":"proof graph 契約実装"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/0/responsibility","value":"Define opt-in introduction, compatibility and shadow period, entry and abort criteria, public and stored-record migration, unresolved-state preservation, rollback, disposal, and predecessor-retirement prohibitions without changing the default route."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/authority_basis","value":"Migration, compatibility, rollback, recovery, and retained-unresolved behavior require evidence independent of the transition-plan author."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/13/resolution_obligations/1/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/13/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/evidence_needed/0","value":"Independent bound transition, migration, rollback, and recovery rehearsal record."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/obligation_id","value":"obligation.transition.independent-rehearsal"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.transition.define-plan-and-prohibitions"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"移行・rollback 計画"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.operational-qualification.independent-review"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"運用資格の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/1/responsibility","value":"Independently observe representative shadow comparison, public and stored-record migration, compatibility, abort, rollback, recovery, unresolved-state preservation, and predecessor restoration under the versioned plan."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/authority_basis","value":"Default switching, risk acceptance, support period, rollback authority, and predecessor retirement are human-owned adoption decisions."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/decision_question","value":"Given the registered field, operational, human-use, migration, rollback, and residual-risk evidence, may the selected route become default, under what abort conditions, and when if ever may the predecessor be retired?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/13/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/evidence_needed/0","value":"Human cutover, rollback, support-period, disposal, and retirement decision record with subject and evidence references."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/obligation_id","value":"obligation.transition.human-cutover-decision"}
{"item_count":5,"node_type":"array","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.transition.define-plan-and-prohibitions"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"移行・rollback 計画"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.transition.independent-rehearsal"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"移行・rollback の独立 rehearsal"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/2/entity_id","value":"obligation.field-policy.execute-evaluation"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/2/label_hint","value":"実務評価の実行観測"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/3/entity_id","value":"obligation.human-use.independent-task-evaluation"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/3/label_hint","value":"人間・agent 利用の独立評価"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/4"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/4/entity_id","value":"obligation.register-completeness.human-denominator-adoption"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/4/label_hint","value":"register 分母の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/precondition_obligation_refs/4/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_obligations/2/responsibility","value":"Accept, revise, defer, or reject only the selected cutover, compatibility period, rollback authority, disposal, and retirement scope after reviewing the complete registered field, operational, human-use, migration, and residual-risk material; this decision does not itself execute cutover."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/13/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/13/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/activation_condition","value":"Applies before any default switch, predecessor retirement, irreversible evidence migration, or disposal action."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/completion_rule","value":"The versioned plan preserves compatibility and unresolved state, bound independent rehearsal demonstrates migration, abort, rollback, recovery, and predecessor restoration, all prerequisite validity material is registered, and a located human decision authorizes only the selected transition scope; semantic-guard still does not execute cutover."}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/path_id","value":"resolution-path.transition.evidence-complete-human-decision"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.transition.define-plan-and-prohibitions"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/0/label_hint","value":"移行・rollback 計画"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.transition.independent-rehearsal"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/1/label_hint","value":"移行・rollback の独立 rehearsal"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.transition.human-cutover-decision"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/2/label_hint","value":"cutover の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/13/resolution_summary","value":"Transition closure is decision material, not execution authority: a versioned plan, independent rehearsal, complete prerequisite evidence, and a located human cutover decision are mandatory."}
{"node_type":"string","pointer":"/unresolved_items/13/subject","value":"A local transition-plan contract and gate validator exist, but no human-adopted transition policy, bound shadow/migration/rollback rehearsal, independent observation, or located human cutover and retirement decisions close default switching, compatibility, disposal, and predecessor retirement."}
{"node_type":"string","pointer":"/unresolved_items/13/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/14"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/14/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/0/entity_id","value":"verification.cross.human-operational-use"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/0/label_hint","value":"人間・coding agent の責任適合利用"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/1/entity_id","value":"verification.or03.repair-effect"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/1/label_hint","value":"修正循環の有効性"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/affected_entity_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/2/entity_id","value":"verification.cross.field-validation"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/2/label_hint","value":"実務資料上の妥当性確認"}
{"node_type":"string","pointer":"/unresolved_items/14/affected_entity_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/14/claim_effect","value":"blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/14/entity_id","value":"unresolved.human-operational-use"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/14/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/14/evidence_gap/0","value":"Human responsibility, decision-rights, and escalation policy."}
{"node_type":"string","pointer":"/unresolved_items/14/evidence_gap/1","value":"Role-aware machine and human material and routing contract."}
{"node_type":"string","pointer":"/unresolved_items/14/evidence_gap/2","value":"Representative task-based agent and human observations."}
{"node_type":"string","pointer":"/unresolved_items/14/evidence_gap/3","value":"Independent routing, comprehension, repair, escalation, and authority-error review."}
{"node_type":"string","pointer":"/unresolved_items/14/label","value":"coding agent・人間の責任適合利用と理解可能性"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/14/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/authority_basis","value":"Which roles may decide, act, escalate, accept risk, or finally accept work is an organizational and human authority decision."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/authority_class","value":"human_required"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/decision_question","value":"Which audit questions may each coding-agent or human role resolve, which must be escalated, what context must accompany them, and which routing or authority errors are intolerable?"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/14/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/evidence_needed/0","value":"Human responsibility, decision-rights, escalation, and authority-error policy record."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/obligation_id","value":"obligation.human-use.human-responsibility-policy"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/14/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.field-policy.human-risk-choice"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"実務用途と危険費用の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/0/responsibility","value":"Choose coding-agent and human role meanings, decision rights, escalation conditions, required context, unacceptable authority errors, and the evidence threshold before audit material may influence repair or acceptance."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/authority_basis","value":"Role-aware schemas, projections, routing metadata, repair targets, and escalation records are technical realization after responsibility and decision rights are fixed."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/14/resolution_obligations/1/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/14/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/evidence_needed/0","value":"Versioned responsibility-aware material and routing contract."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/evidence_needed/1","value":"Negative tests for missing context, wrong recipient, authority escalation, technical-pass acceptance, and unresolved-scope loss."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/obligation_id","value":"obligation.human-use.implement-responsibility-aware-material"}
{"item_count":5,"node_type":"array","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.human-use.human-responsibility-policy"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"責任・escalation 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/2/entity_id","value":"obligation.proof-graph.implement-replayable-contract"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/2/label_hint","value":"proof graph 契約実装"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/3/entity_id","value":"obligation.lifecycle-composition.implement-trace-and-rules"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/3/label_hint","value":"工程横断 trace・合成実装"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/4"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/4/entity_id","value":"obligation.repair-loop.implement-and-reaudit"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/4/label_hint","value":"修正循環・再監査の実装"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/precondition_obligation_refs/4/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/1/responsibility","value":"Implement versioned coding-agent and human projections that preserve subject, proposition, finding, evidence, limitations, unresolved scope, authority class, repair target, decision question, escalation reason, and responsibility boundary without moving control or final acceptance into semantic-guard."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/authority_basis","value":"Comprehension, routing, actionability, repair correctness, escalation, and authority errors cannot be validated only by the output authors or implementing agent."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/14/resolution_obligations/2/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/14/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/evidence_needed/0","value":"Independent task protocol, observations, disagreements, and adjudication for coding-agent and human roles."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/evidence_needed/1","value":"Stratified routing, comprehension, repair, escalation, residual-uncertainty, and authority-error results."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/obligation_id","value":"obligation.human-use.independent-task-evaluation"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.human-use.implement-responsibility-aware-material"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"責任適合 material 実装"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.field-policy.evaluation-protocol"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"実務評価手順"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/2/entity_id","value":"obligation.field-policy.independent-labels"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/2/label_hint","value":"独立標識と裁定証拠"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_obligations/2/responsibility","value":"Independently evaluate representative coding-agent and human tasks, separately measuring correct routing, comprehension, uncertainty retention, repair outcome, escalation, time and effort, authority error, and final-decision separation, while preserving disagreement and failure cases."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/14/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/14/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/activation_condition","value":"Applies before audit material is claimed usable for coding-agent repair, human escalation, or accept/request_revision/defer decisions."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/completion_rule","value":"The human-owned role and escalation policy is explicit, role-aware material preserves evidence and authority boundaries, and independent task evidence supports routing, comprehension, repair, escalation, and final-decision separation for the declared population without hiding failure cases."}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/path_id","value":"resolution-path.human-use.policy-material-and-independent-evaluation"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.human-use.human-responsibility-policy"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/0/label_hint","value":"責任・escalation 方針の人間判断"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.human-use.implement-responsibility-aware-material"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/1/label_hint","value":"責任適合 material 実装"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.human-use.independent-task-evaluation"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/2/label_hint","value":"人間・agent 利用の独立評価"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/14/resolution_summary","value":"Correct technical content is not operationally usable by itself; human-owned responsibility policy, role-aware material, and independent task-based evidence must close together."}
{"node_type":"string","pointer":"/unresolved_items/14/subject","value":"A local role-aware responsibility-material and repair-target contract exists, but no human-adopted responsibility policy or independent task-based evidence establishes correct routing, comprehension, repair, escalation, authority preservation, and decision support for coding agents and humans."}
{"node_type":"string","pointer":"/unresolved_items/14/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/15"}
{"item_count":16,"node_type":"array","pointer":"/unresolved_items/15/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/0/entity_id","value":"verification.or01.discovery-effectiveness"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/0/label_hint","value":"未解決・欠陥の発見性能"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/1/entity_id","value":"verification.cross.field-validation"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/1/label_hint","value":"実務資料上の妥当性確認"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/2/entity_id","value":"conformance.INV-VN-001"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/2/label_hint","value":"未知・被覆不足の保持"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/3/entity_id","value":"conformance.INV-VN-002"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/3/label_hint","value":"直接 satisfied の残余危険門"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/4"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/4/entity_id","value":"conformance.INV-VN-004"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/4/label_hint","value":"必須解析器障害の fail-closed"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/5"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/5/entity_id","value":"conformance.INV-VN-006"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/5/label_hint","value":"否定・引用・条件の疑義化"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/5/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/6"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/6/entity_id","value":"conformance.INV-VN-007"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/6/label_hint","value":"開いた自由文の非断定"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/6/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/7"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/7/entity_id","value":"conformance.INV-VN-011"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/7/label_hint","value":"分野語共有の非証明"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/7/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/8"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/8/entity_id","value":"conformance.INV-VN-012"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/8/label_hint","value":"解析器能力・span 会計"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/8/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/9"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/9/entity_id","value":"conformance.stage.provisional-direct-audit"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/9/label_hint","value":"義務別仮判定"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/9/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/10"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/10/entity_id","value":"conformance.stage.residual-risk-gate"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/10/label_hint","value":"残余危険門"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/10/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/11"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/11/entity_id","value":"conformance.stage.morphology"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/11/label_hint","value":"形態素解析"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/11/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/12"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/12/entity_id","value":"conformance.stage.dependency-analysis-bundle"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/12/label_hint","value":"依存構造解析束"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/12/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/13"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/13/entity_id","value":"conformance.stage.versioned-lifting-rule"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/13/label_hint","value":"版付き導出"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/13/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/14"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/14/entity_id","value":"conformance.stage.llm-candidate"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/14/label_hint","value":"LLM 候補"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/14/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/affected_entity_refs/15"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/15/entity_id","value":"conformance.completeness.provider-accounting"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/15/label_hint","value":"解析器実行会計"}
{"node_type":"string","pointer":"/unresolved_items/15/affected_entity_refs/15/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/claim_effect","value":"partially_blocks_claim"}
{"node_type":"string","pointer":"/unresolved_items/15/entity_id","value":"unresolved.analyzer-route-effectiveness-and-incremental-value"}
{"item_count":5,"node_type":"array","pointer":"/unresolved_items/15/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/15/evidence_gap/0","value":"No-analyzer versus morphology ablation on the same accepted corpus."}
{"node_type":"string","pointer":"/unresolved_items/15/evidence_gap/1","value":"Dependency and coreference accuracy by relation and linguistic phenomenon, including long and cross-sentence cases."}
{"node_type":"string","pointer":"/unresolved_items/15/evidence_gap/2","value":"Versioned lifting-rule coverage expansion and error effects beyond conditional attachment v0."}
{"node_type":"string","pointer":"/unresolved_items/15/evidence_gap/3","value":"LLM incremental discovery, false-satisfaction, abstention, reproducibility, model-version, latency, and cost effects over the best deterministic route."}
{"node_type":"string","pointer":"/unresolved_items/15/evidence_gap/4","value":"Independent route-level review under the governed field protocol."}
{"node_type":"string","pointer":"/unresolved_items/15/label","value":"解析 route 別の発見性能・増分価値"}
{"item_count":6,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/authority_basis","value":"A controlled route-ablation and incremental-value protocol is bounded measurement design after the field, engineering, subject-binding, and secure-use prerequisites are fixed."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/15/resolution_obligations/0/decision_question","value":null}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/evidence_needed/0","value":"Versioned route-ablation and incremental-value protocol."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/evidence_needed/1","value":"Closed corpus, subject, analyzer resource, rule, and model manifest."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/evidence_needed/2","value":"Predeclared catastrophic false-satisfaction, false-defect, abstention, silent-gap, challenge-capture, span-fidelity, reproducibility, latency, and cost measures."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/obligation_id","value":"obligation.analyzer-effectiveness.define-route-protocol"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/0/entity_id","value":"obligation.field-policy.evaluation-protocol"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/0/label_hint","value":"実務評価手順"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/1/entity_id","value":"obligation.state-derivation.implement-assessment-record"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/1/label_hint","value":"状態導出・対象拘束記録"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/0/responsibility","value":"Define one versioned subject-bound protocol, corpus split, route configuration, capability accounting, error taxonomy, and metrics for direct-only, morphology, dependency/coreference, lifting, and LLM candidate routes without granting any provider assertion authority."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/authority_basis","value":"Running the predeclared direct-only versus morphology comparison is technical execution after the common corpus and independent labels exist."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/15/resolution_obligations/1/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/1/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/evidence_needed/0","value":"Bound paired direct-only/morphology predictions and stratified ablation results."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/obligation_id","value":"obligation.analyzer-effectiveness.measure-morphology-ablation"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/0/entity_id","value":"obligation.analyzer-effectiveness.define-route-protocol"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/0/label_hint","value":"解析 route 評価手順"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/1/entity_id","value":"obligation.field-policy.independent-labels"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/1/label_hint","value":"独立標識と裁定証拠"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/1/responsibility","value":"Execute direct-only and morphology-enabled routes on identical bound cases and report incremental discovery, false satisfaction, false defect, abstention, challenge capture, source-span fidelity, failure, and resource effects without interpreting local passage as general accuracy."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/2"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/authority_basis","value":"Executing the accepted dependency/coreference evaluation and stratified error accounting is bounded technical work."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/15/resolution_obligations/2/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/2/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/evidence_needed/0","value":"Bound dependency/coreference predictions, capability observations, and phenomenon-stratified error results."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/obligation_id","value":"obligation.analyzer-effectiveness.measure-dependency-coreference"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/0/entity_id","value":"obligation.analyzer-effectiveness.define-route-protocol"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/0/label_hint","value":"解析 route 評価手順"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/1/entity_id","value":"obligation.field-policy.independent-labels"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/1/label_hint","value":"独立標識と裁定証拠"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/2/responsibility","value":"Measure dependency and coreference candidate accuracy, missing capability, attachment, role reversal, long-sentence, cross-sentence, coordination, negation, quotation, and ambiguity effects against independent labels, preserving provider failures and abstentions."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/3"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/authority_basis","value":"Versioning and evaluating additional deterministic lifting families under the accepted engineering basis is bounded technical work."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/15/resolution_obligations/3/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/3/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/evidence_needed/0","value":"Versioned lifting-family mappings and rule digests."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/evidence_needed/1","value":"Bound per-family and cumulative lifting ablation results on the isolated holdout."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/obligation_id","value":"obligation.analyzer-effectiveness.measure-lifting-expansion"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/0/entity_id","value":"obligation.analyzer-effectiveness.define-route-protocol"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/0/label_hint","value":"解析 route 評価手順"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/1/entity_id","value":"obligation.field-policy.independent-labels"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/1/label_hint","value":"独立標識と裁定証拠"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/2/entity_id","value":"obligation.rule-pack.human-adoption"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/2/label_hint","value":"体系知 rule pack の人間採用"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/3/responsibility","value":"Add candidate lifting families only through versioned governed mappings, then measure each family's coverage gain, false satisfaction, false defect, conflict, abstention, source-span fidelity, and rule interaction against the unchanged holdout without tuning on it."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/4"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/authority_basis","value":"Running a fixed LLM candidate route against the best deterministic baseline and calculating predeclared increments is bounded technical work after model and secure-use boundaries are fixed."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/15/resolution_obligations/4/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/4/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/evidence_needed/0","value":"Bound prompts, model/provider identity, configuration, raw candidates, unavailable/skipped observations, and deterministic-baseline comparison."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/evidence_needed/1","value":"Stratified incremental-value, reproducibility, latency, and cost results."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/obligation_id","value":"obligation.analyzer-effectiveness.measure-llm-incremental-value"}
{"item_count":3,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/0/entity_id","value":"obligation.analyzer-effectiveness.define-route-protocol"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/0/label_hint","value":"解析 route 評価手順"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/1/entity_id","value":"obligation.field-policy.independent-labels"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/1/label_hint","value":"独立標識と裁定証拠"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/2/entity_id","value":"obligation.secure-operation.human-policy"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/2/label_hint","value":"安全運用の適用性判断"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/4/responsibility","value":"Measure the LLM candidate route's incremental discovery, false satisfaction, false defect, abstention, challenge capture, reproducibility, model-version sensitivity, latency, and cost over the best deterministic route on identical bound cases, recording unavailable and skipped states and retaining the candidate-only authority ceiling."}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/5"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/authority_basis","value":"Route labels, error interpretation, holdout isolation, and incremental-value claims cannot be established solely by analyzer and rule authors."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/authority_class","value":"external_evidence_required"}
{"node_type":"null","pointer":"/unresolved_items/15/resolution_obligations/5/decision_question","value":null}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/5/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/evidence_needed/0","value":"Independent analyzer-route, ablation, holdout, and incremental-value review record."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/obligation_id","value":"obligation.analyzer-effectiveness.independent-route-review"}
{"item_count":4,"node_type":"array","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/0/entity_id","value":"obligation.analyzer-effectiveness.measure-morphology-ablation"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/0/label_hint","value":"形態素解析 ablation"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/1/entity_id","value":"obligation.analyzer-effectiveness.measure-dependency-coreference"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/1/label_hint","value":"係り受け・照応精度評価"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/2/entity_id","value":"obligation.analyzer-effectiveness.measure-lifting-expansion"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/2/label_hint","value":"lifting 拡張評価"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/3/entity_id","value":"obligation.analyzer-effectiveness.measure-llm-incremental-value"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/3/label_hint","value":"LLM 増分価値評価"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/precondition_obligation_refs/3/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_obligations/5/responsibility","value":"Independently review corpus isolation, labels and adjudication, resource and model binding, capability accounting, each route's raw predictions, catastrophic errors, abstentions, interactions, uncertainty, and the bounded morphology, dependency/coreference, lifting, and LLM value claims."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/15/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/15/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/activation_condition","value":"Applies before any morphology, dependency/coreference, lifting, or LLM route is credited with discovery effectiveness or practical incremental value."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/completion_rule","value":"All four route gaps are measured on the same governed, subject-bound, independently labeled holdout under fixed manifests and authority ceilings, catastrophic and abstention effects remain separate, and independent review supports only the stratified incremental claims actually observed."}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/path_id","value":"resolution-path.analyzer-effectiveness.common-holdout-and-independent-review"}
{"item_count":6,"node_type":"array","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.analyzer-effectiveness.define-route-protocol"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/0/label_hint","value":"解析 route 評価手順"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/1/entity_id","value":"obligation.analyzer-effectiveness.measure-morphology-ablation"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/1/label_hint","value":"形態素解析 ablation"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/2"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/2/entity_id","value":"obligation.analyzer-effectiveness.measure-dependency-coreference"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/2/label_hint","value":"係り受け・照応精度評価"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/3"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/3/entity_id","value":"obligation.analyzer-effectiveness.measure-lifting-expansion"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/3/label_hint","value":"lifting 拡張評価"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/4"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/4/entity_id","value":"obligation.analyzer-effectiveness.measure-llm-incremental-value"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/4/label_hint","value":"LLM 増分価値評価"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/5"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/5/entity_id","value":"obligation.analyzer-effectiveness.independent-route-review"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/5/label_hint","value":"解析 route の独立査読"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_paths/0/required_obligation_refs/5/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/15/resolution_summary","value":"Morphology, dependency/coreference, lifting, and LLM value remain one registered family so their incremental effects are compared on the same governed holdout; each has a distinct obligation and all require independent route-level review."}
{"node_type":"string","pointer":"/unresolved_items/15/subject","value":"Morphology ablation, dependency and coreference accuracy, deterministic lifting expansion, and LLM incremental value are declared only as free remaining-obligation text and lack one registered, subject-bound, independently reviewed evaluation family."}
{"node_type":"string","pointer":"/unresolved_items/15/uncertainty_kind","value":"known_gap"}
{"keys":["affected_entity_refs","claim_effect","entity_id","evidence_gap","label","resolution_obligations","resolution_paths","resolution_summary","subject","uncertainty_kind"],"member_count":10,"node_type":"object","pointer":"/unresolved_items/16"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/16/affected_entity_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/16/affected_entity_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/16/affected_entity_refs/0/entity_id","value":"view.origin-purpose-coverage"}
{"node_type":"string","pointer":"/unresolved_items/16/affected_entity_refs/0/label_hint","value":"原点要求被覆ビュー"}
{"node_type":"string","pointer":"/unresolved_items/16/affected_entity_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/16/affected_entity_refs/1"}
{"node_type":"string","pointer":"/unresolved_items/16/affected_entity_refs/1/entity_id","value":"view.local-implementation-conformance"}
{"node_type":"string","pointer":"/unresolved_items/16/affected_entity_refs/1/label_hint","value":"局所実装適合ビュー"}
{"node_type":"string","pointer":"/unresolved_items/16/affected_entity_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/16/claim_effect","value":"does_not_block_claim"}
{"node_type":"string","pointer":"/unresolved_items/16/entity_id","value":"unresolved.projection-value-equivalence"}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/16/evidence_gap"}
{"node_type":"string","pointer":"/unresolved_items/16/evidence_gap/0","value":"A stable field-to-table projection contract."}
{"node_type":"string","pointer":"/unresolved_items/16/evidence_gap/1","value":"A deterministic generator or value-level equivalence checker."}
{"node_type":"string","pointer":"/unresolved_items/16/label","value":"Markdown 投影の値級一致又は自動生成"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/16/resolution_obligations"}
{"keys":["authority_basis","authority_class","decision_question","evidence_needed","obligation_id","precondition_obligation_refs","responsibility"],"member_count":7,"node_type":"object","pointer":"/unresolved_items/16/resolution_obligations/0"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_obligations/0/authority_basis","value":"Deterministic projection generation or value comparison changes no normative decision and is bounded implementation work."}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_obligations/0/authority_class","value":"agent_resolvable"}
{"node_type":"null","pointer":"/unresolved_items/16/resolution_obligations/0/decision_question","value":null}
{"item_count":2,"node_type":"array","pointer":"/unresolved_items/16/resolution_obligations/0/evidence_needed"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_obligations/0/evidence_needed/0","value":"Stable projection contract."}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_obligations/0/evidence_needed/1","value":"Generator or value-level equivalence test."}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_obligations/0/obligation_id","value":"obligation.projection.generate-or-compare"}
{"item_count":0,"node_type":"array","pointer":"/unresolved_items/16/resolution_obligations/0/precondition_obligation_refs"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_obligations/0/responsibility","value":"Generate the projection deterministically or check every projected state and evidence cell against an explicit mapping."}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/16/resolution_paths"}
{"keys":["activation_condition","completion_rule","path_id","required_obligation_refs"],"member_count":4,"node_type":"object","pointer":"/unresolved_items/16/resolution_paths/0"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_paths/0/activation_condition","value":"Applies whenever the Markdown projection is presented as a readable rendering of the canonical source."}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_paths/0/completion_rule","value":"The projection is generated deterministically from the source or every projected state and evidence cell is checked against an explicit bounded mapping."}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_paths/0/path_id","value":"resolution-path.projection.generated-or-value-compared"}
{"item_count":1,"node_type":"array","pointer":"/unresolved_items/16/resolution_paths/0/required_obligation_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/unresolved_items/16/resolution_paths/0/required_obligation_refs/0"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_paths/0/required_obligation_refs/0/entity_id","value":"obligation.projection.generate-or-compare"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_paths/0/required_obligation_refs/0/label_hint","value":"投影の生成又は全値比較"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_paths/0/required_obligation_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/unresolved_items/16/resolution_summary","value":"Deterministic generation and exact comparison are implemented locally; bound execution evidence and independent review remain before this registered gap can be closed."}
{"node_type":"string","pointer":"/unresolved_items/16/subject","value":"A deterministic complete-node Markdown projection and exact-equality validator now exist locally, while verification-matrix.md remains a curated non-canonical explanation. The mechanism lacks a registered current bound execution observation and independent review, so value-equivalence closure is not yet promoted in this register."}
{"node_type":"string","pointer":"/unresolved_items/16/uncertainty_kind","value":"evidence_gap"}
{"item_count":13,"node_type":"array","pointer":"/upstream_sources"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/0"}
{"node_type":"string","pointer":"/upstream_sources/0/authority","value":"purpose"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/0/limitations"}
{"node_type":"string","pointer":"/upstream_sources/0/limitations/0","value":"Defines target meaning and boundaries; it is not a completion claim or implementation contract."}
{"node_type":"string","pointer":"/upstream_sources/0/path","value":"../docs/prototypes/origin-requirement.md"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/0/ref"}
{"node_type":"string","pointer":"/upstream_sources/0/ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/upstream_sources/0/ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/upstream_sources/0/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/0/version_or_digest","value":"sha256:6960dfbc79670712b45ea3b02da8a2f7239c770ec9bf861cd7aa652009b5d3fb"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/1"}
{"node_type":"string","pointer":"/upstream_sources/1/authority","value":"normative_model"}
{"item_count":2,"node_type":"array","pointer":"/upstream_sources/1/limitations"}
{"node_type":"string","pointer":"/upstream_sources/1/limitations/0","value":"Pending human acceptance."}
{"node_type":"string","pointer":"/upstream_sources/1/limitations/1","value":"Defines semantics and invariants but does not itself prove implementation or field performance."}
{"node_type":"string","pointer":"/upstream_sources/1/path","value":"../constitution/semantic-guard-constitution.yaml"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/1/ref"}
{"node_type":"string","pointer":"/upstream_sources/1/ref/entity_id","value":"constitution.semantic-guard.r0"}
{"node_type":"string","pointer":"/upstream_sources/1/ref/label_hint","value":"v1 基幹憲法"}
{"node_type":"string","pointer":"/upstream_sources/1/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/1/version_or_digest","value":"sha256:4f1662fa4ba00d866dbfd808dd02f57249bfddf87306762d107205d626b23337"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/2"}
{"node_type":"string","pointer":"/upstream_sources/2/authority","value":"normative_model"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/2/limitations"}
{"node_type":"string","pointer":"/upstream_sources/2/limitations/0","value":"Candidate implementation gate with human acceptance pending; it defines bounded target behavior but is not implementation, verification, field-validity, or acceptance evidence."}
{"node_type":"string","pointer":"/upstream_sources/2/path","value":"../docs/prototypes/proof-obligation-assurance-graph-charter-2026-07-16.md"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/2/ref"}
{"node_type":"string","pointer":"/upstream_sources/2/ref/entity_id","value":"document.prototype-proof-obligation-assurance-graph-charter.v0"}
{"node_type":"string","pointer":"/upstream_sources/2/ref/label_hint","value":"proof obligation / assurance graph charter"}
{"node_type":"string","pointer":"/upstream_sources/2/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/2/version_or_digest","value":"sha256:ba3ba1afd8f6c0161a03da58ca6f1cade9dfdb5d65866f1914006e5ac3ad5ec8"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/3"}
{"node_type":"string","pointer":"/upstream_sources/3/authority","value":"normative_model"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/3/limitations"}
{"node_type":"string","pointer":"/upstream_sources/3/limitations/0","value":"Candidate completeness model with human acceptance pending; it cannot establish complete discovery of unknown unknowns or accept a denominator by itself."}
{"node_type":"string","pointer":"/upstream_sources/3/path","value":"../docs/prototypes/verification-register-completeness-charter-2026-07-16.md"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/3/ref"}
{"node_type":"string","pointer":"/upstream_sources/3/ref/entity_id","value":"document.prototype-verification-register-completeness-charter.v0"}
{"node_type":"string","pointer":"/upstream_sources/3/ref/label_hint","value":"verification register completeness charter"}
{"node_type":"string","pointer":"/upstream_sources/3/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/3/version_or_digest","value":"sha256:c8d5b91a99d2122ff51bac11a8316d6a7f9fb5ad32161c85badf6af7a5493230"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/4"}
{"node_type":"string","pointer":"/upstream_sources/4/authority","value":"internal_contract"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/4/limitations"}
{"node_type":"string","pointer":"/upstream_sources/4/limitations/0","value":"Provides shared identity and digest types; it does not define verification-register semantics by itself."}
{"node_type":"string","pointer":"/upstream_sources/4/path","value":"../schemas/common.schema.json"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/4/ref"}
{"node_type":"string","pointer":"/upstream_sources/4/ref/entity_id","value":"schema.semantic-guard.common.v0"}
{"node_type":"string","pointer":"/upstream_sources/4/ref/label_hint","value":"v1 共通型 schema"}
{"node_type":"string","pointer":"/upstream_sources/4/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/4/version_or_digest","value":"sha256:1a5df685a46f1418f3413c505c65d147b20a7b5f0a41f743576a46394cc7590f"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/5"}
{"node_type":"string","pointer":"/upstream_sources/5/authority","value":"internal_contract"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/5/limitations"}
{"node_type":"string","pointer":"/upstream_sources/5/limitations/0","value":"Defines the closed register shape and conditional constraints; cross-file identity, digest, and projection checks still require the internal validator."}
{"node_type":"string","pointer":"/upstream_sources/5/path","value":"verification-source.schema.json"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/5/ref"}
{"node_type":"string","pointer":"/upstream_sources/5/ref/entity_id","value":"schema.semantic-guard.verification-source.v0"}
{"node_type":"string","pointer":"/upstream_sources/5/ref/label_hint","value":"検証正本 schema"}
{"node_type":"string","pointer":"/upstream_sources/5/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/5/version_or_digest","value":"sha256:b52ef17d6aedc953c67667d0edc8a7d22dbc346e930b592e5a91cdf46b4bef18"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/6"}
{"node_type":"string","pointer":"/upstream_sources/6/authority","value":"internal_contract"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/6/limitations"}
{"node_type":"string","pointer":"/upstream_sources/6/limitations/0","value":"Defines the validator output envelope; it does not make a successful consistency result into field or action evidence."}
{"node_type":"string","pointer":"/upstream_sources/6/path","value":"verification-validation-result.schema.json"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/6/ref"}
{"node_type":"string","pointer":"/upstream_sources/6/ref/entity_id","value":"schema.semantic-guard.verification-validation-result.v0"}
{"node_type":"string","pointer":"/upstream_sources/6/ref/label_hint","value":"検証正本内部検証結果 schema"}
{"node_type":"string","pointer":"/upstream_sources/6/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/6/version_or_digest","value":"sha256:a71deee2046841cdd9343e7d4473d9de9716091aac25182072becf52eb1edfee"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/7"}
{"node_type":"string","pointer":"/upstream_sources/7/authority","value":"validation_implementation"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/7/limitations"}
{"node_type":"string","pointer":"/upstream_sources/7/limitations/0","value":"Checks bounded repository-local consistency only; its output records its own digest and runtime but is not independent evidence."}
{"node_type":"string","pointer":"/upstream_sources/7/path","value":"../scripts/validate_verification_source.py"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/7/ref"}
{"node_type":"string","pointer":"/upstream_sources/7/ref/entity_id","value":"validator.semantic-guard.verification-source.v0"}
{"node_type":"string","pointer":"/upstream_sources/7/ref/label_hint","value":"検証正本内部検証器"}
{"node_type":"string","pointer":"/upstream_sources/7/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/7/version_or_digest","value":"sha256:e290e9468d1250338dbc488da73a5d4e955a28080f0bdb8cab8738484f0e45cb"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/8"}
{"node_type":"string","pointer":"/upstream_sources/8/authority","value":"public_contract"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/8/limitations"}
{"node_type":"string","pointer":"/upstream_sources/8/limitations/0","value":"Public runtime result contract; it is not the verification register contract."}
{"node_type":"string","pointer":"/upstream_sources/8/path","value":"../schemas/audit-result.schema.json"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/8/ref"}
{"node_type":"string","pointer":"/upstream_sources/8/ref/entity_id","value":"schema.semantic-guard.audit-result.v0"}
{"node_type":"string","pointer":"/upstream_sources/8/ref/label_hint","value":"v1 監査結果 schema"}
{"node_type":"string","pointer":"/upstream_sources/8/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/8/version_or_digest","value":"sha256:dc72be89438a922af884475528877af00cd6dcebe2d5e6faa33e57af2ec9d22f"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/9"}
{"node_type":"string","pointer":"/upstream_sources/9/authority","value":"evidence_observation"}
{"item_count":2,"node_type":"array","pointer":"/upstream_sources/9/limitations"}
{"node_type":"string","pointer":"/upstream_sources/9/limitations/0","value":"Dated local record, but not bound to a closed tested-source manifest."}
{"node_type":"string","pointer":"/upstream_sources/9/limitations/1","value":"Does not establish field performance, authenticity, production readiness, or human acceptance."}
{"node_type":"string","pointer":"/upstream_sources/9/path","value":"integrated-verification-2026-07-16.json"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/9/ref"}
{"node_type":"string","pointer":"/upstream_sources/9/ref/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/upstream_sources/9/ref/label_hint","value":"2026-07-16 統合検証記録"}
{"node_type":"string","pointer":"/upstream_sources/9/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/9/version_or_digest","value":"sha256:c61681d5f73d767060730331e21e2093a776bbdbf0e44ace389d83faca8aa2f3"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/10"}
{"node_type":"string","pointer":"/upstream_sources/10/authority","value":"evidence_observation"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/10/limitations"}
{"node_type":"string","pointer":"/upstream_sources/10/limitations/0","value":"Defines the selected legacy comparison subject and drift boundary; it is not a correctness oracle."}
{"node_type":"string","pointer":"/upstream_sources/10/path","value":"../migration/legacy-baseline-2026-07-16.json"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/10/ref"}
{"node_type":"string","pointer":"/upstream_sources/10/ref/entity_id","value":"migration.legacy-baseline.v1"}
{"node_type":"string","pointer":"/upstream_sources/10/ref/label_hint","value":"旧版基線 v1"}
{"node_type":"string","pointer":"/upstream_sources/10/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/10/version_or_digest","value":"sha256:c95657f65430acf6e36729bbac3f873ba0f9d7c3b34087fc0a8de2d7e56cc5c1"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/11"}
{"node_type":"string","pointer":"/upstream_sources/11/authority","value":"evidence_observation"}
{"item_count":1,"node_type":"array","pointer":"/upstream_sources/11/limitations"}
{"node_type":"string","pointer":"/upstream_sources/11/limitations/0","value":"The integrated record contains the dated legacy characterization observation; it does not make legacy behavior correct."}
{"node_type":"string","pointer":"/upstream_sources/11/path","value":"integrated-verification-2026-07-16.json"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/11/ref"}
{"node_type":"string","pointer":"/upstream_sources/11/ref/entity_id","value":"migration.legacy-characterization.2026-07-16"}
{"node_type":"string","pointer":"/upstream_sources/11/ref/label_hint","value":"旧版特性試験観測"}
{"node_type":"string","pointer":"/upstream_sources/11/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/11/version_or_digest","value":"sha256:c61681d5f73d767060730331e21e2093a776bbdbf0e44ace389d83faca8aa2f3"}
{"keys":["authority","limitations","path","ref","version_or_digest"],"member_count":5,"node_type":"object","pointer":"/upstream_sources/12"}
{"node_type":"string","pointer":"/upstream_sources/12/authority","value":"historical_assessment"}
{"item_count":2,"node_type":"array","pointer":"/upstream_sources/12/limitations"}
{"node_type":"string","pointer":"/upstream_sources/12/limitations/0","value":"Predates the current v1 implementation and is supporting historical evidence, not current completion proof."}
{"node_type":"string","pointer":"/upstream_sources/12/limitations/1","value":"The public artifact is a publication-sanitized derivative: terminal-specific paths, private-dialogue provenance, and an unavailable structured-ledger command are omitted. A separate private original was recorded under sha256:788499cc5cb8c283cf130f9fd2c645733f18f6c63c5755a334973a83196a3159; its current availability is not established by this public repository."}
{"node_type":"string","pointer":"/upstream_sources/12/path","value":"../docs/audits/semantic-guard-full-evaluation-2026-07-11.md"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/upstream_sources/12/ref"}
{"node_type":"string","pointer":"/upstream_sources/12/ref/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/upstream_sources/12/ref/label_hint","value":"2026-07-11 全体監査"}
{"node_type":"string","pointer":"/upstream_sources/12/ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/upstream_sources/12/version_or_digest","value":"sha256:e13e5a539372aff599b2c3c1241dce364b9962ad07eed6bc2047548b29ae2d37"}
{"item_count":17,"node_type":"array","pointer":"/verification_items"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surface_assessments","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":26,"node_type":"object","pointer":"/verification_items/0"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/0/acceptance_criteria/0","value":"Every enumerated lifecycle surface traces to a profile, contract, implementation, verification evidence, and declared unproven scope."}
{"node_type":"string","pointer":"/verification_items/0/acceptance_criteria/1","value":"Missing profiles remain visible and prevent whole-purpose completion claims."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/assumptions"}
{"node_type":"string","pointer":"/verification_items/0/assumptions/0","value":"The OR-01 surface list is the current denominator."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/0/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/0/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/0/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/0/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/0/authority_boundary/source_may/0","value":"Expose missing lifecycle coverage."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/0/authority_boundary/source_must_not/0","value":"Prioritize or schedule profile implementation."}
{"node_type":"string","pointer":"/verification_items/0/authority_boundary/source_must_not/1","value":"Declare whole-purpose acceptance."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/claim_classes"}
{"node_type":"string","pointer":"/verification_items/0/claim_classes/0","value":"description_completeness"}
{"node_type":"string","pointer":"/verification_items/0/claim_classes/1","value":"requirement_conformance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/0/counterconditions/0","value":"A future human-approved origin revision changes the denominator."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/counterevidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/counterevidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/counterevidence_refs/0/label_hint","value":"九面の v1 縦断実装が未存在"}
{"node_type":"string","pointer":"/verification_items/0/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/0/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/0/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/0/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/0/evidence_refs/1/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/evidence_refs/1/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/failure_consequence","value":"A successful requirement-relation slice could be mistaken for completion of the whole cross-process audit purpose."}
{"node_type":"string","pointer":"/verification_items/0/item_kind","value":"purpose_coverage"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/0/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/applicability","value":"All AI-agent development lifecycle audit profiles."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/counterconditions/0","value":"A lifecycle surface explicitly declared outside semantic-guard audit ownership."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/limitations/0","value":"The origin requirement names target surfaces but does not prescribe one implementation architecture."}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/locator","value":"OR-01"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/0/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/0/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/0/label","value":"OR-01 工程横断被覆"}
{"item_count":10,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/0"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/0/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/0/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/scope_note","value":"A candidate request profile exists, but it is not human-adopted and has no public resolver, stage adapter, vertical implementation, or bound conformance evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/0/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/0/surface","value":"request"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/1"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/1/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/1/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/scope_note","value":"A candidate exploration profile exists, but it is not human-adopted and has no public resolver, stage adapter, vertical implementation, or bound conformance evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/1/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/1/surface","value":"exploration_question"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/2"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/2/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/2/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/scope_note","value":"The structured functional-requirement relation slice is implemented and historically test-reported, but its evidence is unbound to the current source snapshot and field use is not validated."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/2/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/state_profile_ref/entity_id","value":"state.local-verified-not-validated"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/state_profile_ref/label_hint","value":"局所検証済み・実務未妥当化"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/2/surface","value":"requirement"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/3"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/3/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/3/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/scope_note","value":"A candidate decision profile exists, but it is not human-adopted and has no public resolver, stage adapter, vertical implementation, or bound conformance evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/3/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/3/surface","value":"decision_state"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/4"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/4/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/4/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/scope_note","value":"A candidate plan profile exists, but it is not human-adopted and has no public resolver, stage adapter, vertical implementation, or bound conformance evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/4/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/4/surface","value":"plan"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/5"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/5/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/5/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/scope_note","value":"A candidate action profile and local action-evidence sidecar exist, but no instrumented runtime action-audit vertical, external authenticity, or bound operational evidence exists."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/5/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/5/surface","value":"action"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/6"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/6/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/6/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/scope_note","value":"A candidate realization profile exists, but it is not human-adopted and has no public resolver, stage adapter, vertical implementation, or bound conformance evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/6/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/6/surface","value":"realization_policy"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/7"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/7/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/7/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/scope_note","value":"A candidate diff profile exists, but it is not human-adopted and has no public resolver, stage adapter, vertical implementation, or bound conformance evidence."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/7/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/7/surface","value":"diff"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/8"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/8/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/8/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/scope_note","value":"A candidate verification profile and local trace, state, and repair sidecars exist, but no human-adopted artifact profile, public stage adapter, or bound verification-artifact evidence exists."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/8/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/8/surface","value":"verification"}
{"keys":["evidence_refs","scope_note","state_profile_ref","surface"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/9"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/lifecycle_surface_assessments/9/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/9/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/scope_note","value":"A candidate completion profile and local responsibility material contract exist, but no human-adopted completion semantics, public vertical implementation, or bound acceptance-material evidence exists."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/lifecycle_surface_assessments/9/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/state_profile_ref/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surface_assessments/9/surface","value":"completion_claim"}
{"item_count":10,"node_type":"array","pointer":"/verification_items/0/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/0","value":"request"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/1","value":"exploration_question"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/2","value":"requirement"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/3","value":"decision_state"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/4","value":"plan"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/5","value":"action"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/6","value":"realization_policy"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/7","value":"diff"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/8","value":"verification"}
{"node_type":"string","pointer":"/verification_items/0/lifecycle_surfaces/9","value":"completion_claim"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/0/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/0/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/0/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/0/proposition","value":"Every OR-01 lifecycle surface has a versioned v1 audit profile, contract, implementation, and bounded verification evidence."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/0/rejection_conditions/0","value":"Any lifecycle surface is omitted from the denominator."}
{"node_type":"string","pointer":"/verification_items/0/rejection_conditions/1","value":"A single requirement slice is projected as OR-01 completion."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/0/required_evidence"}
{"node_type":"string","pointer":"/verification_items/0/required_evidence/0","value":"Per-surface contract and implementation references."}
{"node_type":"string","pointer":"/verification_items/0/required_evidence/1","value":"Per-surface conformance and adversarial tests."}
{"node_type":"string","pointer":"/verification_items/0/required_evidence/2","value":"Representative operational shadow observations."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/residual_risks"}
{"node_type":"string","pointer":"/verification_items/0/residual_risks/0","value":"Progress on the requirement slice can dominate attention and hide untouched lifecycle surfaces."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/0/reverification"}
{"node_type":"string","pointer":"/verification_items/0/reverification/last_evaluated_at","value":"2026-08-27T15:43:40+09:00"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/0/reverification/procedure_refs/0","value":"docs/implementation-status.md"}
{"node_type":"string","pointer":"/verification_items/0/reverification/procedure_refs/1","value":"validation/verification-source.json"}
{"node_type":"string","pointer":"/verification_items/0/reverification/status","value":"defined"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/0/reverification/triggers/0","value":"Origin requirement revision."}
{"node_type":"string","pointer":"/verification_items/0/reverification/triggers/1","value":"A lifecycle profile is added, removed, or re-scoped."}
{"node_type":"null","pointer":"/verification_items/0/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/0/scope","value":"The lifecycle surfaces enumerated by OR-01."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/0/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/0/state_profile_ref/entity_id","value":"state.known-incomplete"}
{"node_type":"string","pointer":"/verification_items/0/state_profile_ref/label_hint","value":"既知の未充足"}
{"node_type":"string","pointer":"/verification_items/0/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/0/unproven_scope/0","value":"Request, exploration-question, decision-state, plan, action, realization-policy, diff, verification-artifact, and completion-claim vertical slices; only the requirement surface has the current v1 vertical implementation."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/validation_method"}
{"node_type":"string","pointer":"/verification_items/0/validation_method/environment","value":"Not yet defined."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/0/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/0/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/0/validation_method/population_or_context","value":"Agents and human reviewers using every lifecycle profile."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/0/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/0/verification_method"}
{"node_type":"string","pointer":"/verification_items/0/verification_method/environment","value":"Repository snapshot recorded by this source."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/0/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/0/verification_method/method_types/1","value":"analysis"}
{"node_type":"string","pointer":"/verification_items/0/verification_method/population_or_context","value":"All OR-01 lifecycle surfaces."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/0/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/0/verification_method/procedure_refs/0","value":"docs/implementation-status.md"}
{"node_type":"string","pointer":"/verification_items/0/verification_method/procedure_refs/1","value":"README.md"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/1"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/1/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/1/acceptance_criteria/0","value":"Every adopted criterion has source version and locator, applicability, counterconditions, required evidence, limitation, interpretation owner or adoption authority, and re-review trigger."}
{"node_type":"string","pointer":"/verification_items/1/acceptance_criteria/1","value":"Repository policy and external standard interpretation remain distinct."}
{"node_type":"string","pointer":"/verification_items/1/acceptance_criteria/2","value":"No standards-conformance claim is inferred from partial adoption."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/assumptions"}
{"node_type":"string","pointer":"/verification_items/1/assumptions/0","value":"The current rule implementation is intended as engineering-informed, not standards-conformant."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/1/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/1/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/1/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/1/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/1/authority_boundary/source_may/0","value":"Expose missing or stale engineering basis and interpretation evidence."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/1/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/1/authority_boundary/source_must_not/0","value":"Adopt an external standard or organizational policy without human authority."}
{"node_type":"string","pointer":"/verification_items/1/authority_boundary/source_must_not/1","value":"Claim standards conformance."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/claim_classes"}
{"node_type":"string","pointer":"/verification_items/1/claim_classes/0","value":"requirement_conformance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/counterconditions"}
{"node_type":"string","pointer":"/verification_items/1/counterconditions/0","value":"A criterion is explicitly classified as repository-local and makes no external engineering claim."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/1/counterevidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/1/counterevidence_refs/0/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/verification_items/1/counterevidence_refs/0/label_hint","value":"体系知採用統治の欠落観測"}
{"node_type":"string","pointer":"/verification_items/1/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/1/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/1/entity_id","value":"verification.or01.engineering-knowledge-governance"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/1/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/1/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/1/evidence_refs/0/entity_id","value":"evidence.constitution.snapshot.2026-08-24"}
{"node_type":"string","pointer":"/verification_items/1/evidence_refs/0/label_hint","value":"v1 憲法 snapshot"}
{"node_type":"string","pointer":"/verification_items/1/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/1/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/1/evidence_refs/1/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/verification_items/1/evidence_refs/1/label_hint","value":"全体監査の歴史的観測"}
{"node_type":"string","pointer":"/verification_items/1/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/1/failure_consequence","value":"The system may precisely compare text against an arbitrary template while presenting the result as engineering-grounded audit."}
{"node_type":"string","pointer":"/verification_items/1/item_kind","value":"engineering_knowledge"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/1/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/applicability","value":"Any rule claiming an engineering knowledge basis."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/counterconditions/0","value":"Purely repository-local syntactic contract checks that make no engineering-grounding claim."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/limitations/0","value":"External standards are not clause-completely mapped or adopted by this source."}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/locator","value":"Acceptance Criteria: engineering knowledge rule trace"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/1/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/1/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/1/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/1/label","value":"OR-01 体系知の根拠統治"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/1/lifecycle_surfaces/0","value":"cross_cutting"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/1/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/1/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/1/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/1/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/1/proposition","value":"Every engineering criterion used for audit records its source edition, concept or clause locator, interpretation, applicability, counterconditions, required evidence, limitations, adoption state, and review condition."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/1/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/1/rejection_conditions/0","value":"Engineering names are present without traceable source and interpretation."}
{"node_type":"string","pointer":"/verification_items/1/rejection_conditions/1","value":"A profile hard-codes criteria without adoption or expiry information."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/1/required_evidence"}
{"node_type":"string","pointer":"/verification_items/1/required_evidence/0","value":"Versioned rule-pack source."}
{"node_type":"string","pointer":"/verification_items/1/required_evidence/1","value":"Clause or concept mapping with application and non-application cases."}
{"node_type":"string","pointer":"/verification_items/1/required_evidence/2","value":"Independent review and adoption record."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/residual_risks"}
{"node_type":"string","pointer":"/verification_items/1/residual_risks/0","value":"A target form may become self-referential if its engineering origin is not independently reviewable."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/1/reverification"}
{"node_type":"string","pointer":"/verification_items/1/reverification/last_evaluated_at","value":"2026-08-24T13:01:52+09:00"}
{"item_count":0,"node_type":"array","pointer":"/verification_items/1/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/1/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/1/reverification/triggers/0","value":"Rule-pack source, external edition, interpretation, or organization profile changes."}
{"node_type":"null","pointer":"/verification_items/1/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/1/scope","value":"All versioned rule packs and audit profiles presented as grounded in requirements, planning, software, or systems engineering."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/1/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/1/state_profile_ref/entity_id","value":"state.partial-challenged"}
{"node_type":"string","pointer":"/verification_items/1/state_profile_ref/label_hint","value":"部分実装・反証材料あり"}
{"node_type":"string","pointer":"/verification_items/1/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/1/unproven_scope/0","value":"Clause-complete mapping, interpretation governance, organizational adoption, exception expiry, and review cadence."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/1/validation_method"}
{"node_type":"string","pointer":"/verification_items/1/validation_method/environment","value":"Future independent domain review."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/1/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/1/validation_method/method_types/0","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/1/validation_method/population_or_context","value":"Representative rule packs and organizational interpretations."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/1/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/1/verification_method"}
{"node_type":"string","pointer":"/verification_items/1/verification_method/environment","value":"Repository source inspection."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/1/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/1/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/1/verification_method/method_types/1","value":"analysis"}
{"node_type":"string","pointer":"/verification_items/1/verification_method/population_or_context","value":"Current v1 rule and profile definitions."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/1/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/1/verification_method/procedure_refs/0","value":"src/semantic_guard/profiles.py"}
{"node_type":"string","pointer":"/verification_items/1/verification_method/procedure_refs/1","value":"src/semantic_guard/direct_rules.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/2"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/2/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/2/acceptance_criteria/0","value":"The denominator enumerates required relations and failure phenomena by lifecycle profile."}
{"node_type":"string","pointer":"/verification_items/2/acceptance_criteria/1","value":"Catastrophic false satisfaction, false defect, abstention, silent coverage gap, challenge capture, and source-span fidelity are reported separately."}
{"node_type":"string","pointer":"/verification_items/2/acceptance_criteria/2","value":"Direct-rule-only, morphology, dependency, and LLM candidate routes are compared by ablation."}
{"node_type":"string","pointer":"/verification_items/2/acceptance_criteria/3","value":"Unseen holdout and paraphrase metamorphic cases remain isolated from rule tuning."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/assumptions"}
{"node_type":"string","pointer":"/verification_items/2/assumptions/0","value":"Catastrophic false satisfaction has greater cost than conservative abstention in the current purpose."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/2/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/2/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/2/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/2/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/2/authority_boundary/source_may/0","value":"Report bounded detection evidence and gaps."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/2/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/2/authority_boundary/source_must_not/0","value":"Choose the human error-cost tradeoff."}
{"node_type":"string","pointer":"/verification_items/2/authority_boundary/source_must_not/1","value":"Infer general accuracy from fixtures or smoke tests."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/2/claim_classes"}
{"node_type":"string","pointer":"/verification_items/2/claim_classes/0","value":"discovery_effectiveness"}
{"node_type":"string","pointer":"/verification_items/2/claim_classes/1","value":"requirement_conformance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/counterconditions"}
{"node_type":"string","pointer":"/verification_items/2/counterconditions/0","value":"A profile declares a closed formal input whose relations are validated before semantic-guard receives it."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/2/counterevidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/2/counterevidence_refs/0/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/2/counterevidence_refs/0/label_hint","value":"coreference 能力欠落と五例限定"}
{"node_type":"string","pointer":"/verification_items/2/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/2/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/2/entity_id","value":"verification.or01.discovery-effectiveness"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/2/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/2/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/2/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/2/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/2/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/2/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/2/evidence_refs/1/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/2/evidence_refs/1/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/verification_items/2/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/2/failure_consequence","value":"A false satisfied result can pass because the system never generated the unknown, conflict, or coverage gap that downstream fail-closed aggregation would preserve."}
{"node_type":"string","pointer":"/verification_items/2/item_kind","value":"detection_effectiveness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/2/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/applicability","value":"All audit routes capable of emitting satisfied, refuted, undetermined, or conflict outcomes."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/counterconditions/0","value":"A declared closed structured field whose complete semantics are supplied directly by a trusted caller and independently verified."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/limitations/0","value":"The constitution names metrics and risks but does not provide a representative target-population corpus."}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/locator","value":"residual_risk_gate and evaluation_contract"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/2/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/source_ref/entity_id","value":"constitution.semantic-guard.r0"}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/source_ref/label_hint","value":"v1 基幹憲法"}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/2/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/2/knowledge_basis/0/version","value":"0.2.0-draft"}
{"node_type":"string","pointer":"/verification_items/2/label","value":"OR-01 未解決・欠陥の発見性能"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/2/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/2/lifecycle_surfaces/0","value":"requirement"}
{"node_type":"string","pointer":"/verification_items/2/lifecycle_surfaces/1","value":"cross_cutting"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/2/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/2/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/2/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/2/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/2/proposition","value":"The audit detects material missing relations, ambiguous attachments, contradictions, and unaccounted semantic scope that should become unresolved, rather than merely preserving unresolved states after another component has generated them."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/2/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/2/rejection_conditions/0","value":"Only preservation of already-generated unknown states is tested."}
{"node_type":"string","pointer":"/verification_items/2/rejection_conditions/1","value":"Fixture pass rate is presented as recall or field accuracy."}
{"node_type":"string","pointer":"/verification_items/2/rejection_conditions/2","value":"The target relation set lacks an engineering basis and application boundary."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/2/required_evidence"}
{"node_type":"string","pointer":"/verification_items/2/required_evidence/0","value":"Requirement-relation and linguistic-phenomenon coverage denominator."}
{"node_type":"string","pointer":"/verification_items/2/required_evidence/1","value":"Independent double labels, adjudication, and disagreement preservation."}
{"node_type":"string","pointer":"/verification_items/2/required_evidence/2","value":"Domain-stratified holdout results and cost matrix."}
{"node_type":"string","pointer":"/verification_items/2/required_evidence/3","value":"Analyzer-route ablation and temporal rerun evidence."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/residual_risks"}
{"node_type":"string","pointer":"/verification_items/2/residual_risks/0","value":"Improved analyzer sophistication can still create confidently wrong candidates if the target relation model is wrong."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/2/reverification"}
{"node_type":"string","pointer":"/verification_items/2/reverification/last_evaluated_at","value":"2026-07-16T08:30:40+09:00"}
{"item_count":0,"node_type":"array","pointer":"/verification_items/2/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/2/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/2/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/2/reverification/triggers/0","value":"Rule, profile, analyzer, model, dictionary, corpus, or target-population change."}
{"node_type":"null","pointer":"/verification_items/2/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/2/scope","value":"The current structured functional-requirement profile and future lifecycle profiles, including direct rules, morphology, dependency candidates, deterministic lifting, and LLM candidates."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/2/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/2/state_profile_ref/entity_id","value":"state.partial-challenged"}
{"node_type":"string","pointer":"/verification_items/2/state_profile_ref/label_hint","value":"部分実装・反証材料あり"}
{"node_type":"string","pointer":"/verification_items/2/state_profile_ref/reference_kind","value":"ref"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/2/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/2/unproven_scope/0","value":"Unknown-unknown discovery recall."}
{"node_type":"string","pointer":"/verification_items/2/unproven_scope/1","value":"Cross-sentence and coreference-dependent relations."}
{"node_type":"string","pointer":"/verification_items/2/unproven_scope/2","value":"Target-population accuracy and generalization."}
{"node_type":"string","pointer":"/verification_items/2/unproven_scope/3","value":"Performance on plans, diffs, actions, verification reports, and completion claims."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/2/validation_method"}
{"node_type":"string","pointer":"/verification_items/2/validation_method/environment","value":"Future shadow use on domain-stratified real artifacts with independent labeling and adjudication."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/2/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/2/validation_method/method_types/0","value":"operational_observation"}
{"node_type":"string","pointer":"/verification_items/2/validation_method/method_types/1","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/2/validation_method/population_or_context","value":"The intended real-work artifact population, which is not yet defined."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/2/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/2/verification_method"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/environment","value":"Deterministic fixtures, metamorphic cases, and bounded real-provider smoke runs."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/2/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/method_types/0","value":"test"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/method_types/1","value":"analysis"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/population_or_context","value":"Known adversarial and hand-selected requirement forms."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/2/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/procedure_refs/0","value":"fixtures/requirement-relations/conformance.jsonl"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/procedure_refs/1","value":"tests/test_conformance_corpus.py"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/procedure_refs/2","value":"tests/test_residual_risk.py"}
{"node_type":"string","pointer":"/verification_items/2/verification_method/procedure_refs/3","value":"tests/test_dependency_projection.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/3"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/3/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/3/acceptance_criteria/0","value":"All required bounded-correctness dimensions are explicit and closed by schema."}
{"node_type":"string","pointer":"/verification_items/3/acceptance_criteria/1","value":"Description, occurrence, identity, authority, provenance, authenticity, causality, verification, and validation remain separate claims."}
{"node_type":"string","pointer":"/verification_items/3/acceptance_criteria/2","value":"Elevated claims are rejected without their required mechanism and trust basis."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/assumptions"}
{"node_type":"string","pointer":"/verification_items/3/assumptions/0","value":"Schema and constitution are interpreted together."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/3/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/3/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/3/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/3/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/3/authority_boundary/source_may/0","value":"Define and check bounded claim structure."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/3/authority_boundary/source_must_not/0","value":"Treat schema validity as occurrence, authenticity, causality, or human acceptance."}
{"item_count":11,"node_type":"array","pointer":"/verification_items/3/claim_classes"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/0","value":"description_completeness"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/1","value":"action_occurrence"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/2","value":"actor_identity"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/3","value":"authority"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/4","value":"procedure_conformance"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/5","value":"artifact_generation"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/6","value":"artifact_provenance"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/7","value":"verification_result"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/8","value":"validation_result"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/9","value":"authenticity"}
{"node_type":"string","pointer":"/verification_items/3/claim_classes/10","value":"causality"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/counterconditions"}
{"node_type":"string","pointer":"/verification_items/3/counterconditions/0","value":"A downstream projection discards required dimensions or merges claim classes."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/3/counterevidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/3/counterevidence_refs/0/entity_id","value":"evidence.public-trust-basis-inspection.2026-07-17"}
{"node_type":"string","pointer":"/verification_items/3/counterevidence_refs/0/label_hint","value":"公開 provenance の高信頼級に根拠拘束なし"}
{"node_type":"string","pointer":"/verification_items/3/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/3/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/3/entity_id","value":"verification.or02.bounded-claim-model"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/3/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/3/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/3/evidence_refs/0/entity_id","value":"evidence.constitution.snapshot.2026-08-24"}
{"node_type":"string","pointer":"/verification_items/3/evidence_refs/0/label_hint","value":"v1 憲法 snapshot"}
{"node_type":"string","pointer":"/verification_items/3/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/3/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/3/evidence_refs/1/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/3/evidence_refs/1/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/3/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/3/failure_consequence","value":"Description completeness can be mistaken for action occurrence, identity, authority, causality, or verified outcome."}
{"node_type":"string","pointer":"/verification_items/3/item_kind","value":"bounded_assurance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/3/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/applicability","value":"All bounded assurance claims."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/counterconditions/0","value":"Pure presentation text that makes no assurance claim."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/limitations/0","value":"A correct claim model does not establish that evidence acquisition mechanisms exist."}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/locator","value":"bounded_correctness and claim_classes_kept_separate"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/3/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/source_ref/entity_id","value":"constitution.semantic-guard.r0"}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/source_ref/label_hint","value":"v1 基幹憲法"}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/3/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/3/knowledge_basis/0/version","value":"0.2.0-draft"}
{"node_type":"string","pointer":"/verification_items/3/label","value":"OR-02 限定的立証の主張模型"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/3/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/3/lifecycle_surfaces/0","value":"action"}
{"node_type":"string","pointer":"/verification_items/3/lifecycle_surfaces/1","value":"verification"}
{"node_type":"string","pointer":"/verification_items/3/lifecycle_surfaces/2","value":"completion_claim"}
{"node_type":"string","pointer":"/verification_items/3/lifecycle_surfaces/3","value":"cross_cutting"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/3/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/3/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/3/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/3/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/3/proposition","value":"The normative and schema basis separates claim classes and retains proposition, scope, rules, evidence, derivation, trust assumptions, counterconditions, coverage, provenance, unproven scope, and residual risks."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/3/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/3/rejection_conditions/0","value":"Any claim class can inherit evidence or authority merely from textual similarity."}
{"node_type":"string","pointer":"/verification_items/3/rejection_conditions/1","value":"Unknown or missing dimensions default to success."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/3/required_evidence"}
{"node_type":"string","pointer":"/verification_items/3/required_evidence/0","value":"Schema self-validation and negative conformance cases."}
{"node_type":"string","pointer":"/verification_items/3/required_evidence/1","value":"Representative assurance records for every claim class."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/residual_risks"}
{"node_type":"string","pointer":"/verification_items/3/residual_risks/0","value":"A structurally complete but semantically wrong claim can still be recorded."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/3/reverification"}
{"node_type":"string","pointer":"/verification_items/3/reverification/last_evaluated_at","value":"2026-08-24T13:01:52+09:00"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/3/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/3/reverification/procedure_refs/0","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/verification_items/3/reverification/procedure_refs/1","value":"tests/test_models_and_aggregation.py"}
{"node_type":"string","pointer":"/verification_items/3/reverification/status","value":"defined"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/3/reverification/triggers/0","value":"Claim taxonomy, schema, authority, or public projection changes."}
{"node_type":"null","pointer":"/verification_items/3/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/3/scope","value":"The v1 constitution and bounded assurance schemas, not the occurrence or authenticity of a real external action."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/3/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/3/state_profile_ref/entity_id","value":"state.partial-challenged"}
{"node_type":"string","pointer":"/verification_items/3/state_profile_ref/label_hint","value":"部分実装・反証材料あり"}
{"node_type":"string","pointer":"/verification_items/3/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/3/unproven_scope/0","value":"Real action evidence acquisition, independent observation, authenticity, and causal proof."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/3/validation_method"}
{"node_type":"string","pointer":"/verification_items/3/validation_method/environment","value":"Future agent and human review of real assurance cases."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/3/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/3/validation_method/method_types/0","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/3/validation_method/population_or_context","value":"Real action, artifact, verification, and completion claims."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/3/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/3/verification_method"}
{"node_type":"string","pointer":"/verification_items/3/verification_method/environment","value":"Schema and public-contract conformance tests."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/3/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/3/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/3/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/3/verification_method/population_or_context","value":"Schema-valid and adversarial assurance records."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/3/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/3/verification_method/procedure_refs/0","value":"schemas/assurance-claim.schema.json"}
{"node_type":"string","pointer":"/verification_items/3/verification_method/procedure_refs/1","value":"schemas/common.schema.json"}
{"node_type":"string","pointer":"/verification_items/3/verification_method/procedure_refs/2","value":"tests/test_public_contract.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/4"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/4/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/4/acceptance_criteria/0","value":"Self-report-only action claims are rejected as occurrence evidence."}
{"node_type":"string","pointer":"/verification_items/4/acceptance_criteria/1","value":"Actor, authority, observer, time, environment, inputs, outputs, artifacts, passed stages, and stop conditions are independently addressable."}
{"node_type":"string","pointer":"/verification_items/4/acceptance_criteria/2","value":"Missing observation or authority remains unproven rather than successful."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/assumptions"}
{"node_type":"string","pointer":"/verification_items/4/assumptions/0","value":"Actual action occurrence requires evidence beyond document analysis."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/4/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/4/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/4/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/4/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/4/authority_boundary/source_may/0","value":"Check action evidence and expose missing authority or observation."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/4/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/4/authority_boundary/source_must_not/0","value":"Grant execution authority."}
{"node_type":"string","pointer":"/verification_items/4/authority_boundary/source_must_not/1","value":"Dispatch actions."}
{"node_type":"string","pointer":"/verification_items/4/authority_boundary/source_must_not/2","value":"Treat successful execution as authorized procedure conformance."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/4/claim_classes"}
{"node_type":"string","pointer":"/verification_items/4/claim_classes/0","value":"action_occurrence"}
{"node_type":"string","pointer":"/verification_items/4/claim_classes/1","value":"actor_identity"}
{"node_type":"string","pointer":"/verification_items/4/claim_classes/2","value":"authority"}
{"node_type":"string","pointer":"/verification_items/4/claim_classes/3","value":"procedure_conformance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/counterconditions"}
{"node_type":"string","pointer":"/verification_items/4/counterconditions/0","value":"The proposition is explicitly limited to description completeness."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/4/counterevidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/4/counterevidence_refs/0/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/verification_items/4/counterevidence_refs/0/label_hint","value":"主体・権限・観測者証拠の欠落観測"}
{"node_type":"string","pointer":"/verification_items/4/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/4/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/4/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/4/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/4/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/4/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/4/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/4/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/4/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/4/evidence_refs/1/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/verification_items/4/evidence_refs/1/label_hint","value":"全体監査の歴史的観測"}
{"node_type":"string","pointer":"/verification_items/4/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/4/failure_consequence","value":"A self-report or well-formed action description can be mistaken for an authorized action that actually occurred and followed the required procedure."}
{"node_type":"string","pointer":"/verification_items/4/item_kind","value":"action_assurance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/4/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/applicability","value":"Claims about actual AI-agent actions."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/counterconditions/0","value":"A claim explicitly concerns only completeness of an action description."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/limitations/0","value":"The origin requirement does not select one runtime attestation mechanism."}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/locator","value":"OR-02 and Hollow Success Conditions"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/4/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/4/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/4/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/4/label","value":"OR-02 行為発生・主体・権限・手続適合"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/4/lifecycle_surfaces/0","value":"action"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/4/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/4/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/4/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/4/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/4/proposition","value":"For each claimed action, the system can bind an observed event, actor or agent, authority, observer, observer-to-actor relationship and trust class, time, environment, input/output digests, passed procedure stages, and stop conditions to a bounded claim; observer independence is required only by assurance profiles that declare it."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/4/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/4/rejection_conditions/0","value":"A prose statement or tool request is accepted as event occurrence."}
{"node_type":"string","pointer":"/verification_items/4/rejection_conditions/1","value":"Authority is inferred from successful execution."}
{"node_type":"string","pointer":"/verification_items/4/rejection_conditions/2","value":"Unobserved stages are assumed to have passed."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/4/required_evidence"}
{"node_type":"string","pointer":"/verification_items/4/required_evidence/0","value":"Versioned action-evidence envelope."}
{"node_type":"string","pointer":"/verification_items/4/required_evidence/1","value":"Runtime observation adapter and adversarial fixtures."}
{"node_type":"string","pointer":"/verification_items/4/required_evidence/2","value":"Authority and observer trust model."}
{"node_type":"string","pointer":"/verification_items/4/required_evidence/3","value":"Replay and digest-mismatch cases."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/residual_risks"}
{"node_type":"string","pointer":"/verification_items/4/residual_risks/0","value":"A future signed event can still carry semantically wrong action metadata."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/4/reverification"}
{"node_type":"string","pointer":"/verification_items/4/reverification/last_evaluated_at","value":"2026-07-16T08:30:40+09:00"}
{"item_count":0,"node_type":"array","pointer":"/verification_items/4/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/4/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/4/reverification/triggers/0","value":"Action envelope, runtime, observer, authority, tool, or environment contract changes."}
{"node_type":"null","pointer":"/verification_items/4/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/4/scope","value":"Actual AI-agent tool calls and external or local actions, not descriptions extracted from prose."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/4/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/4/state_profile_ref/entity_id","value":"state.missing-refuted"}
{"node_type":"string","pointer":"/verification_items/4/state_profile_ref/label_hint","value":"必要機構欠落により非充足"}
{"node_type":"string","pointer":"/verification_items/4/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/4/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/4/unproven_scope/0","value":"Action occurrence, actor identity, runtime authority, observer relationship and trust, profile-required observer independence, passed procedure stages, and stop-condition compliance."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/4/validation_method"}
{"node_type":"string","pointer":"/verification_items/4/validation_method/environment","value":"Future instrumented agent runtime and independent review."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/4/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/4/validation_method/method_types/0","value":"operational_observation"}
{"node_type":"string","pointer":"/verification_items/4/validation_method/method_types/1","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/4/validation_method/population_or_context","value":"Actions whose occurrence, authority, and procedure matter to completion or risk acceptance."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/4/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/4/verification_method"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/environment","value":"A local action-evidence/v1 sidecar contract and adversarial fixtures exist. They replay declared occurrence, actor, authority, procedure, provenance, authenticity, and causality claims separately, but no instrumented runtime, external identity, signature verifier, trusted time, or external ledger is bound."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/4/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/population_or_context","value":"Representative local and external agent actions."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/4/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/procedure_refs/0","value":"schemas/action-assurance-profile.schema.json"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/procedure_refs/1","value":"schemas/action-evidence.schema.json"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/procedure_refs/2","value":"src/semantic_guard/action_evidence.py"}
{"node_type":"string","pointer":"/verification_items/4/verification_method/procedure_refs/3","value":"tests/test_action_evidence.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/5"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/5/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/5/acceptance_criteria/0","value":"Original evidence and subject artifact digests are rechecked."}
{"node_type":"string","pointer":"/verification_items/5/acceptance_criteria/1","value":"Trust root and provenance mechanism are explicit."}
{"node_type":"string","pointer":"/verification_items/5/acceptance_criteria/2","value":"Authenticity and causality remain separate claims."}
{"node_type":"string","pointer":"/verification_items/5/acceptance_criteria/3","value":"Replay, substitution, and digest mismatch are detected."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/assumptions"}
{"node_type":"string","pointer":"/verification_items/5/assumptions/0","value":"Current digest checks establish bounded content consistency, not authenticity."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/5/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/5/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/5/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/5/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/5/authority_boundary/source_may/0","value":"Check declared provenance and expose unproven elevated claims."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/5/authority_boundary/source_must_not/0","value":"Issue identities, signatures, trusted time, or final authenticity judgments without mechanisms."}
{"item_count":5,"node_type":"array","pointer":"/verification_items/5/claim_classes"}
{"node_type":"string","pointer":"/verification_items/5/claim_classes/0","value":"artifact_generation"}
{"node_type":"string","pointer":"/verification_items/5/claim_classes/1","value":"artifact_provenance"}
{"node_type":"string","pointer":"/verification_items/5/claim_classes/2","value":"verification_result"}
{"node_type":"string","pointer":"/verification_items/5/claim_classes/3","value":"authenticity"}
{"node_type":"string","pointer":"/verification_items/5/claim_classes/4","value":"causality"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/counterconditions"}
{"node_type":"string","pointer":"/verification_items/5/counterconditions/0","value":"Only local content equality is claimed and the subject bytes are directly available."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/5/counterevidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/5/counterevidence_refs/0/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/verification_items/5/counterevidence_refs/0/label_hint","value":"真正性・因果機構の欠落観測"}
{"node_type":"string","pointer":"/verification_items/5/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/5/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/5/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/5/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/5/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/5/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/5/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/5/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/5/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/5/evidence_refs/1/entity_id","value":"evidence.full-evaluation.2026-07-11"}
{"node_type":"string","pointer":"/verification_items/5/evidence_refs/1/label_hint","value":"全体監査の歴史的観測"}
{"node_type":"string","pointer":"/verification_items/5/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/5/failure_consequence","value":"The system can produce cryptographically strong evidence for the wrong artifact, wrong input, wrong actor, or wrong causal claim."}
{"node_type":"string","pointer":"/verification_items/5/item_kind","value":"action_assurance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/5/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/applicability","value":"Claims of artifact generation, provenance, authenticity, verification result, or causality."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/counterconditions/0","value":"The claim is explicitly limited to local content equality or schema validity."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/limitations/0","value":"No trust root, signature, transparency record, or causal model is selected."}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/locator","value":"Meaning Of Correctness And Bounded Proof"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/5/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/5/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/5/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/5/label","value":"OR-02 成果物来歴・真正性・因果境界"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/5/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/5/lifecycle_surfaces/0","value":"action"}
{"node_type":"string","pointer":"/verification_items/5/lifecycle_surfaces/1","value":"diff"}
{"node_type":"string","pointer":"/verification_items/5/lifecycle_surfaces/2","value":"verification"}
{"node_type":"string","pointer":"/verification_items/5/lifecycle_surfaces/3","value":"completion_claim"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/5/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/5/origin_requirement_refs/0/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/5/origin_requirement_refs/0/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/5/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/5/proposition","value":"A claimed artifact and verification result can be bound to the observed action, input and output digests, environment, original evidence, provenance mechanism, and declared trust root without inferring authenticity or causality from content alone."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/5/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/5/rejection_conditions/0","value":"A digest alone is treated as authenticity."}
{"node_type":"string","pointer":"/verification_items/5/rejection_conditions/1","value":"A signed claim is treated as semantically correct."}
{"node_type":"string","pointer":"/verification_items/5/rejection_conditions/2","value":"Temporal sequence is treated as causality without a declared model."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/5/required_evidence"}
{"node_type":"string","pointer":"/verification_items/5/required_evidence/0","value":"Artifact evidence reader."}
{"node_type":"string","pointer":"/verification_items/5/required_evidence/1","value":"Signed or append-only provenance mechanism where elevated claims are needed."}
{"node_type":"string","pointer":"/verification_items/5/required_evidence/2","value":"Replay, substitution, and semantic-mismatch adversarial tests."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/residual_risks"}
{"node_type":"string","pointer":"/verification_items/5/residual_risks/0","value":"Semantic extraction error may be preserved by a strong provenance mechanism."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/5/reverification"}
{"node_type":"string","pointer":"/verification_items/5/reverification/last_evaluated_at","value":"2026-07-16T08:30:40+09:00"}
{"item_count":0,"node_type":"array","pointer":"/verification_items/5/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/5/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/5/reverification/triggers/0","value":"Provenance, signature, artifact reader, trust-root, or causal model changes."}
{"node_type":"null","pointer":"/verification_items/5/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/5/scope","value":"Artifacts and verification outputs used to support agent completion claims."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/5/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/5/state_profile_ref/entity_id","value":"state.missing-refuted"}
{"node_type":"string","pointer":"/verification_items/5/state_profile_ref/label_hint","value":"必要機構欠落により非充足"}
{"node_type":"string","pointer":"/verification_items/5/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/5/unproven_scope/0","value":"Trusted time, actor identity, original-evidence authenticity, artifact generation event, and causality."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/5/validation_method"}
{"node_type":"string","pointer":"/verification_items/5/validation_method/environment","value":"Future trusted provenance and independent evidence-reader environment."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/5/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/5/validation_method/method_types/0","value":"operational_observation"}
{"node_type":"string","pointer":"/verification_items/5/validation_method/method_types/1","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/5/validation_method/population_or_context","value":"Artifacts used for real completion and acceptance decisions."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/5/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/5/verification_method"}
{"node_type":"string","pointer":"/verification_items/5/verification_method/environment","value":"Current digest and provenance field checks only."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/5/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/5/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/5/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/5/verification_method/population_or_context","value":"Public audit records and claimed external artifacts."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/5/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/5/verification_method/procedure_refs/0","value":"src/semantic_guard/public_contract.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/6"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/6/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/6/acceptance_criteria/0","value":"A finding maps to a bounded repair target and can be re-audited."}
{"node_type":"string","pointer":"/verification_items/6/acceptance_criteria/1","value":"Repair success, regression, escalation correctness, and unresolved remainder are measured separately."}
{"node_type":"string","pointer":"/verification_items/6/acceptance_criteria/2","value":"The caller or control plane owns execution and sequencing."}
{"node_type":"string","pointer":"/verification_items/6/acceptance_criteria/3","value":"Human review can understand and contest the repair material."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/assumptions"}
{"node_type":"string","pointer":"/verification_items/6/assumptions/0","value":"Repair effectiveness must be measured on the downstream work, not inferred from finding count."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/6/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/6/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/6/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/6/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/6/authority_boundary/source_may/0","value":"Emit bounded repair material and re-audit revised artifacts."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/6/authority_boundary/source_must_not/0","value":"Own work priority, delegation, execution, or acceptance."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/claim_classes"}
{"node_type":"string","pointer":"/verification_items/6/claim_classes/0","value":"repair_effect"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/counterconditions"}
{"node_type":"string","pointer":"/verification_items/6/counterconditions/0","value":"The output is explicitly research material with no repair-effect claim."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/6/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/6/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/6/entity_id","value":"verification.or03.repair-effect"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/6/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/6/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/6/evidence_refs/0/entity_id","value":"evidence.constitution.snapshot.2026-08-24"}
{"node_type":"string","pointer":"/verification_items/6/evidence_refs/0/label_hint","value":"v1 憲法 snapshot"}
{"node_type":"string","pointer":"/verification_items/6/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/6/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/6/evidence_refs/1/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/6/evidence_refs/1/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/6/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/6/failure_consequence","value":"The system can generate detailed reports that never improve work or human decisions, satisfying document production while failing its practical purpose."}
{"node_type":"string","pointer":"/verification_items/6/item_kind","value":"repair_effect"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/6/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/applicability","value":"Audit results intended for agent revision or human review."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/counterconditions/0","value":"An audit is explicitly exploratory and no revision outcome is claimed."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/limitations/0","value":"The origin requirement does not define one repair interface or performance threshold."}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/locator","value":"OR-03 and Hollow Success Conditions"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/6/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/6/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/6/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/6/label","value":"OR-03 修正循環の有効性"}
{"item_count":5,"node_type":"array","pointer":"/verification_items/6/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/6/lifecycle_surfaces/0","value":"plan"}
{"node_type":"string","pointer":"/verification_items/6/lifecycle_surfaces/1","value":"action"}
{"node_type":"string","pointer":"/verification_items/6/lifecycle_surfaces/2","value":"diff"}
{"node_type":"string","pointer":"/verification_items/6/lifecycle_surfaces/3","value":"verification"}
{"node_type":"string","pointer":"/verification_items/6/lifecycle_surfaces/4","value":"completion_claim"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/6/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/6/origin_requirement_refs/0/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/6/origin_requirement_refs/0/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/6/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/6/proposition","value":"Audit findings can be consumed by a coding agent to produce a more correct replan, reimplementation, change explanation, verification, or completion report, and the change in outcome can be measured without allowing semantic-guard to own the work."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/6/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/6/rejection_conditions/0","value":"The report has no machine-consumable repair target."}
{"node_type":"string","pointer":"/verification_items/6/rejection_conditions/1","value":"A changed output is counted as improvement without re-audit."}
{"node_type":"string","pointer":"/verification_items/6/rejection_conditions/2","value":"semantic-guard automatically executes or accepts the repair."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/6/required_evidence"}
{"node_type":"string","pointer":"/verification_items/6/required_evidence/0","value":"Versioned finding-to-repair mapping."}
{"node_type":"string","pointer":"/verification_items/6/required_evidence/1","value":"Before/after cases with independent review."}
{"node_type":"string","pointer":"/verification_items/6/required_evidence/2","value":"Regression and escalation evidence."}
{"node_type":"string","pointer":"/verification_items/6/required_evidence/3","value":"Human comprehension and contestability observations."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/residual_risks"}
{"node_type":"string","pointer":"/verification_items/6/residual_risks/0","value":"Agents may optimize wording to silence findings without fixing the underlying defect."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/6/reverification"}
{"node_type":"null","pointer":"/verification_items/6/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/6/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/6/reverification/status","value":"not_defined"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/6/reverification/triggers/0","value":"Finding schema, repair mapping, agent workflow, or acceptance process changes."}
{"node_type":"null","pointer":"/verification_items/6/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/6/scope","value":"The feedback path from audit output to subsequent agent revision and re-audit."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/6/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/6/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/6/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/6/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/6/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/6/unproven_scope/0","value":"Agent repair success, regression rate, handoff usability, correct escalation, and human comprehension."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/6/validation_method"}
{"node_type":"string","pointer":"/verification_items/6/validation_method/environment","value":"Future controlled before/after agent revision study."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/6/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/6/validation_method/method_types/0","value":"operational_observation"}
{"node_type":"string","pointer":"/verification_items/6/validation_method/method_types/1","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/6/validation_method/population_or_context","value":"Real coding-agent work with preserved human acceptance."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/6/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/6/verification_method"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/environment","value":"A local responsibility-policy/v2 and repair-cycle/v2 sidecar contract replays typed post-change audit, regression, effect transition, and independent-review records. It is not connected to a real coding-agent workflow and has no field evidence of repair effectiveness or human comprehension."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/6/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/method_types/0","value":"test"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/method_types/1","value":"demonstration"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/population_or_context","value":"Representative agent plans, changes, verification reports, and completion claims."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/6/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/procedure_refs/0","value":"schemas/responsibility-policy.schema.json"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/procedure_refs/1","value":"schemas/repair-cycle.schema.json"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/procedure_refs/2","value":"src/semantic_guard/repair_loop.py"}
{"node_type":"string","pointer":"/verification_items/6/verification_method/procedure_refs/3","value":"tests/test_repair_loop.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/7"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/7/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/7/acceptance_criteria/0","value":"Technical states and human acceptance are separate fields."}
{"node_type":"string","pointer":"/verification_items/7/acceptance_criteria/1","value":"Pending acceptance cannot acquire a decision record or decided_at value."}
{"node_type":"string","pointer":"/verification_items/7/acceptance_criteria/2","value":"Risk acceptance does not mutate audit facts."}
{"node_type":"string","pointer":"/verification_items/7/acceptance_criteria/3","value":"Final acceptance remains human-owned in documentation and runtime contracts."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/assumptions"}
{"node_type":"string","pointer":"/verification_items/7/assumptions/0","value":"The human decision is recorded outside semantic-guard or supplied by an authorized caller."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/7/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/7/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/7/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/7/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/7/authority_boundary/source_may/0","value":"Expose decision material and required authority class."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/7/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/7/authority_boundary/source_must_not/0","value":"Fill or infer a final human decision."}
{"node_type":"string","pointer":"/verification_items/7/authority_boundary/source_must_not/1","value":"Erase audit facts after risk acceptance."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/claim_classes"}
{"node_type":"string","pointer":"/verification_items/7/claim_classes/0","value":"human_decision_boundary"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/counterconditions"}
{"node_type":"string","pointer":"/verification_items/7/counterconditions/0","value":"No final human decision is being represented."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/7/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/7/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/7/entity_id","value":"verification.or03.human-decision-boundary"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/7/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/7/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/7/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/1/entity_id","value":"evidence.constitution.snapshot.2026-08-24"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/1/label_hint","value":"v1 憲法 snapshot"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/7/evidence_refs/2"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/2/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/2/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/7/evidence_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/7/failure_consequence","value":"Technical pass or a reviewer recommendation can silently replace the human value and residual-risk decision."}
{"node_type":"string","pointer":"/verification_items/7/item_kind","value":"human_decision_boundary"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/7/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/applicability","value":"All audit, verification, validation, and acceptance projections."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/counterconditions/0","value":"A human has supplied an explicit decision record with basis and time."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/limitations/0","value":"The current repository does not own a durable human-decision ledger."}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/locator","value":"decision_boundary and change_control.final_adoption_status"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/7/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/source_ref/entity_id","value":"constitution.semantic-guard.r0"}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/source_ref/label_hint","value":"v1 基幹憲法"}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/7/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/7/knowledge_basis/0/version","value":"0.2.0-draft"}
{"node_type":"string","pointer":"/verification_items/7/label","value":"OR-03 人間判断境界"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/7/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/7/lifecycle_surfaces/0","value":"decision_state"}
{"node_type":"string","pointer":"/verification_items/7/lifecycle_surfaces/1","value":"verification"}
{"node_type":"string","pointer":"/verification_items/7/lifecycle_surfaces/2","value":"completion_claim"}
{"node_type":"string","pointer":"/verification_items/7/lifecycle_surfaces/3","value":"cross_cutting"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/7/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/7/origin_requirement_refs/0/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/7/origin_requirement_refs/0/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/7/origin_requirement_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/7/proposition","value":"Audit and verification states remain decision material and cannot be projected as human accept, request_revision, or defer without a human-owned decision record."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/7/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/7/rejection_conditions/0","value":"Workflow pass is described as human acceptance."}
{"node_type":"string","pointer":"/verification_items/7/rejection_conditions/1","value":"An automated reviewer fills a final human decision."}
{"node_type":"string","pointer":"/verification_items/7/rejection_conditions/2","value":"Human risk acceptance deletes findings or unproven scope."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/7/required_evidence"}
{"node_type":"string","pointer":"/verification_items/7/required_evidence/0","value":"Schema negative cases."}
{"node_type":"string","pointer":"/verification_items/7/required_evidence/1","value":"Aggregation and projection tests."}
{"node_type":"string","pointer":"/verification_items/7/required_evidence/2","value":"Human acceptance-review observation before cutover."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/residual_risks"}
{"node_type":"string","pointer":"/verification_items/7/residual_risks/0","value":"External callers can still mislabel pass as acceptance outside the contract."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/7/reverification"}
{"node_type":"string","pointer":"/verification_items/7/reverification/last_evaluated_at","value":"2026-08-27T15:43:40+09:00"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/7/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/7/reverification/procedure_refs/0","value":"tests/test_models_and_aggregation.py"}
{"node_type":"string","pointer":"/verification_items/7/reverification/procedure_refs/1","value":"tests/test_public_contract.py"}
{"node_type":"string","pointer":"/verification_items/7/reverification/status","value":"defined"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/7/reverification/triggers/0","value":"Decision schema, workflow projection, acceptance documentation, or ownership changes."}
{"node_type":"null","pointer":"/verification_items/7/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/7/scope","value":"v1 schemas, aggregation, public projection, documentation, and this verification source."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/7/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/7/state_profile_ref/entity_id","value":"state.boundary-verified"}
{"node_type":"string","pointer":"/verification_items/7/state_profile_ref/label_hint","value":"境界局所検証済み"}
{"node_type":"string","pointer":"/verification_items/7/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/7/unproven_scope/0","value":"Usability and completeness of a future human acceptance record."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/7/validation_method"}
{"node_type":"string","pointer":"/verification_items/7/validation_method/environment","value":"Future acceptance-review use."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/7/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/7/validation_method/method_types/0","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/7/validation_method/population_or_context","value":"Human accept, request_revision, and defer decisions."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/7/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/7/verification_method"}
{"node_type":"string","pointer":"/verification_items/7/verification_method/environment","value":"Schema and aggregation tests plus source inspection."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/7/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/7/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/7/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/7/verification_method/population_or_context","value":"Audit results and this verification source."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/7/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/7/verification_method/procedure_refs/0","value":"schemas/audit-result.schema.json"}
{"node_type":"string","pointer":"/verification_items/7/verification_method/procedure_refs/1","value":"src/semantic_guard/aggregation.py"}
{"node_type":"string","pointer":"/verification_items/7/verification_method/procedure_refs/2","value":"src/semantic_guard/public_contract.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/8"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/8/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/8/acceptance_criteria/0","value":"Target population, estimand, sampling frame, holdout policy, error cost, thresholds, and uncertainty are declared."}
{"node_type":"string","pointer":"/verification_items/8/acceptance_criteria/1","value":"Independent double review and adjudication preserve disagreement."}
{"node_type":"string","pointer":"/verification_items/8/acceptance_criteria/2","value":"Performance is reported by domain, artifact type, relation type, linguistic phenomenon, and analyzer route."}
{"node_type":"string","pointer":"/verification_items/8/acceptance_criteria/3","value":"Repair and human-decision outcomes are measured separately from detector accuracy."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/assumptions"}
{"node_type":"string","pointer":"/verification_items/8/assumptions/0","value":"Field performance varies by profile, domain, artifact type, and cost policy."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/8/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/8/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/8/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/8/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/8/authority_boundary/source_may/0","value":"Record field-validation evidence, limitations, and uncertainty."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/8/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/8/authority_boundary/source_must_not/0","value":"Choose acceptable risk or cut over the default route."}
{"node_type":"string","pointer":"/verification_items/8/authority_boundary/source_must_not/1","value":"Collapse domain-specific results into unconditional readiness."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/8/claim_classes"}
{"node_type":"string","pointer":"/verification_items/8/claim_classes/0","value":"validation_result"}
{"node_type":"string","pointer":"/verification_items/8/claim_classes/1","value":"discovery_effectiveness"}
{"node_type":"string","pointer":"/verification_items/8/claim_classes/2","value":"repair_effect"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/counterconditions"}
{"node_type":"string","pointer":"/verification_items/8/counterconditions/0","value":"Only a named deterministic fixture claim is made."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/8/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/8/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/8/entity_id","value":"verification.cross.field-validation"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/8/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/8/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/8/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/8/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/8/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/8/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/8/evidence_refs/1/entity_id","value":"evidence.real-nlp-smoke.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/8/evidence_refs/1/label_hint","value":"実解析器煙試験"}
{"node_type":"string","pointer":"/verification_items/8/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/8/failure_consequence","value":"Local conformance and smoke results can be mistaken for practical reliability and value."}
{"node_type":"string","pointer":"/verification_items/8/item_kind","value":"field_validation"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/8/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/applicability","value":"Claims of field performance, practical readiness, or default-route safety."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/counterconditions/0","value":"A claim is explicitly limited to deterministic regression behavior on named fixtures."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/limitations/0","value":"Target population, sampling frame, thresholds, and uncertainty method are not yet fixed."}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/locator","value":"evaluation_contract"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/8/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/source_ref/entity_id","value":"constitution.semantic-guard.r0"}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/source_ref/label_hint","value":"v1 基幹憲法"}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/8/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/8/knowledge_basis/0/version","value":"0.2.0-draft"}
{"node_type":"string","pointer":"/verification_items/8/label","value":"実務資料上の妥当性確認"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/8/lifecycle_surfaces/0","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/8/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/8/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/8/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/8/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/8/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/8/proposition","value":"For a declared target population and intended use, the system's detection quality, abstention, evidence usefulness, repair effect, and human decision support are measured with uncertainty and independent labeling."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/8/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/8/rejection_conditions/0","value":"Artificial fixture pass is called field validation."}
{"node_type":"string","pointer":"/verification_items/8/rejection_conditions/1","value":"One aggregate score hides catastrophic false satisfaction or abstention."}
{"node_type":"string","pointer":"/verification_items/8/rejection_conditions/2","value":"Labels are produced only by the implementation authors without independent review."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/8/required_evidence"}
{"node_type":"string","pointer":"/verification_items/8/required_evidence/0","value":"Domain-stratified corpus."}
{"node_type":"string","pointer":"/verification_items/8/required_evidence/1","value":"Labeling guide, independent reviewers, disagreement, and adjudication."}
{"node_type":"string","pointer":"/verification_items/8/required_evidence/2","value":"Cost matrix, thresholds, uncertainty, and holdout isolation."}
{"node_type":"string","pointer":"/verification_items/8/required_evidence/3","value":"Operational shadow observations and repair/human outcomes."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/residual_risks"}
{"node_type":"string","pointer":"/verification_items/8/residual_risks/0","value":"A benchmark can become a tuning target and cease to represent unseen work."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/8/reverification"}
{"node_type":"null","pointer":"/verification_items/8/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/8/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/8/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/8/reverification/triggers/0","value":"Profile, rule, analyzer, model, corpus, target population, cost matrix, or use context changes."}
{"node_type":"null","pointer":"/verification_items/8/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/8/scope","value":"Every lifecycle profile before practical acceptance or default-route cutover."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/8/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/8/state_profile_ref/entity_id","value":"state.field-not-evaluated"}
{"node_type":"string","pointer":"/verification_items/8/state_profile_ref/label_hint","value":"評価設計のみ・実務未評価"}
{"node_type":"string","pointer":"/verification_items/8/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/8/unproven_scope/0","value":"Target population, generalization, confidence bounds, reviewer agreement, user comprehension, repair success, and operational value."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/8/validation_method"}
{"node_type":"string","pointer":"/verification_items/8/validation_method/environment","value":"Future domain-stratified shadow operation."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/8/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/8/validation_method/method_types/0","value":"operational_observation"}
{"node_type":"string","pointer":"/verification_items/8/validation_method/method_types/1","value":"human_evaluation"}
{"node_type":"string","pointer":"/verification_items/8/validation_method/method_types/2","value":"analysis"}
{"node_type":"string","pointer":"/verification_items/8/validation_method/population_or_context","value":"Not yet defined target populations for each lifecycle profile."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/8/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/8/verification_method"}
{"node_type":"string","pointer":"/verification_items/8/verification_method/environment","value":"Inspection of current evidence limitations."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/8/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/8/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/8/verification_method/population_or_context","value":"Existing fixtures and smoke cases only."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/8/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/8/verification_method/procedure_refs/0","value":"validation/integrated-verification-2026-07-16.json"}
{"node_type":"string","pointer":"/verification_items/8/verification_method/procedure_refs/1","value":"validation/real-nlp-smoke-2026-07-16.json"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/9"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/9/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/9/acceptance_criteria/0","value":"Every provider route declares data classes, allowed egress, authority or consent, minimization, redaction, retention, deletion, and audit logging boundaries."}
{"node_type":"string","pointer":"/verification_items/9/acceptance_criteria/1","value":"Secrets and personal or confidential data fail closed before external transmission unless explicitly authorized by policy."}
{"node_type":"string","pointer":"/verification_items/9/acceptance_criteria/2","value":"Prompt injection, malicious artifacts, resource substitution, dependency or model provenance, least privilege, denial of service, and incident recovery have profile-specific controls and tests."}
{"node_type":"string","pointer":"/verification_items/9/acceptance_criteria/3","value":"Security and privacy observations remain separate from semantic correctness, action authenticity, and human risk acceptance."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/assumptions"}
{"node_type":"string","pointer":"/verification_items/9/assumptions/0","value":"Real-work deployment may include protected source artifacts, external providers, privileged tool calls, or durable evidence."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/9/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/9/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/9/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/9/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/9/authority_boundary/source_may/0","value":"Before adoption, expose the candidate criterion, decision branches, and missing boundary evidence; after adoption, expose missing controls, observations, and unproven boundaries."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/9/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/9/authority_boundary/source_must_not/0","value":"Grant data egress or tool authority."}
{"node_type":"string","pointer":"/verification_items/9/authority_boundary/source_must_not/1","value":"Choose acceptable security or privacy risk."}
{"node_type":"string","pointer":"/verification_items/9/authority_boundary/source_must_not/2","value":"Present itself as a general vulnerability scanner or compliance certifier."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/9/claim_classes"}
{"node_type":"string","pointer":"/verification_items/9/claim_classes/0","value":"secure_operation"}
{"node_type":"string","pointer":"/verification_items/9/claim_classes/1","value":"authority"}
{"node_type":"string","pointer":"/verification_items/9/claim_classes/2","value":"procedure_conformance"}
{"node_type":"string","pointer":"/verification_items/9/claim_classes/3","value":"operational_readiness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/counterconditions"}
{"node_type":"string","pointer":"/verification_items/9/counterconditions/0","value":"A versioned human-approved non-applicability record and repository-local inspection evidence close the profile to synthetic public data, local-only analysis, no external provider, no privileged action, and no durable operation, and name the changes that reactivate this criterion."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/9/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/9/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/9/entity_id","value":"verification.cross.secure-and-responsible-operation"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/9/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/9/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/9/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/9/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/9/evidence_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/9/evidence_refs/1"}
{"node_type":"string","pointer":"/verification_items/9/evidence_refs/1/entity_id","value":"evidence.constitution.snapshot.2026-08-24"}
{"node_type":"string","pointer":"/verification_items/9/evidence_refs/1/label_hint","value":"v1 憲法 snapshot"}
{"node_type":"string","pointer":"/verification_items/9/evidence_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/9/failure_consequence","value":"A semantically careful audit can still disclose protected material, trust poisoned inputs or resources, exceed granted authority, or preserve unsafe evidence while appearing suitable for real work."}
{"node_type":"string","pointer":"/verification_items/9/item_kind","value":"secure_operation"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/9/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/adoption_status","value":"candidate"}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/applicability","value":"Any use with non-public artifacts, external providers, privileged actions, third-party resources, or durable evidence."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/counterconditions/0","value":"A closed local demonstration uses only synthetic public data, no external provider, no privilege, and no durable operational claim."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/limitations/0","value":"The origin requirement implies danger, authority, input, evidence, and trust handling but does not separately enumerate a security or privacy profile; adoption and acceptable controls remain a human decision."}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/locator","value":"OR-01 dangers and OR-02 authority, inputs, outputs, evidence, and trust conditions"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/9/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/9/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/9/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/9/label","value":"安全・責任ある情報取扱いと外部境界"}
{"item_count":5,"node_type":"array","pointer":"/verification_items/9/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/9/lifecycle_surfaces/0","value":"request"}
{"node_type":"string","pointer":"/verification_items/9/lifecycle_surfaces/1","value":"action"}
{"node_type":"string","pointer":"/verification_items/9/lifecycle_surfaces/2","value":"verification"}
{"node_type":"string","pointer":"/verification_items/9/lifecycle_surfaces/3","value":"completion_claim"}
{"node_type":"string","pointer":"/verification_items/9/lifecycle_surfaces/4","value":"cross_cutting"}
{"item_count":2,"node_type":"array","pointer":"/verification_items/9/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/9/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/9/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/9/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/9/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/9/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/9/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/9/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/9/origin_requirement_refs/1/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/9/proposition","value":"The audit path handles source artifacts, external analyzers or LLMs, dependencies, privileges, and incident evidence under explicit data classification, authority or consent, minimization, secret and personal-data controls, egress and retention rules, adversarial-input boundaries, resource provenance, least privilege, and fail-closed recovery."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/9/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/9/rejection_conditions/0","value":"An external LLM or analyzer can receive source material without a declared data and authority policy."}
{"node_type":"string","pointer":"/verification_items/9/rejection_conditions/1","value":"Logs or evidence records retain secrets or personal data without minimization and lifecycle controls."}
{"node_type":"string","pointer":"/verification_items/9/rejection_conditions/2","value":"A dependency, model, dictionary, rule pack, or input artifact is trusted only because it is present or parseable."}
{"node_type":"string","pointer":"/verification_items/9/rejection_conditions/3","value":"A local security check is presented as general secure-operation readiness."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/9/required_evidence"}
{"node_type":"string","pointer":"/verification_items/9/required_evidence/0","value":"Human-approved intended-use, data-classification, egress, retention, and incident policy."}
{"node_type":"string","pointer":"/verification_items/9/required_evidence/1","value":"Versioned data-flow and threat model with provider, privilege, resource, and evidence-store boundaries."}
{"node_type":"string","pointer":"/verification_items/9/required_evidence/2","value":"Adversarial tests for injection, exfiltration, substitution, privilege misuse, resource exhaustion, and recovery."}
{"node_type":"string","pointer":"/verification_items/9/required_evidence/3","value":"Independent review appropriate to the selected deployment risk."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/residual_risks"}
{"node_type":"string","pointer":"/verification_items/9/residual_risks/0","value":"Even an accepted control profile cannot eliminate provider compromise, malicious dependencies, insider misuse, or semantic leakage through allowed outputs."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/9/reverification"}
{"node_type":"null","pointer":"/verification_items/9/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/9/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/9/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/9/reverification/triggers/0","value":"Intended use, data class, provider, model, dependency, privilege, evidence store, retention, incident policy, or deployment boundary changes."}
{"node_type":"null","pointer":"/verification_items/9/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/9/scope","value":"semantic-guard inputs, local and external providers, LLM candidate exchange, evidence records, dependencies, model and dictionary resources, logs, and operational incidents; this is safe operation of the audit system, not a claim that it is a general security scanner."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/9/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/9/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/9/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/9/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/9/unproven_scope/0","value":"Data classification, consent or authority, provider egress, minimization, secret and personal-data controls, retention and deletion, prompt-injection resistance, dependency and model provenance, least privilege, incident response, and independent review."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/9/validation_method"}
{"node_type":"string","pointer":"/verification_items/9/validation_method/environment","value":"Not defined pending intended-use, data, threat, and incident policy."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/9/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/9/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/9/validation_method/population_or_context","value":"Real organizations, repositories, providers, and evidence stores selected by the human owner."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/9/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/9/verification_method"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/environment","value":"A local secure-operation/v1 sidecar checks the internal consistency of declared route, scope, retention, deletion, latest adoption or retirement, restart, evidence-kind, inventory, and resource-limit records. No accepted deployment profile, external authenticity, trusted time, independent operational observation, or end-to-end qualification evidence exists."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/9/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/population_or_context","value":"Candidate deployment profiles involving real source artifacts or external providers."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/9/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/procedure_refs/0","value":"schemas/secure-operation.schema.json"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/procedure_refs/1","value":"src/semantic_guard/secure_operation.py"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/procedure_refs/2","value":"tests/test_secure_operation.py"}
{"node_type":"string","pointer":"/verification_items/9/verification_method/procedure_refs/3","value":"docs/secure-operation-boundary.md"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/10"}
{"item_count":4,"node_type":"array","pointer":"/verification_items/10/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/10/acceptance_criteria/0","value":"Every evidence observation identifies subject snapshot, environment, versions, time, and limitations."}
{"node_type":"string","pointer":"/verification_items/10/acceptance_criteria/1","value":"Invalidation triggers and rerun procedure are defined for each critical item."}
{"node_type":"string","pointer":"/verification_items/10/acceptance_criteria/2","value":"Stale or unbound evidence cannot support current readiness."}
{"node_type":"string","pointer":"/verification_items/10/acceptance_criteria/3","value":"Load, concurrency, failure recovery, compatibility, and rollback thresholds exist before release."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/assumptions"}
{"node_type":"string","pointer":"/verification_items/10/assumptions/0","value":"Current evidence paths and digests remain locally available."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/10/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/10/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/10/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/10/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/10/authority_boundary/source_may/0","value":"Mark evidence stale, unbound, failed, or due for recheck."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/10/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/10/authority_boundary/source_must_not/0","value":"Schedule deployment or accept operational risk."}
{"node_type":"string","pointer":"/verification_items/10/authority_boundary/source_must_not/1","value":"Infer readiness from freshness alone."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/10/claim_classes"}
{"node_type":"string","pointer":"/verification_items/10/claim_classes/0","value":"operational_readiness"}
{"node_type":"string","pointer":"/verification_items/10/claim_classes/1","value":"verification_result"}
{"node_type":"string","pointer":"/verification_items/10/claim_classes/2","value":"validation_result"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/counterconditions"}
{"node_type":"string","pointer":"/verification_items/10/counterconditions/0","value":"A record is used only as a historical observation and makes no current-state claim."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/counterevidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/10/counterevidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/10/counterevidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/10/counterevidence_refs/0/label_hint","value":"試験対象 manifest と失効方針の欠落"}
{"node_type":"string","pointer":"/verification_items/10/counterevidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/10/criticality","value":"high"}
{"node_type":"string","pointer":"/verification_items/10/entity_id","value":"verification.cross.operational-reverification"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/10/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/10/evidence_refs/0/entity_id","value":"evidence.integrated-verification.2026-07-16"}
{"node_type":"string","pointer":"/verification_items/10/evidence_refs/0/label_hint","value":"統合検証観測"}
{"node_type":"string","pointer":"/verification_items/10/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/10/failure_consequence","value":"Stale evidence can silently support a changed system or changed use context."}
{"node_type":"string","pointer":"/verification_items/10/item_kind","value":"operational_readiness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/10/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/applicability","value":"Any evidence used beyond a one-time local observation."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/counterconditions/0","value":"A claim explicitly identifies itself as a historical observation only."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/limitations/0","value":"No complete evidence expiry or requalification policy exists."}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/locator","value":"evaluation_contract and change_control"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/10/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/source_ref/entity_id","value":"constitution.semantic-guard.r0"}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/source_ref/label_hint","value":"v1 基幹憲法"}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/10/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/10/knowledge_basis/0/version","value":"0.2.0-draft"}
{"node_type":"string","pointer":"/verification_items/10/label","value":"運用・変更影響・再検証"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/10/lifecycle_surfaces/0","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/10/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/10/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/10/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/10/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/10/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/10/proposition","value":"Evidence remains bound to a subject snapshot and is invalidated or rechecked when rules, schemas, analyzers, models, resources, corpora, environments, or use contexts change."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/10/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/10/rejection_conditions/0","value":"A path or test name without execution observation is treated as current evidence."}
{"node_type":"string","pointer":"/verification_items/10/rejection_conditions/1","value":"A model, rule, dictionary, or use-context change leaves prior performance evidence current by default."}
{"node_type":"string","pointer":"/verification_items/10/rejection_conditions/2","value":"Release readiness is inferred from doctor or local unit tests alone."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/10/required_evidence"}
{"node_type":"string","pointer":"/verification_items/10/required_evidence/0","value":"Version and subject-bound evidence records."}
{"node_type":"string","pointer":"/verification_items/10/required_evidence/1","value":"Requalification and expiry policy."}
{"node_type":"string","pointer":"/verification_items/10/required_evidence/2","value":"Load, concurrency, resource exhaustion, recovery, compatibility, and cross-platform results."}
{"node_type":"string","pointer":"/verification_items/10/required_evidence/3","value":"Incident and drift feedback route."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/residual_risks"}
{"node_type":"string","pointer":"/verification_items/10/residual_risks/0","value":"A technically current snapshot may still be invalid for a changed target population or risk policy."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/10/reverification"}
{"node_type":"string","pointer":"/verification_items/10/reverification/last_evaluated_at","value":"2026-07-16T00:00:00+09:00"}
{"item_count":0,"node_type":"array","pointer":"/verification_items/10/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/10/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/10/reverification/triggers/0","value":"Rule, schema, model, analyzer, resource, dependency, OS, runtime, corpus, or use-context change."}
{"node_type":"null","pointer":"/verification_items/10/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/10/scope","value":"Verification evidence used for release, practical operation, or default-route decisions."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/10/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/10/state_profile_ref/entity_id","value":"state.partial-challenged"}
{"node_type":"string","pointer":"/verification_items/10/state_profile_ref/label_hint","value":"部分実装・反証材料あり"}
{"node_type":"string","pointer":"/verification_items/10/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/10/unproven_scope/0","value":"Evidence expiry policy, cross-platform operation, long-duration behavior, concurrency, denial of service, incident feedback, and rollback qualification."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/10/validation_method"}
{"node_type":"string","pointer":"/verification_items/10/validation_method/environment","value":"Future long-running, concurrent, cross-platform, and incident-feedback operation."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/10/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/10/validation_method/method_types/0","value":"operational_observation"}
{"node_type":"string","pointer":"/verification_items/10/validation_method/population_or_context","value":"Intended deployment profiles, not yet selected."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/10/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/10/verification_method"}
{"node_type":"string","pointer":"/verification_items/10/verification_method/environment","value":"Current local baseline and dependency lock checks."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/10/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/10/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/10/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/10/verification_method/population_or_context","value":"Repository assets, Python environments, package artifacts, and provider resources named in current evidence."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/10/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/10/verification_method/procedure_refs/0","value":"scripts/validate_verification_source.py"}
{"node_type":"string","pointer":"/verification_items/10/verification_method/procedure_refs/1","value":"docs/operations.md"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/11"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/11/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/11/acceptance_criteria/0","value":"An independent validator reconstructs the same outcome, finality, challenge, coverage, holds, evidence closure, and unproved scope from the embedded obligations and graph."}
{"node_type":"string","pointer":"/verification_items/11/acceptance_criteria/1","value":"Every required obligation has exactly one result and every typed reference resolves in an acyclic graph."}
{"node_type":"string","pointer":"/verification_items/11/acceptance_criteria/2","value":"Subject, proposition, rules, evidence, and aggregate state substitution fail closed, while v0 remains available until a separate migration decision."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/assumptions"}
{"node_type":"string","pointer":"/verification_items/11/assumptions/0","value":"The candidate charter remains the proposed bounded meaning; the local opt-in v1 implementation does not itself adopt the assurance or migration profile."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/11/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/11/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/11/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/11/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/11/authority_boundary/source_may/0","value":"Reject unreplayable or internally inconsistent assurance derivations and expose the exact failed obligation or edge."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/11/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/11/authority_boundary/source_must_not/0","value":"Treat graph closure as action occurrence, authenticity, formal proof, cutover authority, or human acceptance."}
{"node_type":"string","pointer":"/verification_items/11/authority_boundary/source_must_not/1","value":"Silently replace v0 or select an assurance profile for the human owner."}
{"item_count":8,"node_type":"array","pointer":"/verification_items/11/claim_classes"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/0","value":"description_completeness"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/1","value":"requirement_conformance"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/2","value":"action_occurrence"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/3","value":"authority"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/4","value":"artifact_provenance"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/5","value":"verification_result"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/6","value":"authenticity"}
{"node_type":"string","pointer":"/verification_items/11/claim_classes/7","value":"causality"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/counterconditions"}
{"node_type":"string","pointer":"/verification_items/11/counterconditions/0","value":"No public assurance claim or derived outcome is emitted."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/11/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/11/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/11/entity_id","value":"verification.or02.proof-obligation-and-assurance-graph-soundness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/11/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/11/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/11/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/11/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/11/failure_consequence","value":"A structurally valid public claim can change its subject, proposition, rules, evidence, authority, or aggregate state while appearing to retain the original bounded assurance."}
{"node_type":"string","pointer":"/verification_items/11/item_kind","value":"bounded_assurance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/11/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/adoption_status","value":"candidate"}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/applicability","value":"Every public requirement-audit assurance claim that represents a derived bounded outcome."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/counterconditions/0","value":"A record is explicitly non-assurance presentation material and cannot enter a public assurance aggregation."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/limitations/0","value":"The charter is a candidate implementation gate with human acceptance pending and is not evidence that the graph or validator exists or is sound."}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/locator","value":"Essential Realization, Target Acceptance Criteria, and Rejection And Hollow-Success Conditions"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/11/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-proof-obligation-assurance-graph-charter.v0"}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/source_ref/label_hint","value":"proof graph charter"}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/11/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/11/knowledge_basis/0/version","value":"proof-obligation-assurance-graph/v0"}
{"node_type":"string","pointer":"/verification_items/11/label","value":"OR-02 proof obligation・assurance graph 健全性"}
{"item_count":5,"node_type":"array","pointer":"/verification_items/11/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/11/lifecycle_surfaces/0","value":"requirement"}
{"node_type":"string","pointer":"/verification_items/11/lifecycle_surfaces/1","value":"action"}
{"node_type":"string","pointer":"/verification_items/11/lifecycle_surfaces/2","value":"verification"}
{"node_type":"string","pointer":"/verification_items/11/lifecycle_surfaces/3","value":"completion_claim"}
{"node_type":"string","pointer":"/verification_items/11/lifecycle_surfaces/4","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/11/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/11/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/11/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/11/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/11/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/11/proposition","value":"Every public assurance claim is independently replayable from one bound subject snapshot, a versioned claim profile and rule set, exactly the required proof-obligation results, located evidence, and an acyclic typed derivation graph, and rejects subject, proposition, rule, evidence, authority, or aggregate-state substitution, duplicate evidence accounting, cycles, and unfulfilled required obligations."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/11/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/11/rejection_conditions/0","value":"Schema-valid mutation can strengthen or redirect claim meaning without a validation failure."}
{"node_type":"string","pointer":"/verification_items/11/rejection_conditions/1","value":"Candidate parser or LLM material can close an obligation by agreement alone."}
{"node_type":"string","pointer":"/verification_items/11/rejection_conditions/2","value":"Graph closure is presented as action occurrence, evidence authenticity, or human acceptance."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/11/required_evidence"}
{"node_type":"string","pointer":"/verification_items/11/required_evidence/0","value":"Versioned proof-obligation and graph contract."}
{"node_type":"string","pointer":"/verification_items/11/required_evidence/1","value":"Independent reaggregation implementation and positive, mutation, cycle, duplicate-accounting, and unclosed-reference observations."}
{"node_type":"string","pointer":"/verification_items/11/required_evidence/2","value":"Independent review of subject, authority, evidence, and aggregation bypasses."}
{"node_type":"string","pointer":"/verification_items/11/required_evidence/3","value":"Human profile and migration decision record where adoption or default-output change is claimed."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/residual_risks"}
{"node_type":"string","pointer":"/verification_items/11/residual_risks/0","value":"A closed graph can still encode a semantically wrong rule or unauthentic observation unless normative governance, subject binding, and evidence trust are independently closed."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/11/reverification"}
{"node_type":"null","pointer":"/verification_items/11/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/11/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/11/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/11/reverification/triggers/0","value":"Claim profile, obligation taxonomy, graph contract, validator, aggregation rule, public schema, or migration policy changes."}
{"node_type":"null","pointer":"/verification_items/11/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/11/scope","value":"Requirement-audit assurance claims and their public validation path; graph closure does not itself prove that an external action occurred or that evidence is authentic."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/11/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/11/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/11/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/11/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/11/unproven_scope/0","value":"Runtime cross-field closure, v1 graph implementation, independent reaggregation, mutation resistance, profile adoption, migration behavior, and independent adversarial review."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/11/validation_method"}
{"node_type":"string","pointer":"/verification_items/11/validation_method/environment","value":"Not defined pending implementation, independent challenge, and human profile adoption."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/11/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/11/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/11/validation_method/population_or_context","value":"Agents and humans consuming bounded assurance claims in real development work."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/11/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/11/verification_method"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/environment","value":"A local opt-in assurance-claim/v1 proof-obligation graph, exact replay validator, v0 substitution checks, and adversarial fixtures exist. Their current executions are not registered as subject-bound evidence, and the assurance and migration profile is not human-adopted."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/11/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/population_or_context","value":"Positive, mutation, graph-closure, authority, evidence-substitution, and aggregation cases for public assurance claims."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/11/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/procedure_refs/0","value":"schemas/assurance-claim-v1.schema.json"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/procedure_refs/1","value":"src/semantic_guard/assurance_graph.py"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/procedure_refs/2","value":"tests/test_assurance_graph.py"}
{"node_type":"string","pointer":"/verification_items/11/verification_method/procedure_refs/3","value":"tests/test_public_contract.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/12"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/12/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/12/acceptance_criteria/0","value":"Every declared denominator entry has exactly one non-contradictory disposition and a resolvable source locator."}
{"node_type":"string","pointer":"/verification_items/12/acceptance_criteria/1","value":"Resolved and non-applicable dispositions require typed evidence or a versioned human decision with reactivation conditions."}
{"node_type":"string","pointer":"/verification_items/12/acceptance_criteria/2","value":"Control-plane handoff preserves audit-side uncertainty and the projection exposes every registered identity."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/assumptions"}
{"node_type":"string","pointer":"/verification_items/12/assumptions/0","value":"Completeness is bounded to a declared, versioned denominator."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/12/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/12/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/12/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/12/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/12/authority_boundary/source_may/0","value":"Reject missing, duplicate, contradictory, dangling, or unsupported dispositions within an accepted bounded denominator."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/12/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/12/authority_boundary/source_must_not/0","value":"Claim exhaustive discovery of unknown unknowns."}
{"node_type":"string","pointer":"/verification_items/12/authority_boundary/source_must_not/1","value":"Set work priority, accept non-applicability or residual risk, or erase uncertainty after handoff."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/12/claim_classes"}
{"node_type":"string","pointer":"/verification_items/12/claim_classes/0","value":"description_completeness"}
{"node_type":"string","pointer":"/verification_items/12/claim_classes/1","value":"requirement_conformance"}
{"node_type":"string","pointer":"/verification_items/12/claim_classes/2","value":"verification_result"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/counterconditions"}
{"node_type":"string","pointer":"/verification_items/12/counterconditions/0","value":"A claim is about unknown-unknown discovery rather than preservation of already declared gaps."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/12/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/12/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/12/entity_id","value":"verification.cross.register-completeness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/12/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/12/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/12/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/12/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/12/failure_consequence","value":"A known gap can disappear outside the canonical denominator and later completion material can look closed because the register validates only what it happened to retain."}
{"node_type":"string","pointer":"/verification_items/12/item_kind","value":"bounded_assurance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/12/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/adoption_status","value":"candidate"}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/applicability","value":"Every declared gap-bearing source covered by the accepted bounded register denominator."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/counterconditions/0","value":"A phenomenon has not been declared or observed and is therefore an unknown unknown rather than a known register omission."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/limitations/0","value":"The candidate denominator and non-applicability policy remain pending human acceptance and cannot guarantee exhaustive discovery of unknown unknowns."}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/locator","value":"Register Denominator, Target Acceptance Criteria, and Rejection And Hollow-Success Conditions"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/12/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-verification-register-completeness-charter.v0"}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/source_ref/label_hint","value":"register completeness charter"}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/12/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/12/knowledge_basis/0/version","value":"verification-register-completeness/v0"}
{"node_type":"string","pointer":"/verification_items/12/label","value":"検証 register の有界完全性"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/12/lifecycle_surfaces/0","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/12/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/12/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/12/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/12/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/12/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/12/proposition","value":"Every gap-bearing entry in the declared verification denominator has a stable identity, an exact source locator, and exactly one inspectable disposition that preserves unresolved audit uncertainty unless supported by located resolution evidence or an authorized human non-applicability decision."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/12/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/12/rejection_conditions/0","value":"The register declares completeness against an unreviewed self-selected denominator."}
{"node_type":"string","pointer":"/verification_items/12/rejection_conditions/1","value":"Deferral, handoff, file presence, or implementation absence is treated as resolution."}
{"node_type":"string","pointer":"/verification_items/12/rejection_conditions/2","value":"The completeness mechanism assigns priority, accepts risk, or claims discovery of unknown unknowns."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/12/required_evidence"}
{"node_type":"string","pointer":"/verification_items/12/required_evidence/0","value":"Versioned denominator and disposition vocabulary."}
{"node_type":"string","pointer":"/verification_items/12/required_evidence/1","value":"Negative omission, dangling-locator, duplicate, contradiction, unsupported-resolution, and unsupported-non-applicability observations."}
{"node_type":"string","pointer":"/verification_items/12/required_evidence/2","value":"Independent denominator review and human bounded-meaning decision."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/residual_risks"}
{"node_type":"string","pointer":"/verification_items/12/residual_risks/0","value":"A mechanically complete register can still use an incomplete or wrongly interpreted denominator."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/12/reverification"}
{"node_type":"null","pointer":"/verification_items/12/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/12/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/12/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/12/reverification/triggers/0","value":"Denominator, disposition vocabulary, source shape, unresolved contract, validator, or projection mapping changes."}
{"node_type":"null","pointer":"/verification_items/12/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/12/scope","value":"Declared unproven scope, residual risks, conformance remaining obligations, unresolved obligations, independent-review findings, transition prohibitions, measured hazards, and unresolved field-evaluation outcomes; unknown unknowns are outside the completeness claim."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/12/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/12/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/12/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/12/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/12/unproven_scope/0","value":"Denominator adoption, stable gap registration, disposition closure, negative omission detection, independent review, and projection value equivalence."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/12/validation_method"}
{"node_type":"string","pointer":"/verification_items/12/validation_method/environment","value":"Not defined pending independent denominator review and human adoption."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/12/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/12/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/12/validation_method/population_or_context","value":"Agents and humans using the register to form progress and completion material."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/12/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/12/verification_method"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/environment","value":"The local canonical denominator, 65-record gap register, exactly-one disposition checks, reference closure, and deterministic complete-value projection are implemented. The bounded denominator is not independently reviewed or human-adopted, and the checks cannot discover unknown unknowns."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/12/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/population_or_context","value":"All source fields and records included by the candidate denominator."}
{"item_count":5,"node_type":"array","pointer":"/verification_items/12/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/procedure_refs/0","value":"validation/verification-source.json"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/procedure_refs/1","value":"validation/verification-gap-register.json"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/procedure_refs/2","value":"scripts/validate_verification_source.py"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/procedure_refs/3","value":"tests/test_verification_source_validator.py"}
{"node_type":"string","pointer":"/verification_items/12/verification_method/procedure_refs/4","value":"tests/test_verification_projection.py"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/13"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/13/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/13/acceptance_criteria/0","value":"Every stage output names its source subjects, transformations, carried and discharged obligations, evidence, authority, and unresolved remainder."}
{"node_type":"string","pointer":"/verification_items/13/acceptance_criteria/1","value":"Split, merge, revision, cancellation, and supersession preserve or explicitly transform identity and proposition meaning under versioned rules."}
{"node_type":"string","pointer":"/verification_items/13/acceptance_criteria/2","value":"Adversarial substitutions, orphaned obligations, duplicated authority, stale evidence, and unsupported strengthening fail closed."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/assumptions"}
{"node_type":"string","pointer":"/verification_items/13/assumptions/0","value":"The current OR-01 surface list remains the lifecycle denominator."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/13/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/13/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/13/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/13/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/13/authority_boundary/source_may/0","value":"Expose broken, ambiguous, stale, or unsupported cross-stage trace and composition."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/13/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/13/authority_boundary/source_must_not/0","value":"Execute or schedule lifecycle work."}
{"node_type":"string","pointer":"/verification_items/13/authority_boundary/source_must_not/1","value":"Infer actor authority, action occurrence, or acceptance from trace continuity alone."}
{"item_count":6,"node_type":"array","pointer":"/verification_items/13/claim_classes"}
{"node_type":"string","pointer":"/verification_items/13/claim_classes/0","value":"description_completeness"}
{"node_type":"string","pointer":"/verification_items/13/claim_classes/1","value":"requirement_conformance"}
{"node_type":"string","pointer":"/verification_items/13/claim_classes/2","value":"action_occurrence"}
{"node_type":"string","pointer":"/verification_items/13/claim_classes/3","value":"artifact_provenance"}
{"node_type":"string","pointer":"/verification_items/13/claim_classes/4","value":"verification_result"}
{"node_type":"string","pointer":"/verification_items/13/claim_classes/5","value":"repair_effect"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/counterconditions"}
{"node_type":"string","pointer":"/verification_items/13/counterconditions/0","value":"A versioned human-approved origin revision changes the lifecycle denominator or explicitly removes a cross-stage claim."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/13/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/13/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/13/entity_id","value":"verification.cross.lifecycle-trace-and-composition"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/13/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/13/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/13/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/13/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/13/failure_consequence","value":"Ten individually implemented surfaces can still fail the original purpose if meaning, authority, evidence, or unresolved scope changes silently between them."}
{"node_type":"string","pointer":"/verification_items/13/item_kind","value":"bounded_assurance"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/13/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/applicability","value":"Every transition and composition among the lifecycle audit surfaces named by OR-01."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/counterconditions/0","value":"Two artifacts are explicitly unrelated and no cross-stage claim is made."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/limitations/0","value":"The origin requirement fixes the purpose and boundaries but does not prescribe a trace schema or composition algebra."}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/locator","value":"OR-01, OR-02, OR-03, Essential Realization, and Invariants 10-14"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/13/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/13/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/13/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/13/label","value":"工程横断 trace・意味合成"}
{"item_count":11,"node_type":"array","pointer":"/verification_items/13/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/0","value":"request"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/1","value":"exploration_question"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/2","value":"requirement"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/3","value":"decision_state"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/4","value":"plan"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/5","value":"action"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/6","value":"realization_policy"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/7","value":"diff"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/8","value":"verification"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/9","value":"completion_claim"}
{"node_type":"string","pointer":"/verification_items/13/lifecycle_surfaces/10","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/13/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/13/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/13/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/13/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/13/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/13/proposition","value":"Typed identities, propositions, assumptions, decisions, authorities, evidence, unresolved obligations, and transformations compose across every OR-01 lifecycle boundary without silent semantic substitution, loss, duplication, or unsupported strengthening."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/13/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/13/rejection_conditions/0","value":"Per-surface presence is counted as lifecycle composition."}
{"node_type":"string","pointer":"/verification_items/13/rejection_conditions/1","value":"Trace is inferred from labels, sequence, or lexical similarity alone."}
{"node_type":"string","pointer":"/verification_items/13/rejection_conditions/2","value":"A downstream completion claim drops upstream contradiction, uncertainty, authority, or evidence limits."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/13/required_evidence"}
{"node_type":"string","pointer":"/verification_items/13/required_evidence/0","value":"Human-accepted cross-stage semantics and ownership boundary."}
{"node_type":"string","pointer":"/verification_items/13/required_evidence/1","value":"Versioned trace and composition contract."}
{"node_type":"string","pointer":"/verification_items/13/required_evidence/2","value":"Vertical, mutation, split/merge, supersession, cancellation, and orphan-detection observations."}
{"node_type":"string","pointer":"/verification_items/13/required_evidence/3","value":"Independent cross-stage omission and semantic-substitution review."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/residual_risks"}
{"node_type":"string","pointer":"/verification_items/13/residual_risks/0","value":"A syntactically closed trace can preserve the wrong engineering meaning if profile semantics or rule-pack interpretation are wrong."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/13/reverification"}
{"node_type":"null","pointer":"/verification_items/13/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/13/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/13/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/13/reverification/triggers/0","value":"Lifecycle profile, denominator, trace contract, composition rule, identity model, or public projection changes."}
{"node_type":"null","pointer":"/verification_items/13/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/13/scope","value":"Trace and composition between the ten OR-01 lifecycle surfaces, including split, merge, revision, cancellation, supersession, repair, and completion projections."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/13/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/13/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/13/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/13/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/13/unproven_scope/0","value":"Cross-stage identity, proposition, obligation, authority, evidence, and unresolved-scope composition for all lifecycle transitions and branching forms."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/13/validation_method"}
{"node_type":"string","pointer":"/verification_items/13/validation_method/environment","value":"Not defined pending lifecycle profiles and representative cross-stage cases."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/13/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/13/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/13/validation_method/population_or_context","value":"Coding agents and human reviewers following work from request through completion material."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/13/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/13/verification_method"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/environment","value":"A local typed lifecycle-trace and composition validator with adversarial fixtures exists. The ten profile meanings remain candidate-only, the resolver and public stage adapters are absent, and no subject-bound full-lifecycle observation or independent review is registered."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/13/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/population_or_context","value":"All declared lifecycle transitions, including branching, merging, supersession, cancellation, and repair."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/13/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/procedure_refs/0","value":"schemas/lifecycle-trace.schema.json"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/procedure_refs/1","value":"src/semantic_guard/lifecycle_trace.py"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/procedure_refs/2","value":"tests/test_lifecycle_trace.py"}
{"node_type":"string","pointer":"/verification_items/13/verification_method/procedure_refs/3","value":"validation/lifecycle-profile-registry.candidate.json"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/14"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/14/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/14/acceptance_criteria/0","value":"The human-selected deployment envelope and failure thresholds are explicit."}
{"node_type":"string","pointer":"/verification_items/14/acceptance_criteria/1","value":"Bound qualification runs cover duration, concurrency, load, exhaustion, provider failure, restart, recovery, compatibility, platform, observability, and rollback triggers."}
{"node_type":"string","pointer":"/verification_items/14/acceptance_criteria/2","value":"Independent review confirms that missing, stale, failed, or out-of-envelope results cannot become readiness."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/assumptions"}
{"node_type":"string","pointer":"/verification_items/14/assumptions/0","value":"Operational behavior varies by deployment profile, provider, platform, resource envelope, and failure policy."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/14/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/14/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/14/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/14/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/14/authority_boundary/source_may/0","value":"Record bounded qualification requirements, observations, failures, and unqualified scope."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/14/authority_boundary/source_must_not/0","value":"Select a deployment profile, schedule deployment, accept operational risk, or claim readiness outside the tested envelope."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/14/claim_classes"}
{"node_type":"string","pointer":"/verification_items/14/claim_classes/0","value":"operational_readiness"}
{"node_type":"string","pointer":"/verification_items/14/claim_classes/1","value":"verification_result"}
{"node_type":"string","pointer":"/verification_items/14/claim_classes/2","value":"validation_result"}
{"node_type":"string","pointer":"/verification_items/14/claim_classes/3","value":"secure_operation"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/counterconditions"}
{"node_type":"string","pointer":"/verification_items/14/counterconditions/0","value":"Only a named historical local observation is asserted with no readiness or continued-operation claim."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/14/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/14/criticality","value":"high"}
{"node_type":"string","pointer":"/verification_items/14/entity_id","value":"verification.cross.operational-qualification"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/14/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/14/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/14/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/14/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/14/failure_consequence","value":"A locally correct audit path can fail, lose evidence, deadlock, leak resources, or recover unsafely under real operational conditions while still appearing ready."}
{"node_type":"string","pointer":"/verification_items/14/item_kind","value":"operational_readiness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/14/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/adoption_status","value":"candidate"}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/applicability","value":"Any deployment or default-route readiness claim beyond a one-time local observation."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/counterconditions/0","value":"A result is explicitly limited to a named historical local execution and makes no operational-readiness claim."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/limitations/0","value":"The constitution does not fix deployment profiles, operational thresholds, or acceptable incident risk; those remain human decisions."}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/locator","value":"evaluation_contract, change_control, and fail-closed invariants"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/14/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/source_ref/entity_id","value":"constitution.semantic-guard.r0"}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/source_ref/label_hint","value":"v1 基幹憲法"}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/14/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/14/knowledge_basis/0/version","value":"0.2.0-draft"}
{"node_type":"string","pointer":"/verification_items/14/label","value":"運用 profile 資格確認"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/14/lifecycle_surfaces/0","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/14/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/14/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/14/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/14/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/14/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/14/proposition","value":"For each human-selected deployment profile, bounded observations establish behavior under declared duration, concurrency, load, resource exhaustion, provider failure, restart, recovery, compatibility, platform, observability, and incident conditions before operational readiness is claimed."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/14/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/14/rejection_conditions/0","value":"Unit, doctor, schema, or smoke passage is called operational qualification."}
{"node_type":"string","pointer":"/verification_items/14/rejection_conditions/1","value":"One platform or short run is generalized beyond its declared envelope."}
{"node_type":"string","pointer":"/verification_items/14/rejection_conditions/2","value":"Qualification silently chooses deployment risk or erases semantic, security, or field-validity gaps."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/14/required_evidence"}
{"node_type":"string","pointer":"/verification_items/14/required_evidence/0","value":"Human deployment-envelope and operational-risk decision."}
{"node_type":"string","pointer":"/verification_items/14/required_evidence/1","value":"Closed subject, environment, dependency, provider, and configuration manifest."}
{"node_type":"string","pointer":"/verification_items/14/required_evidence/2","value":"Bound qualification executions and raw incident, recovery, and resource observations."}
{"node_type":"string","pointer":"/verification_items/14/required_evidence/3","value":"Independent operational review."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/residual_risks"}
{"node_type":"string","pointer":"/verification_items/14/residual_risks/0","value":"Qualification cannot enumerate every correlated failure or establish continued validity after the subject or environment changes."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/14/reverification"}
{"node_type":"null","pointer":"/verification_items/14/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/14/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/14/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/14/reverification/triggers/0","value":"Deployment profile, dependency, provider, platform, resource limit, failure policy, observability, or recovery path changes."}
{"node_type":"null","pointer":"/verification_items/14/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/14/scope","value":"Selected local, CI, sidecar, service, and external-provider deployment profiles; qualification is distinct from semantic field validity and later evidence requalification."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/14/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/14/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/14/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/14/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/14/unproven_scope/0","value":"Deployment envelope, duration, concurrency, load, resource exhaustion, provider failure, restart, recovery, compatibility, multiple platforms, observability, incident response, and independent qualification review."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/14/validation_method"}
{"node_type":"string","pointer":"/verification_items/14/validation_method/environment","value":"Not defined pending intended deployment and operational risk policy."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/14/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/14/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/14/validation_method/population_or_context","value":"Real operators, platforms, providers, and incident conditions selected by the human owner."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/14/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/14/verification_method"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/environment","value":"A local five-profile, 12-scenario operational-qualification contract and fail-closed validator exist. No human-selected deployment envelope, bound operational run, external observation, or readiness decision exists."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/14/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/population_or_context","value":"Deployment-profile-specific load, concurrency, duration, failure, recovery, platform, and incident scenarios."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/14/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/procedure_refs/0","value":"schemas/operational-qualification.schema.json"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/procedure_refs/1","value":"src/semantic_guard/operational_qualification.py"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/procedure_refs/2","value":"tests/test_operational_qualification.py"}
{"node_type":"string","pointer":"/verification_items/14/verification_method/procedure_refs/3","value":"docs/operational-qualification-and-transition.md"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/15"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/15/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/15/acceptance_criteria/0","value":"A versioned transition plan declares compatibility, shadowing, entry and abort criteria, evidence migration, rollback, disposal, and retirement boundaries."}
{"node_type":"string","pointer":"/verification_items/15/acceptance_criteria/1","value":"Bound rehearsal and independent observation demonstrate rollback and recovery without erasing unresolved audit state."}
{"node_type":"string","pointer":"/verification_items/15/acceptance_criteria/2","value":"A human-owned decision authorizes only the selected transition after required field, operational, and human-use evidence is located."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/assumptions"}
{"node_type":"string","pointer":"/verification_items/15/assumptions/0","value":"The current v1 path remains sidecar or opt-in until a separate human cutover decision."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/15/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/15/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/15/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/15/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/15/authority_boundary/source_may/0","value":"Expose transition prohibitions, missing evidence, rehearsal results, and decision material."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/15/authority_boundary/source_must_not/0","value":"Switch defaults, retire predecessors, execute deployment, set transition timing, or fill the human cutover decision."}
{"item_count":5,"node_type":"array","pointer":"/verification_items/15/claim_classes"}
{"node_type":"string","pointer":"/verification_items/15/claim_classes/0","value":"procedure_conformance"}
{"node_type":"string","pointer":"/verification_items/15/claim_classes/1","value":"verification_result"}
{"node_type":"string","pointer":"/verification_items/15/claim_classes/2","value":"validation_result"}
{"node_type":"string","pointer":"/verification_items/15/claim_classes/3","value":"human_decision_boundary"}
{"node_type":"string","pointer":"/verification_items/15/claim_classes/4","value":"operational_readiness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/counterconditions"}
{"node_type":"string","pointer":"/verification_items/15/counterconditions/0","value":"No default, migration, disposal, or predecessor-retirement effect is proposed."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/15/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/15/criticality","value":"high"}
{"node_type":"string","pointer":"/verification_items/15/entity_id","value":"verification.cross.transition-and-cutover"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/15/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/15/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/15/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/15/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/15/failure_consequence","value":"An unqualified sidecar can become authoritative, strand users or evidence, or become difficult to withdraw before its semantic and operational limits are understood."}
{"node_type":"string","pointer":"/verification_items/15/item_kind","value":"operational_readiness"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/15/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/applicability","value":"Any promotion from prototype or sidecar to a default or retired-predecessor state."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/counterconditions/0","value":"A prototype remains isolated, opt-in, non-authoritative, and makes no migration or retirement claim."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/limitations/0","value":"The origin requirement fixes the human and sidecar boundary but does not choose a migration window, cutover threshold, or retirement date."}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/locator","value":"Invariants 4-8 and Prototype Charter Requirement: promotion_criteria and rollback_or_disposal"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/15/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/15/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/15/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/15/label","value":"移行・cutover・rollback・retirement 統治"}
{"item_count":6,"node_type":"array","pointer":"/verification_items/15/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/15/lifecycle_surfaces/0","value":"decision_state"}
{"node_type":"string","pointer":"/verification_items/15/lifecycle_surfaces/1","value":"plan"}
{"node_type":"string","pointer":"/verification_items/15/lifecycle_surfaces/2","value":"action"}
{"node_type":"string","pointer":"/verification_items/15/lifecycle_surfaces/3","value":"verification"}
{"node_type":"string","pointer":"/verification_items/15/lifecycle_surfaces/4","value":"completion_claim"}
{"node_type":"string","pointer":"/verification_items/15/lifecycle_surfaces/5","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/15/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/15/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/15/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/15/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/15/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/15/proposition","value":"A sidecar, opt-in contract, or replacement path cannot become default, retire its predecessor, or lose its rollback route until compatibility, migration, shadow comparison, rollback rehearsal, operational and field evidence, human-use evidence, prohibitions, and a located human cutover decision are closed for the selected scope."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/15/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/15/rejection_conditions/0","value":"File presence, local passage, or implementation completion silently changes the default route."}
{"node_type":"string","pointer":"/verification_items/15/rejection_conditions/1","value":"Rollback is documentary only or predecessor retirement precedes bounded compatibility and recovery evidence."}
{"node_type":"string","pointer":"/verification_items/15/rejection_conditions/2","value":"semantic-guard performs cutover, accepts risk, or fabricates the human transition decision."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/15/required_evidence"}
{"node_type":"string","pointer":"/verification_items/15/required_evidence/0","value":"Versioned migration, compatibility, rollback, disposal, and retirement plan."}
{"node_type":"string","pointer":"/verification_items/15/required_evidence/1","value":"Bound shadow, migration, rollback, and recovery rehearsal with independent observation."}
{"node_type":"string","pointer":"/verification_items/15/required_evidence/2","value":"Located field, operational-qualification, human-use, and human cutover decision records."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/residual_risks"}
{"node_type":"string","pointer":"/verification_items/15/residual_risks/0","value":"A rehearsed transition can still encounter unrepresented callers, stored records, environments, or organizational dependencies."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/15/reverification"}
{"node_type":"null","pointer":"/verification_items/15/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/15/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/15/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/15/reverification/triggers/0","value":"Public contract, default route, predecessor support, compatibility target, stored-record format, deployment profile, or rollback mechanism changes."}
{"node_type":"null","pointer":"/verification_items/15/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/15/scope","value":"Opt-in introduction, default-route switch, compatibility period, rollback, disposal, and predecessor retirement for v1 profiles and assurance contracts."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/15/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/15/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/15/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/15/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/15/unproven_scope/0","value":"Transition contract, compatibility window, shadow comparison, evidence migration, rollback rehearsal, abort criteria, human cutover decision, and predecessor retirement."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/15/validation_method"}
{"node_type":"string","pointer":"/verification_items/15/validation_method/environment","value":"Not defined pending field, operational, and human-use evidence."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/15/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/15/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/15/validation_method/population_or_context","value":"Agents, humans, callers, and stored evidence affected by a route or contract transition."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/15/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/15/verification_method"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/environment","value":"A local sidecar-to-retirement transition contract, nine gates, abort and rollback checks, and adversarial fixtures exist. No human-adopted transition policy, bound rehearsal, independent observation, cutover decision, or retirement decision exists."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/15/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/population_or_context","value":"Every opt-in, default switch, compatibility window, rollback, and predecessor-retirement transition."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/15/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/procedure_refs/0","value":"schemas/transition-plan.schema.json"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/procedure_refs/1","value":"src/semantic_guard/transition_control.py"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/procedure_refs/2","value":"tests/test_transition_control.py"}
{"node_type":"string","pointer":"/verification_items/15/verification_method/procedure_refs/3","value":"docs/operational-qualification-and-transition.md"}
{"keys":["acceptance_criteria","assumptions","authority_boundary","claim_classes","counterconditions","counterevidence_refs","criticality","entity_id","evidence_refs","failure_consequence","item_kind","knowledge_basis","label","lifecycle_surfaces","origin_requirement_refs","proposition","rejection_conditions","required_evidence","residual_risks","reverification","scope","state_profile_ref","unproven_scope","validation_method","verification_method"],"member_count":25,"node_type":"object","pointer":"/verification_items/16"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/16/acceptance_criteria"}
{"node_type":"string","pointer":"/verification_items/16/acceptance_criteria/0","value":"A human-owned responsibility and escalation policy defines which questions an agent may resolve and which must reach a human role."}
{"node_type":"string","pointer":"/verification_items/16/acceptance_criteria/1","value":"Outputs preserve finding, evidence, limitation, unresolved scope, authority class, repair target, and decision question in responsibility-correct projections."}
{"node_type":"string","pointer":"/verification_items/16/acceptance_criteria/2","value":"Independent task-based evaluation measures routing, comprehension, repair correctness, escalation, residual uncertainty, and authority errors separately."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/assumptions"}
{"node_type":"string","pointer":"/verification_items/16/assumptions/0","value":"Coding agents and humans have materially different authority, context, and decision capacities."}
{"keys":["audit_owner","control_owner","final_acceptance_owner","source_may","source_must_not"],"member_count":5,"node_type":"object","pointer":"/verification_items/16/authority_boundary"}
{"node_type":"string","pointer":"/verification_items/16/authority_boundary/audit_owner","value":"semantic-guard"}
{"node_type":"string","pointer":"/verification_items/16/authority_boundary/control_owner","value":"external_caller_or_resource_control_plane"}
{"node_type":"string","pointer":"/verification_items/16/authority_boundary/final_acceptance_owner","value":"human"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/authority_boundary/source_may"}
{"node_type":"string","pointer":"/verification_items/16/authority_boundary/source_may/0","value":"Expose responsibility class, decision questions, repair targets, uncertainty, and evidence limits in role-appropriate material."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/authority_boundary/source_must_not"}
{"node_type":"string","pointer":"/verification_items/16/authority_boundary/source_must_not/0","value":"Assign organizational roles, authorize work, route around the caller's control plane, or fill a human acceptance decision."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/16/claim_classes"}
{"node_type":"string","pointer":"/verification_items/16/claim_classes/0","value":"description_completeness"}
{"node_type":"string","pointer":"/verification_items/16/claim_classes/1","value":"repair_effect"}
{"node_type":"string","pointer":"/verification_items/16/claim_classes/2","value":"human_decision_boundary"}
{"node_type":"string","pointer":"/verification_items/16/claim_classes/3","value":"validation_result"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/counterconditions"}
{"node_type":"string","pointer":"/verification_items/16/counterconditions/0","value":"No output is used for repair, escalation, operational action, or human decision support."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/16/counterevidence_refs"}
{"node_type":"string","pointer":"/verification_items/16/criticality","value":"critical"}
{"node_type":"string","pointer":"/verification_items/16/entity_id","value":"verification.cross.human-operational-use"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/evidence_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/16/evidence_refs/0"}
{"node_type":"string","pointer":"/verification_items/16/evidence_refs/0/entity_id","value":"evidence.origin-requirement.snapshot.2026-08-27"}
{"node_type":"string","pointer":"/verification_items/16/evidence_refs/0/label_hint","value":"原点要求 snapshot"}
{"node_type":"string","pointer":"/verification_items/16/evidence_refs/0/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/16/failure_consequence","value":"Correct audit material can be ignored, misrouted, misunderstood, or acted on by an unauthorized layer, leaving defects unchanged or silently converting technical pass into human acceptance."}
{"node_type":"string","pointer":"/verification_items/16/item_kind","value":"human_decision_boundary"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/knowledge_basis"}
{"keys":["adoption_status","applicability","counterconditions","limitations","locator","source_ref","standards_conformance_claimed","version"],"member_count":8,"node_type":"object","pointer":"/verification_items/16/knowledge_basis/0"}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/adoption_status","value":"adopted_internal"}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/applicability","value":"Every audit result or bounded assurance record intended to change agent work or support a human decision."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/knowledge_basis/0/counterconditions"}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/counterconditions/0","value":"A record is retained only as internal diagnostic data and is not presented as repair, escalation, or decision material."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/knowledge_basis/0/limitations"}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/limitations/0","value":"The origin requirement fixes decision ownership but does not define organization-specific roles, routing, comprehension thresholds, or escalation policy."}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/locator","value":"OR-03, Audience And Use, Essential Realization, and Invariants 1-4 and 14"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/16/knowledge_basis/0/source_ref"}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/source_ref/entity_id","value":"document.prototype-origin-requirement.v3"}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/source_ref/label_hint","value":"原点要求"}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/source_ref/reference_kind","value":"ref"}
{"node_type":"boolean","pointer":"/verification_items/16/knowledge_basis/0/standards_conformance_claimed","value":false}
{"node_type":"string","pointer":"/verification_items/16/knowledge_basis/0/version","value":"prototype-origin-requirement/v3"}
{"node_type":"string","pointer":"/verification_items/16/label","value":"人間・coding agent の責任適合利用"}
{"item_count":7,"node_type":"array","pointer":"/verification_items/16/lifecycle_surfaces"}
{"node_type":"string","pointer":"/verification_items/16/lifecycle_surfaces/0","value":"request"}
{"node_type":"string","pointer":"/verification_items/16/lifecycle_surfaces/1","value":"decision_state"}
{"node_type":"string","pointer":"/verification_items/16/lifecycle_surfaces/2","value":"plan"}
{"node_type":"string","pointer":"/verification_items/16/lifecycle_surfaces/3","value":"action"}
{"node_type":"string","pointer":"/verification_items/16/lifecycle_surfaces/4","value":"verification"}
{"node_type":"string","pointer":"/verification_items/16/lifecycle_surfaces/5","value":"completion_claim"}
{"node_type":"string","pointer":"/verification_items/16/lifecycle_surfaces/6","value":"cross_cutting"}
{"item_count":3,"node_type":"array","pointer":"/verification_items/16/origin_requirement_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/16/origin_requirement_refs/0"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/0/entity_id","value":"OR-01"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/0/label_hint","value":"工程横断の体系監査"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/16/origin_requirement_refs/1"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/1/entity_id","value":"OR-02"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/1/label_hint","value":"AI エージェント行為の限定的立証"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/16/origin_requirement_refs/2"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/2/entity_id","value":"OR-03"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/2/label_hint","value":"修正と人間判断への接続"}
{"node_type":"string","pointer":"/verification_items/16/origin_requirement_refs/2/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/verification_items/16/proposition","value":"Audit and assurance material reaches the responsible coding agent or human at the correct decision layer, preserves what each may decide, and is understandable and actionable enough to support repair, escalation, accept, request_revision, or defer without turning technical state into authority or acceptance."}
{"item_count":3,"node_type":"array","pointer":"/verification_items/16/rejection_conditions"}
{"node_type":"string","pointer":"/verification_items/16/rejection_conditions/0","value":"One message shape is assumed suitable for coding agents and humans without role-specific evidence."}
{"node_type":"string","pointer":"/verification_items/16/rejection_conditions/1","value":"A recommendation, score, or technical pass is projected as authorization or acceptance."}
{"node_type":"string","pointer":"/verification_items/16/rejection_conditions/2","value":"Comprehension is inferred from schema validity or reviewer agreement alone."}
{"item_count":4,"node_type":"array","pointer":"/verification_items/16/required_evidence"}
{"node_type":"string","pointer":"/verification_items/16/required_evidence/0","value":"Human responsibility, escalation, and decision-rights policy."}
{"node_type":"string","pointer":"/verification_items/16/required_evidence/1","value":"Versioned responsibility-aware material and routing contract."}
{"node_type":"string","pointer":"/verification_items/16/required_evidence/2","value":"Representative task-based agent and human evaluation with preserved errors and disagreement."}
{"node_type":"string","pointer":"/verification_items/16/required_evidence/3","value":"Independent review of authority, comprehension, and repair outcomes."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/residual_risks"}
{"node_type":"string","pointer":"/verification_items/16/residual_risks/0","value":"Usable material in one organization, language, domain, or model may not transfer to another without re-evaluation."}
{"keys":["last_evaluated_at","procedure_refs","status","triggers","valid_until"],"member_count":5,"node_type":"object","pointer":"/verification_items/16/reverification"}
{"node_type":"null","pointer":"/verification_items/16/reverification/last_evaluated_at","value":null}
{"item_count":0,"node_type":"array","pointer":"/verification_items/16/reverification/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/16/reverification/status","value":"blocked"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/reverification/triggers"}
{"node_type":"string","pointer":"/verification_items/16/reverification/triggers/0","value":"Role, responsibility, workflow, output contract, agent model, language, domain, or decision policy changes."}
{"node_type":"null","pointer":"/verification_items/16/reverification/valid_until","value":null}
{"node_type":"string","pointer":"/verification_items/16/scope","value":"Machine-readable and human-readable findings, unresolved obligations, proof limits, repair targets, escalation material, and acceptance material across coding-agent and human responsibility layers."}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/verification_items/16/state_profile_ref"}
{"node_type":"string","pointer":"/verification_items/16/state_profile_ref/entity_id","value":"state.not-assessed"}
{"node_type":"string","pointer":"/verification_items/16/state_profile_ref/label_hint","value":"未評価"}
{"node_type":"string","pointer":"/verification_items/16/state_profile_ref/reference_kind","value":"ref"}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/unproven_scope"}
{"node_type":"string","pointer":"/verification_items/16/unproven_scope/0","value":"Role taxonomy, routing accuracy, agent actionability, human comprehension, escalation correctness, repair quality, authority errors, accessibility, and organizational fit."}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/16/validation_method"}
{"node_type":"string","pointer":"/verification_items/16/validation_method/environment","value":"Not defined pending human role and risk policy plus representative use evaluation."}
{"item_count":1,"node_type":"array","pointer":"/verification_items/16/validation_method/method_types"}
{"node_type":"string","pointer":"/verification_items/16/validation_method/method_types/0","value":"not_defined"}
{"node_type":"string","pointer":"/verification_items/16/validation_method/population_or_context","value":"Representative coding-agent and human decision tasks across the intended lifecycle profiles."}
{"item_count":0,"node_type":"array","pointer":"/verification_items/16/validation_method/procedure_refs"}
{"keys":["environment","method_types","population_or_context","procedure_refs"],"member_count":4,"node_type":"object","pointer":"/verification_items/16/verification_method"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/environment","value":"Local responsibility-aware material, repair-cycle, and operational-outcome evaluation contracts exist with adversarial fixtures. No human-adopted organizational routing policy, real participants, bound task execution, independently authenticated observation, or human-use validity evidence exists."}
{"item_count":2,"node_type":"array","pointer":"/verification_items/16/verification_method/method_types"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/method_types/0","value":"inspection"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/method_types/1","value":"test"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/population_or_context","value":"Coding agents, human requesters, reviewers, approvers, and maintainers receiving audit material."}
{"item_count":6,"node_type":"array","pointer":"/verification_items/16/verification_method/procedure_refs"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/procedure_refs/0","value":"schemas/responsibility-material.schema.json"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/procedure_refs/1","value":"src/semantic_guard/repair_loop.py"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/procedure_refs/2","value":"schemas/operational-outcome-evaluation.schema.json"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/procedure_refs/3","value":"src/semantic_guard/operational_outcomes.py"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/procedure_refs/4","value":"tests/test_repair_loop.py"}
{"node_type":"string","pointer":"/verification_items/16/verification_method/procedure_refs/5","value":"tests/test_operational_outcomes.py"}
{"item_count":5,"node_type":"array","pointer":"/views"}
{"keys":["canonical","entity_id","item_refs","label","purpose"],"member_count":5,"node_type":"object","pointer":"/views/0"}
{"node_type":"boolean","pointer":"/views/0/canonical","value":false}
{"node_type":"string","pointer":"/views/0/entity_id","value":"view.origin-purpose-coverage"}
{"item_count":17,"node_type":"array","pointer":"/views/0/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/0"}
{"node_type":"string","pointer":"/views/0/item_refs/0/entity_id","value":"verification.or01.lifecycle-surface-coverage"}
{"node_type":"string","pointer":"/views/0/item_refs/0/label_hint","value":"OR-01 工程横断被覆"}
{"node_type":"string","pointer":"/views/0/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/1"}
{"node_type":"string","pointer":"/views/0/item_refs/1/entity_id","value":"verification.or01.engineering-knowledge-governance"}
{"node_type":"string","pointer":"/views/0/item_refs/1/label_hint","value":"OR-01 体系知の根拠統治"}
{"node_type":"string","pointer":"/views/0/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/2"}
{"node_type":"string","pointer":"/views/0/item_refs/2/entity_id","value":"verification.or01.discovery-effectiveness"}
{"node_type":"string","pointer":"/views/0/item_refs/2/label_hint","value":"OR-01 未解決・欠陥の発見性能"}
{"node_type":"string","pointer":"/views/0/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/3"}
{"node_type":"string","pointer":"/views/0/item_refs/3/entity_id","value":"verification.or02.bounded-claim-model"}
{"node_type":"string","pointer":"/views/0/item_refs/3/label_hint","value":"OR-02 限定的立証の主張模型"}
{"node_type":"string","pointer":"/views/0/item_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/4"}
{"node_type":"string","pointer":"/views/0/item_refs/4/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"node_type":"string","pointer":"/views/0/item_refs/4/label_hint","value":"OR-02 行為発生・主体・権限・手続適合"}
{"node_type":"string","pointer":"/views/0/item_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/5"}
{"node_type":"string","pointer":"/views/0/item_refs/5/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"node_type":"string","pointer":"/views/0/item_refs/5/label_hint","value":"OR-02 成果物来歴・真正性・因果境界"}
{"node_type":"string","pointer":"/views/0/item_refs/5/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/6"}
{"node_type":"string","pointer":"/views/0/item_refs/6/entity_id","value":"verification.or03.repair-effect"}
{"node_type":"string","pointer":"/views/0/item_refs/6/label_hint","value":"OR-03 修正循環の有効性"}
{"node_type":"string","pointer":"/views/0/item_refs/6/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/7"}
{"node_type":"string","pointer":"/views/0/item_refs/7/entity_id","value":"verification.or03.human-decision-boundary"}
{"node_type":"string","pointer":"/views/0/item_refs/7/label_hint","value":"OR-03 人間判断境界"}
{"node_type":"string","pointer":"/views/0/item_refs/7/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/8"}
{"node_type":"string","pointer":"/views/0/item_refs/8/entity_id","value":"verification.cross.field-validation"}
{"node_type":"string","pointer":"/views/0/item_refs/8/label_hint","value":"実務資料上の妥当性確認"}
{"node_type":"string","pointer":"/views/0/item_refs/8/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/9"}
{"node_type":"string","pointer":"/views/0/item_refs/9/entity_id","value":"verification.cross.secure-and-responsible-operation"}
{"node_type":"string","pointer":"/views/0/item_refs/9/label_hint","value":"安全・責任ある情報取扱いと外部境界"}
{"node_type":"string","pointer":"/views/0/item_refs/9/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/10"}
{"node_type":"string","pointer":"/views/0/item_refs/10/entity_id","value":"verification.cross.operational-reverification"}
{"node_type":"string","pointer":"/views/0/item_refs/10/label_hint","value":"運用・変更影響・再検証"}
{"node_type":"string","pointer":"/views/0/item_refs/10/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/11"}
{"node_type":"string","pointer":"/views/0/item_refs/11/entity_id","value":"verification.or02.proof-obligation-and-assurance-graph-soundness"}
{"node_type":"string","pointer":"/views/0/item_refs/11/label_hint","value":"proof obligation・assurance graph 健全性"}
{"node_type":"string","pointer":"/views/0/item_refs/11/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/12"}
{"node_type":"string","pointer":"/views/0/item_refs/12/entity_id","value":"verification.cross.register-completeness"}
{"node_type":"string","pointer":"/views/0/item_refs/12/label_hint","value":"検証 register の有界完全性"}
{"node_type":"string","pointer":"/views/0/item_refs/12/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/13"}
{"node_type":"string","pointer":"/views/0/item_refs/13/entity_id","value":"verification.cross.lifecycle-trace-and-composition"}
{"node_type":"string","pointer":"/views/0/item_refs/13/label_hint","value":"工程横断 trace・意味合成"}
{"node_type":"string","pointer":"/views/0/item_refs/13/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/14"}
{"node_type":"string","pointer":"/views/0/item_refs/14/entity_id","value":"verification.cross.operational-qualification"}
{"node_type":"string","pointer":"/views/0/item_refs/14/label_hint","value":"運用 profile 資格確認"}
{"node_type":"string","pointer":"/views/0/item_refs/14/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/15"}
{"node_type":"string","pointer":"/views/0/item_refs/15/entity_id","value":"verification.cross.transition-and-cutover"}
{"node_type":"string","pointer":"/views/0/item_refs/15/label_hint","value":"移行・cutover 統治"}
{"node_type":"string","pointer":"/views/0/item_refs/15/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/0/item_refs/16"}
{"node_type":"string","pointer":"/views/0/item_refs/16/entity_id","value":"verification.cross.human-operational-use"}
{"node_type":"string","pointer":"/views/0/item_refs/16/label_hint","value":"人間・coding agent の責任適合利用"}
{"node_type":"string","pointer":"/views/0/item_refs/16/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/views/0/label","value":"原点要求被覆ビュー"}
{"node_type":"string","pointer":"/views/0/purpose","value":"Show whether OR-01, OR-02, and OR-03 are supported, refuted, or unproven without being hidden by local implementation progress."}
{"keys":["canonical","entity_id","item_refs","label","purpose"],"member_count":5,"node_type":"object","pointer":"/views/1"}
{"node_type":"boolean","pointer":"/views/1/canonical","value":false}
{"node_type":"string","pointer":"/views/1/entity_id","value":"view.discovery-effectiveness"}
{"item_count":7,"node_type":"array","pointer":"/views/1/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/1/item_refs/0"}
{"node_type":"string","pointer":"/views/1/item_refs/0/entity_id","value":"verification.or01.discovery-effectiveness"}
{"node_type":"string","pointer":"/views/1/item_refs/0/label_hint","value":"OR-01 未解決・欠陥の発見性能"}
{"node_type":"string","pointer":"/views/1/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/1/item_refs/1"}
{"node_type":"string","pointer":"/views/1/item_refs/1/entity_id","value":"conformance.INV-VN-001"}
{"node_type":"string","pointer":"/views/1/item_refs/1/label_hint","value":"INV-VN-001 局所適合"}
{"node_type":"string","pointer":"/views/1/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/1/item_refs/2"}
{"node_type":"string","pointer":"/views/1/item_refs/2/entity_id","value":"conformance.stage.residual-risk-gate"}
{"node_type":"string","pointer":"/views/1/item_refs/2/label_hint","value":"残余危険門"}
{"node_type":"string","pointer":"/views/1/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/1/item_refs/3"}
{"node_type":"string","pointer":"/views/1/item_refs/3/entity_id","value":"conformance.stage.morphology"}
{"node_type":"string","pointer":"/views/1/item_refs/3/label_hint","value":"形態素解析"}
{"node_type":"string","pointer":"/views/1/item_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/1/item_refs/4"}
{"node_type":"string","pointer":"/views/1/item_refs/4/entity_id","value":"conformance.stage.dependency-analysis-bundle"}
{"node_type":"string","pointer":"/views/1/item_refs/4/label_hint","value":"依存構造解析束"}
{"node_type":"string","pointer":"/views/1/item_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/1/item_refs/5"}
{"node_type":"string","pointer":"/views/1/item_refs/5/entity_id","value":"conformance.stage.versioned-lifting-rule"}
{"node_type":"string","pointer":"/views/1/item_refs/5/label_hint","value":"版付き導出"}
{"node_type":"string","pointer":"/views/1/item_refs/5/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/1/item_refs/6"}
{"node_type":"string","pointer":"/views/1/item_refs/6/entity_id","value":"conformance.stage.llm-candidate"}
{"node_type":"string","pointer":"/views/1/item_refs/6/label_hint","value":"LLM候補"}
{"node_type":"string","pointer":"/views/1/item_refs/6/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/views/1/label","value":"発見性能ビュー"}
{"node_type":"string","pointer":"/views/1/purpose","value":"Separate discovery of missing or ambiguous relations from preservation of already-generated unresolved states."}
{"keys":["canonical","entity_id","item_refs","label","purpose"],"member_count":5,"node_type":"object","pointer":"/views/2"}
{"node_type":"boolean","pointer":"/views/2/canonical","value":false}
{"node_type":"string","pointer":"/views/2/entity_id","value":"view.action-assurance"}
{"item_count":4,"node_type":"array","pointer":"/views/2/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/2/item_refs/0"}
{"node_type":"string","pointer":"/views/2/item_refs/0/entity_id","value":"verification.or02.bounded-claim-model"}
{"node_type":"string","pointer":"/views/2/item_refs/0/label_hint","value":"限定的立証の主張模型"}
{"node_type":"string","pointer":"/views/2/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/2/item_refs/1"}
{"node_type":"string","pointer":"/views/2/item_refs/1/entity_id","value":"verification.or02.action-occurrence-and-procedure"}
{"node_type":"string","pointer":"/views/2/item_refs/1/label_hint","value":"行為発生・主体・権限・手続適合"}
{"node_type":"string","pointer":"/views/2/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/2/item_refs/2"}
{"node_type":"string","pointer":"/views/2/item_refs/2/entity_id","value":"verification.or02.artifact-provenance-authenticity"}
{"node_type":"string","pointer":"/views/2/item_refs/2/label_hint","value":"成果物来歴・真正性・因果境界"}
{"node_type":"string","pointer":"/views/2/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/2/item_refs/3"}
{"node_type":"string","pointer":"/views/2/item_refs/3/entity_id","value":"verification.or02.proof-obligation-and-assurance-graph-soundness"}
{"node_type":"string","pointer":"/views/2/item_refs/3/label_hint","value":"proof obligation・assurance graph 健全性"}
{"node_type":"string","pointer":"/views/2/item_refs/3/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/views/2/label","value":"行為立証ビュー"}
{"node_type":"string","pointer":"/views/2/purpose","value":"Keep claim structure, action occurrence, authority, procedure, artifact provenance, authenticity, and causality separate."}
{"keys":["canonical","entity_id","item_refs","label","purpose"],"member_count":5,"node_type":"object","pointer":"/views/3"}
{"node_type":"boolean","pointer":"/views/3/canonical","value":false}
{"node_type":"string","pointer":"/views/3/entity_id","value":"view.repair-and-human-decision"}
{"item_count":4,"node_type":"array","pointer":"/views/3/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/3/item_refs/0"}
{"node_type":"string","pointer":"/views/3/item_refs/0/entity_id","value":"verification.or03.repair-effect"}
{"node_type":"string","pointer":"/views/3/item_refs/0/label_hint","value":"修正循環の有効性"}
{"node_type":"string","pointer":"/views/3/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/3/item_refs/1"}
{"node_type":"string","pointer":"/views/3/item_refs/1/entity_id","value":"verification.or03.human-decision-boundary"}
{"node_type":"string","pointer":"/views/3/item_refs/1/label_hint","value":"人間判断境界"}
{"node_type":"string","pointer":"/views/3/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/3/item_refs/2"}
{"node_type":"string","pointer":"/views/3/item_refs/2/entity_id","value":"verification.cross.human-operational-use"}
{"node_type":"string","pointer":"/views/3/item_refs/2/label_hint","value":"人間・coding agent の責任適合利用"}
{"node_type":"string","pointer":"/views/3/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/3/item_refs/3"}
{"node_type":"string","pointer":"/views/3/item_refs/3/entity_id","value":"conformance.stage.decision-request-materialization"}
{"node_type":"string","pointer":"/views/3/item_refs/3/label_hint","value":"判断要求生成"}
{"node_type":"string","pointer":"/views/3/item_refs/3/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/views/3/label","value":"修正循環・人間判断ビュー"}
{"node_type":"string","pointer":"/views/3/purpose","value":"Show repair effectiveness and human acceptance boundary without moving control or final decision authority into semantic-guard."}
{"keys":["canonical","entity_id","item_refs","label","purpose"],"member_count":5,"node_type":"object","pointer":"/views/4"}
{"node_type":"boolean","pointer":"/views/4/canonical","value":false}
{"node_type":"string","pointer":"/views/4/entity_id","value":"view.local-implementation-conformance"}
{"item_count":27,"node_type":"array","pointer":"/views/4/item_refs"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/0"}
{"node_type":"string","pointer":"/views/4/item_refs/0/entity_id","value":"conformance.INV-VN-001"}
{"node_type":"string","pointer":"/views/4/item_refs/0/label_hint","value":"INV-VN-001"}
{"node_type":"string","pointer":"/views/4/item_refs/0/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/1"}
{"node_type":"string","pointer":"/views/4/item_refs/1/entity_id","value":"conformance.INV-VN-002"}
{"node_type":"string","pointer":"/views/4/item_refs/1/label_hint","value":"INV-VN-002"}
{"node_type":"string","pointer":"/views/4/item_refs/1/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/2"}
{"node_type":"string","pointer":"/views/4/item_refs/2/entity_id","value":"conformance.INV-VN-003"}
{"node_type":"string","pointer":"/views/4/item_refs/2/label_hint","value":"INV-VN-003"}
{"node_type":"string","pointer":"/views/4/item_refs/2/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/3"}
{"node_type":"string","pointer":"/views/4/item_refs/3/entity_id","value":"conformance.INV-VN-004"}
{"node_type":"string","pointer":"/views/4/item_refs/3/label_hint","value":"INV-VN-004"}
{"node_type":"string","pointer":"/views/4/item_refs/3/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/4"}
{"node_type":"string","pointer":"/views/4/item_refs/4/entity_id","value":"conformance.INV-VN-005"}
{"node_type":"string","pointer":"/views/4/item_refs/4/label_hint","value":"INV-VN-005"}
{"node_type":"string","pointer":"/views/4/item_refs/4/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/5"}
{"node_type":"string","pointer":"/views/4/item_refs/5/entity_id","value":"conformance.INV-VN-006"}
{"node_type":"string","pointer":"/views/4/item_refs/5/label_hint","value":"INV-VN-006"}
{"node_type":"string","pointer":"/views/4/item_refs/5/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/6"}
{"node_type":"string","pointer":"/views/4/item_refs/6/entity_id","value":"conformance.INV-VN-007"}
{"node_type":"string","pointer":"/views/4/item_refs/6/label_hint","value":"INV-VN-007"}
{"node_type":"string","pointer":"/views/4/item_refs/6/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/7"}
{"node_type":"string","pointer":"/views/4/item_refs/7/entity_id","value":"conformance.INV-VN-008"}
{"node_type":"string","pointer":"/views/4/item_refs/7/label_hint","value":"INV-VN-008"}
{"node_type":"string","pointer":"/views/4/item_refs/7/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/8"}
{"node_type":"string","pointer":"/views/4/item_refs/8/entity_id","value":"conformance.INV-VN-009"}
{"node_type":"string","pointer":"/views/4/item_refs/8/label_hint","value":"INV-VN-009"}
{"node_type":"string","pointer":"/views/4/item_refs/8/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/9"}
{"node_type":"string","pointer":"/views/4/item_refs/9/entity_id","value":"conformance.INV-VN-010"}
{"node_type":"string","pointer":"/views/4/item_refs/9/label_hint","value":"INV-VN-010"}
{"node_type":"string","pointer":"/views/4/item_refs/9/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/10"}
{"node_type":"string","pointer":"/views/4/item_refs/10/entity_id","value":"conformance.INV-VN-011"}
{"node_type":"string","pointer":"/views/4/item_refs/10/label_hint","value":"INV-VN-011"}
{"node_type":"string","pointer":"/views/4/item_refs/10/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/11"}
{"node_type":"string","pointer":"/views/4/item_refs/11/entity_id","value":"conformance.INV-VN-012"}
{"node_type":"string","pointer":"/views/4/item_refs/11/label_hint","value":"INV-VN-012"}
{"node_type":"string","pointer":"/views/4/item_refs/11/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/12"}
{"node_type":"string","pointer":"/views/4/item_refs/12/entity_id","value":"conformance.INV-VN-013"}
{"node_type":"string","pointer":"/views/4/item_refs/12/label_hint","value":"INV-VN-013"}
{"node_type":"string","pointer":"/views/4/item_refs/12/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/13"}
{"node_type":"string","pointer":"/views/4/item_refs/13/entity_id","value":"conformance.INV-VN-014"}
{"node_type":"string","pointer":"/views/4/item_refs/13/label_hint","value":"INV-VN-014"}
{"node_type":"string","pointer":"/views/4/item_refs/13/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/14"}
{"node_type":"string","pointer":"/views/4/item_refs/14/entity_id","value":"conformance.stage.input-boundary"}
{"node_type":"string","pointer":"/views/4/item_refs/14/label_hint","value":"入力境界"}
{"node_type":"string","pointer":"/views/4/item_refs/14/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/15"}
{"node_type":"string","pointer":"/views/4/item_refs/15/entity_id","value":"conformance.stage.provisional-direct-audit"}
{"node_type":"string","pointer":"/views/4/item_refs/15/label_hint","value":"義務別仮判定"}
{"node_type":"string","pointer":"/views/4/item_refs/15/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/16"}
{"node_type":"string","pointer":"/views/4/item_refs/16/entity_id","value":"conformance.stage.residual-risk-gate"}
{"node_type":"string","pointer":"/views/4/item_refs/16/label_hint","value":"残余危険門"}
{"node_type":"string","pointer":"/views/4/item_refs/16/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/17"}
{"node_type":"string","pointer":"/views/4/item_refs/17/entity_id","value":"conformance.stage.morphology"}
{"node_type":"string","pointer":"/views/4/item_refs/17/label_hint","value":"形態素解析"}
{"node_type":"string","pointer":"/views/4/item_refs/17/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/18"}
{"node_type":"string","pointer":"/views/4/item_refs/18/entity_id","value":"conformance.stage.dependency-analysis-bundle"}
{"node_type":"string","pointer":"/views/4/item_refs/18/label_hint","value":"依存構造解析束"}
{"node_type":"string","pointer":"/views/4/item_refs/18/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/19"}
{"node_type":"string","pointer":"/views/4/item_refs/19/entity_id","value":"conformance.stage.versioned-lifting-rule"}
{"node_type":"string","pointer":"/views/4/item_refs/19/label_hint","value":"版付き導出"}
{"node_type":"string","pointer":"/views/4/item_refs/19/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/20"}
{"node_type":"string","pointer":"/views/4/item_refs/20/entity_id","value":"conformance.stage.llm-candidate"}
{"node_type":"string","pointer":"/views/4/item_refs/20/label_hint","value":"LLM候補"}
{"node_type":"string","pointer":"/views/4/item_refs/20/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/21"}
{"node_type":"string","pointer":"/views/4/item_refs/21/entity_id","value":"conformance.stage.obligation-reaggregation"}
{"node_type":"string","pointer":"/views/4/item_refs/21/label_hint","value":"義務別再集約"}
{"node_type":"string","pointer":"/views/4/item_refs/21/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/22"}
{"node_type":"string","pointer":"/views/4/item_refs/22/entity_id","value":"conformance.stage.decision-request-materialization"}
{"node_type":"string","pointer":"/views/4/item_refs/22/label_hint","value":"判断要求生成"}
{"node_type":"string","pointer":"/views/4/item_refs/22/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/23"}
{"node_type":"string","pointer":"/views/4/item_refs/23/entity_id","value":"conformance.completeness.provider-accounting"}
{"node_type":"string","pointer":"/views/4/item_refs/23/label_hint","value":"解析器実行会計"}
{"node_type":"string","pointer":"/views/4/item_refs/23/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/24"}
{"node_type":"string","pointer":"/views/4/item_refs/24/entity_id","value":"conformance.completeness.public-result"}
{"node_type":"string","pointer":"/views/4/item_refs/24/label_hint","value":"公開結果完全性"}
{"node_type":"string","pointer":"/views/4/item_refs/24/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/25"}
{"node_type":"string","pointer":"/views/4/item_refs/25/entity_id","value":"conformance.migration.legacy-baseline"}
{"node_type":"string","pointer":"/views/4/item_refs/25/label_hint","value":"旧版基線"}
{"node_type":"string","pointer":"/views/4/item_refs/25/reference_kind","value":"ref"}
{"keys":["entity_id","label_hint","reference_kind"],"member_count":3,"node_type":"object","pointer":"/views/4/item_refs/26"}
{"node_type":"string","pointer":"/views/4/item_refs/26/entity_id","value":"conformance.migration.legacy-characterization"}
{"node_type":"string","pointer":"/views/4/item_refs/26/label_hint","value":"旧版特性試験"}
{"node_type":"string","pointer":"/views/4/item_refs/26/reference_kind","value":"ref"}
{"node_type":"string","pointer":"/views/4/label","value":"局所実装適合ビュー"}
{"node_type":"string","pointer":"/views/4/purpose","value":"Project invariant, pipeline, completeness, and migration checks without presenting them as field validation or whole-purpose completion."}
```
