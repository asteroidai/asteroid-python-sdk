#!/bin/bash

# Define the regex pattern for commit messages
pattern='^\[SDK-[0-9]+\]? ?(feat|fix|docs|style|refactor|perf|test|chore): .{1,80}(\n.*)*$'

# Get the commit messages for the PR
commit_messages=$(git log --format='%H' origin/main..HEAD)

# Check each commit message against the pattern
for commit_hash in $commit_messages; do
  commit_message=$(git log --format=%B -n 1 $commit_hash)
  echo "Checking commit message: $commit_message"
  if ! [[ $commit_message =~ $pattern ]]; then
    echo "Error: Commit message does not match the required pattern!"
    echo "Your message: '$commit_message'"
    echo -e "\nThe message should:"
    # if ! [[ $commit_message =~ ^\[SDK-[0-9]+\] ]]; then
    #   echo "- Start with [SDK-XXX] where XXX is a number"
    # fi
    if ! [[ $commit_message =~ ^\[SDK-[0-9]+\]\ (feat|fix|docs|style|refactor|perf|test|chore): ]]; then
      echo "- Include one of these types after the SDK number: feat, fix, docs, style, refactor, perf, test, chore"
    fi
    if ! [[ $commit_message =~ ^\[SDK-[0-9]+\]\ (feat|fix|docs|style|refactor|perf|test|chore):\ .+ ]]; then
      echo "- Include a description after the type"
    fi
    if [[ ${#commit_message} -gt 80 ]]; then
      echo "- Be no longer than 80 characters on the first line"
    fi
    echo -e "\nExample: [SDK-123] feat: add new awesome feature"
    exit 1
  fi
done

echo "All commit messages match the required pattern."
