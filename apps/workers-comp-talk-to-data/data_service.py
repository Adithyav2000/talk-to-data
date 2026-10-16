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
import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import config

logger = logging.getLogger(__name__)


def _q(value) -> str:
    """Escape a value for use inside a single-quoted SQL string literal."""
    return str(value).replace("\\", "\\\\").replace("'", "''")


def _check_state(state: str) -> str:
    if state not in config.DATA_CALL_STATES or state == "All":
        raise ValueError(f"Invalid state: {state!r}")
    return state


class DataService:
    """All SQL operations for compliance data-calls and IT-review workflow."""

    def __init__(self):
        pat = os.environ.get("DATABRICKS_PAT")
        if pat:
            if not pat.startswith(("dapi", "dose", "eyJ")):
                raise ValueError(
                    "DATABRICKS_PAT is not a Databricks access token (expected it to "
                    "start with 'dapi'). Generate one in Databricks: User Settings > "
                    "Developer > Access tokens, then set it in .env and restart."
                )
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
        def val(s):
            return s if isinstance(s, str) else getattr(s, "value", "")

        # An explicit warehouse (e.g. the app's SQL-warehouse resource) beats discovery,
        # which needs permission to list every warehouse.
        explicit = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
        if explicit:
            self.warehouse_id = explicit
            logger.info("Using configured warehouse %s", explicit)
            return

        try:
            whs = list(self.w.warehouses.list())
        except Exception as exc:
            logger.error("Warehouse discovery failed: %s", exc)
            return
        if not whs:
            return

        def rank(wh):
            running = val(getattr(wh, "state", None)) == "RUNNING"
            serverless = bool(getattr(wh, "enable_serverless_compute", False))
            return (not running, not serverless)

        best = min(whs, key=rank)
        self.warehouse_id = best.id
        logger.info("Using warehouse %s (%s, %s)", best.name, best.id, val(getattr(best, "state", None)))

    # ------------------------------------------------------------------
    # Generic SQL runner
    # ------------------------------------------------------------------
    def execute_sql(self, sql: str) -> dict:
        """Return {columns, rows} or {error}."""
        if not self.warehouse_id:
            self._discover_warehouse()
        if not self.warehouse_id:
            return {"error": "No SQL warehouse is available in this Databricks workspace."}
        try:
            api = self.w.statement_execution
            resp = api.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                wait_timeout="30s",
            )
            deadline = time.monotonic() + 120
            pending = (StatementState.PENDING, StatementState.RUNNING)
            while resp.status and resp.status.state in pending and time.monotonic() < deadline:
                time.sleep(2)
                resp = api.get_statement(resp.statement_id)

            state = resp.status.state if resp.status else None
            if state == StatementState.SUCCEEDED:
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
            if state in pending:
                try:
                    api.cancel_execution(resp.statement_id)
                except Exception:
                    pass
                self.warehouse_id = None
                return {"error": "The SQL warehouse is still starting up. Wait a minute and refresh."}
            err = resp.status.error if resp.status else None
            msg = getattr(err, "message", None) or str(err or f"Query did not succeed (state: {getattr(state, 'value', state)})")
            return {"error": msg}
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Table bootstrap (only IT requests -- data-calls table already exists)
    # ------------------------------------------------------------------
    def ensure_tables_exist(self):
        res = self.execute_sql(f"""
            CREATE TABLE IF NOT EXISTS {config.IT_REQUESTS_TABLE} (
                id                    BIGINT GENERATED ALWAYS AS IDENTITY,
                request_description   STRING NOT NULL,
                matched_data_call     STRING,
                similarity_score      DOUBLE,
                is_new_request        BOOLEAN,
                status                STRING,
                genie_sql             STRING,
                reviewed_by           STRING,
                review_notes          STRING,
                requested_by          STRING,
                requested_at          TIMESTAMP,
                reviewed_at           TIMESTAMP,
                category              STRING
            )
        """)
        if "error" in res:
            logger.error("Could not create %s: %s", config.IT_REQUESTS_TABLE, res["error"])
        # Tables created before registries were scoped lack `category`; add it
        # (errors if it already exists -- that is fine).
        self.has_category = "error" not in self.execute_sql(
            f"SELECT category FROM {config.IT_REQUESTS_TABLE} LIMIT 1"
        )
        if not self.has_category:
            alter = self.execute_sql(
                f"ALTER TABLE {config.IT_REQUESTS_TABLE} ADD COLUMNS (category STRING)"
            )
            self.has_category = "error" not in alter
            if not self.has_category:
                logger.warning("Requests table has no category column: %s", alter["error"])

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
            clauses.append(f"state = '{_q(state)}'")
        if name_search:
            clauses.append(f"LOWER(data_call_name) LIKE LOWER('%{_q(name_search)}%')")
        where = " AND ".join(clauses)
        return self.execute_sql(
            f"SELECT data_call_id, data_call_name, file_name, description, state "
            f"FROM {tbl} WHERE {where} ORDER BY data_call_id"
        )

    def get_data_call_sql(self, asset_location: str) -> str | None:
        """Read the SQL content of a registry asset (workspace file or UC volume file)."""
        path = (asset_location or "").strip()
        if not path:
            return None
        try:
            if path.startswith("/Volumes/"):
                return self.w.files.download(path).contents.read().decode("utf-8")
            import base64
            # Default export format returns files as-is (and notebooks as source).
            resp = self.w.workspace.export(path=path)
            if resp.content:
                return base64.b64decode(resp.content).decode("utf-8")
        except Exception as exc:
            logger.warning("Could not read SQL file %s: %s", path, exc)
        return None

    def get_data_call_asset(self, table: str, data_call_id: int) -> dict | None:
        """Registry row (name, file, asset location) for one data call."""
        if table not in config.DATA_CALL_CATEGORIES.values():
            raise ValueError(f"Unknown registry table: {table!r}")
        res = self.execute_sql(
            f"SELECT data_call_name, file_name, asset_location FROM {table} "
            f"WHERE data_call_id = {int(data_call_id)}"
        )
        if "error" in res:
            raise RuntimeError(res["error"])
        if not res.get("rows"):
            return None
        name, file_name, location = res["rows"][0]
        return {"name": name, "file_name": file_name, "asset_location": location}

    # ------------------------------------------------------------------
    # Registry sync: persist SQL of IT-approved calls as files next to the others
    # ------------------------------------------------------------------
    def list_unsynced(self) -> list[dict]:
        """Registry rows with no SQL asset file (created by approving a request)."""
        items: list[dict] = []
        for category, table in config.DATA_CALL_CATEGORIES.items():
            res = self.execute_sql(
                f"SELECT data_call_id, data_call_name, file_name, description FROM {table} "
                f"WHERE asset_location IS NULL OR TRIM(asset_location) = '' ORDER BY data_call_id"
            )
            if "error" in res:
                raise RuntimeError(f"{category} registry: {res['error']}")
            for cid, name, file_name, description in res["rows"]:
                items.append({
                    "category": category, "dataCallId": int(cid), "name": name,
                    "fileName": file_name, "description": description,
                    "hasSql": bool(self.get_approved_sql(file_name)),
                })
        return items

    def _asset_folder_and_next_number(self, table: str, category: str) -> tuple[str, int]:
        import posixpath, re
        from collections import Counter
        res = self.execute_sql(
            f"SELECT file_name, asset_location FROM {table} "
            f"WHERE asset_location IS NOT NULL AND TRIM(asset_location) <> ''"
        )
        if "error" in res:
            raise RuntimeError(res["error"])
        folders = Counter(posixpath.dirname(loc) for _, loc in res["rows"] if loc)
        numbers = [int(m.group(1)) for fn, _ in res["rows"] if (m := re.match(r"(\d+)_", fn or ""))]
        if folders:
            folder = folders.most_common(1)[0][0]
        elif config.SQL_ASSET_ROOT:
            folder = f"{config.SQL_ASSET_ROOT.rstrip('/')}/{category.lower().replace(' ', '_')}"
        else:
            raise RuntimeError(
                f"No existing SQL files in the {category} registry to copy the location from. "
                "Set SQL_ASSET_ROOT to a workspace folder."
            )
        return folder, (max(numbers) + 1 if numbers else 1)

    def sync_to_registry(self, items: list[dict], synced_by: str) -> list[dict]:
        """Write each item's SQL to a workspace file and point its registry row at it."""
        import io, re
        from databricks.sdk.service.workspace import ImportFormat

        plan: dict[str, tuple[str, int]] = {}
        results = []
        for it in items:
            category = it["category"]
            try:
                table = config.DATA_CALL_CATEGORIES[category]
                sql = self.get_approved_sql(it["fileName"])
                if not sql:
                    raise RuntimeError("No approved SQL was found for this data call.")
                if category not in plan:
                    plan[category] = self._asset_folder_and_next_number(table, category)
                folder, number = plan[category]
                slug = re.sub(r"[^a-z0-9]+", "_", str(it["name"]).lower()).strip("_")[:60] or "data_call"
                file_name = f"{number:02d}_{slug}.sql"
                path = f"{folder}/{file_name}"
                header = (
                    f"-- Data call: {it['name']}\n"
                    f"-- Registered by Claimsight from {it['fileName']} (synced by {synced_by})\n\n"
                )
                body = sql.strip().rstrip(";") + ";\n"
                self.w.workspace.upload(path, io.BytesIO((header + body).encode("utf-8")),
                                        format=ImportFormat.AUTO, overwrite=False)
                res = self.execute_sql(
                    f"UPDATE {table} SET file_name = '{_q(file_name)}', asset_location = '{_q(path)}' "
                    f"WHERE data_call_id = {int(it['dataCallId'])}"
                )
                if "error" in res:
                    raise RuntimeError(f"File written to {path}, but the registry update failed: {res['error']}")
                plan[category] = (folder, number + 1)
                results.append({**it, "ok": True, "fileName": file_name, "assetLocation": path})
            except Exception as exc:
                results.append({**it, "ok": False, "error": str(exc)})
        return results

    def get_approved_sql(self, file_name: str) -> str | None:
        """SQL stored with an IT-approved request (registry file name `approved_<id>.sql`)."""
        import re
        m = re.fullmatch(r"approved_(\d+)\.sql", file_name or "")
        if not m:
            return None
        res = self.execute_sql(
            f"SELECT genie_sql FROM {config.IT_REQUESTS_TABLE} WHERE id = {int(m.group(1))}"
        )
        rows = res.get("rows") or []
        return rows[0][0] if rows and rows[0][0] else None

    def get_it_requests(
        self, status_filter: str | None = None, requested_by: str | None = None
    ) -> dict:
        clause = ""
        if status_filter and status_filter != "All":
            clause += f" AND status = '{_q(status_filter)}'"
        if requested_by:
            clause += f" AND requested_by = '{_q(requested_by)}'"
        return self.execute_sql(
            f"SELECT * FROM {config.IT_REQUESTS_TABLE} WHERE 1=1{clause} "
            f"ORDER BY requested_at DESC"
        )

    # ------------------------------------------------------------------
    # Semantic matching against existing registry descriptions
    # ------------------------------------------------------------------
    def find_similar_data_call(
        self, description: str, category: str | None = None
    ) -> tuple[str | None, float]:
        names: list[str] = []
        descs: list[str] = []
        tables = (
            [config.DATA_CALL_CATEGORIES[category]] if category in config.DATA_CALL_CATEGORIES
            else list(config.DATA_CALL_CATEGORIES.values())
        )
        for tbl in tables:
            result = self.execute_sql(
                f"SELECT data_call_name, description FROM {tbl}"
            )
            if "error" in result:
                logger.warning("Similarity lookup failed for %s: %s", tbl, result["error"])
                continue
            for r in result.get("rows", []):
                names.append(r[0])
                descs.append(r[1] or "")
        if not names:
            return None, 0.0

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
    def submit_request(self, description: str, requested_by: str, category: str | None = None) -> dict:
        matched, score = self.find_similar_data_call(description, category)
        is_new = matched is None
        safe_desc = _q(description)
        matched_val = f"'{_q(matched)}'" if matched else "NULL"
        with_cat = bool(category) and getattr(self, "has_category", False)
        res = self.execute_sql(f"""
            INSERT INTO {config.IT_REQUESTS_TABLE}
            (request_description, matched_data_call, similarity_score,
             is_new_request, status, requested_by, requested_at{", category" if with_cat else ""})
            VALUES ('{safe_desc}', {matched_val}, {score}, {is_new},
                    'pending', '{_q(requested_by)}', current_timestamp(){f", '{_q(category)}'" if with_cat else ""})
        """)
        if "error" in res:
            raise RuntimeError(res["error"])
        return {
            "is_new": is_new,
            "matched_name": matched,
            "similarity_score": score,
        }

    def approve_request(
        self, request_id: int, reviewer: str,
        sql_query: str, data_call_name: str, description: str, state: str,
        table: str | None = None,
    ):
        table = table or config.DATA_CALLS_TABLE
        if table not in config.DATA_CALL_CATEGORIES.values():
            raise ValueError(f"Unknown registry table: {table!r}")
        state = _check_state(state)
        request_id = int(request_id)
        safe_sql = _q(sql_query)
        safe_name = _q(data_call_name)
        safe_desc = _q(description)
        # Also insert into the registry so new call appears immediately
        next_id = self.execute_sql(
            f"SELECT COALESCE(MAX(data_call_id), 0) + 1 FROM {table}"
        )
        nid = int(next_id["rows"][0][0]) if next_id.get("rows") else 99
        res = self.execute_sql(f"""
            INSERT INTO {table}
            (data_call_id, data_call_name, file_name, asset_location,
             description, state)
            VALUES ({nid}, '{safe_name}', 'approved_{request_id}.sql',
                    '', '{safe_desc}', '{state}')
        """)
        if "error" in res:
            raise RuntimeError(res["error"])
        res = self.execute_sql(f"""
            UPDATE {config.IT_REQUESTS_TABLE}
            SET status = 'approved', reviewed_by = '{_q(reviewer)}',
                genie_sql = '{safe_sql}', reviewed_at = current_timestamp()
            WHERE id = {request_id}
        """)
        if "error" in res:
            raise RuntimeError(res["error"])

    def set_call_state(self, table: str, data_call_id: int, state: str):
        """Governance sign-off: record a data call's test state in its registry."""
        if table not in config.DATA_CALL_CATEGORIES.values():
            raise ValueError(f"Unknown registry table: {table!r}")
        res = self.execute_sql(
            f"UPDATE {table} SET state = '{_check_state(state)}' WHERE data_call_id = {int(data_call_id)}"
        )
        if "error" in res:
            raise RuntimeError(res["error"])

    def reject_request(self, request_id: int, reviewer: str, notes: str):
        res = self.execute_sql(f"""
            UPDATE {config.IT_REQUESTS_TABLE}
            SET status = 'rejected', reviewed_by = '{_q(reviewer)}',
                review_notes = '{_q(notes)}', reviewed_at = current_timestamp()
            WHERE id = {int(request_id)}
        """)
        if "error" in res:
            raise RuntimeError(res["error"])
