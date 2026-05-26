#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MAVEN_BIN="${MAVEN:-mvn}"
TOOL_DIR="tools/soot_extractor"
TOOL_MAIN="org.evomicro.sootextractor.SootExtractorCli"
PROJECT_DIR="data/raw_projects/xerces-j"
CLASSES_DIR="$PROJECT_DIR/target/classes"
CLASSPATH="$CLASSES_DIR:$PROJECT_DIR/tools/icu4j.jar:$PROJECT_DIR/tools/resolver.jar:$PROJECT_DIR/tools/serializer.jar"

if [[ -z "${SKIP_XERCES_J_PREPARE:-}" ]]; then
  bash scripts/prepare_xerces_j.sh
fi

if [[ -z "${JAVA_HOME:-}" ]] && command -v /usr/libexec/java_home >/dev/null 2>&1; then
  JAVA_HOME="$(/usr/libexec/java_home -v 17)"
  export JAVA_HOME
fi

"$MAVEN_BIN" -q -f "$TOOL_DIR/pom.xml" -DskipTests compile exec:java \
  -Dexec.mainClass="$TOOL_MAIN" \
  -Dexec.args="--subject xerces-j --classes-dir $CLASSES_DIR --classpath $CLASSPATH --app-packages org.apache.xerces,org.apache.xml --out-dir data/extracted/xerces-j"
