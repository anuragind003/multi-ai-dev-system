# Architecture Decision Record 1: Database Choice

**Date:** 2023-10-27

**Decision:** Use PostgreSQL as the primary database.

**Status:** Approved

**Context:** We need to choose a database for our web application.  We considered several options, including MySQL, MongoDB, and PostgreSQL.

**Considerations:**

*   **PostgreSQL:**  Robust, reliable, supports complex queries, ACID compliant.
*   **MySQL:**  Popular, widely supported, good performance.
*   **MongoDB:**  NoSQL, flexible schema, good for unstructured data.

**Decision Drivers:**

*   ACID compliance is important for data integrity.
*   We anticipate needing complex queries.
*   PostgreSQL has a strong reputation for reliability.

**Consequences:**

*   Increased complexity compared to a NoSQL database.
*   Requires more careful schema design.