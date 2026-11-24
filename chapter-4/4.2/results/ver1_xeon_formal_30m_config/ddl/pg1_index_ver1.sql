CREATE INDEX pg1_idx ON cmp_formal43_v3_20261123.pg1 USING brin (CounterID,EventDate) WITH (pages_per_range=128);
