# Load environment variables from .env into the current process.
# Usage (from repo root): . scripts/load-env.sh
# Or: . scripts/load-env.sh .env
# After loading, run: uvicorn app.api.main:app --host 0.0.0.0 --port 8000
# and in another terminal (after loading env again): python -m arq app.workers.arq_tasks.WorkerSettings

_PATH="${1:-.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
if [ -z "${_PATH##*/*}" ]; then
  ENV_FILE="$_PATH"
else
  ENV_FILE="$REPO_ROOT/$_PATH"
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE" >&2
  if [ "$_PATH" = ".env" ]; then
    echo "Copy .env.example to .env and fill in your values, then run this script again." >&2
  fi
  return 2>/dev/null || exit 1
fi

while IFS= read -r line || [ -n "$line" ]; do
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [ -z "$line" ] && continue
  [ "${line#\#}" != "$line" ] && continue
  if printf '%s' "$line" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*='; then
    key="${line%%=*}"
    key="$(printf '%s' "$key" | sed 's/[[:space:]]*$//')"
    val="${line#*=}"
    val="$(printf '%s' "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [ -n "$val" ] && [ "${val#\"}" != "$val" ] && [ "${val%\"}" != "$val" ]; then
      val="${val%\"}"
      val="${val#\"}"
    elif [ -n "$val" ] && [ "${val#\'}" != "$val" ] && [ "${val%\'}" != "$val" ]; then
      val="${val%\'}"
      val="${val#\'}"
    fi
    export "$key=$val"
  fi
done < "$ENV_FILE"
echo "Loaded env from $ENV_FILE"
