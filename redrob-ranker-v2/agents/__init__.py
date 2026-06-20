"""
Agentic pipeline (blueprint Section 8).

For the contest these 'agents' run as a deterministic, in-process sequence
(no network, CPU-only). In production each becomes an autonomous microservice.
The orchestrator wires them together; each agent is a thin, single-responsibility
wrapper around the corresponding `src/` module so the architecture is identical
in both modes — only the execution substrate changes.
"""
