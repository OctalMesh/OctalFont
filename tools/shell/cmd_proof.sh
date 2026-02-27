#!/usr/bin/env bash

# ============================================================================ #
# Handler for the 'proof' command.                                             #
#                                                                              #
# Generates HTML proof documents for each selected font family via             #
# diffenator2 and exits 1 if any family failed.                                #
#                                                                              #
# Depends on:                                                                  #
#   logging.sh, common.sh, env.sh (env_activate), build_family.sh,             #
#   cli.sh (_get_families_to_process), and OPT_* globals from octalfont.       #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_CMD_PROOF_LOADED:-}" ]] && return 0
readonly _OCTALFONT_CMD_PROOF_LOADED=1

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Generates proof documents for all selected families and exits 1 if any failed.
function cmd_proof() {
    info "OctalFont Build CLI ${OCTALFONT_VERSION} - command: proof"
    env_activate || {
        fatal "Cannot activate virtualenv. Run: octalfont env --setup";
        exit 1;
    }

    local families
    families="$(_get_families_to_process)"

    if [[ -z "${families}" ]]; then
        warn "No families selected. Use --family=<id> or --all."
        exit 0
    fi

    while IFS= read -r triple; do
        [[ -z "${triple}" ]] && continue
        _unpack_family "${triple}"

        local t_start t_end
        t_start=$(date +%s)
        local status="OK"

        if ! proof_family "${FAM_ID}" "${FAM_NAME}"; then
            status="FAIL"
        fi

        t_end=$(date +%s)
        _record_result "${FAM_NAME}" "${status}" "$(_fmt_duration $(( t_end - t_start )))"
    done <<< "${families}"

    print_summary

    for st in "${_RESULT_STATUSES[@]:-}"; do
        [[ "${st}" == "FAIL" ]] && exit 1
    done

    return 0
}
