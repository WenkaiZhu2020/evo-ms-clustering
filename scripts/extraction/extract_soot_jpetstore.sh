#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

MAVEN_BIN="${MAVEN:-mvn}"
TOOL_DIR="tools/soot_extractor"
TOOL_MAIN="org.evomicro.sootextractor.SootExtractorCli"
UV_BIN="${UV:-uv}"

if [[ -z "${SKIP_JPETSTORE_PREPARE:-}" ]]; then
  bash scripts/extraction/prepare_jpetstore.sh
fi

if [[ -z "${JAVA_HOME:-}" ]] && command -v /usr/libexec/java_home >/dev/null 2>&1; then
  JAVA_HOME="$(/usr/libexec/java_home -v 17)"
  export JAVA_HOME
fi

EXTRACTOR_ARGS="$(PYTHONPATH=src "$UV_BIN" run --frozen python scripts/extraction/subject_extraction_config.py --subject jpetstore)"

"$MAVEN_BIN" -q -f "$TOOL_DIR/pom.xml" -DskipTests compile exec:java \
  -Dexec.mainClass="$TOOL_MAIN" \
  -Dexec.args="$EXTRACTOR_ARGS"
