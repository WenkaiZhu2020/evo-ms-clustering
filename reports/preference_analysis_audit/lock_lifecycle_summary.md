# Lock/PID lifecycle

The analysis runner uses an exclusive `fcntl` lock with PID, command, branch, HEAD, start time, working directory, output directory, and hostname metadata. Active PIDs are rejected before stale removal. A dead lock is removable only for the current command/branch; foreign branch/command metadata is rejected. The unrelated Xerces tail process was not touched.
