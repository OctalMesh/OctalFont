#!/usr/bin/env bash

# ============================================================================ #
# Shared constants, path definitions, YAML helpers, and result tracking.       #
#                                                                              #
# Provides:                                                                    #
#   REPO_ROOT, SOURCES_DIR, FONTS_DIR, LOG_DIR, VENV_DIR, PROJECT_CONFIG       #
#   PYTHON - active Python interpreter (venv-first, falls back to system)      #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_COMMON_LOADED:-}" ]] && return 0
readonly _OCTALFONT_COMMON_LOADED=1

# ============================================================================ #
#                                  Variables                                   #
# ============================================================================ #

# Absolute path to the repository root (two levels up from tools/shell/).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export REPO_ROOT

export SOURCES_DIR="${REPO_ROOT}/sources"
export FONTS_DIR="${REPO_ROOT}/fonts"
export LOG_DIR="${REPO_ROOT}/logs"
export VENV_DIR="${REPO_ROOT}/venv"
export PROJECT_CONFIG="${SOURCES_DIR}/config.yaml"

# Activate the virtual-environment Python if available; fall back to system.
if [[ -f "${VENV_DIR}/bin/python" ]]; then
    PYTHON="${VENV_DIR}/bin/python"
elif [[ -f "${VENV_DIR}/Scripts/python.exe" ]]; then
    # Git-Bash / WSL path for Windows venvs
    PYTHON="${VENV_DIR}/Scripts/python"
else
    # Find the first Python >= 3.9 that actually runs (skip Windows Store stubs)
    PYTHON=""
    for _py in python3 python py; do
        _py_path="$(command -v "${_py}" 2>/dev/null)" || continue
        if "${_py_path}" -c "import sys; assert sys.version_info >= (3,9)" 2>/dev/null; then
            PYTHON="${_py_path}"; break
        fi
    done
    unset _py _py_path
fi
export PYTHON

# Result-tracking arrays - populated by _record_result, printed by print_summary.

declare -a _RESULT_FAMILIES=()
declare -a _RESULT_STATUSES=()
declare -a _RESULT_DURATIONS=()

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Returns the scalar value at a dotted key path inside a YAML file.
# Uses Python to avoid a hard dependency on yq/shyaml.
#
# Arguments:
#   $1 - Dotted key path (e.g. "outputDir")
#   $2 - Absolute path to the YAML file
function _yaml_get() {
    local key_path="$1"
    local yaml_file="$2"
    "${PYTHON}" - "${yaml_file}" "${key_path}" <<'EOF'
import sys, yaml
def get(doc, path):
    for k in path.split('.'):
        doc = doc[k]
    return doc
with open(sys.argv[1]) as f:
    doc = yaml.safe_load(f)
val = get(doc, sys.argv[2])
print(val if val is not None else '')
EOF
}

# Prints one "id:name:config" triple per line for families matching the given
# status filter. An empty filter returns all families.
#
# Arguments:
#   $1 - Status filter ("active", "inactive", or "" for all families)
#   $2 - Absolute path to the project config YAML
function _yaml_families() {
    local status_filter="$1"
    local yaml_file="$2"
    "${PYTHON}" - "${yaml_file}" "${status_filter}" <<'EOF'
import sys, yaml
with open(sys.argv[1]) as f:
    families = yaml.safe_load(f).get('families', [])
status_filter = sys.argv[2]
for fam in families:
    if not status_filter or fam.get('status') == status_filter:
        print(f"{fam['id']}:{fam['name']}:{fam['config']}")
EOF
}

# Resolves a colon-separated "id:name:config" triple into the FAM_ID, FAM_NAME,
# and FAM_CONFIG exported shell variables.
#
# Arguments:
#   $1 - Triple string, e.g. "titan:OctalFont-Titan:OctalFont-Titan/config.yaml"
function _unpack_family() {
    local triple="$1"
    export FAM_ID="${triple%%:*}"
    local rest="${triple#*:}"
    export FAM_NAME="${rest%%:*}"
    local rel_config="${rest#*:}"
    export FAM_CONFIG="${SOURCES_DIR}/${rel_config}"
}

# Formats a duration in seconds as a human-readable string.
#
# Arguments:
#   $1 - Duration in seconds
function _fmt_duration() {
    local secs="$1"
    local m=$(( secs / 60 ))
    local s=$(( secs % 60 ))
    if (( m > 0 )); then
        printf "%dm %ds" "${m}" "${s}"
    else
        printf "%ds" "${s}"
    fi
}

# Records a per-family result in the tracking arrays.
#
# Arguments:
#   $1 - Family name
#   $2 - Status: OK | FAIL | SKIP
#   $3 - Duration string (e.g. "18s" or "1m 3s")
function _record_result() {
    local family="$1"
    local status="$2"
    local duration="$3"
    _RESULT_FAMILIES+=("${family}")
    _RESULT_STATUSES+=("${status}")
    _RESULT_DURATIONS+=("${duration}")
}

# Prints the final per-family summary table and aggregate totals.
function print_summary() {
    local total="${#_RESULT_FAMILIES[@]}"
    [[ "${total}" -eq 0 ]] && return 0

    local ok=0 fail=0 skip=0
    for st in "${_RESULT_STATUSES[@]}"; do
        case "${st}" in
            OK)   ok=$(( ok + 1 ))   ;;
            FAIL) fail=$(( fail + 1 )) ;;
            SKIP) skip=$(( skip + 1 )) ;;
        esac
    done

    echo ""
    echo "┌──────────────────────────────────┬──────────┬──────────┐"
    printf "│ %-32s │ %-8s │ %-8s │\n" "Family" "Status" "Duration"
    echo "├──────────────────────────────────┼──────────┼──────────┤"
    for i in "${!_RESULT_FAMILIES[@]}"; do
        local fam="${_RESULT_FAMILIES[$i]}"
        local st="${_RESULT_STATUSES[$i]}"
        local dur="${_RESULT_DURATIONS[$i]}"
        printf "│ %-32s │ %-8s │ %-8s │\n" "${fam}" "${st}" "${dur}"
    done
    echo "└──────────────────────────────────┴──────────┴──────────┘"
    printf "  Totals:  %d built  %d failed  %d skipped\n" "${ok}" "${fail}" "${skip}"
    echo ""
}
