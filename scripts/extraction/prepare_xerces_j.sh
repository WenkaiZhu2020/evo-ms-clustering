#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

REPO_URL="${XERCES_J_REPO_URL:-https://github.com/apache/xerces2-j.git}"
REPO_DIR="data/raw_projects/xerces-j"

if [[ -z "${JAVA_HOME:-}" ]] && command -v /usr/libexec/java_home >/dev/null 2>&1; then
  JAVA_HOME="$(/usr/libexec/java_home -v 17)"
  export JAVA_HOME
fi

if [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/javac" ]]; then
  JAVAC_BIN="$JAVA_HOME/bin/javac"
elif command -v javac >/dev/null 2>&1; then
  JAVAC_BIN="$(command -v javac)"
else
  echo "ERROR: javac not found. Set JAVA_HOME or add javac to PATH." >&2
  exit 1
fi

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone "$REPO_URL" "$REPO_DIR"
fi

(
  cd "$REPO_DIR"
  ./build.sh -Djavac.source=8 -Djavac.target=8 clean prepare-src
  rm -rf target/classes target/xerces_sources.txt
  mkdir -p target/classes
  find build/src/org/apache/xerces build/src/org/apache/xml -type f -name '*.java' | sort > target/xerces_sources.txt
  "$JAVAC_BIN" --release 8 -encoding UTF-8 \
    -cp "tools/icu4j.jar:tools/resolver.jar:tools/serializer.jar" \
    -d target/classes \
    @target/xerces_sources.txt
)

CLASS_COUNT="$(find "$REPO_DIR/target/classes" -type f -name '*.class' | wc -l | tr -d ' ')"
echo "xerces_j_staged_classes=$CLASS_COUNT"
