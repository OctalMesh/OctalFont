#!/usr/bin/env bash

# ============================================================================ #
# Handler for the 'clean' command.                                             #
#                                                                              #
# Removes compiled font output, gftools/ninja artifacts, and optionally all    #
# logs, QA reports, and Python caches in --deep mode.                          #
#                                                                              #
# Depends on:                                                                  #
#   logging.sh, common.sh (FONTS_DIR, SOURCES_DIR, REPO_ROOT, _yaml_get,       #
#   _unpack_family, _record_result, print_summary), cli.sh, and OPT_* globals. #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_CMD_CLEAN_LOADED:-}" ]] && return 0
readonly _OCTALFONT_CMD_CLEAN_LOADED=1

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Cleans build artifacts for all selected families.
# With --deep also removes logs/, out/, fonts/, and Python caches repo-wide.
function cmd_clean() {
    info "OctalFont Build CLI ${OCTALFONT_VERSION} - command: clean"
    if (( OPT_CLEAN_DEEP )); then
        info "Mode: deep (full reset)"
    fi

    local families
    families="$(_get_families_to_process)"

    if [[ -z "${families}" ]]; then
        warn "No families selected. Use --family=<id> or --all."
        exit 0
    fi

    while IFS= read -r triple; do
        [[ -z "${triple}" ]] && continue
        _unpack_family "${triple}"

        info "Cleaning ${FAM_NAME}..."

        # Compiled font output (fonts/<Family>/)
        # FONTS_DIR is defined in common.sh as ${REPO_ROOT}/fonts.
        # Use it directly; also fall back to parsing outputDir from config in
        # case a family overrides the output location.
        local out_dir="${FONTS_DIR}/${FAM_NAME}"

        if [[ -f "${FAM_CONFIG}" ]]; then
            local raw_out_dir
            raw_out_dir="$(_yaml_get "outputDir" "${FAM_CONFIG}" 2>/dev/null)" || raw_out_dir=""

            if [[ -n "${raw_out_dir}" ]]; then
                # Resolve relative path without relying on `realpath` (not
                # guaranteed to exist on all platforms when path is absent).
                local cfg_dir
                cfg_dir="$(cd "$(dirname "${FAM_CONFIG}")" && pwd)"
                out_dir="$(cd "${cfg_dir}" && cd "${raw_out_dir}" 2>/dev/null && pwd || echo "${FONTS_DIR}/${FAM_NAME}")"
            fi
        fi

        if [[ -n "${out_dir}" && -d "${out_dir}" ]]; then
            debug "Removing: ${out_dir}"
            rm -rf "${out_dir}"
            success "Removed font output: ${out_dir}"
        fi

        # gftools/ninja build artifacts
        local src_dir="${SOURCES_DIR}/${FAM_NAME}"
        if [[ -d "${src_dir}" ]]; then
            find "${src_dir}" \( -name "build.ninja" -o -name ".ninja_log" \) \
                 -type f -delete 2>/dev/null
            find "${src_dir}" -name "instance_ufos" -type d \
                 -exec rm -rf {} + 2>/dev/null || true
        fi

        _record_result "${FAM_NAME}" "OK" "-"
    done <<< "${families}"

    # Deep: global artifacts (independent of family selection)

    if (( OPT_CLEAN_DEEP )); then
        # QA reports
        if [[ -d "${REPO_ROOT}/out" ]]; then
            rm -rf "${REPO_ROOT}/out"
            success "Removed out/  (QA reports)"
        fi

        # Build logs (best-effort - active log file inode stays open)
        if [[ -d "${REPO_ROOT}/logs" ]]; then
            rm -rf "${REPO_ROOT}/logs" 2>/dev/null || true
            success "Removed logs/"
        fi

        # Root fonts/ dir if now empty
        if [[ -d "${REPO_ROOT}/fonts" ]]; then
            local remaining
            remaining="$(ls -A "${REPO_ROOT}/fonts" 2>/dev/null || true)"

            if [[ -z "${remaining}" ]]; then
                rm -rf "${REPO_ROOT}/fonts"
                success "Removed fonts/  (now empty)"
            fi
        fi

        # Python bytecode and test caches - skip venv/ and .git/
        while IFS= read -r _d; do
            rm -rf "${_d}"
        done < <(find "${REPO_ROOT}" \
                      \( -path "${REPO_ROOT}/venv" \
                         -o -path "${REPO_ROOT}/.git" \) -prune \
                      -o \( -name "__pycache__" \
                            -o -name ".pytest_cache" \
                            -o -name ".mypy_cache" \) \
                         -type d -print \
                      2>/dev/null || true)
        find "${REPO_ROOT}" \
             \( -path "${REPO_ROOT}/venv" \
                -o -path "${REPO_ROOT}/.git" \) -prune \
             -o \( -name "*.pyc" -o -name "*.pyo" \) \
                -type f -delete \
             2>/dev/null || true
        success "Removed Python cache files (__pycache__, .pytest_cache, .mypy_cache, .pyc)"
    fi

    print_summary
    success "Clean complete."
}
