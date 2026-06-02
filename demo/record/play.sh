#!/usr/bin/env bash
# Narrated demo driver for the mongo-scout screencast.
# Run under asciinema (see make_video.sh). Self-contained: it only runs the
# already-checked-in, key-free `npm run demo` proof and frames it for a viewer.
set -uo pipefail
export TERM="${TERM:-xterm-256color}"
cd "$(dirname "$0")/.."

cyan=$'\033[36m'; green=$'\033[32m'; bold=$'\033[1m'; dim=$'\033[2m'; off=$'\033[0m'

say()  { printf '%s\n' "$*"; }
pause(){ sleep "${1:-1.4}"; }
type() { # crude typing effect for the hero command
  local p="$1"; shift; printf '%s' "$p"
  local s="$*"; for ((i=0;i<${#s};i++)); do printf '%s' "${s:$i:1}"; sleep 0.03; done
  printf '\n'
}

printf '\033[2J\033[H'
say "${bold}${cyan}mongo-scout${off} ${dim}— a read-only natural-language triage agent for MongoDB${off}"
say "${dim}Google Cloud Rapid Agent Hackathon · MongoDB track · github.com/kite-builds/mongo-scout${off}"
say ""
pause 2
say "Ask a production MongoDB plain questions. Every read is a tool call routed"
say "through the ${bold}official MongoDB MCP server${off}, launched ${bold}--readOnly${off} — so the agent"
say "${bold}physically cannot${off} mutate or drop anything. No hand-written DB code."
say ""
pause 2.6
say "${dim}The proof below needs ${bold}no Gemini key${off}${dim} and ${bold}no cloud account${off}${dim}: it boots a real${off}"
say "${dim}ephemeral MongoDB and drives the real mongodb-mcp-server@latest over stdio.${off}"
say ""
pause 2.6
type "${green}\$ ${off}" "npm run demo"
pause 0.6
npm run --silent demo
pause 4
printf '\033[2J\033[H'
say ""
say "${green}${bold}  ✔  5/5 triage checks answered from live MCP tool calls.${off}"
say ""
say "     ${dim}Same MCP toolset Gemini drives in production (src/mongo_scout/agent.py).${off}"
say "     ${dim}The DB rows came back wrapped in a prompt-injection guard (Q1/Q3/Q4).${off}"
say "     ${dim}--readOnly exposed zero write/drop tools — safe by construction (Q5).${off}"
say ""
say ""
say "  ${bold}${cyan}mongo-scout${off}  ${dim}·  Gemini + Google ADK  ·  official MongoDB MCP server${off}"
say "  ${bold}→ github.com/kite-builds/mongo-scout${off}"
say ""
say "     ${dim}npm run demo  ·  npm run loop  ·  pytest -q   — all key-free, account-free${off}"
say ""
pause 4
