import unittest
import os
import json
from src.providers.ollama import OllamaProvider
from src.scorer import _build_prm_judge_prompt, _parse_prm_score

class TestAntiV13Updates(unittest.TestCase):
    def test_ollama_format_messages_preserves_system_role(self):
        provider = OllamaProvider()
        test_messages = [
            {"role": "system", "content": "Keep it concise."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        
        formatted = provider._format_messages(test_messages)
        
        # Verify that the system message is preserved and not discarded!
        self.assertEqual(len(formatted), 3)
        self.assertEqual(formatted[0]["role"], "system")
        self.assertEqual(formatted[0]["content"], "Keep it concise.")

    def test_prm_scorer_cot_prompt_content(self):
        prompt = _build_prm_judge_prompt("I wrote app.py", "Create an app")
        
        # Debe contener las directrices de análisis y score
        self.assertTrue(any("Analysis:" in msg["content"] or "Provide your Analysis" in msg["content"] for msg in prompt))
        self.assertTrue(any("Score: 1" in msg["content"] for msg in prompt))

    def test_prm_scorer_cot_parsing(self):
        # El parser debe ignorar el texto preliminar de Chain-of-Thought
        cot_output = (
            "Analysis: The assistant responded with clear, accurate steps.\n"
            "Score: 1"
        )
        score = _parse_prm_score(cot_output)
        self.assertEqual(score, 1)

        cot_output_zero = (
            "Analysis: Partially complete but missing details.\n"
            "Score: 0"
        )
        score_zero = _parse_prm_score(cot_output_zero)
        self.assertEqual(score_zero, 0)

if __name__ == "__main__":
    unittest.main()
