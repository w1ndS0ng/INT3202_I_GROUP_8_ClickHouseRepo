CREATE INDEX pg1_idx ON cmp_pilot42_v2_20261123.pg1 USING brin (CounterID,EventDate) WITH (pages_per_range=128);
