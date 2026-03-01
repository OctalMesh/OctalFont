#!/usr/bin/env bash

# ============================================================================ #
# Single-family build, test, and proof pipeline.                               #
#                                                                              #
# Exposes:                                                                     #
#   build_family  - builds fonts from a gftools builder config                 #
#   test_family   - runs fontbakery QA on built fonts                          #
#   proof_family  - generates HTML proof documents via diffenator2             #
#                                                                              #
# Callers must source logging.sh, common.sh, and env.sh first.                 #
# ============================================================================ #

# Guard against double-sourcing

[[ -n "${_OCTALFONT_BUILD_FAMILY_LOADED:-}" ]] && return 0
readonly _OCTALFONT_BUILD_FAMILY_LOADED=1

# ============================================================================ #
#                                  Variables                                   #
# ============================================================================ #

export FONTS_DIR

# ============================================================================ #
#                                  Functions                                   #
# ============================================================================ #

# Prints all .ttf and .otf files found below the given output directory.
#
# Arguments:
#   $1 - Absolute path to the family output directory
function _find_built_fonts() {
    local dir="$1"
    find "${dir}" \( -name "*.ttf" -o -name "*.otf" \) -type f 2>/dev/null | sort
}

# Asserts that the gftools builder config file exists at the given path.
# Returns 1 (with an error log) when the file is missing.
#
# Arguments:
#   $1 - Absolute path to the config file
function _assert_config_exists() {
    local cfg="$1"

    if [[ ! -f "${cfg}" ]]; then
        error "gftools builder config not found: ${cfg}"
        return 1
    fi
}

# Builds a single font family through the full gftools builder pipeline and
# optionally runs fontbakery QA checks.
#
# Arguments:
#   $1 - Family ID (e.g. "titan")
#   $2 - Family name (e.g. "OctalFont-Titan")
#   $3 - Absolute path to the gftools builder config
#
# Environment variables honoured:
#   BUILD_LOG_DIR  Where to write per-family build logs (default: LOG_DIR)
#   BUILD_NO_QA    Skip fontbakery when set to "1"
function build_family() {
    local fam_id="$1"
    local fam_name="$2"
    local fam_config="$3"
    local no_qa="${BUILD_NO_QA:-0}"

    info "━━━  Building ${fam_name}  ━━━"
    _assert_config_exists "${fam_config}" || return 1

    local cfg_dir
    cfg_dir="$(dirname "${fam_config}")"

    local log_dir="${BUILD_LOG_DIR:-${LOG_DIR}}"
    mkdir -p "${log_dir}"
    local build_log="${log_dir}/build-${fam_id}.log"

    local t_start
    t_start=$(date +%s)

    # Step 0: SVG -> UFO

    local svg_dir="${cfg_dir}/svg"

    if [[ -d "${svg_dir}" ]]; then
        local svg_count
        svg_count=$(find "${svg_dir}" -name "*.svg" -type f 2>/dev/null | wc -l)

        if (( svg_count > 0 )); then
            info "[${fam_name}] Syncing UFO from ${svg_count} SVG file(s)..."

            if ! "${PYTHON}" "${REPO_ROOT}/tools/python/svg_to_ufo.py" \
                    "${cfg_dir}" 2>&1 | tee -a "${build_log}"; then

                error "[${fam_name}] svg_to_ufo.py failed."
                error "[${fam_name}] See log: ${build_log}"
                return 1
            fi

            success "[${fam_name}] UFO sync complete."
        fi
    fi

    # Step 1: gftools builder

    info "[${fam_name}] Running gftools builder..."
    debug "[${fam_name}] Config: ${fam_config}"
    debug "[${fam_name}] Log:    ${build_log}"

    local gftools_exit=0
    gftools builder "${fam_config}" 2>&1 | tee -a "${build_log}" || gftools_exit=$?

    local t_end
    t_end=$(date +%s)

    # gftools-fix-font is known to exit non-zero even when fonts are produced.
    # Treat the build as successful if at least one output font file exists.
    local fonts_produced
    fonts_produced=$(_find_built_fonts "${FONTS_DIR}/${fam_name}")

    if [[ "${gftools_exit}" -ne 0 ]] && [[ -z "${fonts_produced}" ]]; then
        error "[${fam_name}] gftools builder failed after $(_fmt_duration $(( t_end - t_start ))) (exit ${gftools_exit}, no fonts produced)."
        error "[${fam_name}] See log: ${build_log}"

        return 1
    elif [[ "${gftools_exit}" -ne 0 ]]; then
        warn "[${fam_name}] gftools builder exited ${gftools_exit} (fix-font warnings); fonts were produced."
    fi

    success "[${fam_name}] Build finished in $(_fmt_duration $(( t_end - t_start )))."

    # Step 1b: production fixups (USE_TYPO_METRICS etc.)

    local fix_targets
    fix_targets=$(_find_built_fonts "${FONTS_DIR}/${fam_name}")

    if [[ -n "${fix_targets}" ]]; then
        debug "[${fam_name}] Running production fixups..."

        # shellcheck disable=SC2086  # word-splitting is intentional here
        "${PYTHON}" "${REPO_ROOT}/tools/python/fix_production.py" \
            ${fix_targets} 2>&1 | tee -a "${build_log}" || true
    fi

    # Step 2: Optional fontbakery QA

    if [[ "${no_qa}" != "1" ]]; then
        _run_fontbakery_qa "${fam_id}" "${fam_name}" "${fam_config}" \
            || warn "[${fam_name}] QA reported issues (build artifacts were still produced)."
    else
        debug "[${fam_name}] QA skipped (--no-qa)."
    fi
}

# Runs fontbakery check-googlefonts on every built font for a family.
# The abs_config defaults to ${SOURCES_DIR}/<fam_id>/config.yaml when omitted.
#
# Arguments:
#   $1 - Family ID (e.g. "titan")
#   $2 - Family name (e.g. "OctalFont-Titan")
#   $3 - Absolute path to the fonts output directory
#   $4 - Absolute path to the gftools builder config (optional)
#
# Environment variables honoured:
#   BUILD_LOG_DIR  Where to write QA log files (default: LOG_DIR)
function test_family() {
    local fam_id="$1"
    local fam_name="$2"
    local fam_dir="$3"
    local fam_config="${4:-${SOURCES_DIR}/${fam_id}/config.yaml}"

    info "━━━  Testing ${fam_name}  ━━━"

    local log_dir="${BUILD_LOG_DIR:-${LOG_DIR}}"
    mkdir -p "${log_dir}"
    local qa_log="${log_dir}/qa-${fam_id}.log"

    _run_fontbakery_qa "${fam_id}" "${fam_name}" "${fam_config}" "${qa_log}"
}

# Generates HTML proof documents for a family via diffenator2.
#
# Arguments:
#   $1 - Family ID (e.g. "titan")
#   $2 - Family name (e.g. "OctalFont-Titan")
#   $3 - (unused; kept for call-site consistency - fonts dir is derived internally)
function proof_family() {
    local fam_id="$1"
    local fam_name="$2"
    local fam_dir="${FONTS_DIR}/${fam_name}"
    local out_dir="${REPO_ROOT}/out/proof/${fam_id}"

    info "━━━  Proofing ${fam_name}  ━━━"

    local fonts
    fonts="$(_find_built_fonts "${fam_dir}")"

    if [[ -z "${fonts}" ]]; then
        warn "[${fam_name}] No fonts found under ${fam_dir}. Build first."
        return 1
    fi

    mkdir -p "${out_dir}"

    info "[${fam_name}] Running diffenator2 proof..."
    # shellcheck disable=SC2086
    if ! diffenator2 proof ${fonts} -o "${out_dir}" 2>&1; then
        error "[${fam_name}] diffenator2 proof failed."
        return 1
    fi

    success "[${fam_name}] Proof documents written to: ${out_dir}"
}

# Internal runner for fontbakery check-googlefonts. Called by build_family and
# test_family; writes both the terminal output and a log file.
#
# Arguments:
#   $1 - Family ID
#   $2 - Family name
#   $3 - Absolute path to the gftools builder config
#   $4 - Path to the QA log file (optional, derived from BUILD_LOG_DIR when omitted)
function _run_fontbakery_qa() {
    local fam_id="$1"
    local fam_name="$2"
    local fam_config="$3"
    local qa_log="${4:-${BUILD_LOG_DIR:-${LOG_DIR}}/qa-${fam_id}.log}"

    # Derive the output dir from the gftools builder config
    local fonts_dir
    fonts_dir="$(_yaml_get "outputDir" "${fam_config}" 2>/dev/null)" || fonts_dir=""

    if [[ -z "${fonts_dir}" ]]; then
        warn "[${fam_name}] Could not determine outputDir from config; skipping QA."
        return 0
    fi

    # outputDir in config is relative to the config file directory
    local cfg_dir
    cfg_dir="$(dirname "${fam_config}")"
    fonts_dir="$(cd "${cfg_dir}" && realpath "${fonts_dir}")"

    # fontbakery must check one directory at a time to avoid
    # family/single_directory FAIL.  TTF is the primary QA target for GF.
    local qa_ttf_dir="${fonts_dir}/ttf"
    local fonts
    if [[ -d "${qa_ttf_dir}" ]]; then
        fonts=$(find "${qa_ttf_dir}" -name "*.ttf" -type f 2>/dev/null | sort)
    else
        fonts="$(_find_built_fonts "${fonts_dir}")"
    fi

    if [[ -z "${fonts}" ]]; then
        warn "[${fam_name}] No built fonts found at ${fonts_dir}; skipping QA."
        return 0
    fi

    local qa_report_dir="${REPO_ROOT}/out/fontbakery/${fam_id}"
    mkdir -p "${qa_report_dir}"

    info "[${fam_name}] Running fontbakery..."
    debug "[${fam_name}] Fonts under test:"
    while IFS= read -r f; do debug "  ${f}"; done <<< "${fonts}"

    # shellcheck disable=SC2086
    if ! fontbakery check-googlefonts \
            --loglevel WARN \
            --full-lists \
            --succinct \
            --html    "${qa_report_dir}/report.html" \
            --ghmarkdown "${qa_report_dir}/report.md" \
            ${fonts} \
            2>&1 | tee -a "${qa_log}"; then
        warn "[${fam_name}] fontbakery reported warnings/errors. See: ${qa_report_dir}/report.html"
        return 1
    fi

    success "[${fam_name}] QA passed. Report: ${qa_report_dir}/report.html"
}
