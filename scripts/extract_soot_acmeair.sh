#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MAVEN_BIN="${MAVEN:-mvn}"
TOOL_DIR="tools/soot_extractor"
TOOL_MAIN="org.evomicro.sootextractor.SootExtractorCli"

"$MAVEN_BIN" -q -f "$TOOL_DIR/pom.xml" -DskipTests compile exec:java \
  -Dexec.mainClass="$TOOL_MAIN" \
  -Dexec.args="--subject acmeair --classes-dir data/raw_projects/acmeair/target/classes --classpath data/raw_projects/acmeair/target/classes --app-packages com.acmeair --out-dir data/extracted/acmeair"
