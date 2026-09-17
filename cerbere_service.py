import os

from agentguard import AgentGuard


collector_url = os.getenv(
    "AGENTGUARD_COLLECTOR_URL",
    "https://agentguard-aqal.onrender.com",
)

api_key = os.getenv("AGENTGUARD_API_KEY")

if not api_key:
    raise RuntimeError(
        "AGENTGUARD_API_KEY is missing"
    )


guard = AgentGuard(
    collector_url=collector_url,
    api_key=api_key,
    max_budget=10.0,
    block_on_high=True,
    debug=True,
)
