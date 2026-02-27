#!/usr/bin/env bash

# ============================================================================ #
# CLI argument parsing, usage help, family selection, and the interrupt        #
# signal handler for the octalfont build tool.                                 #
#                                                                              #
# Depends on:                                                                  #
#   logging.sh  (warn, error, fatal)                                           #
#   common.sh   (_yaml_families, print_summary, PROJECT_CONFIG)                #
#   OCTALFONT_VERSION and OPT_* globals defined in the octalfont entrypoint.   #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_CLI_LOADED:-}" ]] && return 0
readonly _OCTALFONT_CLI_LOADED=1

# ============================================================================ #
#                                  Variables                                   #
# ============================================================================ #

# Command name resolved by _parse_args; consumed by octalfont main().
export CMD=""

# Option flags populated by _parse_args; consumed by cmd_* handlers.
export OPT_FAMILY=""
export OPT_ALL=0
export OPT_NO_QA=0
export OPT_VERBOSE=0
export OPT_ENV_SETUP=0
export OPT_UPDATE_TEST=0
export OPT_CLEAN_DEEP=0

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Register the interrupt handler immediately on source so Ctrl-C during any
# build run prints the partial summary before exiting.
trap '_on_interrupt' INT TERM

# Handles SIGINT / SIGTERM: prints the partial summary and exits with code 130.
function _on_interrupt() {
    echo ""
    warn "Build interrupted by user."
    print_summary
    exit 130
}

# Prints full usage information and examples to stdout.
function _usage() {
    cat <<EOF

  OctalFont Build CLI  v${OCTALFONT_VERSION}

  Usage:
    octalfont <command> [options]

  Commands:
    build   Build one or more font families with gftools builder
    test    Run fontbakery QA checks on built fonts
    proof   Generate HTML proof documents via diffenator2
    clean   Remove build artifacts (fonts/ outputs and temp files)
    env     Check or set up the Python virtual environment
    update  Re-compile requirements lockfiles with pip-tools
    help    Show this help message

  Options (build / test / proof / clean):
    --family=<id>    Target a single family  [titan | cuprum | mercury]
    --all            Target all families regardless of their 'status' flag
    --no-qa          Skip fontbakery QA after building
    --verbose        Enable DEBUG-level log output

  Options (clean):
    --deep           Full reset: also removes out/ (QA reports), logs/,
                     and Python caches (__pycache__, .pytest_cache, .pyc).
                     UFO masters are NOT deleted - features.fea inside them
                     is hand-edited and preserved between builds.

  Options (env):
    --setup          Create the venv and install requirements.txt
    --check          Verify tools only (default)

  Options (update):
    --test           Also recompile requirements-test.in

  First run:
    1. octalfont env --setup      Create the venv and install all dependencies
    2. octalfont env              Verify the environment is ready
    3. octalfont build --all      Build all active font families
    4. octalfont test  --all      Run QA checks on the built fonts

EOF
}

# Parses the command-line arguments passed to the octalfont entrypoint and
# populates CMD and OPT_* globals accordingly.
#
# Arguments:
#   $@ - All arguments forwarded from the octalfont entry point
function _parse_args() {
    if [[ $# -eq 0 ]]; then
        _usage
        exit 0
    fi

    # Handle global flags that may appear before the command name.
    case "$1" in
        --version)      echo "octalfont ${OCTALFONT_VERSION}"; exit 0 ;;
        --help|-h)      _usage; exit 0 ;;
    esac

    CMD="$1"
    shift

    for arg in "$@"; do
        case "${arg}" in
            --family=*)    OPT_FAMILY="${arg#--family=}" ;;
            --all)         OPT_ALL=1 ;;
            --no-qa)       OPT_NO_QA=1 ;;
            --verbose)     OPT_VERBOSE=1; export LOG_LEVEL="DEBUG" ;;
            --setup)       OPT_ENV_SETUP=1 ;;
            --check)       OPT_ENV_SETUP=0 ;;
            --test)        OPT_UPDATE_TEST=1 ;;
            --deep)        OPT_CLEAN_DEEP=1 ;;
            --version)     echo "octalfont ${OCTALFONT_VERSION}"; exit 0 ;;
            --help|-h)     _usage; exit 0 ;;
            *)
                error "Unknown option: ${arg}"
                _usage
                exit 1
                ;;
        esac
    done
}

# Prints one "id:name:config" triple per line based on the current option flags.
# Respects --family=<id>, --all, or defaults to active families.
#
# Environment variables honoured:
#   OPT_FAMILY      Single family ID to target (overrides all others)
#   OPT_ALL         When 1, targets all families regardless of status
#   PROJECT_CONFIG  Absolute path to the project config YAML
function _get_families_to_process() {
    if [[ -n "${OPT_FAMILY}" ]]; then
        local match
        match="$(_yaml_families "" "${PROJECT_CONFIG}" \
            | grep "^${OPT_FAMILY}:" || true)"

        if [[ -z "${match}" ]]; then
            fatal "Unknown family id '${OPT_FAMILY}'. Available: $(
                _yaml_families "" "${PROJECT_CONFIG}" | cut -d: -f1 | tr '\n' ' '
            )"
            return 1
        fi

        echo "${match}"
    elif (( OPT_ALL )); then
        _yaml_families "" "${PROJECT_CONFIG}"
    else
        _yaml_families "active" "${PROJECT_CONFIG}"
    fi
}
