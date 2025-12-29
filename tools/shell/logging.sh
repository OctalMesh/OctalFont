#!/usr/bin/env bash

# ============================================================================ #
# Logging utility functions for shell scripts.                                 #
# Provides functions to print messages with timestamps and color coding.       #
#                                                                              #
# Available functions:                                                         #
#   debug <message>   - Detailed debug information (Purple).                   #
#   info <message>    - Informational messages (Blue).                         #
#   success <message> - Success messages (Green).                              #
#   warn <message>    - Warning messages (Yellow).                             #
#   error <message>   - Error messages (Red).                                  #
#   fatal <message>   - Fatal failure (Bold Red).                              #
#                                                                              #
# Environment Variables:                                                       #
#   LOG_LEVEL      - Set the logging level (DEBUG, INFO, SUCCESS, WARN, ERROR, #
#                    FATAL, OFF). Default is DEBUG.                            #
#   LOG_DIR        - Directory to save log files. Default is empty.            #
#   LOG_ERASE_DAYS - Number of days to keep log files. Default is '7'.         #
#                                                                              #
# Example usage:                                                               #
#   export LOG_LEVEL=INFO                                                      #
#   export LOG_DIR="./logs"                                                    #
#   source logging.sh                                                          #
#   info "This is an info message."                                            #
# ============================================================================ #

# ============================================================================ #
#                                   Variables                                  #
# ============================================================================ #

# Color codes
readonly PURPLE='\033[0;35m'
readonly BLUE='\033[0;34m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BOLD_RED='\033[1;31m'
readonly RESET='\033[0m'

readonly LOG_MSG_PATTERN="[%s] [%s] [PID %s]: %b"
readonly LOG_TIMESTAMP_FORMAT="%H:%M:%S"
readonly SED_FILTER="s/\x1b\[[0-9;]*[mGJKHF]//g"

# Configuration (Can be overridden via environment variables)
: "${LOG_LEVEL:=DEBUG}"
: "${LOG_DIR:=}"
: "${LOG_ERASE_DAYS:=7}"

# Map levels to numeric values for comparison
declare -A _LOG_PRIORITIES=([DEBUG]=0 [INFO]=1 [SUCCESS]=1 [WARN]=2 [ERROR]=3 [FATAL]=4 [OFF]=5)

# Detect if colors should be used
_USE_COLOR=true
if [[ ! -t 1 || -n "${NO_COLOR:-}" ]]; then
    _USE_COLOR=false
fi

# Internal variable to hold current log file path
_CURRENT_LOG_FILE_PATH=""

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Start session logging by creating a log file in the specified LOG_DIR.
# The log file is named with the current date and an incrementing index to avoid
# overwriting existing logs.
function start_session_logging() {
    local log_dir
    log_dir="$(realpath "${LOG_DIR}")"
    mkdir -p "${log_dir}"

    local date_str
    date_str=$(date +%Y-%m-%d)
    local index=1

    # Clean up old log files (older than LOG_ERASE_DAYS)
    find "${log_dir}" -name "*.log" -type f -mtime +"${LOG_ERASE_DAYS}" -delete 2>/dev/null

    # Search for the next available log file name
    while true; do
        local formatted_index
        formatted_index=$(printf "%03d" "${index}")
        local candidate="${log_dir}/${date_str}-${formatted_index}.log"

        if [[ ! -f "$candidate" ]]; then
            _CURRENT_LOG_FILE="$candidate"
            break
        fi

        ((index++))
    done

    # Redirect all output to the log file while still printing to console
    exec > >(tee -a >(sed -r "${SED_FILTER}" >> "${_CURRENT_LOG_FILE}") ) 2>&1

    info "Session logging started. Saving to: ${_CURRENT_LOG_FILE}"
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
