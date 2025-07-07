#!/bin/bash
# Performance benchmarking script (example using pgbench)
pgbench -h localhost -p 5432 -U postgres mydatabase -c 10 -j 10 -t 1000