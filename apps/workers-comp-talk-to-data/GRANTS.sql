-- Permissions the deployed Claimsight app needs.
--
-- A Databricks App runs as its own service principal, not as the person who deployed it,
-- so it needs its own access. Run this in a SQL editor as a user who can grant on these
-- objects (catalog owner / metastore admin).
--
-- Service principal for this app:
--   name:      app-40rq8w workers-comp-talk-to-data
--   client id: aeb240eb-ccf6-4bae-ba50-9a4862b9e8da
-- (Compute > Apps > workers-comp-talk-to-data shows it under "Authorization".)

-- 1. Registry and claims data: read everything the data-call SQL files query.
GRANT USE CATALOG ON CATALOG workers_comp_insurance TO `aeb240eb-ccf6-4bae-ba50-9a4862b9e8da`;
GRANT USE SCHEMA, SELECT ON CATALOG workers_comp_insurance TO `aeb240eb-ccf6-4bae-ba50-9a4862b9e8da`;

-- 2. Registry tables are updated by IT approval, governance sign-off and Sync to registry.
GRANT MODIFY ON SCHEMA workers_comp_insurance.data_call_registry TO `aeb240eb-ccf6-4bae-ba50-9a4862b9e8da`;

-- 3. IT request log (created and written by the app).
GRANT USE CATALOG ON CATALOG easewithdata_adb TO `aeb240eb-ccf6-4bae-ba50-9a4862b9e8da`;
GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE ON SCHEMA easewithdata_adb.bronze TO `aeb240eb-ccf6-4bae-ba50-9a4862b9e8da`;

-- Not SQL grants -- also needed, set in the Databricks UI:
--   * SQL warehouse: add the service principal with CAN USE (or add the warehouse as an app
--     resource and set DATABRICKS_WAREHOUSE_ID).
--   * Genie space (Ask Data, IT SQL drafting): Share > add the service principal with CAN RUN.
--   * Workspace folder .../workers_comp_sql_reports: Share > add the service principal with
--     CAN EDIT (CAN READ is enough to run data calls; Sync to registry also writes files).
