#!/usr/bin/env bash

# ============================================================================ #
# .env file loader for OctalFont shell scripts.                                #
#                                                                              #
# Sources either .env (local overrides) or .env.example (project defaults)     #
# from the repository root.  At least one of these files MUST exist and        #
# contain active values - the toolchain has no built-in defaults and will      #
# abort with a fatal error if neither file is present or usable.               #
#                                                                              #
# Exposes:                                                                     #
#   load_dotenv - loads the .env (or fallback) and exports variables           #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_DOTENV_LOADED:-}" ]] && return 0
readonly _OCTALFONT_DOTENV_LOADED=1

# ============================================================================ #
#                                  Variables                                   #
# ============================================================================ #

declare -A _DOTENV_LOADED_FILES=()

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Sources a single env file, tracking which files have already been loaded.
#
# Arguments:
#   $1 - Absolute path to the file to source
#
# shellcheck disable=SC1090
function _dotenv_source_file() {
    local file="$1"

    if [[ -n "${_DOTENV_LOADED_FILES[$file]+_}" ]]; then
        warn "dotenv: '${file}' was already loaded, skipping."
        return 0
    fi

    info "dotenv: loading '${file}'"
    set -a
    source "${file}"
    set +a

    _DOTENV_LOADED_FILES["$file"]=1
}

# Loads the .env file (or its fallback .env.example) from the given directory.
# Aborts with a fatal error when no usable config file can be found - the
# toolchain has no built-in defaults and cannot run without one.
#
# Arguments:
#   $1 - Directory to look in (defaults to REPO_ROOT)
#   $2 - Main env filename (defaults to .env)
#   $3 - Fallback filename (defaults to $2.example)
function load_dotenv() {
    local dir="${1:-${REPO_ROOT}}"
    local main_name="${2:-.env}"
    local fallback_name="${3:-${main_name}.example}"

    local main_file="${dir}/${main_name}"
    local fallback_file="${dir}/${fallback_name}"

    local main_exists=false
    local fallback_exists=false

    [[ -f "${main_file}" ]]     && main_exists=true
    [[ -f "${fallback_file}" ]] && fallback_exists=true

    # Main file takes priority.
    if [[ "${main_exists}" == true ]]; then
        _dotenv_source_file "${main_file}"
        return 0
    fi

    # Fall back to the .example template when it contains active (non-comment) values.
    if [[ "${fallback_exists}" == true ]]; then
        if grep -qE '^\s*[^#[:space:]]' "${fallback_file}" 2>/dev/null; then
            info "dotenv: no '${main_name}' found; loading default config from '${fallback_file}'"
            _dotenv_source_file "${fallback_file}"
            return 0
        else
            fatal "dotenv: '${fallback_file}' exists but contains no active values." \
                  "Restore it from git or create '${main_file}'."
            exit 1
        fi
    fi

    fatal "dotenv: no config file found." \
          "Expected '${main_file}' or '${fallback_file}'." \
          "Restore '.env.example' from git or create a '.env' with your settings."
    exit 1
}
