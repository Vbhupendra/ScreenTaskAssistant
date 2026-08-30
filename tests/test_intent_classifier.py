import sys
import os
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.reasoning.intent_classifier import IntentClassifier, Intent

class TestIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()

    def test_examples(self):
        test_cases = [
            # UNDERSTAND
            ("What's this?", Intent.UNDERSTAND),
            ("What is this", Intent.UNDERSTAND),
            ("What is on my screen?", Intent.UNDERSTAND),
            ("look at this", Intent.UNDERSTAND),
            ("check this", Intent.UNDERSTAND),
            ("what am I looking at", Intent.UNDERSTAND),
            
            # DIAGNOSE
            ("What's wrong?", Intent.DIAGNOSE),
            ("Find the error", Intent.DIAGNOSE),
            ("check the error", Intent.DIAGNOSE),
            ("find the problem", Intent.DIAGNOSE),
            ("why isn't this working", Intent.DIAGNOSE),
            ("debug this", Intent.DIAGNOSE),
            
            # SOLVE
            ("Fix this", Intent.SOLVE),
            ("solve this", Intent.SOLVE),
            ("help me fix this", Intent.SOLVE),
            ("how do I fix this", Intent.SOLVE),
            
            # EXPLAIN
            ("Explain this", Intent.EXPLAIN),
            ("what does this mean", Intent.EXPLAIN),
            ("why is this happening", Intent.EXPLAIN),
            
            # SUMMARIZE
            ("Summarize this", Intent.SUMMARIZE),
            
            # CANCEL
            ("Stop", Intent.CANCEL),
            ("Cancel", Intent.CANCEL),
            ("Nevermind", Intent.CANCEL),
            
            # UNKNOWN / Empty
            ("Random query about weather", Intent.UNKNOWN),
            ("", Intent.UNKNOWN),
            (None, Intent.UNKNOWN),
            
            # STT / Spelling Mistakes (Failing Cases)
            ("whats this", Intent.UNDERSTAND),
            ("check dis", Intent.UNDERSTAND),
            ("fix dis", Intent.SOLVE),
        ]
        
        for text, expected_intent in test_cases:
            with self.subTest(text=text):
                actual_intent = self.classifier.classify(text)
                self.assertEqual(actual_intent, expected_intent, f"Failed for query: '{text}'")

if __name__ == "__main__":
    unittest.main()
