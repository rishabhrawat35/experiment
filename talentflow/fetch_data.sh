#!/usr/bin/env bash
# Pulls every record from each TalentFlow Airtable table, paginating at 100/page
# and sleeping between requests to stay under the 5 req/s base limit.
set -euo pipefail
cd "$(dirname "$0")"
source .env

TABLES=(Departments People "Job Openings" Candidates Applications Interviews Offers Findings)

for table in "${TABLES[@]}"; do
  encoded=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$table")
  outfile="data/$(echo "$table" | tr '[:upper:] ' '[:lower:]_').json"
  offset=""
  page=0
  echo "[]" > "$outfile.tmp"

  while : ; do
    url="https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$encoded?pageSize=100"
    if [ -n "$offset" ]; then
      url="$url&offset=$offset"
    fi

    resp=$(curl -s -H "Authorization: Bearer $AIRTABLE_TOKEN" "$url")

    if echo "$resp" | jq -e '.error' > /dev/null 2>&1; then
      echo "ERROR fetching $table (page $page): $(echo "$resp" | jq -c '.error')"
      exit 1
    fi

    jq -s '.[0] + .[1].records' "$outfile.tmp" <(echo "$resp") > "$outfile.tmp2"
    mv "$outfile.tmp2" "$outfile.tmp"

    offset=$(echo "$resp" | jq -r '.offset // empty')
    page=$((page + 1))
    count=$(echo "$resp" | jq '.records | length')
    echo "$table: page $page, +$count records"

    if [ -z "$offset" ]; then
      break
    fi
    sleep 0.25
  done

  mv "$outfile.tmp" "$outfile"
  total=$(jq 'length' "$outfile")
  echo "$table: done, $total total records -> $outfile"
  sleep 0.25
done
