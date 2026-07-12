#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

REPO_DIR="data/raw_projects/jpetstore"

if [[ ! -d "$REPO_DIR" ]]; then
  echo "ERROR: JPetStore source directory not found: $REPO_DIR" >&2
  echo "Clone or place the JPetStore source there before preparing extraction inputs." >&2
  exit 1
fi

if [[ -x "$REPO_DIR/mvnw" ]]; then
  (
    cd "$REPO_DIR"
    ./mvnw clean package -DskipTests
  )
else
  MAVEN_BIN="${MAVEN:-mvn}"
  "$MAVEN_BIN" -f "$REPO_DIR/pom.xml" clean package -DskipTests
fi

CLASS_COUNT="$(find "$REPO_DIR/target/classes" -type f -name '*.class' | wc -l | tr -d ' ')"
echo "jpetstore_staged_classes=$CLASS_COUNT"
