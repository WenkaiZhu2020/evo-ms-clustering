#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MAVEN_BIN="${MAVEN:-mvn}"
TOOL_DIR="tools/soot_extractor"
TOOL_MAIN="org.evomicro.sootextractor.SootExtractorCli"

if [[ -z "${SKIP_DAYTRADER_PREPARE:-}" ]]; then
  bash scripts/prepare_daytrader.sh
fi

if [[ -z "${JAVA_HOME:-}" ]] && command -v /usr/libexec/java_home >/dev/null 2>&1; then
  JAVA_HOME="$(/usr/libexec/java_home -v 17)"
  export JAVA_HOME
fi

"$MAVEN_BIN" -q -f "$TOOL_DIR/pom.xml" -DskipTests compile exec:java \
  -Dexec.mainClass="$TOOL_MAIN" \
  -Dexec.args="--subject daytrader --classes-dir data/raw_projects/daytrader/target/classes --classpath data/raw_projects/daytrader/target/classes --app-packages com.ibm.websphere.samples.daytrader --out-dir data/extracted/daytrader"
