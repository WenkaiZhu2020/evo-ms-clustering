#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

REPO_URL="${DAYTRADER_REPO_URL:-https://github.com/WASdev/sample.daytrader7.git}"
REPO_DIR="data/raw_projects/daytrader"
MAVEN_BIN="${MAVEN:-mvn}"

if [[ -z "${JAVA_HOME:-}" ]] && command -v /usr/libexec/java_home >/dev/null 2>&1; then
  JAVA_HOME="$(/usr/libexec/java_home -v 17)"
  export JAVA_HOME
fi

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone "$REPO_URL" "$REPO_DIR"
fi

"$MAVEN_BIN" -q -f "$REPO_DIR/pom.xml" -DskipTests package

STAGED_CLASSES="$REPO_DIR/target/classes"
rm -rf "$STAGED_CLASSES"
mkdir -p "$STAGED_CLASSES"

cp -R "$REPO_DIR/daytrader-ee7-ejb/target/classes/." "$STAGED_CLASSES/"
cp -R "$REPO_DIR/daytrader-ee7-web/target/classes/." "$STAGED_CLASSES/"

CLASS_COUNT="$(find "$STAGED_CLASSES" -type f -name '*.class' | wc -l | tr -d ' ')"
echo "daytrader_staged_classes=$CLASS_COUNT"
