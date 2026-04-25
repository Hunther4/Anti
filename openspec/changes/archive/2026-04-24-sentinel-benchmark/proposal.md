# Proposal: Sentinel Gauntlet Automation

## Intent

The goal is to automate the SENTINEL GAUNTLET v1.0 benchmark protocol within the Antigravity (Anti) ecosystem. This will allow for objective evaluation of different LLM models by measuring TPS, context efficiency, reasoning depth, tool usage, and persona alignment.

## Scope

### In Scope
- Automatic detection of the active LLM model.
- Execution of the 5 sequential tests defined in the protocol.
- Capture and calculation of metrics (TPS, Success/Failure, Score).
- Generation of a summary report in Markdown format.
- Comparison of current results with previous benchmarks.

### Out of Scope
- Automatic switching of models in LM Studio (requires manual intervention for now).
- Real-time visualization of metrics (focused on report generation).

## Capabilities

### New Capabilities
- benchmark-automation: Capability to run standardized benchmarks and generate reports.

### Modified Capabilities
None.

## Approach

1.  **Metric Capture**: Enhance `Brain` to return detailed timing and token counts per request (already partially exists).
2.  **Benchmark Runner**: Create `Anti/core/benchmark.py` implementing the `SentinelGauntlet` class.
3.  **Command Integration**: Add a `benchmark` command to `AntiAgent.handle_command` to trigger the tests.
4.  **Reporting**: Save reports to `Anti/workspace/benchmarks/` with naming convention `sentinel_{model_name}_{timestamp}.md`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `Anti/core/benchmark.py` | New | Main runner logic. |
| `Anti/core/agent.py` | Modified | Integration of the `benchmark` command. |
| `Anti/workspace/benchmarks/` | New | Output directory for reports. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Inaccurate TPS due to background load | Med | Add a warning to close other apps (as per protocol). |
| Model detection failure | Low | Use fallback names and allow manual override. |

## Rollback Plan

Delete `Anti/core/benchmark.py` and revert changes in `Anti/core/agent.py`.

## Dependencies

- Existing `AntiAgent` core infrastructure.
- LM Studio API (running locally).

## Success Criteria

- [ ] System automatically detects the model name.
- [ ] All 5 tests are executed sequentially.
- [ ] A report is generated with all metrics populated.
- [ ] The generated report uses the Rioplatense persona check results.
