"""
Core Agent Unit Tests — Sprint 4.2

Tests the ReAct loop, tool error recovery, recursive refinement,
and strict reading mode. All external dependencies are mocked.
"""

import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import os
import sys
import asyncio
import tempfile

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent import AntiAgent


class TestAntiAgentCore(unittest.TestCase):
    """Core agent unit tests with fully mocked dependencies."""

    MAX_TOOL_STEPS = 10  # Must match src/agent.py _process()

    @classmethod
    def setUpClass(cls):
        # Detect the event loop policy once
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass

    def setUp(self):
        # ---------------------------------------------------------------
        # Patch every external dependency that AntiAgent.__init__ touches
        # ---------------------------------------------------------------
        self.patches = [
            patch("src.agent.Brain"),
            patch("src.agent.MemoryManager"),
            patch("src.agent.ContextManager"),
            patch("src.agent.PRMScorer"),
            patch("src.agent.SkillEvolver"),
            # PluginManager and auto_create are imported inside __init__
            patch("src.plugin_manager.PluginManager"),
            patch("src.agent.MemoryConsolidator"),
            patch("src.agent.build_system_prompt"),
            patch("src.providers.create_provider"),
            patch("src.providers.auto_create"),
        ]
        self.mocks = [p.start() for p in self.patches]

        (
            self.MockBrain,
            self.MockMemory,
            self.MockContextMgr,
            self.MockScorer,
            self.MockEvolver,
            self.MockPluginMgr,
            self.MockConsolidator,
            self.mock_build_prompt,
            self.mock_create_provider,
            self.mock_auto_create,
        ) = self.mocks

        # -- Brain mock -------------------------------------------------
        self.brain_instance = self.MockBrain.return_value
        self.brain_instance.chat = AsyncMock(
            return_value=(
                "Test answer",
                {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "total_tokens": 150,
                    "duration": 1.0,
                    "tps": 100,
                },
            )
        )
        self.brain_instance.model = "test-model"
        self.brain_instance.check_connection = AsyncMock(return_value=True)
        self.brain_instance.sync_model_context = AsyncMock()
        self.brain_instance.get_context_info = AsyncMock(
            return_value={"max": 32000, "usable": 28000, "threshold": 22400}
        )
        self.brain_instance.record_usage = MagicMock()

        self.mock_auto_create.return_value = self.brain_instance
        self.mock_create_provider.return_value = self.brain_instance

        # -- Memory mock ------------------------------------------------
        self.memory_instance = self.MockMemory.return_value
        self.memory_instance.retrieve_omni_context.return_value = ""
        self.memory_instance.log_experience = MagicMock()
        self.memory_instance.update_usage_stats = MagicMock()
        self.memory_instance.count_engrams.return_value = 0
        # Skills nested mock (used by _check_integrity)
        self.memory_instance.skills = MagicMock()
        self.memory_instance.skills.skills = []
        self.memory_instance.load_patterns.return_value = ""

        # -- Scorer mock ------------------------------------------------
        self.scorer_instance = self.MockScorer.return_value
        self.scorer_instance.evaluate = AsyncMock(
            return_value={"score": 1.0, "votes": [1, 1, 1]}
        )
        # prm_model is set as an attribute, will be overridden by tests

        # -- Plugin manager mock ----------------------------------------
        self.plugin_instance = self.MockPluginMgr.return_value
        self.plugin_instance.get_tool_descriptions.return_value = (
            "- [SEARCH: query]: Search the web\n- [FETCH: url]: Fetch URL"
        )
        self.plugin_instance.tools = {}
        self.plugin_instance.execute_tool = AsyncMock(
            return_value="Tool executed OK"
        )

        # -- Context manager mock ---------------------------------------
        self.ctx_instance = self.MockContextMgr.return_value
        self.ctx_instance.token_count = 0
        self.ctx_instance.usage_percent = 10
        self.ctx_instance.get_load_level.return_value = "green"
        self.ctx_instance.get_integrity_action.return_value = "none"
        self.ctx_instance.deduplicate.return_value = 0

        # -- Consolidator mock ------------------------------------------
        self.consolidator_instance = self.MockConsolidator.return_value
        self.consolidator_instance.run_maintenance = AsyncMock()

        # -- System prompt builder mock ---------------------------------
        self.mock_build_prompt.return_value = "Default system prompt"

        # -- Create the agent under test --------------------------------
        self.agent = AntiAgent()

        # Redirect base_dir to a temp directory so @doc resolution works
        self.temp_dir = tempfile.mkdtemp()
        self.agent.base_dir = self.temp_dir
        self.agent.config["enable_prm_scorer"] = True
        self.agent.task_counter = 0

    def tearDown(self):
        for p in self.patches:
            p.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _run(self, coro):
        return asyncio.run(coro)

    # ------------------------------------------------------------------
    # 1. ReAct Loop Termination
    # ------------------------------------------------------------------
    def test_react_loop_termination(self):
        """
        Mock the LLM to return tool calls indefinitely.
        Verify the agent stops at MAX_TOOL_STEPS and does NOT infinite-loop.
        """
        chat_call_count = [0]

        async def _always_tool(messages, temperature=0.7):
            chat_call_count[0] += 1
            return (
                "[SEARCH: keep looping]",
                {
                    "prompt_tokens": 50,
                    "completion_tokens": 10,
                    "total_tokens": 60,
                    "duration": 0.05,
                    "tps": 200,
                },
            )

        self.brain_instance.chat = AsyncMock(side_effect=_always_tool)

        # Register SEARCH so the tool trigger is recognized
        self.plugin_instance.tools = {
            "SEARCH": {
                "func": MagicMock(return_value="result"),
                "description": "Search the web",
            }
        }
        # Disable PRM scorer so it does not add extra chat calls
        self.agent.config["enable_prm_scorer"] = False

        result = self._run(self.agent._process("test infinite loop"))

        # Must have exactly MAX_TOOL_STEPS execution steps
        self.assertEqual(
            len(result["steps"]),
            self.MAX_TOOL_STEPS,
            f"Agent should stop at {self.MAX_TOOL_STEPS} tool steps, "
            f"got {len(result['steps'])}",
        )

        # Every step should be a SEARCH call
        for i, step in enumerate(result["steps"]):
            self.assertEqual(step["tool"], "SEARCH", f"Step {i} should be SEARCH")

        # The number of chat() calls equals 1 (initial) + tool steps
        self.assertEqual(
            chat_call_count[0],
            self.MAX_TOOL_STEPS + 1,
            f"Expected {self.MAX_TOOL_STEPS + 1} chat calls, got {chat_call_count[0]}",
        )

    # ------------------------------------------------------------------
    # 2. Tool Error Recovery
    # ------------------------------------------------------------------
    def test_tool_error_recovery(self):
        """
        Mock a tool to throw an exception; verify the agent feeds the
        error message back to the LLM in the next chat context.
        """
        # Phase 1: LLM returns a tool call
        # Phase 2: after tool_error, return a final answer
        responses = [
            (
                "[SEARCH: find data]",
                {"prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55, "duration": 0.1, "tps": 50},
            ),
            (
                "Final answer after error",
                {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100, "duration": 0.2, "tps": 100},
            ),
        ]

        # Register SEARCH tool whose function raises an exception
        def _failing_tool(raw_args):
            raise RuntimeError("API connection refused")

        self.plugin_instance.tools = {
            "SEARCH": {
                "func": _failing_tool,
                "description": "Search the web",
            }
        }

        # Make execute_tool actually call the real tool function (not a mock)
        # so the error propagates from the tool
        async def _real_execute(name, raw_args):
            if name not in self.plugin_instance.tools:
                return f"[ERROR] Herramienta '{name}' no existe."
            try:
                func = self.plugin_instance.tools[name]["func"]
                if asyncio.iscoroutinefunction(func):
                    return await func(raw_args)
                return func(raw_args)
            except Exception as e:
                return f"[ERROR] Fallo al ejecutar '{name}': {str(e)}"

        self.plugin_instance.execute_tool.side_effect = _real_execute

        # Intercept messages passed to brain.chat for verification
        messages_log = []
        response_idx = [0]

        async def _chat_with_tracking(messages, temperature=0.7):
            messages_log.append(messages)
            idx = response_idx[0]
            response_idx[0] += 1
            return responses[min(idx, len(responses) - 1)]

        self.brain_instance.chat = AsyncMock(side_effect=_chat_with_tracking)
        self.agent.config["enable_prm_scorer"] = False

        result = self._run(self.agent._process("run tool that fails"))

        # The error must have been sent back to the LLM
        # messages_log[0] = initial chat
        # messages_log[1] = chat after tool execution (should contain error)
        self.assertGreaterEqual(
            len(messages_log), 2,
            "Need at least 2 chat calls for the tool error flow"
        )

        # The second call's last user message should contain the tool result
        tool_feedback = messages_log[1][-1]["content"]
        self.assertIn(
            "RESULTADO SEARCH",
            tool_feedback,
            "Tool feedback should include [RESULTADO SEARCH]",
        )
        self.assertIn(
            "connection refused",
            tool_feedback.lower(),
            "Tool feedback should propagate the runtime error message",
        )
        self.assertIn(
            "Fallo al ejecutar",
            tool_feedback,
            "Tool feedback should mention execution failure",
        )

        # The agent should have recorded exactly 1 tool execution step
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["tool"], "SEARCH")

    # ------------------------------------------------------------------
    # 3. Recursive Refinement
    # ------------------------------------------------------------------
    def test_recursive_refinement(self):
        """
        Mock PRMScorer to return score < 0.5; verify the agent triggers
        the recursive metacognition refinement loop.
        """
        # LLM returns a plain answer (no tool calls)
        self.brain_instance.chat = AsyncMock(
            return_value=(
                "Initial low-quality answer",
                {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60, "duration": 0.1, "tps": 100},
            )
        )
        # We'll also need the refinement calls to return something
        # side_effect: first call returns initial, refinement calls return improved
        chat_responses = [
            ("Initial low-quality answer", {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60, "duration": 0.1, "tps": 100}),
            ("Refined answer attempt 1",  {"prompt_tokens": 70, "completion_tokens": 15, "total_tokens": 85, "duration": 0.15, "tps": 100}),
        ]
        self.brain_instance.chat = AsyncMock(side_effect=chat_responses)

        # Scorer first returns low score, then better (to exit refinement)
        scorer_calls = [
            {"score": 0.3, "votes": [0, 0, 1]},    # triggers refinement
            {"score": 0.8, "votes": [1, 1, 0]},    # passes
        ]
        self.scorer_instance.evaluate = AsyncMock(side_effect=scorer_calls)

        # Enable PRM scorer explicitly (it is already True from setUp)
        self.agent.config["enable_prm_scorer"] = True

        result = self._run(self.agent._process("write a high-quality report"))

        # Scorer must have been called at least twice (initial + after refinement)
        self.assertGreaterEqual(
            self.scorer_instance.evaluate.call_count, 2,
            "PRMScorer.evaluate should be called at least twice when refinement triggers",
        )

        # The final score should be >= 0.5
        self.assertGreaterEqual(
            result["score"], 0.5,
            f"Final score should be >= 0.5 after refinement, got {result['score']}",
        )

        # The refinement branch logs "Calidad insuficiente" for the first attempt
        # (we can't easily assert on printed output, but the score history is observable)
        # Chat should have been called 2 times: initial + 1 refinement
        self.assertEqual(
            self.brain_instance.chat.call_count, 2,
            "Expected 2 chat calls (initial + refinement)",
        )

    # ------------------------------------------------------------------
    # 4. Strict Reading Mode
    # ------------------------------------------------------------------
    def test_strict_reading_mode(self):
        """
        Test that @doc.txt mentions inject the correct system prompt
        override (=== MODO LECTURA ESTRICTO ACTIVADO ===).
        """
        # Create a mock document in the lectura/ directory
        lectura_dir = os.path.join(self.agent.base_dir, "lectura")
        os.makedirs(lectura_dir, exist_ok=True)
        doc_path = os.path.join(lectura_dir, "doc.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Contenido del documento de prueba para el agente.")

        # Capture the messages passed to brain.chat
        messages_log = []

        async def _chat_capture(messages, temperature=0.7):
            messages_log.append(messages)
            return (
                "Answer based on document",
                {"prompt_tokens": 60, "completion_tokens": 20, "total_tokens": 80, "duration": 0.2, "tps": 100},
            )

        self.brain_instance.chat = AsyncMock(side_effect=_chat_capture)
        self.agent.config["enable_prm_scorer"] = False

        self._run(self.agent._process("What does @doc.txt say about the topic?"))

        # The messages sent to brain.chat must include the strict reading override
        self.assertGreaterEqual(len(messages_log), 1, "At least one chat call expected")

        system_content = messages_log[0][0]["content"]
        self.assertIn(
            "MODO LECTURA ESTRICTO ACTIVADO",
            system_content,
            "System prompt should contain the strict reading mode header",
        )
        self.assertIn(
            "PROHIBICIÓN ABSOLUTA",
            system_content,
            "System prompt should forbid web search tools",
        )
        self.assertIn(
            "Contenido del documento de prueba",
            system_content,
            "System prompt should include the loaded document content",
        )


if __name__ == "__main__":
    unittest.main()
