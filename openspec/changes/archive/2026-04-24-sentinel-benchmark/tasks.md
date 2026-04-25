# Tasks: Sentinel Gauntlet Automation

## Phase 1: Infrastructure
- [x] 1.1 Create output directory `Anti/workspace/benchmarks/`.
- [x] 1.2 Modify `Anti/core/brain.py` to return `tps` and `duration` in `usage`.

## Phase 2: Core Implementation
- [x] 2.1 Create `Anti/core/benchmark.py`.
- [x] 2.2 Implement `BenchmarkRunner.run_test()` with metric capturing.
- [x] 2.3 Implement the 5 test prompts in `BenchmarkRunner`.
- [x] 2.4 Implement Markdown report generation.

## Phase 3: Integration
- [x] 3.1 Add `benchmark` command to `AntiAgent.handle_command`.
- [x] 3.2 Add `run_benchmark` method to `AntiAgent`.

## Phase 4: Verification
- [x] 4.1 Run a full benchmark with a local model.
- [x] 4.2 Verify report generation and content accuracy.
