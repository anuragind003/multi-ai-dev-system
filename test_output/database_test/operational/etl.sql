-- Example ETL script (using COPY command for bulk data loading)
COPY users FROM '/path/to/users.csv' DELIMITER ',' CSV HEADER;