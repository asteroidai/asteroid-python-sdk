#!/bin/bash

# Define the regex pattern for commit messages
pattern='^\[SDK-[0-9]+\] (feat|fix|docs|style|refactor|perf|test|chore): .{1,80}(\n.*)*$'

# Get the commit messages for the PR
commit_messages=$(git log --format='%H' origin/main..HEAD)

# Check each commit message against the pattern
for commit_hash in $commit_messages; do
  commit_message=$(git log --format=%B -n 1 $commit_hash)
  echo "Checking commit message: $commit_message"
  if ! [[ $commit_message =~ $pattern ]]; then
    echo "Commit message does not match the required pattern:"
    echo "$commit_message"
    exit 1
  fi
done

echo "All commit messages match the required pattern."
