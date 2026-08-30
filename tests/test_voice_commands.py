import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.reasoning.intent_classifier import IntentClassifier, Intent

def run_test_suite():
    classifier = IntentClassifier()
    
    # 66 test cases: 52 original + 14 new regression cases for expanded rules
    test_cases = [
        # Normal sentences (UNDERSTAND / DIAGNOSE / EXPLAIN / SOLVE)
        ("Can you tell me what is on my screen right now?", Intent.UNDERSTAND),
        ("Describe the active window on my screen please.", Intent.UNDERSTAND),
        ("I need you to find the error in this code.", Intent.DIAGNOSE),
        ("Please help me debug this compilation issue.", Intent.DIAGNOSE),
        ("How do I fix this broken layout?", Intent.SOLVE),
        ("Give me a solution for this traceback.", Intent.SOLVE),
        ("Can you explain how this python algorithm works?", Intent.EXPLAIN),
        ("Please explain the code structure visible on the screen.", Intent.EXPLAIN),
        ("Give me a brief summary of the main points on this page.", Intent.SUMMARIZE),
        
        # Short phrases
        ("Check this", Intent.UNDERSTAND),
        ("Look at this", Intent.UNDERSTAND),
        ("Fix this", Intent.SOLVE),
        ("Explain this", Intent.EXPLAIN),
        ("Stop", Intent.CANCEL),
        ("Cancel", Intent.CANCEL),
        ("Summarize this", Intent.SUMMARIZE),
        ("Nevermind", Intent.CANCEL),
        
        # Incomplete phrases
        ("what's", Intent.UNKNOWN),
        ("explain", Intent.UNKNOWN),
        ("find error", Intent.DIAGNOSE),
        ("fix it", Intent.SOLVE),
        ("solve it", Intent.SOLVE),
        
        # Context-dependent "this"
        ("what is this", Intent.UNDERSTAND),
        ("what's this", Intent.UNDERSTAND),
        ("diagnose this", Intent.DIAGNOSE),
        ("solve this", Intent.SOLVE),
        ("explain this", Intent.EXPLAIN),
        ("summarize this", Intent.SUMMARIZE),
        
        # Context-dependent "that"
        ("explain that", Intent.EXPLAIN),
        ("check that", Intent.UNDERSTAND),  # Maps to check (UNDERSTAND)
        ("solve that", Intent.SOLVE),      # Maps to solve (SOLVE)
        
        # Context-dependent "here"
        ("what's wrong here", Intent.DIAGNOSE),
        ("explain the code here", Intent.EXPLAIN),
        ("find the bug here", Intent.DIAGNOSE),
        
        # Common speech-to-text / spelling mistakes
        ("whats this", Intent.UNDERSTAND),
        ("check dis", Intent.UNDERSTAND),
        ("fix dis", Intent.SOLVE),
        ("look at this cold", Intent.UNDERSTAND),      # cold -> code
        ("what is on my scream", Intent.UNDERSTAND),   # scream -> screen
        ("what's on my stream", Intent.UNDERSTAND),    # stream -> screen
        ("read the fast paragraph", Intent.UNKNOWN),   # fast -> first (treated as UNKNOWN since first is not mapped as direct trigger)
        
        # Technical terms
        ("explain the Dockerfile", Intent.EXPLAIN),
        ("debug this python exception", Intent.DIAGNOSE),
        ("solve the git merge conflict", Intent.SOLVE),
        ("diagnose my react component crash", Intent.DIAGNOSE),
        ("explain this json payload", Intent.EXPLAIN),
        
        # Unclear / Unrelated commands
        ("hello", Intent.UNKNOWN),
        ("hi blackbox", Intent.UNKNOWN),
        ("what is the weather today", Intent.UNKNOWN),
        ("tell me a joke", Intent.UNKNOWN),
        ("open google chrome", Intent.UNKNOWN),
        ("computer play some music", Intent.UNKNOWN),
        ("", Intent.UNKNOWN),
        (None, Intent.UNKNOWN),

        # ── NEW REGRESSION CASES (14) ─────────────────────────────────────────
        # Covers every phrase added by the rule-expansion sprint.

        # UNDERSTAND — new variants
        ("what is on that", Intent.UNDERSTAND),           # broadened "what is on"
        ("what's visible here", Intent.UNDERSTAND),       # new "what.{0,10}visible"
        ("look at it", Intent.UNDERSTAND),                # generalized "look at (this|that|it)"
        ("hey tell me what you see in front of me", Intent.UNDERSTAND),  # new "what you see"

        # DIAGNOSE — new variants
        ("check for stack trace", Intent.DIAGNOSE),       # new "stack trace"
        ("analyze exception traceback", Intent.DIAGNOSE), # new "traceback"
        ("why isn't it running", Intent.DIAGNOSE),        # generalized "why isn't … it … running"

        # EXPLAIN — new variants
        ("explain it", Intent.EXPLAIN),                   # generalized "explain (this|that|it)"
        ("what does this code do", Intent.EXPLAIN),       # broadened "what does this"
        ("what does this do", Intent.EXPLAIN),            # broadened "what does this"
        ("explain what this is doing", Intent.EXPLAIN),   # new "explain what"

        # SUMMARIZE — new variants
        ("summarize that", Intent.SUMMARIZE),             # generalized "summarize (this|that|it)"
        ("summarize it", Intent.SUMMARIZE),               # generalized "summarize (this|that|it)"
        ("what's the summary here", Intent.SUMMARIZE),    # broadened "what.{0,5}summary"
    ]

    print(f"{'INPUT':<45} | {'EXPECTED':<12} | {'ACTUAL':<12} | {'RESULT':<6}")
    print("-" * 85)
    
    passed = 0
    failed = 0
    
    for text, expected in test_cases:
        actual = classifier.classify(text)
        result = "PASS" if actual == expected else "FAIL"
        if result == "PASS":
            passed += 1
        else:
            failed += 1
        
        text_str = str(text)[:43] if text is not None else "None"
        print(f"{text_str:<45} | {expected:<12} | {actual:<12} | {result:<6}")
        
    print("-" * 85)
    print(f"Total: {len(test_cases)} | Passed: {passed} | Failed: {failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)
