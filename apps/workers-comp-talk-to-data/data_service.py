"""Data service -- SQL execution, CRUD, and semantic matching for data calls.

Reads from the existing registry table:
    workers_comp_insurance.data_call_registry.compliance_data_calls
    Columns: data_call_id, data_call_name, file_name, asset_location,
             description, state (TESTED_PASS | TESTED_FAIL | NA)

IT review requests are stored in:
    easewithdata_adb.bronze.it_review_requests
"""

import logging
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import config

logger = logging.getLogger(__name__)


class DataService:
    """All SQL operations for compliance data-calls and IT-review workflow."""

    def __init__(self):
        pat = os.environ.get("DATABRICKS_PAT")
        if pat:
            self.w = WorkspaceClient(
                host=os.environ.get("DATABRICKS_HOST"),
                token=pat,
                auth_type="pat",
            )
        else:
            self.w = WorkspaceClient()
        self.warehouse_id: str | None = None
        self._discover_warehouse()

    # ------------------------------------------------------------------
    # Warehouse auto-discovery
    # ------------------------------------------------------------------
    def _discover_warehouse(self):
        try:
            for wh in self.w.warehouses.list():
                state = getattr(wh, "state", None)
                val = state if isinstance(state, str) else getattr(state, "value", "")
                if val == "RUNNING":
                    self.warehouse_id = wh.id
                    logger.info("Using warehouse %s (%s)", wh.name, wh.id)
                    return
            for wh in self.w.warehouses.list():
                self.warehouse_id = wh.id
                logger.info("Fallback warehouse %s (%s)", wh.name, wh.id)
                return
        except Exception as exc:
            logger.error("Warehouse discovery failed: %s", exc)

    # ------------------------------------------------------------------
    # Generic SQL runner
    # ------------------------------------------------------------------
    def execute_sql(self, sql: str) -> dict:
        """Return {columns, rows} or {error}."""
        try:
            resp = self.w.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                wait_timeout="50s",
            )
            if resp.status and resp.status.state == StatementState.SUCCEEDED:
                cols = (
                    [c.name for c in resp.manifest.schema.columns]
                    if resp.manifest
                    else []
                )
                rows = (
                    [list(r) for r in resp.result.data_array]
                    if resp.result and resp.result.data_array
                    else []
                )
                return {"columns": cols, "rows": rows}
            err = resp.status.error if resp.status else "Unknown"
            return {"error": str(err)}
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Table bootstrap (only IT requests -- data-calls table already exists)
    # ------------------------------------------------------------------
    def ensure_tables_exist(self):
        self.execute_sql(f"""
            CREATE TABLE IF NOT EXISTS {config.IT_REQUESTS_TABLE} (
                id                    BIGINT GENERATED ALWAYS AS IDENTITY,
                request_description   STRING NOT NULL,
                matched_data_call     STRING,
                similarity_score      DOUBLE,
                is_new_request        BOOLEAN,
                status                STRING DEFAULT 'pending',
                genie_sql             STRING,
                reviewed_by           STRING,
                review_notes          STRING,
                requested_by          STRING,
                requested_at          TIMESTAMP DEFAULT current_timestamp(),
                reviewed_at           TIMESTAMP
            )
        """)

    # ------------------------------------------------------------------
    # Data-call queries (reads existing registry table)
    # ------------------------------------------------------------------
    def get_data_calls(
        self,
        table: str | None = None,
        state: str | None = None,
        name_search: str | None = None,
    ) -> dict:
        tbl = table or config.DATA_CALLS_TABLE
        clauses = ["1=1"]
        if state and state != "All":
            clauses.append(f"state = '{state}'")
        if name_search:
            safe = name_search.replace("'", "''")
            clauses.append(f"LOWER(data_call_name) LIKE LOWER('%{safe}%')")
        where = " AND ".join(clauses)
        return self.execute_sql(
            f"SELECT data_call_id, data_call_name, file_name, description, state "
            f"FROM {tbl} WHERE {where} ORDER BY data_call_id"
        )

    def get_data_call_sql(self, asset_location: str) -> str | None:
        """Read the SQL content from a workspace file path."""
        try:
            import base64
            resp = self.w.workspace.export(path=asset_location, format="AUTO")
            if resp.content:
                return base64.b64decode(resp.content).decode("utf-8")
        except Exception as exc:
            logger.warning("Could not read SQL file %s: %s", asset_location, exc)
        return None

    def get_it_requests(self, status_filter: str | None = None) -> dict:
        clause = (
            "" if not status_filter or status_filter == "All"
            else f" AND status = '{status_filter}'"
        )
        return self.execute_sql(
            f"SELECT * FROM {config.IT_REQUESTS_TABLE} WHERE 1=1{clause} "
            f"ORDER BY requested_at DESC"
        )

    # ------------------------------------------------------------------
    # Semantic matching against existing registry descriptions
    # ------------------------------------------------------------------
    def find_similar_data_call(self, description: str) -> tuple[str | None, float]:
        result = self.execute_sql(
            f"SELECT data_call_name, description FROM {config.DATA_CALLS_TABLE}"
        )
        if "error" in result or not result.get("rows"):
            return None, 0.0

        names = [r[0] for r in result["rows"]]
        descs = [r[1] or "" for r in result["rows"]]

        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(descs + [description])
        sims = cosine_similarity(matrix[-1:], matrix[:-1])[0]

        best = int(sims.argmax())
        score = float(sims[best])
        if score >= config.SIMILARITY_THRESHOLD:
            return names[best], score
        return None, score

    # ------------------------------------------------------------------
    # Request lifecycle
    # ------------------------------------------------------------------
    def submit_request(self, description: str, requested_by: str) -> dict:
        matched, score = self.find_similar_data_call(description)
        is_new = matched is None
        safe_desc = description.replace("'", "''")
        matched_val = f"'{matched}'" if matched else "NULL"
        self.execute_sql(f"""
            INSERT INTO {config.IT_REQUESTS_TABLE}
            (request_description, matched_data_call, similarity_score,
             is_new_request, status, requested_by)
            VALUES ('{safe_desc}', {matched_val}, {score}, {is_new},
                    'pending', '{requested_by}')
        """)
        return {
            "is_new": is_new,
            "matched_name": matched,
            "similarity_score": score,
        }

    def approve_request(
        self, request_id: int, reviewer: str,
        sql_query: str, data_call_name: str, description: str, state: str,
    ):
        safe_sql = sql_query.replace("'", "''")
        safe_name = data_call_name.replace("'", "''")
        safe_desc = description.replace("'", "''")
        self.execute_sql(f"""
            UPDATE {config.IT_REQUESTS_TABLE}
            SET status = 'approved', reviewed_by = '{reviewer}',
                genie_sql = '{safe_sql}', reviewed_at = current_timestamp()
            WHERE id = {request_id}
        """)
        # Also insert into the registry so new call appears immediately
        next_id = self.execute_sql(
            f"SELECT COALESCE(MAX(data_call_id), 0) + 1 FROM {config.DATA_CALLS_TABLE}"
        )
        nid = int(next_id["rows"][0][0]) if next_id.get("rows") else 99
        self.execute_sql(f"""
            INSERT INTO {config.DATA_CALLS_TABLE}
            (data_call_id, data_call_name, file_name, asset_location,
             description, state)
            VALUES ({nid}, '{safe_name}', 'approved_{request_id}.sql',
                    '', '{safe_desc}', '{state}')
        """)

    def reject_request(self, request_id: int, reviewer: str, notes: str):
        safe = notes.replace("'", "''")
        self.execute_sql(f"""
            UPDATE {config.IT_REQUESTS_TABLE}
            SET status = 'rejected', reviewed_by = '{reviewer}',
                review_notes = '{safe}', reviewed_at = current_timestamp()
            WHERE id = {request_id}
        """)
