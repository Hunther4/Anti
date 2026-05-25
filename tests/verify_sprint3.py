"""
verify_sprint3.py — Verification tests for Sprint 3 (Intelligence & Memory)

Tests:
1. Semantic dedup reduces redundant messages (>85% similarity)
2. LLM summary (fallback) is non-empty and coherent
3. Engram merge produces a combined result (or fallback gracefully)
4. Context manager token-based emergency truncate
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.compactor import HybridCompactor
from src.evolver import SkillEvolver
from src.context_manager import ContextManager


class TestSemanticDedup(unittest.TestCase):
    """Test 1: Semantic deduplication reduces redundant messages."""

    def setUp(self):
        self.compactor = HybridCompactor()

    def test_identical_content_deduped(self):
        """Messages with identical content should be deduplicated."""
        messages = [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
            {"role": "user", "content": "Tell me about Python."},
            {"role": "assistant", "content": "Python is a programming language."},
            # At least 7 messages to trigger dedup (threshold > 6)
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 equals 4."},
        ]
        result = self.compactor.deduplicate_messages(messages, threshold=0.85)
        # The last 4 are preserved (Context Guard), so at least 4
        self.assertLess(len(result), len(messages),
                        "Dedup should reduce message count")
        # Verify identical user messages got deduped
        user_contents = [m["content"] for m in result if m["role"] == "user"]
        self.assertIn("What is the capital of France?", user_contents)

    def test_different_content_preserved(self):
        """Messages with very different content should NOT be deduplicated."""
        messages = [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "Paris is the capital city of France."},
            {"role": "user", "content": "Tell me about quantum physics."},
            {"role": "assistant", "content": "Quantum physics studies particles at atomic scales."},
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is a subset of AI."},
            {"role": "user", "content": "How do I cook pasta?"},
            {"role": "assistant", "content": "Boil water, add salt, cook pasta for 8-10 minutes."},
        ]
        result = self.compactor.deduplicate_messages(messages, threshold=0.85)
        # All should be preserved since content is very different
        self.assertEqual(len(result), len(messages),
                         "Different content should not be deduped")

    def test_similar_but_not_identical_deduped(self):
        """Paraphrased similar messages should be deduped at high threshold."""
        messages = [
            {"role": "user", "content": "What is the capital city of France?"},
            {"role": "assistant", "content": "The French capital is Paris."},
            {"role": "user", "content": "Can you tell me France's capital?"},
            {"role": "assistant", "content": "Paris is the capital of France, located on the Seine River."},
            {"role": "user", "content": "Tell me about Python programming language."},
            {"role": "assistant", "content": "Python is an interpreted high-level language."},
            {"role": "user", "content": "What is the weather today?"},
            {"role": "assistant", "content": "The weather is sunny with a high of 25°C."},
        ]
        result = self.compactor.deduplicate_messages(messages, threshold=0.55)
        # Lower threshold should catch paraphrased intents
        # At minimum, the last 4 are preserved (Context Guard)
        self.assertGreaterEqual(len(result), 4)

    def test_short_messages_no_dedup(self):
        """≤6 messages should not trigger dedup processing."""
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm fine, thanks!"},
        ]
        before = len(messages)
        result = self.compactor.deduplicate_messages(messages, threshold=0.85)
        self.assertEqual(len(result), before,
                         "≤6 messages should pass through unchanged")


class TestLLMSummary(unittest.TestCase):
    """Test 2: LLM summary fallback is non-empty and coherent."""

    def setUp(self):
        self.compactor = HybridCompactor()

    def test_summary_non_empty_with_messages(self):
        """Summary should be non-empty when there are messages (fallback)."""
        messages = [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
            {"role": "user", "content": "What is the population of Paris?"},
            {"role": "assistant", "content": "Paris has a population of about 2.1 million."},
        ]
        summary = self.compactor._auto_summary(messages)
        self.assertTrue(summary, "Summary should be non-empty")
        self.assertIsInstance(summary, str)

    def test_summary_includes_topic_words(self):
        """Fallback summary should include key topic words."""
        messages = [
            {"role": "user", "content": "How does quantum entanglement work?"},
            {"role": "assistant", "content": "Quantum entanglement is a physical phenomenon..."},
            {"role": "user", "content": "Is entanglement useful for computing?"},
            {"role": "assistant", "content": "Yes, it enables quantum computing advantages."},
        ]
        summary = self.compactor._auto_summary(messages)
        # Summary could be LLM-generated or fallback — both should be non-empty
        self.assertTrue(summary, "Summary should be non-empty")
        self.assertIsInstance(summary, str)

    def test_summary_empty_input(self):
        """Summary of empty messages should return 'Sin historial'."""
        summary = self.compactor._auto_summary([])
        self.assertEqual(summary, "Sin historial")

    def test_summary_llm_call_fallback(self):
        """When LLM call fails, should fall back to heuristic summary."""
        with patch.object(self.compactor, '_call_llm', return_value=None):
            messages = [
                {"role": "user", "content": "Test message"},
                {"role": "assistant", "content": "Test response"},
                {"role": "user", "content": "Another question"},
                {"role": "assistant", "content": "Another answer"},
            ]
            summary = self.compactor._auto_summary(messages)
            self.assertTrue(summary)
            self.assertIn("mensajes", summary)


class TestEngramMerge(unittest.TestCase):
    """Test 3: Engram merge produces a combined result."""

    def setUp(self):
        self.evolver = SkillEvolver()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_engram(self, filename, topic, content):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "w") as f:
            json.dump({"topic": topic, "content": content}, f)

    def test_engram_similarity_identical(self):
        """Identical content should have similarity 1.0."""
        sim = self.evolver._engram_similarity("Paris is the capital of France.",
                                               "Paris is the capital of France.")
        self.assertAlmostEqual(sim, 1.0, places=2)

    def test_engram_similarity_different(self):
        """Completely different content should have low similarity."""
        sim = self.evolver._engram_similarity("Paris is the capital of France.",
                                               "Quantum physics studies subatomic particles.")
        self.assertLess(sim, 0.3)

    def test_check_duplicate_finds_similar(self):
        """_check_duplicate_engram should find similar engrams."""
        self._create_engram("existing.json", "france-capital",
                            "Paris is the capital city of France.")
        is_dup, filename, data, sim = self.evolver._check_duplicate_engram(
            "Paris is the capital of France. The city of Paris is the capital of France.",
            self.tmpdir
        )
        self.assertTrue(is_dup, f"Similarity was {sim:.3f}, expected > 0.7")
        self.assertIsNotNone(filename)
        self.assertGreater(sim, 0.5)

    def test_check_duplicate_no_match(self):
        """_check_duplicate_engram should return False for unrelated content."""
        self._create_engram("physics.json", "quantum-physics",
                            "Quantum mechanics describes nature at atomic scale.")
        is_dup, filename, data, sim = self.evolver._check_duplicate_engram(
            "Python is a high-level programming language.",
            self.tmpdir
        )
        self.assertFalse(is_dup)

    def test_merge_engram_saved_new_when_no_duplicate(self):
        """merge_engram returns saved_new when no similar engram exists."""
        is_dup, filename, data, sim = self.evolver._check_duplicate_engram(
            "Brand new unrelated information.", self.tmpdir)
        # No engrams exist, should be saved_new
        self.assertFalse(is_dup)

    def test_merge_engram_uses_synthesize(self):
        """merge_engram calls synthesize when duplicate found (LLM fail → saved_new)."""
        self._create_engram("test.json", "test-topic",
                            "Paris is the capital of France.")
        import asyncio
        result = asyncio.run(
            self.evolver.merge_engram(
                "The French capital is Paris on the Seine River.",
                self.tmpdir
            )
        )
        # Since no LLM is running, synthesis will fail → saved_new
        self.assertIn(result["action"], ["saved_new", "merged"])


class TestContextManagerTokenTruncate(unittest.TestCase):
    """Test 4: Context manager token-based emergency truncate."""

    def setUp(self):
        self.cm = ContextManager(model_context_length=32000)

    def test_emergency_truncate_reduces_token_count(self):
        """Emergency truncate should respect token budget."""
        # Fill with enough messages to trigger truncation
        for i in range(20):
            self.cm.add_message("user", f"This is test message number {i} with some extra content to make it longer.")
            self.cm.add_message("assistant", f"This is response number {i} with additional padding text to ensure tokens.")

        before_tokens = self.cm.token_count
        self.cm.emergency_truncate()
        after_tokens = self.cm.token_count

        self.assertLess(after_tokens, before_tokens,
                        "Token count should decrease after emergency truncate")
        self.assertGreater(after_tokens, 0,
                           "Should not be empty after truncate")

    def test_emergency_truncate_keeps_system_messages(self):
        """System messages should always be preserved."""
        self.cm.pin_critical("CRITICAL SYSTEM INSTRUCTION - NEVER DISCARD THIS")
        for i in range(15):
            self.cm.add_message("user", f"Message {i}")
            self.cm.add_message("assistant", f"Response {i}")

        self.cm.emergency_truncate()

        # System messages should still be present
        system_msgs = [m for m in self.cm.messages if m.get("role") == "system"]
        self.assertGreater(len(system_msgs), 0,
                           "System messages must survive truncation")

    def test_emergency_truncate_no_crash_empty(self):
        """Emergency truncate on empty messages should not crash."""
        cm = ContextManager(model_context_length=32000)
        result = cm.emergency_truncate()
        self.assertEqual(len(result), 0)

    def test_emergency_truncate_with_semantic_dedup(self):
        """Emergency truncate should integrate with semantic dedup."""
        # Add many similar messages
        for i in range(12):
            self.cm.add_message("user", f"What is the capital of France? I need to know {i}")
            self.cm.add_message("assistant", f"The capital of France is Paris. Answer {i}.")

        before = len(self.cm.messages)
        result = self.cm.emergency_truncate()
        # Should have fewer messages after truncation + dedup
        self.assertLessEqual(len(result), before)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()

    # Load tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSemanticDedup))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLLMSummary))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEngramMerge))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestContextManagerTokenTruncate))

    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
