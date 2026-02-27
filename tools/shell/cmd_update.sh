#!/usr/bin/env bash

# ============================================================================ #
# Handler for the 'update' command.                                            #
#                                                                              #
# Recompiles requirements lockfiles with pip-compile and synchronises the      #
# virtual environment with pip-sync. Passes --test to also recompile the test  #
# dependency lockfile.                                                         #
#                                                                              #
# Depends on:                                                                  #
#   logging.sh, common.sh (REPO_ROOT, VENV_DIR), env.sh (env_activate), and    #
#   the OPT_UPDATE_TEST global set by the CLI argument parser.                 #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_CMD_UPDATE_LOADED:-}" ]] && return 0
readonly _OCTALFONT_CMD_UPDATE_LOADED=1

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Recompiles pip-tools lockfiles and synchronises the virtual environment.
function cmd_update() {
    info "OctalFont Build CLI ${OCTALFONT_VERSION} - command: update"
    env_activate || {
        fatal "Cannot activate virtualenv. Run: octalfont env --setup";
        exit 1;
    }

    # Derive venv bin directory (Scripts on Windows, bin everywhere else).
    local _venv_bin
    if [[ -d "${VENV_DIR}/Scripts" ]]; then
        _venv_bin="${VENV_DIR}/Scripts"
    else
        _venv_bin="${VENV_DIR}/bin"
    fi

    local pip_compile="${_venv_bin}/pip-compile"
    local pip_sync="${_venv_bin}/pip-sync"

    local reqs_in="${REPO_ROOT}/requirements.in"
    local reqs_txt="${REPO_ROOT}/requirements.txt"
    local reqs_test_in="${REPO_ROOT}/requirements-test.in"
    local reqs_test_txt="${REPO_ROOT}/requirements-test.txt"

    # Resolve venv Python for upgrading pip itself (pip >= 25 requires this).
    local _venv_python
    if [[ -f "${VENV_DIR}/Scripts/python.exe" ]]; then
        _venv_python="${VENV_DIR}/Scripts/python"
    else
        _venv_python="${VENV_DIR}/bin/python"
    fi

    info "Upgrading pip-tools …"
    "${_venv_python}" -m pip install --quiet --upgrade pip pip-tools

    if [[ ! -f "${reqs_in}" ]]; then
        fatal "requirements.in not found at ${reqs_in}"
        exit 1
    fi

    info "Compiling requirements.in -> requirements.txt …"
    "${pip_compile}" --upgrade --resolver=backtracking "${reqs_in}"

    if (( OPT_UPDATE_TEST )) && [[ -f "${reqs_test_in}" ]]; then
        info "Compiling requirements-test.in -> requirements-test.txt …"
        "${pip_compile}" --upgrade --resolver=backtracking \
            --constraint "${reqs_txt}" \
            "${reqs_test_in}"
    fi

    info "Syncing virtual environment …"
    if (( OPT_UPDATE_TEST )) && [[ -f "${reqs_test_txt}" ]]; then
        "${pip_sync}" "${reqs_txt}" "${reqs_test_txt}"
    else
        "${pip_sync}" "${reqs_txt}"
    fi

    success "Dependencies updated and environment synchronized."
}
