#!/usr/bin/env bash

# Update agent context files with information from design.md
#
# This script maintains AI agent context files by parsing feature specifications 
# and updating agent-specific configuration files with project information.
#
# MAIN FUNCTIONS:
# 1. Environment Validation
#    - Verifies git repository structure and branch information
#    - Checks for required design.md files and templates
#    - Validates file permissions and accessibility
#
# 2. Design Data Extraction
#    - Parses design.md files to extract project metadata
#    - Identifies language/version, frameworks, databases, and project types
#    - Handles missing or incomplete specification data gracefully
#
# 3. Agent File Management
#    - Creates new agent context files from templates when needed
#    - Updates existing agent files with new project information
#    - Preserves manual additions and custom configurations
#    - Supports multiple AI agent formats and directory structures
#
# 4. Content Generation
#    - Generates language-specific build/test commands
#    - Creates appropriate project directory structures
#    - Updates technology stacks and recent changes sections
#    - Maintains consistent formatting and timestamps
#
# 5. Multi-Agent Support
#    - Handles agent-specific file paths and naming conventions
#    - Supports: Claude, Cursor, Flow
#    - Can update single agents or all existing agent files
#    - Creates default Claude file if no agent files exist
#
# Usage: ./update-agent-context.sh [--agent-type <type>] [--help]
# Agent types: claude|cursor-agent|flow
# Leave empty to update all existing agent files

set -e

# Enable strict error handling
set -u
set -o pipefail

#==============================================================================
# USAGE AND HELP INFORMATION
#==============================================================================
# This function displays usage information and is placed at the top for easy reference.
# To add a new agent type, see the AGENT_REGISTRY section below.

show_help() {
    local agent_list="${valid_agents:-claude|cursor-agent|flow}"
    
    cat <<EOF
Usage: ./update-agent-context.sh [--agent-type <type>] [--help]

Update agent context files with information from design.md

OPTIONS:
  --agent-type <type>  (Optional) Update a specific agent type
                       If not specified, auto-detects from repository structure
  --help, -h           Show this help message

AGENT TYPES:
  $agent_list

EXAMPLES:
  # Update all existing agent files
  ./update-agent-context.sh
  
  # Update specific agent
  ./update-agent-context.sh --agent-type claude

NOTES:
  - If no agent type is specified, automatically detects ALL agent types from repository structure:
    * .cursor/ directory -> cursor-agent
    * .flow/ directory -> flow
    * .claude/ directory -> claude
  - If multiple agent directories exist, ALL detected agents will be updated
  - If no agent directories found, updates all existing agent files
  - To add new agent types, register them in AGENT_REGISTRY (see below)
EOF
}

#==============================================================================
# Configuration and Global Variables
#==============================================================================

# Get script directory and load common functions
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Global variables for parsed arguments
AGENT_TYPE=""

#==============================================================================
# Argument Parsing Functions
#==============================================================================

# Parse command line arguments
# Args: all script arguments
# Output: Sets global AGENT_TYPE variable
# Returns: 0 on success, 1 on error (and exits on help request)
parse_arguments() {
    local i=1
    local total_args=$#
    local args=("$@")
    
    while [ $i -le $total_args ]; do
        local arg="${args[$((i - 1))]}"
        
        case "$arg" in
            --agent-type)
                if ! handle_agent_type_option "$i" "$total_args" "${args[@]}"; then
                    return 1
                fi
                i=$((i + 2))
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                if ! handle_positional_argument "$arg" "$i"; then
                    return 1
                fi
                i=$((i + 1))
                ;;
        esac
    done
    
    return 0
}

# Handle --agent-type option
# Args: current_index, total_args, all_arguments_array...
handle_agent_type_option() {
    local current_idx="$1"
    local total_args="$2"
    shift 2
    local args=("$@")
    
    # Check if next argument exists
    if [ $((current_idx + 1)) -gt $total_args ]; then
        echo "ERROR: --agent-type requires a value" >&2
        return 1
    fi
    
    # Get the next argument (args array is 0-indexed, current_idx is 1-indexed)
    local next_array_idx=$current_idx  # args[0] = script_arg[1], so current_idx maps correctly
    AGENT_TYPE="${args[$next_array_idx]}"
    
    return 0
}

# Handle positional arguments (for backward compatibility)
# Args: argument_value, argument_index
handle_positional_argument() {
    local arg="$1"
    local idx="$2"
    
    # For backward compatibility: first positional argument is treated as agent-type
    if [ "$idx" -eq 1 ]; then
        AGENT_TYPE="$arg"
        return 0
    else
        echo "ERROR: Unknown option '$arg'. Use --help for usage information." >&2
        return 1
    fi
}

# Auto-detect agent types from repository structure
# Checks for all agent-specific directories in $REPO_ROOT
# Output: detected agent types (space-separated, prints to stdout)
# Returns: 0 if at least one agent found, 1 if not found
detect_agent_types() {
    if [[ ! -d "$REPO_ROOT" ]]; then
        return 1
    fi

    local detected_agents=()
    
    # Check all possible agent directories
    if [[ -d "$REPO_ROOT/.cursor" ]]; then
        detected_agents+=("cursor-agent")
    fi
    
    if [[ -d "$REPO_ROOT/.flow" ]]; then
        detected_agents+=("flow")
    fi
    
    if [[ -d "$REPO_ROOT/.claude" ]]; then
        detected_agents+=("claude")
    fi
    
    # Output detected agents (space-separated)
    if [[ ${#detected_agents[@]} -gt 0 ]]; then
        echo "${detected_agents[*]}"
        return 0
    else
        echo ""
        return 1
    fi
}

# Get count of agents from space-separated string
# Args: agent_string (space-separated)
# Output: number of agents
get_agent_count() {
    local agent_string="$1"
    if [[ -z "$agent_string" ]]; then
        echo 0
        return 0
    fi
    local agents_array=($agent_string)
    echo ${#agents_array[@]}
}

# Validate agent type against registry
# Args: agent_type
# Returns: 0 if valid, 1 if invalid
validate_agent_type() {
    local agent_type="$1"
    
    if [[ -z "$agent_type" ]]; then
        return 0  # Empty is valid (will trigger auto-detection or update all)
    fi
    
    if [[ -z "${AGENT_REGISTRY[$agent_type]}" ]]; then
        log_error "Invalid agent type '$agent_type'"
        log_error "Valid types: $valid_agents"
        return 1
    fi
    
    return 0
}

# Parse command line arguments
parse_arguments "$@"

# Get all paths and variables from common functions
eval $(get_feature_paths)

NEW_DESIGN="$IMPL_DESIGN"  # Alias for compatibility with existing code

#==============================================================================
# Agent Configuration Registry
#==============================================================================
# To add a new agent type, simply add an entry here with:
#   - Key: agent type identifier (used in --agent-type parameter)
#   - Value format: "file_path|display_name"
#   - file_path: full path to agent context file (use $REPO_ROOT)
#   - display_name: human-readable name for logging
#
# Example:
#   AGENT_REGISTRY[new-agent]="$REPO_ROOT/.new-agent/rules/specify-rules.md|New Agent IDE"

declare -A AGENT_REGISTRY

# Register agent types here
AGENT_REGISTRY[claude]="$REPO_ROOT/CLAUDE.md|Claude Code"
AGENT_REGISTRY[cursor-agent]="$REPO_ROOT/.cursor/rules/specify-rules.mdc|Cursor IDE"
AGENT_REGISTRY[flow]="$REPO_ROOT/.flow/rules/specify-rules.mdc|Flow IDE"

# Generate valid_agents string from registry
valid_agents=$(IFS='|'; echo "${!AGENT_REGISTRY[*]}")

# Template file
TEMPLATE_FILE="$REPO_ROOT/.infra/templates/agent-file-template.md"

# Global variables for parsed design data
NEW_LANG=""
NEW_FRAMEWORK=""
NEW_DB=""
NEW_PROJECT_TYPE=""

#==============================================================================
# Utility Functions
#==============================================================================

log_info() {
    echo "INFO: $1"
}

log_success() {
    echo "✓ $1"
}

log_error() {
    echo "ERROR: $1" >&2
}

log_warning() {
    echo "WARNING: $1" >&2
}

# Cleanup function for temporary files
cleanup() {
    local exit_code=$?
    rm -f /tmp/agent_update_*_$$
    rm -f /tmp/manual_additions_$$
    exit $exit_code
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

#==============================================================================
# Validation Functions
#==============================================================================

validate_environment() {
    # Check if we have a current branch/feature (git or non-git)
    if [[ -z "$CURRENT_BRANCH" ]]; then
        log_error "Unable to determine current feature"
        if [[ "$HAS_GIT" == "true" ]]; then
            log_info "Make sure you're on a feature branch"
        else
            log_info "Set SPECIFY_FEATURE environment variable or create a feature first"
        fi
        exit 1
    fi
    
    # Check if design.md exists
    if [[ ! -f "$NEW_DESIGN" ]]; then
        log_error "No design.md found at $NEW_DESIGN"
        log_info "Make sure you're working on a feature with a corresponding spec directory"
        if [[ "$HAS_GIT" != "true" ]]; then
            log_info "Use: export SPECIFY_FEATURE=your-feature-name or create a new feature first"
        fi
        exit 1
    fi
    
    # Check if template exists (needed for new files)
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        log_warning "Template file not found at $TEMPLATE_FILE"
        log_warning "Creating new agent files will fail"
    fi
}

#==============================================================================
# Design Parsing Functions
#==============================================================================

extract_design_field() {
    local field_pattern="$1"
    local design_file="$2"
    
    grep "^\*\*${field_pattern}\*\*: " "$design_file" 2>/dev/null | \
        head -1 | \
        sed "s|^\*\*${field_pattern}\*\*: ||" | \
        sed 's/^[ \t]*//;s/[ \t]*$//' | \
        grep -v "NEEDS CLARIFICATION" | \
        grep -v "^N/A$" || echo ""
}

parse_design_data() {
    local design_file="$1"
    
    if [[ ! -f "$design_file" ]]; then
        log_error "Design file not found: $design_file"
        return 1
    fi
    
    if [[ ! -r "$design_file" ]]; then
        log_error "Design file is not readable: $design_file"
        return 1
    fi
    
    log_info "Parsing design data from $design_file"
    
    NEW_LANG=$(extract_design_field "Language/Version" "$design_file")
    NEW_FRAMEWORK=$(extract_design_field "Primary Dependencies" "$design_file")
    NEW_DB=$(extract_design_field "Storage" "$design_file")
    NEW_PROJECT_TYPE=$(extract_design_field "Project Type" "$design_file")
    
    # Log what we found
    if [[ -n "$NEW_LANG" ]]; then
        log_info "Found language: $NEW_LANG"
    else
        log_warning "No language information found in design"
    fi
    
    if [[ -n "$NEW_FRAMEWORK" ]]; then
        log_info "Found framework: $NEW_FRAMEWORK"
    fi
    
    if [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]]; then
        log_info "Found database: $NEW_DB"
    fi
    
    if [[ -n "$NEW_PROJECT_TYPE" ]]; then
        log_info "Found project type: $NEW_PROJECT_TYPE"
    fi
}

format_technology_stack() {
    local lang="$1"
    local framework="$2"
    local parts=()
    
    # Add non-empty parts
    [[ -n "$lang" && "$lang" != "NEEDS CLARIFICATION" ]] && parts+=("$lang")
    [[ -n "$framework" && "$framework" != "NEEDS CLARIFICATION" && "$framework" != "N/A" ]] && parts+=("$framework")
    
    # Join with proper formatting
    if [[ ${#parts[@]} -eq 0 ]]; then
        echo ""
    elif [[ ${#parts[@]} -eq 1 ]]; then
        echo "${parts[0]}"
    else
        # Join multiple parts with " + "
        local result="${parts[0]}"
        for ((i=1; i<${#parts[@]}; i++)); do
            result="$result + ${parts[i]}"
        done
        echo "$result"
    fi
}

#==============================================================================
# Template and Content Generation Functions
#==============================================================================

get_project_structure() {
    local project_type="$1"
    
    if [[ "$project_type" == *"web"* ]]; then
        echo "backend/\\nfrontend/\\ntests/"
    else
        echo "src/\\ntests/"
    fi
}

get_commands_for_language() {
    local lang="$1"
    
    case "$lang" in
        *"Python"*)
            echo "cd src && pytest && ruff check ."
            ;;
        *"Rust"*)
            echo "cargo test && cargo clippy"
            ;;
        *"JavaScript"*|*"TypeScript"*)
            echo "npm test \\&\\& npm run lint"
            ;;
        *)
            echo "# Add commands for $lang"
            ;;
    esac
}

get_language_conventions() {
    local lang="$1"
    echo "$lang: Follow standard conventions"
}

create_new_agent_file() {
    local target_file="$1"
    local temp_file="$2"
    local project_name="$3"
    local current_date="$4"
    
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        log_error "Template not found at $TEMPLATE_FILE"
        return 1
    fi
    
    if [[ ! -r "$TEMPLATE_FILE" ]]; then
        log_error "Template file is not readable: $TEMPLATE_FILE"
        return 1
    fi
    
    log_info "Creating new agent context file from template..."
    
    if ! cp "$TEMPLATE_FILE" "$temp_file"; then
        log_error "Failed to copy template file"
        return 1
    fi
    
    # Replace template placeholders
    local project_structure
    project_structure=$(get_project_structure "$NEW_PROJECT_TYPE")
    
    local commands
    commands=$(get_commands_for_language "$NEW_LANG")
    
    local language_conventions
    language_conventions=$(get_language_conventions "$NEW_LANG")
    
    # Perform substitutions with error checking using safer approach
    # Escape special characters for sed by using a different delimiter or escaping
    local escaped_lang=$(printf '%s\n' "$NEW_LANG" | sed 's/[\[\.*^$()+{}|]/\\&/g')
    local escaped_framework=$(printf '%s\n' "$NEW_FRAMEWORK" | sed 's/[\[\.*^$()+{}|]/\\&/g')
    local escaped_branch=$(printf '%s\n' "$CURRENT_BRANCH" | sed 's/[\[\.*^$()+{}|]/\\&/g')
    
    # Build technology stack and recent change strings conditionally
    local tech_stack
    if [[ -n "$escaped_lang" && -n "$escaped_framework" ]]; then
        tech_stack="- $escaped_lang + $escaped_framework ($escaped_branch)"
    elif [[ -n "$escaped_lang" ]]; then
        tech_stack="- $escaped_lang ($escaped_branch)"
    elif [[ -n "$escaped_framework" ]]; then
        tech_stack="- $escaped_framework ($escaped_branch)"
    else
        tech_stack="- ($escaped_branch)"
    fi

    local recent_change
    if [[ -n "$escaped_lang" && -n "$escaped_framework" ]]; then
        recent_change="- $escaped_branch: Added $escaped_lang + $escaped_framework"
    elif [[ -n "$escaped_lang" ]]; then
        recent_change="- $escaped_branch: Added $escaped_lang"
    elif [[ -n "$escaped_framework" ]]; then
        recent_change="- $escaped_branch: Added $escaped_framework"
    else
        recent_change="- $escaped_branch: Added"
    fi

    local substitutions=(
        "s|\[PROJECT NAME\]|$project_name|"
        "s|\[DATE\]|$current_date|"
        "s|\[EXTRACTED FROM ALL DESIGN.MD FILES\]|$tech_stack|"
        "s|\[ACTUAL STRUCTURE FROM DESIGNS\]|$project_structure|g"
        "s|\[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES\]|$commands|"
        "s|\[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE\]|$language_conventions|"
        "s|\[LAST 3 FEATURES AND WHAT THEY ADDED\]|$recent_change|"
    )
    
    for substitution in "${substitutions[@]}"; do
        if ! sed -i.bak -e "$substitution" "$temp_file"; then
            log_error "Failed to perform substitution: $substitution"
            rm -f "$temp_file" "$temp_file.bak"
            return 1
        fi
    done
    
    # Convert \n sequences to actual newlines
    newline=$(printf '\n')
    sed -i.bak2 "s/\\\\n/${newline}/g" "$temp_file"
    
    # Clean up backup files
    rm -f "$temp_file.bak" "$temp_file.bak2"
    
    return 0
}

update_existing_agent_file() {
    local target_file="$1"
    local current_date="$2"
    
    log_info "Updating existing agent context file..."
    
    # Use a single temporary file for atomic update
    local temp_file
    temp_file=$(mktemp) || {
        log_error "Failed to create temporary file"
        return 1
    }
    
    # Process the file in one pass
    local tech_stack=$(format_technology_stack "$NEW_LANG" "$NEW_FRAMEWORK")
    local new_tech_entries=()
    local new_change_entry=""
    
    # Prepare new technology entries
    if [[ -n "$tech_stack" ]] && ! grep -q "$tech_stack" "$target_file"; then
        new_tech_entries+=("- $tech_stack ($CURRENT_BRANCH)")
    fi
    
    if [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]] && [[ "$NEW_DB" != "NEEDS CLARIFICATION" ]] && ! grep -q "$NEW_DB" "$target_file"; then
        new_tech_entries+=("- $NEW_DB ($CURRENT_BRANCH)")
    fi
    
    # Prepare new change entry
    if [[ -n "$tech_stack" ]]; then
        new_change_entry="- $CURRENT_BRANCH: Added $tech_stack"
    elif [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]] && [[ "$NEW_DB" != "NEEDS CLARIFICATION" ]]; then
        new_change_entry="- $CURRENT_BRANCH: Added $NEW_DB"
    fi
    
    # Check if sections exist in the file
    local has_active_technologies=0
    local has_recent_changes=0
    
    if grep -q "^## Active Technologies" "$target_file" 2>/dev/null; then
        has_active_technologies=1
    fi
    
    if grep -q "^## Recent Changes" "$target_file" 2>/dev/null; then
        has_recent_changes=1
    fi
    
    # Process file line by line
    local in_tech_section=false
    local in_changes_section=false
    local tech_entries_added=false
    local changes_entries_added=false
    local existing_changes_count=0
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Handle Active Technologies section
        if [[ "$line" == "## Active Technologies" ]]; then
            echo "$line" >> "$temp_file"
            in_tech_section=true
            continue
        elif [[ $in_tech_section == true ]] && [[ "$line" =~ ^##[[:space:]] ]]; then
            # Add new tech entries before closing the section
            if [[ $tech_entries_added == false ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
                printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
                tech_entries_added=true
            fi
            echo "$line" >> "$temp_file"
            in_tech_section=false
            continue
        elif [[ $in_tech_section == true ]] && [[ -z "$line" ]]; then
            # Add new tech entries before empty line in tech section
            if [[ $tech_entries_added == false ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
                printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
                tech_entries_added=true
            fi
            echo "$line" >> "$temp_file"
            continue
        fi
        
        # Handle Recent Changes section
        if [[ "$line" == "## Recent Changes" ]]; then
            echo "$line" >> "$temp_file"
            # Add new change entry right after the heading
            if [[ -n "$new_change_entry" ]]; then
                echo "$new_change_entry" >> "$temp_file"
            fi
            in_changes_section=true
            changes_entries_added=true
            continue
        elif [[ $in_changes_section == true ]] && [[ "$line" =~ ^##[[:space:]] ]]; then
            echo "$line" >> "$temp_file"
            in_changes_section=false
            continue
        elif [[ $in_changes_section == true ]] && [[ "$line" == "- "* ]]; then
            # Keep only first 2 existing changes
            if [[ $existing_changes_count -lt 2 ]]; then
                echo "$line" >> "$temp_file"
                ((existing_changes_count++))
            fi
            continue
        fi
        
        # Update timestamp
        if [[ "$line" =~ \*\*Last\ updated\*\*:.*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] ]]; then
            echo "$line" | sed "s/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/$current_date/" >> "$temp_file"
        else
            echo "$line" >> "$temp_file"
        fi
    done < "$target_file"
    
    # Post-loop check: if we're still in the Active Technologies section and haven't added new entries
    if [[ $in_tech_section == true ]] && [[ $tech_entries_added == false ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
        printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
        tech_entries_added=true
    fi
    
    # If sections don't exist, add them at the end of the file
    if [[ $has_active_technologies -eq 0 ]] && [[ ${#new_tech_entries[@]} -gt 0 ]]; then
        echo "" >> "$temp_file"
        echo "## Active Technologies" >> "$temp_file"
        printf '%s\n' "${new_tech_entries[@]}" >> "$temp_file"
        tech_entries_added=true
    fi
    
    if [[ $has_recent_changes -eq 0 ]] && [[ -n "$new_change_entry" ]]; then
        echo "" >> "$temp_file"
        echo "## Recent Changes" >> "$temp_file"
        echo "$new_change_entry" >> "$temp_file"
        changes_entries_added=true
    fi
    
    # Move temp file to target atomically
    if ! mv "$temp_file" "$target_file"; then
        log_error "Failed to update target file"
        rm -f "$temp_file"
        return 1
    fi
    
    return 0
}
#==============================================================================
# Main Agent File Update Function
#==============================================================================

update_agent_file() {
    local target_file="$1"
    local agent_name="$2"
    
    if [[ -z "$target_file" ]] || [[ -z "$agent_name" ]]; then
        log_error "update_agent_file requires target_file and agent_name parameters"
        return 1
    fi
    
    log_info "Updating $agent_name context file: $target_file"
    
    local project_name
    project_name=$(basename "$REPO_ROOT")
    local current_date
    current_date=$(date +%Y-%m-%d)
    
    # Create directory if it doesn't exist
    local target_dir
    target_dir=$(dirname "$target_file")
    if [[ ! -d "$target_dir" ]]; then
        if ! mkdir -p "$target_dir"; then
            log_error "Failed to create directory: $target_dir"
            return 1
        fi
    fi
    
    if [[ ! -f "$target_file" ]]; then
        # Create new file from template
        local temp_file
        temp_file=$(mktemp) || {
            log_error "Failed to create temporary file"
            return 1
        }
        
        if create_new_agent_file "$target_file" "$temp_file" "$project_name" "$current_date"; then
            if mv "$temp_file" "$target_file"; then
                log_success "Created new $agent_name context file"
            else
                log_error "Failed to move temporary file to $target_file"
                rm -f "$temp_file"
                return 1
            fi
        else
            log_error "Failed to create new agent file"
            rm -f "$temp_file"
            return 1
        fi
    else
        # Update existing file
        if [[ ! -r "$target_file" ]]; then
            log_error "Cannot read existing file: $target_file"
            return 1
        fi
        
        if [[ ! -w "$target_file" ]]; then
            log_error "Cannot write to existing file: $target_file"
            return 1
        fi
        
        if update_existing_agent_file "$target_file" "$current_date"; then
            log_success "Updated existing $agent_name context file"
        else
            log_error "Failed to update existing agent file"
            return 1
        fi
    fi
    
    return 0
}

#==============================================================================
# Agent Selection and Processing
#==============================================================================

# Get agent file path from registry
get_agent_file() {
    local agent_type="$1"
    local config="${AGENT_REGISTRY[$agent_type]}"
    if [[ -z "$config" ]]; then
        return 1
    fi
    echo "$config" | cut -d'|' -f1
}

# Get agent display name from registry
get_agent_name() {
    local agent_type="$1"
    local config="${AGENT_REGISTRY[$agent_type]}"
    if [[ -z "$config" ]]; then
        return 1
    fi
    echo "$config" | cut -d'|' -f2
}

update_specific_agent() {
    local agent_type="$1"
    
    local agent_file
    local agent_name
    
    agent_file=$(get_agent_file "$agent_type")
    agent_name=$(get_agent_name "$agent_type")
    
    if [[ -z "$agent_file" ]] || [[ -z "$agent_name" ]]; then
        log_error "Unknown agent type '$agent_type'"
        log_error "Expected: $valid_agents"
        exit 1
    fi
    
    update_agent_file "$agent_file" "$agent_name"
}

# Update multiple agent types
# Args: space-separated list of agent types
# Returns: 0 if all succeed, 1 if any fail
update_multiple_agents() {
    local agent_types="$1"
    local success=true
    
    if [[ -z "$agent_types" ]]; then
        return 1
    fi
    
    # Convert space-separated string to array
    local agents_array=($agent_types)
    
    log_info "Updating ${#agents_array[@]} detected agent(s): ${agents_array[*]}"
    
    for agent_type in "${agents_array[@]}"; do
        if ! update_specific_agent "$agent_type"; then
            success=false
        fi
    done
    
    if [[ "$success" == true ]]; then
        return 0
    else
        return 1
    fi
}

update_all_existing_agents() {
    local found_agent=false
    local default_agent=""
    
    # Iterate through all registered agents
    for agent_type in "${!AGENT_REGISTRY[@]}"; do
        local agent_file
        local agent_name
        
        agent_file=$(get_agent_file "$agent_type")
        agent_name=$(get_agent_name "$agent_type")
        
        if [[ -z "$agent_file" ]] || [[ -z "$agent_name" ]]; then
            continue
        fi
        
        # Store first agent as default (usually claude)
        if [[ -z "$default_agent" ]]; then
            default_agent="$agent_type"
        fi
        
        # Check if agent file exists and update it
        if [[ -f "$agent_file" ]]; then
            update_agent_file "$agent_file" "$agent_name"
            found_agent=true
        fi
    done
    
    # If no agent files exist, create a default agent file
    if [[ "$found_agent" == false ]] && [[ -n "$default_agent" ]]; then
        log_info "No existing agent files found, creating default agent file..."
        local default_file
        local default_name
        default_file=$(get_agent_file "$default_agent")
        default_name=$(get_agent_name "$default_agent")
        update_agent_file "$default_file" "$default_name"
    fi
}
print_summary() {
    echo
    log_info "Summary of changes:"
    
    if [[ -n "$NEW_LANG" ]]; then
        echo "  - Added language: $NEW_LANG"
    fi
    
    if [[ -n "$NEW_FRAMEWORK" ]]; then
        echo "  - Added framework: $NEW_FRAMEWORK"
    fi
    
    if [[ -n "$NEW_DB" ]] && [[ "$NEW_DB" != "N/A" ]]; then
        echo "  - Added database: $NEW_DB"
    fi
    
    echo

    log_info "Usage: $0 [--agent-type <type>]"
    log_info "Agent types: $valid_agents"
}

#==============================================================================
# Main Execution
#==============================================================================

main() {
    # Validate environment before proceeding
    validate_environment
    
    # Auto-detect agent types if not specified
    if [[ -z "$AGENT_TYPE" ]]; then
        log_info "No agent type specified, attempting auto-detection..."
        local detected_agents
        detected_agents=$(detect_agent_types)
        
        if [[ -n "$detected_agents" ]]; then
            AGENT_TYPE="$detected_agents"
            # Check if multiple agents detected
            local agent_count
            agent_count=$(get_agent_count "$detected_agents")
            if [[ $agent_count -gt 1 ]]; then
                log_info "Auto-detected $agent_count agent types: ${detected_agents}"
                log_info "Will update all detected agents"
            else
                log_info "Auto-detected agent type: $AGENT_TYPE"
            fi
        else
            log_info "No agent directories found (.cursor, .flow, or .claude)"
            log_info "Will update all existing agent files"
        fi
    fi
    
    # Validate agent type(s) if specified (registry is now initialized)
    if [[ -n "$AGENT_TYPE" ]]; then
        local agents_to_validate=($AGENT_TYPE)
        for agent_type in "${agents_to_validate[@]}"; do
            if ! validate_agent_type "$agent_type"; then
                exit 1
            fi
        done
    fi
    
    log_info "=== Updating agent context files for feature $CURRENT_BRANCH ==="
    
    # Parse the design file to extract project information
    if ! parse_design_data "$NEW_DESIGN"; then
        log_error "Failed to parse design data"
        exit 1
    fi
    
    # Process based on agent type argument
    local success=true
    
    if [[ -z "$AGENT_TYPE" ]]; then
        # No specific agent provided and auto-detection failed - update all existing agent files
        log_info "Updating all existing agent files..."
        if ! update_all_existing_agents; then
            success=false
        fi
    else
        # Check if multiple agents specified (space-separated)
        local agent_count
        agent_count=$(get_agent_count "$AGENT_TYPE")
        if [[ $agent_count -gt 1 ]]; then
            # Multiple agents detected or specified - update all of them
            if ! update_multiple_agents "$AGENT_TYPE"; then
                success=false
            fi
        else
            # Single agent specified - update only that agent
            log_info "Updating agent: $AGENT_TYPE"
            if ! update_specific_agent "$AGENT_TYPE"; then
                success=false
            fi
        fi
    fi
    
    # Print summary
    print_summary
    
    if [[ "$success" == true ]]; then
        log_success "Agent context update completed successfully"
        exit 0
    else
        log_error "Agent context update completed with errors"
        exit 1
    fi
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

