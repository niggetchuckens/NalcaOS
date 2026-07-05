#!/usr/bin/env python3
import os
import sys
import re
import time
import datetime
import urllib.request
import urllib.error
import concurrent.futures
import argparse
import subprocess
import shutil

# Paths
MIRRORLIST_PATH = "/etc/pacman.d/cachyos-mirrorlist"
REMOTE_MIRRORLIST_URL = "https://raw.githubusercontent.com/CachyOS/CachyOS-PKGBUILDS/master/cachyos-mirrorlist/cachyos-mirrorlist"

# ANSI Colors
GREEN = "\033[1;32m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[1;36m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Regex for parsing Server = ... lines
# This matches lines like "Server = https://..." or commented out "# Server = https://..."
SERVER_REGEX = re.compile(r'^\s*(#*)\s*Server\s*=\s*(https?://[^\s#]+)', re.IGNORECASE)

class CachyMirror:
    def __init__(self, url, original_line=None, comment_lines=None, is_active=True):
        self.url = url
        self.original_line = original_line
        self.comment_lines = comment_lines or []  # Descriptive comments preceding this mirror
        self.is_active = is_active  # Was it active (uncommented) in the file?
        self.latency = float('inf')
        self.status = "untested"
        self.error_msg = ""

def check_root_or_elevate():
    """Checks if the script is run with root permissions, otherwise elevates via sudo."""
    if os.geteuid() != 0:
        print(f"{YELLOW}This operation requires root privileges. Elevating with sudo...{RESET}")
        try:
            # Re-run the script with sudo, keeping the arguments
            args = ["sudo", sys.executable] + sys.argv
            result = subprocess.run(args)
            sys.exit(result.returncode)
        except Exception as e:
            print(f"{RED}Elevation failed: {e}{RESET}")
            sys.exit(1)

def parse_mirrorlist_content(content):
    """Parses mirrorlist file content and extracts CachyMirror objects."""
    mirrors = []
    current_comments = []
    
    for line in content.splitlines():
        line_strip = line.strip()
        if not line_strip:
            continue
        
        match = SERVER_REGEX.match(line)
        if match:
            comment_char, url = match.groups()
            is_active = (comment_char == '')
            
            # Clean comments of header blocks to prevent them accumulating
            cleaned_comments = []
            for c in current_comments:
                c_upper = c.upper()
                if "CACHYOS" in c_upper and "MIRRORLIST" in c_upper:
                    continue
                if "#####" in c:
                    continue
                if c.strip() in ("#", "##"):
                    continue
                cleaned_comments.append(c)
                
            # Deduplicate by url in the local session
            if not any(m.url == url for m in mirrors):
                mirror = CachyMirror(
                    url=url,
                    original_line=line,
                    comment_lines=cleaned_comments,
                    is_active=is_active
                )
                mirrors.append(mirror)
            current_comments = []
        else:
            current_comments.append(line)
            
    return mirrors

def fetch_local_mirrors():
    """Reads mirrors from the local cachyos-mirrorlist file."""
    if not os.path.exists(MIRRORLIST_PATH):
        return []
    try:
        with open(MIRRORLIST_PATH, "r") as f:
            content = f.read()
        return parse_mirrorlist_content(content)
    except Exception as e:
        print(f"{RED}Error reading local mirrorlist: {e}{RESET}")
        return []

def fetch_remote_mirrors():
    """Downloads the latest mirrorlist from CachyOS's official repository."""
    try:
        req = urllib.request.Request(
            REMOTE_MIRRORLIST_URL,
            headers={'User-Agent': 'cachyos-mirror-manager'}
        )
        with urllib.request.urlopen(req, timeout=5.0) as response:
            content = response.read().decode('utf-8')
        return parse_mirrorlist_content(content)
    except Exception as e:
        raise Exception(f"Failed to download remote mirrorlist: {e}")

def test_single_mirror(mirror, timeout=3.0):
    """Measures connection latency for a single mirror by retrieving a byte range of the DB."""
    url = mirror.url
    # Substitute pacman variables for connection test
    test_url = url.replace('$arch', 'x86_64').replace('$repo', 'cachyos')
    if not test_url.endswith('/'):
        test_url += '/'
    test_url += 'cachyos.db'
    
    start_time = time.time()
    try:
        req = urllib.request.Request(test_url)
        req.add_header('Range', 'bytes=0-0')
        req.add_header('User-Agent', 'cachyos-mirror-manager')
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status in (200, 206):
                response.read(1)
                mirror.latency = (time.time() - start_time) * 1000  # ms
                mirror.status = "working"
            else:
                mirror.latency = float('inf')
                mirror.status = "failed"
                mirror.error_msg = f"HTTP {response.status}"
    except urllib.error.HTTPError as e:
        mirror.latency = float('inf')
        mirror.status = "failed"
        mirror.error_msg = f"HTTP {e.code}"
    except urllib.error.URLError as e:
        mirror.latency = float('inf')
        mirror.status = "failed"
        mirror.error_msg = f"Network Error: {e.reason}"
    except Exception as e:
        mirror.latency = float('inf')
        mirror.status = "failed"
        mirror.error_msg = f"Error: {str(e)}"
    
    return mirror

def rank_mirrors(mirrors, timeout=3.0, threads=16):
    """Ranks all unique mirrors concurrently."""
    print(f"Testing {len(mirrors)} mirrors concurrently with {threads} threads (timeout={timeout}s)...")
    
    # Deduplicate mirrors by URL
    unique_mirrors = {}
    for m in mirrors:
        if m.url not in unique_mirrors:
            unique_mirrors[m.url] = m
            
    mirrors_to_test = list(unique_mirrors.values())
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(test_single_mirror, m, timeout): m for m in mirrors_to_test}
        
        completed = 0
        total = len(futures)
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            percent = (completed / total) * 100
            print(f"\rProgress: {completed}/{total} ({percent:.1f}%) tested...", end="", flush=True)
            
    print("\nRanking complete!")
    
    # Sort: working first (by latency), then failed
    working_mirrors = [m for m in mirrors_to_test if m.status == "working"]
    failed_mirrors = [m for m in mirrors_to_test if m.status != "working"]
    
    working_mirrors.sort(key=lambda x: x.latency)
    
    return working_mirrors + failed_mirrors

def perform_backup():
    """Creates a timestamped backup of the current mirrorlist."""
    if not os.path.exists(MIRRORLIST_PATH):
        return None
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{MIRRORLIST_PATH}.{timestamp}"
    shutil.copy2(MIRRORLIST_PATH, backup_file)
    # Maintain a general backup file
    shutil.copy2(MIRRORLIST_PATH, f"{MIRRORLIST_PATH}.bak")
    return backup_file

def get_backups():
    """Gets list of all backup files in /etc/pacman.d/."""
    dir_path = "/etc/pacman.d"
    backups = []
    if os.path.exists(dir_path):
        for f in os.listdir(dir_path):
            if f.startswith("cachyos-mirrorlist") and f != "cachyos-mirrorlist":
                backups.append(os.path.join(dir_path, f))
    return sorted(backups)

def generate_mirrorlist_content(ranked_mirrors, top_n=None):
    """Generates the mirrorlist file string format."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "######################################################",
        "####                                              ####",
        "####      CachyOS Repository Mirrorlist (Ranked)  ####",
        "####                                              ####",
        f"####  Generated on: {timestamp}               ####",
        "####                                              ####",
        "######################################################",
        ""
    ]
    
    active_count = 0
    for m in ranked_mirrors:
        is_working = (m.status == "working")
        should_activate = False
        
        if is_working:
            if top_n is None or active_count < top_n:
                should_activate = True
                active_count += 1
                
        # Write mirror comments
        for comment in m.comment_lines:
            lines.append(comment)
            
        # Write server status
        if is_working:
            latency_str = f"{m.latency:.1f}ms"
            lines.append(f"## Status: Working | Latency: {latency_str}")
        else:
            lines.append(f"## Status: Failed | Error: {m.error_msg}")
            
        if should_activate:
            lines.append(f"Server = {m.url}")
        else:
            lines.append(f"# Server = {m.url}")
        lines.append("")  # Spacer
        
    return "\n".join(lines)

# --- Interactive TUI Operations ---
def print_header(title):
    print(f"{CYAN}" + "=" * 60 + f"{RESET}")
    print(f"{BOLD}{title.center(60)}{RESET}")
    print(f"{CYAN}" + "=" * 60 + f"{RESET}")

def list_mirrors_op():
    os.system('clear')
    run_list_cli()
    input("\nPress Enter to return to menu...")

def rank_and_update_op(remote=False):
    os.system('clear')
    print_header("Rank and Update Mirrors")
    
    if remote:
        print("Fetching latest mirrors from GitHub...")
        try:
            mirrors = fetch_remote_mirrors()
            print(f"Fetched {len(mirrors)} mirrors.")
        except Exception as e:
            print(f"{RED}Error fetching remote mirrors: {e}{RESET}")
            input("\nPress Enter to return...")
            return
    else:
        mirrors = fetch_local_mirrors()
        if not mirrors:
            print(f"{RED}No local mirrors found.{RESET}")
            input("\nPress Enter to return...")
            return
            
    ans = input("Limit to top N fastest mirrors? (Enter for all working, or enter a number): ").strip()
    try:
        top_n = int(ans) if ans.isdigit() else None
    except ValueError:
        top_n = None
        
    ranked = rank_mirrors(mirrors)
    
    print(f"\n{BOLD}Ranked Results:{RESET}")
    print(f"{'No.':<4} | {'Latency':<10} | {'Status':<10} | {'URL'}")
    print("-" * 80)
    for i, m in enumerate(ranked):
        latency_str = f"{m.latency:.1f} ms" if m.status == "working" else "N/A"
        color = GREEN if m.status == "working" else RED
        print(f"{i+1:<4} | {latency_str:<10} | {color}{m.status:<10}{RESET} | {m.url}")
        
    confirm = input("\nApply this new mirrorlist to your system? (y/n): ").strip().lower()
    if confirm == 'y':
        check_root_or_elevate()
        try:
            backup_path = perform_backup()
            if backup_path:
                print(f"Backup created at {backup_path}")
            content = generate_mirrorlist_content(ranked, top_n)
            with open(MIRRORLIST_PATH, "w") as f:
                f.write(content)
            print(f"{GREEN}System mirrorlist successfully updated!{RESET}")
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")
    else:
        print("Discarded changes.")
        
    input("\nPress Enter to return to menu...")

def backup_op():
    os.system('clear')
    print_header("Backup Mirrorlist")
    check_root_or_elevate()
    try:
        backup_path = perform_backup()
        print(f"{GREEN}Backup successfully created: {backup_path}{RESET}")
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
    input("\nPress Enter to return to menu...")

def restore_op():
    os.system('clear')
    print_header("Restore Mirrorlist")
    run_restore_cli()
    input("\nPress Enter to return to menu...")

def view_raw_op():
    os.system('clear')
    print_header(f"Raw Mirrorlist ({MIRRORLIST_PATH})")
    if not os.path.exists(MIRRORLIST_PATH):
        print(f"{RED}File does not exist.{RESET}")
    else:
        try:
            with open(MIRRORLIST_PATH, "r") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                print(f"{i+1:3d}: {line}", end="")
        except Exception as e:
            print(f"{RED}Error reading file: {e}{RESET}")
    input("\nPress Enter to return to menu...")

def setup_live_environment(interactive=False):
    """Initializes CachyOS repositories on a Live ISO by downloading and running the official script."""
    check_root_or_elevate()
    if interactive:
        os.system('clear')
        print_header("Live ISO Setup")
    print(f"{YELLOW}Downloading and running official CachyOS repo setup script...{RESET}")
    try:
        cmd = "curl -s https://mirror.cachyos.org/cachyos-repo.tar.xz | tar xJ -C /tmp && cd /tmp/cachyos-repo && ./cachyos-repo.sh"
        subprocess.run(cmd, shell=True, check=True)
        print(f"{GREEN}CachyOS repositories successfully initialized!{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error setting up Live ISO environment: {e}{RESET}")
        if not interactive:
            sys.exit(1)
    if interactive:
        input("\nPress Enter to continue...")

def interactive_menu():
    while True:
        os.system('clear')
        print_header("CachyOS Mirror Manager")
        print("  1. List current mirrors (status & config)")
        print("  2. Rank local mirrors and update mirrorlist")
        print("  3. Fetch latest mirrors from GitHub, rank, & update")
        print("  4. Backup current mirrorlist")
        print("  5. Restore mirrorlist from backup")
        print("  6. View raw mirrorlist file")
        print("  7. Setup CachyOS repositories (Live ISO)")
        print("  8. Exit")
        print(f"{CYAN}" + "-" * 60 + f"{RESET}")
        
        choice = input(f"{BOLD}Select an option (1-8): {RESET}").strip()
        
        if choice == '1':
            list_mirrors_op()
        elif choice == '2':
            rank_and_update_op(remote=False)
        elif choice == '3':
            rank_and_update_op(remote=True)
        elif choice == '4':
            backup_op()
        elif choice == '5':
            restore_op()
        elif choice == '6':
            view_raw_op()
        elif choice == '7':
            setup_live_environment(interactive=True)
        elif choice == '8':
            print(f"{GREEN}Goodbye!{RESET}")
            break
        else:
            print(f"{RED}Invalid option. Press Enter to try again.{RESET}")
            input()

# --- CLI Mode Operations ---
def run_list_cli():
    mirrors = fetch_local_mirrors()
    if not mirrors:
        print(f"{RED}No local mirrors found.{RESET}")
        return
        
    print(f"{CYAN}=== Local CachyOS Mirrors ==={RESET}")
    print(f"{'No.':<4} | {'Active':<8} | {'URL'}")
    print("-" * 80)
    for i, m in enumerate(mirrors):
        active_str = f"{GREEN}Yes{RESET}" if m.is_active else f"{RED}No{RESET}"
        print(f"{i+1:<4} | {active_str:<8} | {m.url}")
    print(f"\nTotal mirrors configured: {len(mirrors)} ({sum(1 for m in mirrors if m.is_active)} active).")

def run_backup_cli():
    check_root_or_elevate()
    if not os.path.exists(MIRRORLIST_PATH):
        print(f"{RED}Error: {MIRRORLIST_PATH} does not exist.{RESET}")
        sys.exit(1)
    try:
        backup_path = perform_backup()
        print(f"{GREEN}Successfully created backup at {backup_path}{RESET}")
    except Exception as e:
        print(f"{RED}Failed to create backup: {e}{RESET}")
        sys.exit(1)

def run_restore_cli(file_path=None):
    check_root_or_elevate()
    if file_path:
        if not os.path.exists(file_path):
            print(f"{RED}Error: Specific backup file {file_path} does not exist.{RESET}")
            sys.exit(1)
        selected_backup = file_path
    else:
        backups = get_backups()
        if not backups:
            print(f"{RED}No backups found in /etc/pacman.d/{RESET}")
            sys.exit(1)
        
        print(f"{CYAN}=== Available Backups ==={RESET}")
        for i, b in enumerate(backups):
            name = os.path.basename(b)
            mtime = os.path.getmtime(b)
            mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  {i+1}. {name:<40} ({mtime_str})")
            
        try:
            choice = input(f"\nSelect backup to restore (1-{len(backups)}) or 'c' to cancel: ").strip()
            if choice.lower() == 'c':
                print("Cancelled.")
                return
            idx = int(choice) - 1
            if idx < 0 or idx >= len(backups):
                raise ValueError
            selected_backup = backups[idx]
        except (ValueError, IndexError):
            print(f"{RED}Invalid selection.{RESET}")
            sys.exit(1)
            
    try:
        shutil.copy2(selected_backup, MIRRORLIST_PATH)
        print(f"{GREEN}Successfully restored {MIRRORLIST_PATH} from {selected_backup}!{RESET}")
    except Exception as e:
        print(f"{RED}Failed to restore backup: {e}{RESET}")
        sys.exit(1)

def run_rank_cli(remote, top_n, timeout, threads, apply):
    print(f"{CYAN}=== CachyOS Mirror Ranking ==={RESET}")
    
    if remote:
        print("Fetching latest mirrors from GitHub...")
        try:
            mirrors = fetch_remote_mirrors()
            print(f"Fetched {len(mirrors)} mirrors from remote.")
        except Exception as e:
            print(f"{RED}Error fetching remote mirrors: {e}{RESET}")
            sys.exit(1)
    else:
        print("Reading mirrors from local configuration...")
        mirrors = fetch_local_mirrors()
        if not mirrors:
            print(f"{RED}No local mirrors found! Try running with --remote to fetch from GitHub.{RESET}")
            sys.exit(1)
        print(f"Read {len(mirrors)} mirrors from local configuration.")
        
    ranked = rank_mirrors(mirrors, timeout=timeout, threads=threads)
    
    print(f"\n{BOLD}Ranked Mirrors:{RESET}")
    print(f"{'No.':<4} | {'Latency':<10} | {'Status':<10} | {'URL'}")
    print("-" * 80)
    for i, m in enumerate(ranked):
        latency_str = f"{m.latency:.1f} ms" if m.status == "working" else "N/A"
        color = GREEN if m.status == "working" else RED
        print(f"{i+1:<4} | {latency_str:<10} | {color}{m.status:<10}{RESET} | {m.url}")
        
    working_count = sum(1 for m in ranked if m.status == "working")
    print(f"\nTotal: {len(ranked)} mirrors. Working: {working_count}.")
    
    if not apply:
        confirm = input("\nDo you want to apply these mirrors to the system? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Action cancelled.")
            sys.exit(0)
            
    # Apply changes
    check_root_or_elevate()
    try:
        backup_path = perform_backup()
        if backup_path:
            print(f"Backup created at {backup_path}")
        
        content = generate_mirrorlist_content(ranked, top_n)
        with open(MIRRORLIST_PATH, "w") as f:
            f.write(content)
        print(f"{GREEN}Successfully updated {MIRRORLIST_PATH}!{RESET}")
    except Exception as e:
        print(f"{RED}Error updating mirrorlist: {e}{RESET}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="CachyOS Mirror Manager - Manage and rank CachyOS package mirrors.")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive TUI/menu mode (default if no arguments).")
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    
    # rank command
    rank_parser = subparsers.add_parser("rank", help="Rank mirrors and update mirrorlist")
    rank_parser.add_argument("--remote", action="store_true", help="Fetch latest mirrors from GitHub before ranking")
    rank_parser.add_argument("--top", type=int, default=None, help="Number of active mirrors to enable (default: all working)")
    rank_parser.add_argument("--timeout", type=float, default=3.0, help="HTTP request timeout in seconds (default: 3.0)")
    rank_parser.add_argument("--threads", type=int, default=16, help="Number of concurrent threads to use (default: 16)")
    rank_parser.add_argument("--apply", action="store_true", help="Automatically apply the ranked mirrorlist without prompting")
    
    # list command
    subparsers.add_parser("list", help="List current mirrors and their status (active/inactive)")
    
    # backup command
    subparsers.add_parser("backup", help="Create a backup of the current mirrorlist")
    
    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore mirrorlist from a backup")
    restore_parser.add_argument("--file", type=str, default=None, help="Specific backup file path to restore")
    
    # setup-live command
    subparsers.add_parser("setup-live", help="Initialize CachyOS repositories on a Live ISO")
    
    args = parser.parse_args()
    
    # Default to interactive if no arguments
    if args.interactive or (args.command is None and len(sys.argv) == 1):
        interactive_menu()
        return
        
    if args.command == "rank":
        run_rank_cli(remote=args.remote, top_n=args.top, timeout=args.timeout, threads=args.threads, apply=args.apply)
    elif args.command == "list":
        run_list_cli()
    elif args.command == "backup":
        run_backup_cli()
    elif args.command == "restore":
        run_restore_cli(file_path=args.file)
    elif args.command == "setup-live":
        setup_live_environment(interactive=False)

if __name__ == "__main__":
    main()
