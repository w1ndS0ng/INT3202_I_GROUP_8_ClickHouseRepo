CREATE TABLE mtr_ha_laptop1_main01.keys_10m_k0
(
    `WatchID` Int64 CODEC(LZ4),
    `UserID` Int64 CODEC(LZ4),
    `CounterID` Int32 CODEC(LZ4),
    `EventDate` Date CODEC(LZ4),
    `EventTime` DateTime('UTC') CODEC(LZ4),
    `RegionID` Int32 CODEC(LZ4),
    `AdvEngineID` Int16 CODEC(LZ4),
    `IsRefresh` Int16 CODEC(LZ4),
    `ResolutionWidth` Int16 CODEC(LZ4),
    `ResolutionHeight` Int16 CODEC(LZ4),
    `DontCountHits` Int16 CODEC(LZ4),
    `ResponseEndTiming` Int32 CODEC(LZ4)
)
ENGINE = MergeTree
ORDER BY tuple()
SETTINGS index_granularity = 8192, index_granularity_bytes = 0, min_bytes_for_wide_part = 0, min_rows_for_wide_part = 0, write_final_mark = 0, fsync_after_insert = 1, auto_statistics_types = '';
