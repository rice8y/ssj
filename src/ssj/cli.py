import subprocess
import re
import argparse
import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

def parse_scontrol_output(output: str) -> Dict[str, str]:
    parts = output.strip().split()
    kv_pairs: Dict[str, str] = {}
    for part in parts:
        if '=' in part:
            key, val = part.split('=', 1)
            kv_pairs[key.strip()] = val.strip()
    return kv_pairs

class JobDisplay:
    def __init__(self, job_id: int):
        self.job_id = job_id
        self.data: Dict[str, str] = {}
        self.console = Console()

    def fetch_data(self) -> bool:
        try:
            result = subprocess.run(['scontrol', 'show', 'job', str(self.job_id)], capture_output=True, text=True, check=True)
            self.data = parse_scontrol_output(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Error[/red]: Failed to execute scontrol for job {self.job_id}: {e}")
            return False
        except Exception as e:
            self.console.print(f"[red]Error[/red]: Unexpected error fetching data for job {self.job_id}: {e}")
            return False

    def print_table(self, fields: Optional[List[str]] = None, regex_filter: Optional[str] = None) -> None:
        table = Table(title=f"Job {self.job_id} Details", show_lines=True)
        table.add_column("Key", style="cyan bold")
        table.add_column("Value", style="magenta")

        if regex_filter:
            try:
                pattern = re.compile(regex_filter, re.IGNORECASE)
            except re.error as e:
                self.console.print(f"[red]Error[/red]: Invalid regex pattern '{regex_filter}': {e}")
                return
        else:
            pattern = None
            
        lower_fields = [f.lower() for f in fields] if fields else None

        rows_added = 0
        for key, value in self.data.items():
            fields_match = True
            if lower_fields:
                fields_match = key.lower() in lower_fields
            
            regex_match = True
            if pattern:
                regex_match = pattern.search(key) is not None
            
            if fields_match and regex_match:
                table.add_row(key, value)
                rows_added += 1

        if rows_added > 0:
            self.console.print(table)
        else:
            self.console.print(f"[yellow]Warning[/yellow]: No matching fields found for job {self.job_id}")

    def get_script_path(self) -> Optional[str]:
        return self.data.get('Command') or self.data.get('BatchScript')

    def get_stdout_path(self) -> Optional[str]:
        return self.data.get('StdOut')

    def get_stderr_path(self) -> Optional[str]:
        return self.data.get('StdErr')

    def get_working_dir(self) -> Optional[str]:
        return self.data.get('WorkDir')

    def show_file_content(self, file_path: str, file_type: str = "file", lines: Optional[int] = None, tail: bool = False) -> None:
        if not file_path or file_path == "(null)":
            self.console.print(f"[yellow]Warning[/yellow]: No {file_type} path available for job {self.job_id}")
            return

        if not os.path.isabs(file_path):
            work_dir = self.get_working_dir()
            if work_dir:
                file_path = os.path.join(work_dir, file_path)

        path = Path(file_path)
        
        if not path.exists():
            self.console.print(f"[red]Error[/red]: {file_type.capitalize()} file not found: {file_path}")
            return

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                if tail and lines:
                    content_lines = f.readlines()
                    content = ''.join(content_lines[-lines:])
                    title_suffix = f" (last {lines} lines)"
                elif lines:
                    content_lines = []
                    for i, line in enumerate(f):
                        if i >= lines:
                            break
                        content_lines.append(line)
                    content = ''.join(content_lines)
                    title_suffix = f" (first {lines} lines)"
                else:
                    content = f.read()
                    title_suffix = ""

            if file_type == "script" or path.suffix in ['.sh', '.bash']:
                lexer = "bash"
            elif path.suffix in ['.py']:
                lexer = "python"
            elif path.suffix in ['.log', '.out', '.err']:
                lexer = "text"
            else:
                lexer = "text"

            syntax = Syntax(content, lexer, theme="monokai", line_numbers=True)

            title = f"Job {self.job_id} - {file_type.capitalize()}: {path.name}{title_suffix}"
            panel = Panel(syntax, title=title, expand=False)
            self.console.print(panel)
        except Exception as e:
            self.console.print(f"[red]Error[/red]: Failed to read {file_type} file {file_path}: {e}")

    def show_script(self, lines: Optional[int] = None, tail: bool = False) -> None:
        script_path = self.get_script_path()
        self.show_file_content(script_path, "script", lines, tail)

    def show_stdout(self, lines: Optional[int] = None, tail: bool = False) -> None:
        stdout_path = self.get_stdout_path()
        self.show_file_content(stdout_path, "stdout log", lines, tail)

    def show_stderr(self, lines: Optional[int] = None, tail: bool = False) -> None:
        stderr_path = self.get_stderr_path()
        self.show_file_content(stderr_path, "stderr log", lines, tail)

    def list_file_paths(self) -> None:
        table = Table(title=f"Job {self.job_id} File Paths", show_lines=True)
        table.add_column("File Type", style="cyan bold")
        table.add_column("Path", style="magenta")
        table.add_column("Exists", style="green")

        files = [
            ("Script", self.get_script_path()),
            ("StdOut", self.get_stdout_path()),
            ("StdErr", self.get_stderr_path()),
            ("WorkDir", self.get_working_dir())
        ]

        for file_type, file_path in files:
            if file_path and file_path != "(null)":
                if file_type == "WorkDir":
                    exists = "✓" if os.path.isdir(file_path) else "✗"
                else:
                    if not os.path.isabs(file_path):
                        work_dir = self.get_working_dir()
                        if work_dir:
                            abs_path = os.path.join(work_dir, file_path)
                        else:
                            abs_path = file_path
                    else:
                        abs_path = file_path
                    exists = "✓" if os.path.exists(abs_path) else "✗"
                table.add_row(file_type, file_path, exists)
        self.console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Display SLURM job information in a user-friendly table.")
    parser.add_argument("job_ids", type=int, nargs='+', help="One or more SLURM job IDs to display.")
    parser.add_argument("-f", "--fields", nargs='+', help="Specific fields to show (exact match, case-insensitive).")
    parser.add_argument("-g", "--grep", metavar="PATTERN", help="Regex to filter keys by name (partial match).")
    parser.add_argument("-j", "--json", action="store_true", help="Output raw JSON instead of a table.")
    parser.add_argument("--script", action="store_true", help="Show the job script file content.")
    parser.add_argument("--stdout", action="store_true", help="Show the stdout log file content.")
    parser.add_argument("--stderr", action="store_true", help="Show the stderr log file content.")
    parser.add_argument("--files", action="store_true", help="List all file paths associated with the job.")
    parser.add_argument("--lines", type=int, metavar="N", help="Show only first N lines of file content (use with --tail for last N lines).")
    parser.add_argument("--tail", action="store_true", help="Show last N lines instead of first N lines (requires --lines).")
    args = parser.parse_args()
    
    for jid in args.job_ids:
        jd = JobDisplay(jid)
        if not jd.fetch_data():
            continue
            
        if args.json:
            print(json.dumps(jd.data, indent=2))
        elif args.files:
            jd.list_file_paths()
        elif args.script:
            jd.show_script(lines=args.lines, tail=args.tail)
        elif args.stdout:
            jd.show_stdout(lines=args.lines, tail=args.tail)
        elif args.stderr:
            jd.show_stderr(lines=args.lines, tail=args.tail)
        else:
            jd.print_table(fields=args.fields, regex_filter=args.grep)

if __name__ == "__main__":
    main()