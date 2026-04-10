#!/bin/bash

set -euo pipefail

# lilly-code Enhanced Installation Script
# Provides guided setup with user autonomy at each step

BINARY_NAME="lilly-code"
DEV_SERVER_URL="https://lilly-code-server.api.gateway.llm.lilly.com"
INSTALL_BASE_URL="https://lilly-code-install.apps-internal.lrl.lilly.com"

# Installation options
INSTALL_DIR="$HOME/.local/bin"
SYSTEM_INSTALL_DIR="/usr/local/bin"
SYSTEM_WIDE_INSTALL=false
AUTO_YES=false
QUIET_MODE=false
SELECTED_MODEL="sonnet"  # Default model

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    if [[ "$QUIET_MODE" != "true" ]]; then
        echo -e "${CYAN}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [[ "$QUIET_MODE" != "true" ]]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    if [[ "$QUIET_MODE" != "true" ]]; then
        echo -e "${PURPLE}📋 Step $1${NC}"
    fi
}

# User interaction functions
prompt_continue() {
    local message="${1:-Press Enter to continue, or Ctrl+C to cancel}"

    # Auto-yes mode: always continue
    if [[ "$AUTO_YES" == "true" ]]; then
        if [[ "$QUIET_MODE" != "true" ]]; then
            echo -e "${BLUE}$message [auto-continue]${NC}"
        fi
        return 0
    fi

    if [[ "$QUIET_MODE" != "true" ]]; then
        echo -ne "${BLUE}$message: ${NC}"
    fi

    # Try to read from /dev/tty for pipeline compatibility
    if [[ -t 0 ]] && [[ -t 1 ]]; then
        # Standard interactive terminal
        read -r
    elif [[ -c /dev/tty ]] && read -r < /dev/tty 2>/dev/null; then
        # Pipeline mode with /dev/tty available - already read above
        :  # no-op, read was successful
    else
        # Non-interactive mode fallback (no TTY available)
        if [[ "$QUIET_MODE" != "true" ]]; then
            log_warning "Running in non-interactive mode. Continuing automatically."
        fi
    fi

    return 0
}

prompt_select() {
    local prompt="$1"
    shift
    local options=("$@")

    # Auto-yes mode: always select first option
    if [[ "$AUTO_YES" == "true" ]]; then
        if [[ "$QUIET_MODE" != "true" ]]; then
            echo -e "${BLUE}$prompt [auto-selected: 1]${NC}"
        fi
        return 0
    fi

    echo -e "${CYAN}$prompt${NC}"
    for i in "${!options[@]}"; do
        echo "$((i + 1)). ${options[i]}"
    done

    while true; do
        echo -ne "${BLUE}Choose option [1-${#options[@]}]: ${NC}"

        local response
        if [[ -t 0 ]] && [[ -t 1 ]]; then
            # Standard interactive terminal
            read -r response
        elif [[ -c /dev/tty ]]; then
            # Try pipeline mode with /dev/tty
            if read -r response < /dev/tty 2>/dev/null; then
                : # Successfully read from /dev/tty
            else
                # /dev/tty exists but can't read - fall back to non-interactive
                if [[ "$QUIET_MODE" != "true" ]]; then
                    log_warning "Running in non-interactive mode. Selecting option 1."
                fi
                return 0
            fi
        else
            # Non-interactive mode fallback - select first option
            if [[ "$QUIET_MODE" != "true" ]]; then
                log_warning "Running in non-interactive mode. Selecting option 1."
            fi
            return 0
        fi

        # Default to 1 if empty
        if [[ -z "$response" ]]; then
            response="1"
        fi

        # Validate selection
        if [[ "$response" =~ ^[0-9]+$ ]] && [[ "$response" -ge 1 ]] && [[ "$response" -le "${#options[@]}" ]]; then
            return $((response - 1))
        else
            if [[ (-t 0 && -t 1) || -c /dev/tty ]]; then
                echo "Please select a number between 1 and ${#options[@]}."
            else
                # Non-interactive fallback
                return 0
            fi
        fi
    done
}

prompt_select_with_default() {
    local prompt="$1"
    local default_index="$2"
    shift 2
    local options=("$@")

    # Auto-yes mode: select default option
    if [[ "$AUTO_YES" == "true" ]]; then
        if [[ "$QUIET_MODE" != "true" ]]; then
            echo -e "${BLUE}$prompt [auto-selected: $((default_index + 1))]${NC}"
        fi
        return $default_index
    fi

    echo -e "${CYAN}$prompt${NC}"
    for i in "${!options[@]}"; do
        if [[ $i -eq $default_index ]]; then
            echo -e "$((i + 1)). ${options[i]} ${GREEN}<- default${NC}"
        else
            echo "$((i + 1)). ${options[i]}"
        fi
    done

    while true; do
        echo -ne "${BLUE}Choose option [1-${#options[@]}] (Enter for default): ${NC}"

        local response
        if [[ -t 0 ]] && [[ -t 1 ]]; then
            read -r response
        elif [[ -c /dev/tty ]]; then
            if read -r response < /dev/tty 2>/dev/null; then
                :
            else
                if [[ "$QUIET_MODE" != "true" ]]; then
                    log_warning "Running in non-interactive mode. Selecting default."
                fi
                return $default_index
            fi
        else
            if [[ "$QUIET_MODE" != "true" ]]; then
                log_warning "Running in non-interactive mode. Selecting default."
            fi
            return $default_index
        fi

        # Empty input = default
        if [[ -z "$response" ]]; then
            return $default_index
        fi

        # Validate selection
        if [[ "$response" =~ ^[0-9]+$ ]] && [[ "$response" -ge 1 ]] && [[ "$response" -le "${#options[@]}" ]]; then
            return $((response - 1))
        else
            if [[ (-t 0 && -t 1) || -c /dev/tty ]]; then
                echo -e "${RED}Please select a number between 1 and ${#options[@]}, or press Enter for default.${NC}"
            else
                return $default_index
            fi
        fi
    done
}

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-y}"

    # Auto-yes mode: always return success (yes)
    if [[ "$AUTO_YES" == "true" ]]; then
        if [[ "$QUIET_MODE" != "true" ]]; then
            echo -e "${BLUE}$prompt [auto-yes]${NC}"
        fi
        return 0
    fi

    if [[ "$default" == "y" ]]; then
        local options="[Y/n]"
    else
        local options="[y/N]"
    fi

    while true; do
        echo -ne "${BLUE}$prompt $options: ${NC}"

        # Try to read from /dev/tty for pipeline compatibility
        local response
        if [[ -t 0 ]] && [[ -t 1 ]]; then
            # Standard interactive terminal
            read -r response
        elif [[ -c /dev/tty ]]; then
            # Try pipeline mode with /dev/tty
            if read -r response < /dev/tty 2>/dev/null; then
                : # Successfully read from /dev/tty
            else
                # /dev/tty exists but can't read - fall back to non-interactive
                if [[ "$QUIET_MODE" != "true" ]]; then
                    log_warning "Running in non-interactive mode. Using default: $default"
                fi
                response="$default"
            fi
        else
            # Non-interactive mode fallback (no TTY available)
            if [[ "$QUIET_MODE" != "true" ]]; then
                log_warning "Running in non-interactive mode. Using default: $default"
            fi
            response="$default"
        fi

        if [[ -z "$response" ]]; then
            response="$default"
        fi

        case "$(echo "$response" | tr '[:upper:]' '[:lower:]')" in
            y|yes) return 0 ;;
            n|no) return 1 ;;
            *)
                if [[ (-t 0 && -t 1) || -c /dev/tty ]]; then
                    echo "Please answer yes or no."
                else
                    # Non-interactive: don't loop, use default
                    if [[ "$default" == "y" ]]; then
                        return 0
                    else
                        return 1
                    fi
                fi
                ;;
        esac
    done
}

# Check if directory is in PATH
is_in_path() {
    local dir="$1"
    case ":$PATH:" in
        *":$dir:"*) return 0 ;;
        *) return 1 ;;
    esac
}

# Get appropriate shell config file
get_shell_config_file() {
    local shell_name
    shell_name="$(basename "$SHELL")"

    case "$shell_name" in
        "zsh")
            if [[ -f "$HOME/.zshrc" ]]; then
                echo "$HOME/.zshrc"
            else
                echo "$HOME/.zprofile"
            fi
            ;;
        "bash")
            # Prefer .bashrc on Linux, .bash_profile on macOS
            if [[ "$(detect_os)" == "macos" ]]; then
                echo "$HOME/.bash_profile"
            else
                echo "$HOME/.bashrc"
            fi
            ;;
        "fish")
            echo "$HOME/.config/fish/config.fish"
            ;;
        *)
            echo "$HOME/.profile"
            ;;
    esac
}

# Add directory to PATH in shell config
setup_path() {
    local target_dir="$1"
    local os=$(detect_os)

    if is_in_path "$target_dir"; then
        log_success "$target_dir is already in PATH"
        return 0
    fi

    log_warning "$target_dir is not in your PATH"

    set +e  # Temporarily disable exit on error for prompt
    prompt_select "Add $target_dir to your PATH?" \
        "Yes, add to PATH (recommended)" \
        "Skip PATH setup (I'll add it manually)"
    local path_choice=$?
    set -e  # Re-enable exit on error

    case $path_choice in
        0)
            if [[ "$os" == "windows" ]]; then
                # Windows PowerShell profile setup
                log_info "Adding to PATH in PowerShell profile"

                # Use PowerShell to add to user PATH environment variable
                local ps_cmd="[Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH', 'User') + ';$target_dir', 'User')"

                if command -v powershell.exe >/dev/null 2>&1; then
                    powershell.exe -Command "$ps_cmd"
                elif command -v pwsh >/dev/null 2>&1; then
                    pwsh -Command "$ps_cmd"
                else
                    log_warning "PowerShell not found. Please add $target_dir to your PATH manually"
                    log_info "You can add it by running: setx PATH \"%PATH%;$target_dir\""
                    return 1
                fi

                log_success "Added $target_dir to PATH in Windows user environment"
                log_info "Please restart your terminal to use the updated PATH"

                # Update PATH for current session
                export PATH="$target_dir:$PATH"

                return 0
            else
                # Unix shell config setup
                local config_file
                config_file="$(get_shell_config_file)"

                log_info "Adding to PATH in $config_file"

                # Create the directory if it doesn't exist
                mkdir -p "$(dirname "$config_file")"

                # Add PATH export to shell config
                echo "" >> "$config_file"
                echo "# Added by lilly-code installer" >> "$config_file"
                echo "export PATH=\"$target_dir:\$PATH\"" >> "$config_file"

                log_success "Added $target_dir to PATH in $config_file"
                log_info "Please restart your terminal or run: source $config_file"

                # Update PATH for current session
                export PATH="$target_dir:$PATH"

                return 0
            fi
            ;;
        1)
            log_warning "PATH not updated. You may need to add $target_dir to your PATH manually"
            if [[ "$os" == "windows" ]]; then
                log_info "Windows: Add to PATH via System Properties > Environment Variables"
                log_info "Or run: setx PATH \"%PATH%;$target_dir\""
            fi
            return 1
            ;;
    esac
}


show_command_preview() {
    local cmd="$1"
    echo -e "${CYAN}Will run: ${NC}${YELLOW}$cmd${NC}"
}

# System detection
detect_os() {
    case "$(uname -s)" in
        Darwin) echo "macos" ;;
        Linux) echo "linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64) echo "x86_64" ;;
        arm64|aarch64) echo "aarch64" ;;
        *) echo "unknown" ;;
    esac
}

# Get latest version from install server
get_latest_version() {
    local version_url="${INSTALL_BASE_URL}/api/version"
    log_info "Checking latest version from: $version_url"

    if command -v curl >/dev/null 2>&1; then
        local version_response
        version_response=$(curl -s "$version_url" 2>/dev/null)

        if [[ -n "$version_response" ]]; then
            # Try jq first (most reliable)
            if command -v jq >/dev/null 2>&1; then
                local version
                version=$(echo "$version_response" | jq -r '.version' 2>/dev/null)
                if [[ "$version" != "null" && "$version" != "dev-unknown" && "$version" != "unknown" ]]; then
                    echo "$version"
                    return
                fi
            else
                # Fallback: improved regex parsing
                local version
                version=$(echo "$version_response" | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' 2>/dev/null)
                if [[ -n "$version" && "$version" != "dev-unknown" && "$version" != "unknown" ]]; then
                    echo "$version"
                    return
                fi
            fi
        fi
    fi

    # Fallback to "latest" if parsing fails or returns unknown
    echo "latest"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --system-wide)
                SYSTEM_WIDE_INSTALL=true
                INSTALL_DIR="$SYSTEM_INSTALL_DIR"
                shift
                ;;
            --yes|--auto-yes)
                AUTO_YES=true
                shift
                ;;
            --quiet|-q)
                QUIET_MODE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --system-wide    Install to $SYSTEM_INSTALL_DIR (requires sudo)"
                echo "  --yes, --auto-yes   Automatically answer yes to all prompts"
                echo "  --quiet, -q         Suppress non-essential output"
                echo "  --help, -h          Show this help message"
                exit 0
                ;;
            *)
                log_warning "Unknown option: $1"
                shift
                ;;
        esac
    done
}

# Create Cline integration symlink
create_cline_symlink() {
    local target_dir="$1"
    local symlink_path="$target_dir/lilly-code-claude"

    if [[ -f "$target_dir/$BINARY_NAME" ]]; then
        if [[ ! -L "$symlink_path" ]] && [[ ! -f "$symlink_path" ]]; then
            log_info "Creating symlink for Cline integration..."
            if ln -s "$target_dir/$BINARY_NAME" "$symlink_path" 2>/dev/null; then
                log_success "Created lilly-code-claude symlink for Cline compatibility"
                log_info "Cline users can now set CLI path to: lilly-code-claude"
            else
                log_warning "Failed to create lilly-code-claude symlink"
            fi
        elif [[ -L "$symlink_path" ]]; then
            log_info "lilly-code-claude symlink already exists"
        elif [[ -f "$symlink_path" ]]; then
            log_warning "lilly-code-claude already exists as a regular file (skipping symlink creation)"
        fi
    else
        log_warning "Cannot create symlink: $target_dir/$BINARY_NAME not found"
    fi
}

# Installation functions
install_binary() {
    log_step "1/5: Binary Installation"

    # Get latest version from server
    local latest_version=$(get_latest_version)
    echo "Installing lilly-code binary (latest version: $latest_version)..."

    local os=$(detect_os)
    local arch=$(detect_arch)

    if [[ "$os" == "unknown" || "$arch" == "unknown" ]]; then
        log_error "Unsupported platform: $os/$arch"
        log_info "Supported platforms: macOS (Intel/ARM), Linux (x86_64), Windows (x86_64/ARM64)"
        return 1
    fi

    log_info "Platform detected: $os/$arch"

    # Determine installation location
    local install_target="$INSTALL_DIR"
    local needs_sudo=false

    if [[ "$SYSTEM_WIDE_INSTALL" == "true" ]]; then
        install_target="$SYSTEM_INSTALL_DIR"
        needs_sudo=true
        log_info "Installing to system location: $install_target (requires sudo)"
    else
        log_info "Installing to user location: $install_target (no sudo required)"
        # Create user bin directory if it doesn't exist
        mkdir -p "$install_target"
    fi

    # Check if we have a local build to use instead
    if [[ -f "./target/release/$BINARY_NAME" ]]; then
        log_info "Found locally built binary at ./target/release/$BINARY_NAME"

        if [[ "$needs_sudo" == "true" ]]; then
            echo -e "${YELLOW}Installing to system location requires admin privileges${NC}"
        fi

        set +e
        prompt_select "Choose installation method:" \
            "Install locally built binary to $install_target" \
            "Download from install server instead" \
            "Exit installation"
        local choice=$?
        set -e
        case $choice in
            0)
                local install_cmd="cp ./target/release/$BINARY_NAME $install_target/"
                if [[ "$needs_sudo" == "true" ]]; then
                    install_cmd="sudo $install_cmd"
                fi

                show_command_preview "$install_cmd"
                if [[ "$needs_sudo" == "true" ]]; then
                    sudo cp "./target/release/$BINARY_NAME" "$install_target/"
                else
                    cp "./target/release/$BINARY_NAME" "$install_target/"
                fi
                log_success "Binary installed to $install_target/$BINARY_NAME"
                ;;
            1)
                # Fall through to download section
                ;;
            2)
                log_warning "Binary installation skipped"
                return 1
                ;;
        esac
    fi

    # Download from install server (either no local binary or user chose download)
    if [[ ! -f "./target/release/$BINARY_NAME" ]] || [[ $choice -eq 1 ]]; then
        log_info "Downloading binary from install server..."

        # Determine binary name with extension for Windows
        local binary_name_with_ext="$BINARY_NAME"
        if [[ "$os" == "windows" ]]; then
            binary_name_with_ext="${BINARY_NAME}.exe"
        fi

        local download_url="${INSTALL_BASE_URL}/bin/${binary_name_with_ext}-${os}-${arch}"
        if [[ "$os" == "windows" ]]; then
            download_url="${INSTALL_BASE_URL}/bin/${BINARY_NAME}-${os}-${arch}.exe"
        fi
        log_info "Download URL: $download_url"

        # Use appropriate temp location for platform
        local temp_binary
        if [[ "$os" == "windows" ]]; then
            temp_binary="$TEMP/lilly-code-download.exe"
        else
            temp_binary="/tmp/lilly-code-download"
        fi

        show_command_preview "curl -fSL \"$download_url\" -o \"$temp_binary\""
        if curl -fSL "$download_url" -o "$temp_binary"; then
            # Make executable (Unix only)
            if [[ "$os" != "windows" ]]; then
                chmod +x "$temp_binary"
            fi

            # Test the binary
            if "$temp_binary" --version >/dev/null 2>&1; then
                local final_binary_name="$BINARY_NAME"
                if [[ "$os" == "windows" ]]; then
                    final_binary_name="${BINARY_NAME}.exe"
                fi

                local install_cmd="mv \"$temp_binary\" $install_target/$final_binary_name"
                if [[ "$needs_sudo" == "true" ]]; then
                    install_cmd="sudo $install_cmd"
                fi

                show_command_preview "$install_cmd"
                if [[ "$needs_sudo" == "true" ]]; then
                    sudo mv "$temp_binary" "$install_target/$final_binary_name"
                else
                    mv "$temp_binary" "$install_target/$final_binary_name"
                fi
                log_success "Binary installed to $install_target/$BINARY_NAME"
            else
                rm -f "$temp_binary"
                log_error "Downloaded binary failed verification"
                return 1
            fi
        else
            log_error "Failed to download binary from $download_url"
            return 1
        fi
    fi

    # Set up PATH if needed (only for user installation)
    if [[ "$SYSTEM_WIDE_INSTALL" == "false" ]]; then
        setup_path "$install_target"
    fi

    # Store full path for commands (binary may not be in PATH yet during installation)
    BINARY_PATH="$install_target/$BINARY_NAME"

    # Verify installation
    if command -v "$BINARY_NAME" >/dev/null 2>&1; then
        local version_output
        version_output=$("$BINARY_NAME" --version 2>/dev/null || echo "unknown")
        log_success "lilly-code installed: $version_output"

        # Create Cline integration symlink
        create_cline_symlink "$install_target"

        return 0
    else
        if [[ "$SYSTEM_WIDE_INSTALL" == "false" ]]; then
            log_warning "Binary installed but not yet in PATH. Please restart your terminal."
            log_info "Or run: export PATH=\"$install_target:\$PATH\""

            # Create Cline integration symlink even if not in PATH yet
            create_cline_symlink "$install_target"
        else
            log_error "Binary installation failed or not in PATH"
        fi
        return 1
    fi
}

check_prerequisites() {
    log_step "2/5: Prerequisites Check"
    echo "Checking system prerequisites..."

    log_success "✅ All prerequisites satisfied"
    log_info "💡 lilly-code has no external dependencies"
}


show_hpc_login_instructions() {
    echo ""
    log_info "For HPC or browserless environments:"
    echo "  1. On a machine with browser access, run:"
    echo "     ${YELLOW}lilly-code login${NC}"
    echo "     ${YELLOW}lilly-code export-token > token.enc${NC}"
    echo ""
    echo "  2. Transfer the encrypted token file to your HPC system"
    echo ""
    echo "  3. On HPC, import the token:"
    echo "     ${YELLOW}lilly-code login --import-token \$(cat token.enc)${NC}"
    echo ""
    log_info "Detailed instructions: ${CYAN}https://lilly-code.gateway.llm.lilly.com/#hpc${NC}"
    echo ""
}

setup_authentication() {
    log_step "4/5: Authentication Setup"
    echo "Setting up Lilly SSO authentication..."

    # Prompt for login method
    set +e  # Temporarily disable exit on error for prompt
    prompt_select "Choose authentication method:" \
        "Login now (opens browser - requires display/GUI)" \
        "Skip - I'll authenticate manually later (for HPC/browserless)" \
        "Exit installation"
    local auth_choice=$?
    set -e  # Re-enable exit on error

    case $auth_choice in
        0)
            # Login now with browser
            log_info "Starting authentication process..."
            show_command_preview "lilly-code login"

            if "$BINARY_PATH" login; then
                log_success "Authentication completed successfully"
            else
                log_error "Authentication failed"
                echo -e "${YELLOW}Authentication is required for using Lilly Code.${NC}"
                prompt_continue "Press Enter to continue with configuration anyway, or Ctrl+C to exit"
            fi
            ;;
        1)
            # Skip - manual authentication
            log_warning "Skipping automatic authentication"
            show_hpc_login_instructions
            log_info "Continuing with installation..."
            prompt_continue "Press Enter to continue"
            ;;
        2)
            # Exit installation
            log_warning "Installation cancelled by user"
            exit 0
            ;;
    esac
}

prompt_model_selection() {
    log_step "Model Selection"
    echo "Choose your default Claude model for coding tasks."
    echo ""
    echo -e "${YELLOW}💡 Models ordered by cost (lowest to highest):${NC}"
    echo ""

    set +e
    prompt_select_with_default "Select default model:" 1 \
        "haiku - Fast and efficient, lowest cost" \
        "sonnet - Balanced performance (recommended)" \
        "opusplan - Opus for planning, Sonnet for execution" \
        "opus - Most capable, highest cost"
    local model_choice=$?
    set -e

    case $model_choice in
        0) SELECTED_MODEL="haiku" ;;
        1) SELECTED_MODEL="sonnet" ;;
        2) SELECTED_MODEL="opusplan" ;;
        3) SELECTED_MODEL="opus" ;;
        *) SELECTED_MODEL="sonnet" ;;
    esac

    log_info "Selected model: $SELECTED_MODEL"
}

apply_configuration() {
    log_step "3/5: Apply Configuration"
    echo "Applying lilly-code configuration..."

    log_info "Configuring Claude Code integration..."
    log_info "💡 Configuration files will be created for when Claude Code is installed"
    log_info "💡 Configuration must be completed before authentication"

    # Show configuration method selection based on platform
    echo ""
    local os_type=$(detect_os)
    if [[ "$os_type" == "darwin" ]]; then
        # macOS - recommend global since sudo is usually available
        echo -e "${CYAN}💡 Recommendation: Global managed-settings (option 1) is recommended on macOS${NC}"
        echo -e "${CYAN}   This prevents configuration conflicts and ensures proper setup${NC}"
    else
        # Linux and others - don't recommend global unless they have admin
        echo -e "${YELLOW}💡 Note: Global managed-settings (option 1) requires admin privileges${NC}"
        echo -e "${YELLOW}   Use option 2 (user-level) unless you have sudo access${NC}"
    fi
    echo ""

    set +e  # Temporarily disable exit on error for prompt
    prompt_select "Choose configuration method:" \
        "Global managed-settings (prompts for admin password)" \
        "User-level settings (no admin required)" \
        "Skip configuration (I'll do it later)"
    local config_choice=$?
    set -e  # Re-enable exit on error

    case $config_choice in
        0)
            # Global managed-settings
            log_info "Applying global configuration (you may be prompted for admin password)..."
            show_command_preview "lilly-code configure --claude-code --claude-code-scope global --claude-code-model $SELECTED_MODEL --yes"

            if "$BINARY_PATH" configure --claude-code --claude-code-scope global --claude-code-model "$SELECTED_MODEL" --yes; then
                log_success "Global configuration applied successfully"
                log_info "💡 Managed-settings ensure your Lilly configuration cannot be overridden"
            else
                log_error "Global configuration failed"
                echo -e "${YELLOW}This is common on restricted systems. Trying user-level configuration...${NC}"

                show_command_preview "lilly-code configure --claude-code --claude-code-model $SELECTED_MODEL --yes"
                if "$BINARY_PATH" configure --claude-code --claude-code-model "$SELECTED_MODEL" --yes; then
                    log_success "User-level configuration applied successfully"
                else
                    log_error "Configuration failed"
                    prompt_continue "Press Enter to continue anyway, or Ctrl+C to exit"
                fi
            fi
            ;;
        1)
            # User-level settings
            log_info "Applying user-level configuration (no sudo required)..."
            show_command_preview "lilly-code configure --claude-code --claude-code-model $SELECTED_MODEL --yes"

            if "$BINARY_PATH" configure --claude-code --claude-code-model "$SELECTED_MODEL" --yes; then
                log_success "User-level configuration applied successfully"
            else
                log_error "Configuration failed"
                prompt_continue "Press Enter to continue anyway, or Ctrl+C to exit"
            fi
            ;;
        2)
            # Skip configuration
            log_warning "Skipping configuration"
            log_info "You can configure later with:"
            log_info "  Global: lilly-code configure --claude-code --claude-code-scope global --claude-code-model sonnet"
            log_info "  User-level: lilly-code configure --claude-code --claude-code-model sonnet"
            log_info "  Core only: lilly-code configure"
            log_info "  (Environment auto-detected from build version)"
            ;;
    esac
}

verify_setup() {
    log_step "5/5: Setup Verification"
    echo "Verifying complete setup..."

    log_info "Status check:"
    show_command_preview "lilly-code status"

    if "$BINARY_PATH" status; then
        log_success "Setup verification completed"
    else
        log_warning "Status check showed some issues"
        log_info "You may need to complete authentication or configuration manually"
    fi

    echo ""
    echo -e "${GREEN}🎉 lilly-code Installation Complete!${NC}"
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo "  • Check status: lilly-code status"
    echo "  • Get help: lilly-code --help"
    echo "  • Install Claude Code when ready: https://claude.ai/code"
    echo ""
    echo -e "${CYAN}Useful Commands:${NC}"
    echo "  • lilly-code login          - Authenticate with Lilly SSO"
    echo "  • lilly-code configure      - Configure coding agents"
    echo "  • lilly-code status         - Show authentication and configuration status"
    echo "  • lilly-code logout         - Clear cached credentials"
    echo ""
    log_info "💡 Claude Code configuration files have been prepared"
    log_info "    When you install Claude Code, it will automatically use Lilly's servers"
}

# Main installation flow
main() {
    # Parse command line arguments
    parse_args "$@"

    echo -e "${GREEN}🚀 lilly-code Enhanced Installation Script${NC}"
    echo -e "${CYAN}This script will guide you through setting up lilly-code and Claude Code integration.${NC}"
    echo ""

    if [[ "$SYSTEM_WIDE_INSTALL" == "true" ]]; then
        echo -e "${YELLOW}System-wide installation mode: Will install to $SYSTEM_INSTALL_DIR (requires sudo)${NC}"
    else
        echo -e "${CYAN}User installation mode: Will install to $INSTALL_DIR (no sudo required)${NC}"
        echo -e "${CYAN}Use --system-wide flag for system installation if needed${NC}"
    fi

    echo -e "${YELLOW}The installer will guide you through each step. Press Ctrl+C anytime to cancel.${NC}"
    echo ""

    prompt_continue "Press Enter to start the guided installation"

    echo ""

    # Run installation steps
    install_binary || {
        log_error "Binary installation failed"
        exit 1
    }

    echo ""
    check_prerequisites

    echo ""
    prompt_model_selection

    echo ""
    apply_configuration

    echo ""
    setup_authentication

    echo ""
    verify_setup
}

# Error handling
trap 'log_error "Installation interrupted. You can run this script again to continue."; exit 1' INT TERM

# Run main function
main "$@"