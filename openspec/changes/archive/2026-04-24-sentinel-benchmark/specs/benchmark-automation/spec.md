# Spec: Benchmark Automation

## Description

This capability provides a standardized way to execute the SENTINEL GAUNTLET benchmark protocol and report the results.

## Requirements

1.  **Model Identification**: The system MUST query the `/v1/models` endpoint of the configured LM Studio server to identify the active model.
2.  **Sequential Execution**: The system SHALL execute the 5 tests defined in `SENTINEL_BENCHMARK_PROTOCOL.md` in order.
3.  **Prompt Consistency**: The system MUST use the exact prompts defined in the protocol.
4.  **Metric Collection**:
    - **TPS (Tokens Per Second)**: Calculated as `completion_tokens / duration`.
    - **Latency**: Total time for the completion.
    - **Success/Failure**: Success if the response is received and any required tools are triggered.
5.  **Reporting**:
    - The system SHALL generate a Markdown report.
    - The report filename MUST include the model name and a timestamp.
    - The report MUST include a summary table comparing the current run with previous runs if available.

## Scenarios

### Scenario 1: Successful Benchmark Run
**Given** LM Studio is running with a loaded model
**When** the user executes the `benchmark` command
**Then** the system identifies the model (e.g., "Meta-Llama-3-8B-Instruct")
**And** executes Test 1 through Test 5
**And** generates `Anti/workspace/benchmarks/sentinel_Meta-Llama-3-8B-Instruct_20240425_2250.md`
**And** displays a summary of the results to the user.

### Scenario 2: Connection Failure
**Given** LM Studio is not running
**When** the user executes the `benchmark` command
**Then** the system reports a connection error
**And** aborts the benchmark.

### Scenario 3: Persona Check Validation
**Given** the model is being evaluated for persona (Test 5)
**When** the response contains "Rioplatense" slang (e.g., "che", "loco", "viste")
**Then** the persona match score SHOULD be high.
