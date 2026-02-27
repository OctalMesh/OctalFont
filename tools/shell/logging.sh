#!/usr/bin/env bash

# ============================================================================ #
# Logging utility functions for shell scripts.                                 #
# Provides functions to print messages with timestamps and color coding.       #
#                                                                              #
# Available functions:                                                         #
#   debug <message>   Detailed debug information (Purple).                     #
#   info <message>    Informational messages (Blue).                           #
#   success <message> Success messages (Green).                                #
#   warn <message>    Warning messages (Yellow).                               #
#   error <message>   Error messages (Red).                                    #
#   fatal <message>   Fatal failure (Bold Red).                                #
#                                                                              #
# Environment Variables:                                                       #
#   LOG_DIR           Directory to save log files. Default is empty.           #
#   LOG_LEVEL         Set the logging level (DEBUG, INFO, SUCCESS, WARN, ERROR #
#                     FATAL, OFF). Default is DEBUG.                           #
#   LOG_ERASE_DAYS    Number of days to keep log files. Default is '-1'.       #
#                     (-1 means no cleanup)                                    #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_LOGGING_LOADED:-}" ]] && return 0
readonly _OCTALFONT_LOGGING_LOADED=1

# ============================================================================ #
#                                  Variables                                   #
# ============================================================================ #

# Color codes

readonly PURPLE='\033[0;35m'
readonly BLUE='\033[0;34m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BOLD_RED='\033[1;31m'
readonly RESET='\033[0m'

readonly LOG_MSG_PATTERN="[%s] [%s] [PID %s]: %s"
readonly LOG_TIMESTAMP_FORMAT="%H:%M:%S"
readonly SED_FILTER="s/\x1b\[[0-9;]*[mGJKHF]//g"

# Configuration (Can be overridden via environment variables)

: "${LOG_DIR:=}"
: "${LOG_LEVEL:=DEBUG}"
: "${LOG_ERASE_DAYS:=-1}"

# Map levels to numeric values for comparison

declare -A _LOG_PRIORITIES=(
    [DEBUG]=0
    [INFO]=1
    [SUCCESS]=1
    [WARN]=2
    [ERROR]=3
    [FATAL]=4
    [OFF]=5
)

# Detect if colors should be used
_USE_COLOR=true
if [[ ! -t 1 || -n "${NO_COLOR:-}" ]]; then
    _USE_COLOR=false
fi

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Start session logging by creating a log file inside the specified log
# directory.
#
# Environment variables honoured:
#   SESSION_LOG_DIR - Directory to save session log (default: LOG_DIR)
function start_session_logging() {
    local log_dir log_file

    log_dir="$(realpath -m "${SESSION_LOG_DIR:-${LOG_DIR}}")"
    log_file="${log_dir}/session.log"

    [[ -n "${log_dir}" ]] || return 0

    # Prepare log directory and clean up old logs before starting the session
    cleanup_logs "${LOG_ERASE_DAYS}"
    mkdir -p "${log_dir}"

    # Redirect all output to the log file while still printing to console
    exec > >(tee -a >(sed -r "${SED_FILTER}" >> "${log_file}") ) 2>&1

    info "Session logging started. Saving to: ${log_file}"
}

# Clean up old log directories in LOG_DIR that are older than the specified
# number of days. If no argument is given, it defaults to -1 which means no
# cleanup.
#
# Arguments:
#   $1 - Number of days to keep logs (default: -1, which means no cleanup)
function cleanup_logs() {
    [[ -z "${LOG_DIR}" ]] && return 0

    local erase_days="${1:=-1}"

    if [[ "${erase_days}" -ne -1 ]]; then
        find "${LOG_DIR}" -mindepth 1 -maxdepth 1 -type d \
            -mtime +"${erase_days}" -exec rm -rf {} + 2>/dev/null || true
    fi
}

# Internal function to handle the logic of printing and saving logs.
#
# Arguments:
#   $1 - Level Name (e.g. INFO)
#   $2 - Color Code
#   $* - Message
function _print() {
    local level_name="$1"
    local color="$2"
    shift 2
    local message="$*"

    local current_pri=${_LOG_PRIORITIES[${level_name}]:-1}
    local config_pri=${_LOG_PRIORITIES[${LOG_LEVEL}]:-1}

    # Skip if current priority is lower than configured
    [[ "${current_pri}" -lt "${config_pri}" ]] && return 0

    local timestamp
    timestamp=$(date +"${LOG_TIMESTAMP_FORMAT}")

    local term_color="${color}"
    local term_reset="${RESET}"
    [[ "$_USE_COLOR" == "false" ]] && term_color="" && term_reset=""

    # Use stderr for ERROR and FATAL
    local stream=1
    [[ "$current_pri" -ge 3 ]] && stream=2

    # shellcheck disable=SC2059
    printf "${term_color}${LOG_MSG_PATTERN}${term_reset}\n" \
           "${timestamp}" "${level_name}" "$$" "${message}" >&"${stream}"
}

# Print debug messages in purple.
# Message pattern: [HH:MM:SS] DEBUG: <message>
#
# Arguments:
#   $* - Message to print
function debug() {
    _print "DEBUG" "${PURPLE}" "$@"
}

# Print info messages in blue.
# Message pattern: [HH:MM:SS] INFO: <message>
#
# Arguments:
#   $* - Message to print
function info() {
    _print "INFO" "${BLUE}" "$@"
}

# Print success messages in green.
# Message pattern: [HH:MM:SS] SUCCESS: <message>
#
# Arguments:
#   $* - Message to print
function success() {
    _print "SUCCESS" "${GREEN}" "$@"
}

# Print warning messages in yellow.
# Message pattern: [HH:MM:SS] WARNING: <message>
#
# Arguments:
#   $* - Message to print
function warn() {
    _print "WARN" "${YELLOW}" "$@"
}

# Print error messages in red.
# Message pattern: [HH:MM:SS] ERROR: <message>
#
# Arguments:
#   $* - Message to print
function error() {
    _print "ERROR" "${RED}" "$@"
}

# Print fatal error messages in bold red.
# Message pattern: [HH:MM:SS] FATAL: <message>
#
# Arguments:
#   $* - Message to print
function fatal() {
    _print "FATAL" "${BOLD_RED}" "$@"
}
