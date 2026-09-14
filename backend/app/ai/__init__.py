"""AI layer: one Gemini client powering two strictly-separated roles:

* **Analysis** — data-grounded theses, chat, recap, FX explainers, vision.
  Analyst voice; the model only translates pre-computed deterministic
  features and never invents numbers.
* **Pulse Assistant (PA)** — the simple-words explainer + light general QA.
  It explains what the analysis (or the page) already says; it never
  performs analysis itself.
"""
