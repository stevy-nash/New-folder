"""Cosmos DB (NoSQL API) conversation / session history store.

Persists each generation interaction (input code + output doc) so sessions
can be replayed, audited, or fed back into future RAG indexing runs.

CosmosDB data model
-------------------
Container : sessions
Partition key : /session_id   ← high cardinality, one logical partition per session
Item schema:
  {
    "id":           "<uuid>",
    "session_id":   "<uuid>",
    "approach":     "rag" | "prompt_based",
    "timestamp":    "<ISO-8601>",
    "input_length": <int>,
    "output_length": <int>,
    "code_snippet": "<first 500 chars>",
    "documentation": "<full markdown>"
  }
"""
import uuid
from datetime import datetime, timezone

from backend.agents.config import config, get_cosmos_client


class CosmosSessionHistory:
    """Stores and retrieves generation history for a given session."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        client = get_cosmos_client()
        self._container = (
            client
            .get_database_client(config.cosmos_database)
            .get_container_client(config.cosmos_sessions_container)
        )

    def save(self, approach: str, code: str, documentation: str) -> str:
        """Persist a generation interaction. Returns the item *id*."""
        item_id = str(uuid.uuid4())
        self._container.upsert_item({
            "id": item_id,
            "session_id": self.session_id,
            "approach": approach,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_length": len(code),
            "output_length": len(documentation),
            "code_snippet": code[:500],
            "documentation": documentation,
        })
        return item_id

    def get_history(self) -> list[dict]:
        """Return all interactions for this session, ordered by timestamp."""
        return list(self._container.query_items(
            query=(
                "SELECT * FROM c WHERE c.session_id = @sid "
                "ORDER BY c.timestamp ASC"
            ),
            parameters=[{"name": "@sid", "value": self.session_id}],
        ))
