#!/usr/bin/env bash

# ============================================================================ #
# Virtual-environment management and tool verification.                        #
#                                                                              #
# Exposes:                                                                     #
#   env_activate  - activates the venv (exports PATH change)                   #
#   env_setup     - creates venv and installs from requirements.txt            #
#   env_check     - verifies all required tools are present                    #
#   cmd_env       - CLI entry point; delegates to env_setup or env_check       #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_ENV_LOADED:-}" ]] && return 0
readonly _OCTALFONT_ENV_LOADED=1

# ============================================================================ #
#                                  Variables                                   #
# ============================================================================ #

_THIS_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${_THIS_ENV_DIR}/logging.sh"
source "${_THIS_ENV_DIR}/common.sh"

# Minimum versions required for key tools. The real version pins live in
# requirements.txt; these rows are informational only.
readonly -A _REQUIRED_CMDS=(
    [ninja]=""
    [pip]=""
)

# Python is special - accept python3 OR python (Windows), skip MS Store stubs
_PYTHON_CMD=""
for _py in python3 python py; do
    _py_path="$(command -v "${_py}" 2>/dev/null)" || continue

    if "${_py_path}" -c "import sys; assert sys.version_info >= (3,9)" 2>/dev/null; then
        _PYTHON_CMD="${_py_path}"; break
    fi
done
unset _py _py_path

readonly -A _REQUIRED_PY_PKGS=(
    [fontmake]="fontmake"
    [gftools]="gftools"
    [fontbakery]="fontbakery"
    [diffenator2]="diffenator2"
)

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Activates the project virtual environment if it exists.
# Returns 1 (without exiting) when no venv is found.
function env_activate() {
    local activate=""

    if [[ -f "${VENV_DIR}/bin/activate" ]]; then
        activate="${VENV_DIR}/bin/activate"
    elif [[ -f "${VENV_DIR}/Scripts/activate" ]]; then
        # Git-Bash on Windows
        activate="${VENV_DIR}/Scripts/activate"
    fi

    if [[ -z "${activate}" ]]; then
        warn "Virtual environment not found at ${VENV_DIR}. Run: octalfont env --setup"
        return 1
    fi

    # shellcheck source=/dev/null
    source "${activate}"
    debug "Virtualenv activated: ${VENV_DIR}"
}

# Creates a fresh venv and installs all dependencies from requirements.txt.
function env_setup() {
    info "Setting up virtual environment at ${VENV_DIR} …"

    local base_python=""
    for _py_candidate in python3 python py; do
        local _py_path
        _py_path="$(command -v "${_py_candidate}" 2>/dev/null)" || continue

        # Verify the candidate actually runs (rules out Windows Store stubs)
        if "${_py_path}" -c "import sys; assert sys.version_info >= (3,9)" 2>/dev/null; then
            base_python="${_py_path}"
            break
        fi
    done
    if [[ -z "${base_python}" ]]; then
        fatal "Python 3 not found on PATH. Install Python >= 3.9 first."
        return 1
    fi

    local py_ver
    py_ver="$("${base_python}" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
    info "Using Python ${py_ver} (${base_python})"

    if [[ ! -d "${VENV_DIR}" ]]; then
        debug "Creating virtualenv …"
        "${base_python}" -m venv "${VENV_DIR}"
    else
        debug "Virtualenv already exists, reusing."
    fi

    env_activate || return 1

    # pip >= 25 requires using `python -m pip` to upgrade pip itself
    local venv_python
    if [[ -f "${VENV_DIR}/Scripts/python.exe" ]]; then
        venv_python="${VENV_DIR}/Scripts/python"
    else
        venv_python="${VENV_DIR}/bin/python"
    fi

    info "Upgrading pip …"
    "${venv_python}" -m pip install --quiet --upgrade pip

    local req_file="${REPO_ROOT}/requirements.txt"
    if [[ ! -f "${req_file}" ]]; then
        fatal "requirements.txt not found at ${req_file}"
        return 1
    fi

    info "Installing dependencies from requirements.txt …"
    "${venv_python}" -m pip install --quiet -r "${req_file}"

    success "Environment ready."
}

# Verifies all required CLI tools and Python packages are reachable.
# Exits with code 1 if anything is missing.
#
# Environment variables honoured:
#   PYTHON  Active Python interpreter, set by common.sh
function env_check() {
    local had_error=0

    info "Checking build environment …"

    # Activate venv first so venv-only tools (ninja, pip) are on PATH
    env_activate 2>/dev/null || true

    # Python (accept python3 or python)
    if [[ -n "${_PYTHON_CMD}" ]]; then
        local py_ver
        py_ver="$("${_PYTHON_CMD}" --version 2>&1)"
        debug "  [OK] python  (${py_ver})"
    else
        error "  [MISSING] python  (python3 / python / py not found on PATH)"
        had_error=1
    fi

    # Venv-provided and system commands
    for cmd in "${!_REQUIRED_CMDS[@]}"; do
        if command -v "${cmd}" &>/dev/null; then
            local ver
            ver="$("${cmd}" --version 2>&1)"
            debug "  [OK] ${cmd}  (${ver})"
        else
            error "  [MISSING] ${cmd}  ->  run: octalfont env --setup"
            had_error=1
        fi
    done

    # Python packages
    for pkg in "${!_REQUIRED_PY_PKGS[@]}"; do
        local import_name="${_REQUIRED_PY_PKGS[$pkg]}"

        if "${PYTHON}" -c "import importlib; importlib.import_module('${import_name}')" &>/dev/null; then
            local ver
            ver="$("${PYTHON}" -m pip show "${pkg}" 2>/dev/null | awk '/^Version:/{print $2}')"
            debug "  [OK] ${pkg} ${ver}"
        else
            error "  [MISSING Python pkg] ${pkg}  ->  run: octalfont env --setup"
            had_error=1
        fi
    done

    if (( had_error )); then
        fatal "Environment check failed. Fix the issues above before building."
        return 1
    fi

    success "Environment check passed."
}

# CLI entry point for octalfont env. Delegates to env_setup or env_check based
# on the OPT_ENV_SETUP flag.
#
# Environment variables honoured:
#   OPT_ENV_SETUP  When 1, runs env_setup; otherwise runs env_check
function cmd_env() {
    if (( OPT_ENV_SETUP )); then
        env_setup
    else
        env_check
    fi
}
