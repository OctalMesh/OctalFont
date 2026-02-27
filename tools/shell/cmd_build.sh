#!/usr/bin/env bash

# ============================================================================ #
# Handler for the 'build' command.                                             #
#                                                                              #
# Iterates over the selected font families, runs the full build pipeline for   #
# each one, and prints a summary table with per-family status and duration.    #
#                                                                              #
# Depends on:                                                                  #
#   logging.sh, common.sh, env.sh (env_activate), build_family.sh,             #
#   cli.sh (_get_families_to_process), and OPT_* globals from octalfont.       #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_CMD_BUILD_LOADED:-}" ]] && return 0
readonly _OCTALFONT_CMD_BUILD_LOADED=1

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Builds all selected font families and exits 1 if any family failed.
function cmd_build() {
    info "OctalFont Build CLI ${OCTALFONT_VERSION} - command: build"
    env_activate || {
        fatal "Cannot activate virtualenv. Run: octalfont env --setup";
        exit 1;
    }

    export BUILD_NO_QA="${OPT_NO_QA}"

    local families
    families="$(_get_families_to_process)"

    if [[ -z "${families}" ]]; then
        warn "No families selected. Use --family=<id> or --all."
        exit 0
    fi

    local grand_total_start
    grand_total_start=$(date +%s)

    while IFS= read -r triple; do
        [[ -z "${triple}" ]] && continue
        _unpack_family "${triple}"

        info ""
        info "Building:  ${FAM_NAME}"
        info "Config:    ${FAM_CONFIG}"

        local t_start t_end
        t_start=$(date +%s)
        local status="OK"

        if ! build_family "${FAM_ID}" "${FAM_NAME}" "${FAM_CONFIG}"; then
            status="FAIL"
        fi

        t_end=$(date +%s)
        _record_result "${FAM_NAME}" "${status}" "$(_fmt_duration $(( t_end - t_start )))"
    done <<< "${families}"

    local grand_total_end
    grand_total_end=$(date +%s)

    print_summary
    info "Total elapsed: $(_fmt_duration $(( grand_total_end - grand_total_start )))"

    for st in "${_RESULT_STATUSES[@]:-}"; do
        [[ "${st}" == "FAIL" ]] && exit 1
    done

    return 0
}
