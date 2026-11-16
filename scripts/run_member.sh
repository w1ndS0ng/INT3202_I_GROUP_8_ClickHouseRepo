#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 3 ]]; then
  echo "Usage: bash scripts/run_member.sh ha|tuan|tai MACHINE NEW_RUN"
  echo "First prepare all 30 input shards. CH_CONFIG points to a private client.xml."
  exit 2
fi
study_member="$1"
study_machine="$2"
study_run="$3"
case "$study_member" in ha|tuan|tai) ;; *) echo 'Unknown member'; exit 2 ;; esac
cd "$(dirname "$0")/.."
study_args=(--member "$study_member" --machine "$study_machine" --run "$study_run")
python3 scripts/study.py init "${study_args[@]}"
case "$study_member" in
  ha)
    for study_scale in 1m 3m 10m; do
      python3 scripts/study.py build "${study_args[@]}" --experiment keys --scale "$study_scale"
      python3 scripts/study.py queries "${study_args[@]}" --experiment keys --scale "$study_scale"
    done
    python3 scripts/study.py fit "${study_args[@]}"
    python3 scripts/study.py build "${study_args[@]}" --experiment keys --scale 30m
    python3 scripts/study.py forecast "${study_args[@]}"
    python3 scripts/study.py queries "${study_args[@]}" --experiment keys --scale 30m
    python3 scripts/study.py compare "${study_args[@]}"
    ;;
  tuan)
    python3 scripts/study.py build "${study_args[@]}" --experiment granularity --scale 30m
    python3 scripts/study.py queries "${study_args[@]}" --experiment granularity --scale 30m
    ;;
  tai)
    python3 scripts/study.py ingest "${study_args[@]}" --scale 30m
    ;;
esac
python3 scripts/study.py summarize "${study_args[@]}"
echo 'Done. Optionally run plot, then package. Do not pool absolute timings across machines.'
