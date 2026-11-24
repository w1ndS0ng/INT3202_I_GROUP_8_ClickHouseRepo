SELECT count() AS matched, sum(ResolutionWidth) AS checksum FROM mtr_ha_laptop1_main01.keys_30m_k0 WHERE EventDate >= toDate('2013-07-15') AND EventDate < toDate('2013-07-23');
