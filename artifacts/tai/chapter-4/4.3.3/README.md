# Chapter 4: Sections 4.3.3 and 4.3.4

Core i5-11400H, Ubuntu on WSL2, 5.65 GiB RAM, ClickHouse 26.10.3.7 and PostgreSQL 18.6.

- [formal30m_i5_20261124_105023](formal30m_i5_20261124_105023/) uses 30 million rows and provides the measurements for Tables 4.6 and 4.7. Each configuration has one preparation measurement. Storage is for active table objects. Preparation times are recorded by operation. Source conversions are outside the timers.
- [pilot_i5_20261124_103104](pilot_i5_20261124_103104/) uses 1 million rows to check the workflow. The pilot uses a local sample and has its own provenance. It is separate from Tables 4.6 and 4.7.

The formal i5 run matches all 30 Parquet hashes and 12 of 30 RowBinary hashes in the shared manifest. All five i5 configurations used the same ordered local input. Each COUNT/SUM answer for W0 through W4 matches the published Xeon answer in all five configurations. See checkpoint_answers.json, answer_crosscheck.json, and input_provenance.json.

The [Xeon protocol and results](https://github.com/w1ndS0ng/clickhouse-mergetree-study/tree/tuan/granularity/artifacts/tuan/wsl_xeon/formal43_v3_20261123) provide query latency and plans for Tables 4.3 through 4.5. The archived i5 run log captures progress as of backup. The i5 storage and setup results are verified by a separate checkpoint. The two runs use distinct hardware.
