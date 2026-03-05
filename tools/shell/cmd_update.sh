#!/usr/bin/env bash

# ============================================================================ #
# Handler for the 'update' command.                                            #
#                                                                              #
# Recompiles ALL requirements lockfiles (main + test) with pip-compile and     #
# synchronises the virtual environment with pip-sync.                          #
#                                                                              #
# Depends on:                                                                  #
#   logging.sh, common.sh (REPO_ROOT, VENV_DIR), env.sh (env_activate).        #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_CMD_UPDATE_LOADED:-}" ]] && return 0
readonly _OCTALFONT_CMD_UPDATE_LOADED=1

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Recompiles pip-tools lockfiles and synchronises the virtual environment.
# Delegates to _update_lockfiles defined in env.sh.
function cmd_update() {
    info "OctalFont Build CLI ${OCTALFONT_VERSION} - command: update"
    env_activate || {
        fatal "Cannot activate virtualenv. Run: octalfont env --setup";
        exit 1;
    }

    _update_lockfiles || {
        fatal "Failed to update lockfiles and virtual environment.";
        exit 1;
    }
}
