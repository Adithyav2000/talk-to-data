"""Genie API client wrapper for the Claimsight app."""

import os
import time
import logging
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class GenieClient:
    """Thin wrapper around the Databricks Genie conversational-query API."""

    def __init__(self, space_id: str):
        pat = os.environ.get("DATABRICKS_PAT")
        if pat:
            self.w = WorkspaceClient(
                host=os.environ.get("DATABRICKS_HOST"),
                token=pat,
                auth_type="pat",
            )
        else:
            self.w = WorkspaceClient()
        self.space_id = space_id

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def ask(
        self,
        question: str,
        conversation_id: str | None = None,
        timeout: int = 120,
    ) -> dict:
        """Send *question* to the Genie space and return a result dict.

        Keys returned (all optional):
            columns        – list[str]
            rows           – list[list]
            sql            – the SQL Genie executed (if any)
            text           – free-text reply (when no query was run)
            conversation_id
            message_id
            error          – error string on failure
        """
        try:
            conversation_id, message_id = self._send(question, conversation_id)
            self._poll(conversation_id, message_id, timeout)
            return self._collect(conversation_id, message_id)
        except Exception as exc:
            logger.error("Genie API error: %s", exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _send(self, question: str, conversation_id: str | None):
        if conversation_id is None:
            resp = self.w.genie.start_conversation(
                space_id=self.space_id, content=question
            )
            return resp.conversation_id, resp.message_id
        resp = self.w.genie.create_message(
            space_id=self.space_id,
            conversation_id=conversation_id,
            content=question,
        )
        return conversation_id, resp.message_id

    def _poll(self, cid: str, mid: str, timeout: int):
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self.w.genie.get_message(self.space_id, cid, mid)
            status = getattr(msg, "status", None)
            if status is None:
                time.sleep(2)
                continue
            val = status if isinstance(status, str) else getattr(status, "value", str(status))
            if val in ("COMPLETED", "EXECUTING_QUERY"):
                if val == "COMPLETED":
                    return
            elif val in ("FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
                raise RuntimeError(f"Genie message {val}")
            time.sleep(2)
        raise TimeoutError("Genie did not complete within timeout")

    def _extract_sql(self, msg) -> str | None:
        for att in getattr(msg, "attachments", None) or []:
            q = getattr(att, "query", None)
            if q:
                return getattr(q, "query", None)
        return None

    def _collect(self, cid: str, mid: str) -> dict:
        msg = self.w.genie.get_message(self.space_id, cid, mid)
        sql_text = self._extract_sql(msg)

        # Collect any plain-text reply (save for later, don't return yet)
        text_content = None
        for att in getattr(msg, "attachments", None) or []:
            txt = getattr(att, "text", None)
            if txt and getattr(txt, "content", None):
                text_content = txt.content
                break

        # Always try to fetch tabular result FIRST
        try:
            result = self.w.genie.get_message_query_result(
                self.space_id, cid, mid
            )
            stmt = result.statement_response
            columns = [c.name for c in stmt.manifest.schema.columns]
            rows = []
            if stmt.result and stmt.result.data_array:
                rows = [list(r) for r in stmt.result.data_array]
            out = {
                "columns": columns,
                "rows": rows,
                "sql": sql_text,
                "conversation_id": cid,
                "message_id": mid,
            }
            if text_content:
                out["text"] = text_content
            return out
        except Exception as exc:
            logger.warning("No tabular result: %s", exc)
            # Fall back to text-only reply
            return {
                "text": text_content or getattr(msg, "content", str(exc)),
                "sql": sql_text,
                "conversation_id": cid,
                "message_id": mid,
            }
