#!/usr/bin/env bash

# ============================================================================ #
# Handler for the 'test' command.                                              #
#                                                                              #
# Runs fontbakery check-googlefonts on the compiled fonts for each selected    #
# family and exits 1 if any family reported failures.                          #
#                                                                              #
# Depends on:                                                                  #
#   logging.sh, common.sh, env.sh (env_activate), build_family.sh,             #
#   cli.sh (_get_families_to_process), and OPT_* globals from octalfont.       #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_CMD_TEST_LOADED:-}" ]] && return 0
readonly _OCTALFONT_CMD_TEST_LOADED=1

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Runs QA checks on all selected font families and exits 1 if any failed.
function cmd_test() {
    info "OctalFont Build CLI ${OCTALFONT_VERSION} - command: test"
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

        if ! test_family "${FAM_ID}" "${FAM_NAME}" "${FONTS_DIR}/${FAM_NAME}" "${FAM_CONFIG}"; then
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
