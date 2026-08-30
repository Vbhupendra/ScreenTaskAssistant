import re
from typing import Dict, List

class Intent:
    UNDERSTAND = "UNDERSTAND"
    DIAGNOSE = "DIAGNOSE"
    SOLVE = "SOLVE"
    EXPLAIN = "EXPLAIN"
    SUMMARIZE = "SUMMARIZE"
    CANCEL = "CANCEL"
    UNKNOWN = "UNKNOWN"

class IntentClassifier:
    """A lightweight, regex-based classifier to map spoken text to core intents."""
    def __init__(self):
        self.rules: Dict[str, List[str]] = {
            Intent.CANCEL: [
                r"\bstop\b",
                r"\bcancel\b",
                r"\bnever\s*mind\b",
                r"\babort\b",
                r"\bquit\b"
            ],
            Intent.UNDERSTAND: [
                r"\bwhat's this\b",
                r"\bwhat is this\b",
                r"\bwhat's on\b",          # broadened: covers "what's on my", "what's on that", "what's on screen"
                r"\bwhat is on\b",         # broadened: covers "what is on my", "what is on that"
                r"\bwhat do you see\b",
                r"\bwhat you see\b",        # NEW: indirect clause — "tell me what you see in front of me"
                r"\bwhat.{0,10}visible\b", # NEW: covers "what's visible here", "what is visible"
                r"\bdescribe\b",           # covers "describe this", "describe the screen", "describe the active window"
                r"\blook at (this|that|it)\b",  # generalized: was "look at this" — now covers "look at it", "look at that"
                r"\bcheck this\b",
                r"\bcheck that\b",
                r"\bwhat am i looking at\b"
            ],
            Intent.DIAGNOSE: [
                r"\bwhat's wrong\b",
                r"\bwhat is wrong\b",
                r"\bfind the error\b",
                r"\bfind error\b",
                r"\bfind the bug\b",        # covers "find the bug here"
                r"\bfind the problem\b",
                r"\bdiagnose\b",
                r"\banalyze the error\b",
                r"\bwhat's the bug\b",
                r"\bwhat is the bug\b",
                r"\blook for error\b",
                r"\bany error\b",
                r"\bcheck for error\b",
                r"\bcheck the error\b",
                r"\bwhy (isn't|is not) (this|it) (working|running)\b",  # generalized: was two separate rules
                r"\bstack\s*trace\b",       # NEW: developer term — "check for stack trace"
                r"\b(analyze|check|look at|inspect|read|show|find|see)\b.{0,20}\btraceback\b",  # NEW: requires diagnostic verb before traceback; avoids SOLVE collision
                r"\bdebug\b"                # covers "debug this", "debug this python exception"
            ],
            Intent.SOLVE: [
                r"\bfix this\b",
                r"\bsolve this\b",
                r"\bsolve that\b",
                r"\bsolve the\b",           # covers "solve the git merge conflict"
                r"\bfix the bug\b",
                r"\bcorrect this\b",
                r"\bresolve this\b",
                r"\bresolve the\b",         # covers "resolve the issue"
                r"\bgive me a solution\b",  # covers "give me a solution for this traceback"
                r"\ba solution for\b",
                r"\bfix it\b",
                r"\bsolve it\b",
                r"\bmake it work\b",
                r"\bhelp me fix this\b",
                r"\bhow do i fix this\b"
            ],
            Intent.EXPLAIN: [
                r"\bexplain (this|that|it)\b", # generalized: was "explain this" + "explain that" — adds "it"
                r"\bexplain what\b",         # NEW: covers "explain what this is doing", "explain what's happening"
                r"\bexplain how\b",
                r"\bexplain why\b",
                r"\bexplain the\b",         # covers "explain the Dockerfile", "explain the code", "explain the function"
                r"\bwhat does this\b",       # broadened: was "what does this mean" — also covers "what does this code do"
                r"\bhow does this work\b",
                r"\bwhy is this happening\b"
            ],
            Intent.SUMMARIZE: [
                r"\bsummarize (this|that|it)\b",  # generalized: was "summarize this" — adds "that" and "it"
                r"\bsummarize the\b",              # generalized: was "summarize the screen" + "summarize the text" — covers all forms
                r"\bgive me a.{0,10}summary\b",   # covers "give me a brief summary", "give me a summary"
                r"\bwhat.{0,15}summary\b",          # broadened: was "what is the summary" — covers "what's the summary here"
            ]
        }
        # Pre-compile the regex patterns for efficiency
        self.compiled_rules = {
            intent: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for intent, patterns in self.rules.items()
        }

    def _normalize(self, text: str) -> str:
        """Lightweight normalization for common punctuation, spelling, and speech errors."""
        # Lowercase and clean surrounding spaces
        text = text.lower().strip()

        # Remove simple punctuation (except apostrophes for contractions like what's/isn't)
        text = re.sub(r"[^\w\s']", "", text)

        # Narrow, safe STT corrections — only fix unambiguous phonetic substitutions
        replacements = {
            r"\bwhats\b":          "what's",   # "whats this" → "what's this"
            r"\bdis\b":            "this",      # "fix dis" → "fix this"
            r"\bdat\b":            "that",      # "check dat" → "check that"
            r"\bcold\b":           "code",      # "look at this cold" → "look at this code"
            r"\bscream\b":         "screen",    # "what's on my scream" → "what's on my screen"
            r"\bon my stream\b":   "on my screen",  # "what's on my stream" (narrow — avoids corrupting "data stream")
            r"\bphotograph\b":     "paragraph"  # "read the photograph" → "read the paragraph"
        }
        # NOTE: "\bfast\b" removed — too destructive ("run as fast as possible" would corrupt)
        # NOTE: "\bstream\b" narrowed to "\bon my stream\b" — avoids corrupting "data stream", "event stream"
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        # Clean up any duplicated whitespace
        return re.sub(r"\s+", " ", text).strip()

    def classify(self, text: str) -> str:
        if not text:
            return Intent.UNKNOWN

        text_clean = self._normalize(text)

        for intent, patterns in self.compiled_rules.items():
            for pattern in patterns:
                if pattern.search(text_clean):
                    return intent

        return Intent.UNKNOWN
