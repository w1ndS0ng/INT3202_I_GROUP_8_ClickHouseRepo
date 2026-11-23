SELECT count() AS matched, sum(ResolutionWidth) AS checksum FROM mtr_ha_laptop1_main01.keys_10m_k2 WHERE CounterID=3258 AND EventDate >= toDate('2013-07-15') AND EventDate < toDate('2013-07-23');
