#!/usr/bin/env python3
"""
InsightFlow one-click launcher (v3 Premium CLI).
Usage: python start.py   (run from the insightflow/ project root)

What this does:
  1. Displays premium ASCII banner and system health checks
  2. Validates API keys
  3. Creates/repairs the Python virtual environment
  4. Runs npm install if node_modules is absent
  5. Launches uvicorn (backend) and vite dev server (frontend) concurrently
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

# Paths
ROOT     = Path(__file__).parent.resolve()
BACKEND  = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV_DIR = BACKEND / "venv"

_BIN = "Scripts" if sys.platform == "win32" else "bin"
_EXE = ".exe"   if sys.platform == "win32" else ""

PYTHON_VENV = VENV_DIR / _BIN / f"python{_EXE}"
UVICORN     = VENV_DIR / _BIN / f"uvicorn{_EXE}"

# Colors
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"

def banner():
    print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██╗███╗  ██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗        ║
║     ██║████╗ ██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝        ║
║     ██║██╔██╗██║███████╗██║██║  ███╗███████║   ██║           ║
║     ██║██║╚████║╚════██║██║██║   ██║██╔══██║   ██║           ║
║     ██║██║ ╚███║███████║██║╚██████╔╝██║  ██║   ██║           ║
║     ╚═╝╚═╝  ╚══╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝           ║
║                  ███████╗██╗      ██████╗ ██╗    ██╗         ║
║                  ██╔════╝██║     ██╔═══██╗██║    ██║         ║
║                  █████╗  ██║     ██║   ██║██║ █╗ ██║         ║
║                  ██╔══╝  ██║     ██║   ██║██║███╗██║         ║
║                  ██║     ███████╗╚██████╔╝╚███╔███╔╝         ║
║                  ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝          ║
║                                                              ║
║           Smart Dashboards from Plain English                ║
║                    v3.0 · Hackathon Edition                  ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

def get_sys_version(cmd, substr_idx=0):
    try:
        use_shell = sys.platform == "win32"
        res = subprocess.run(cmd, capture_output=True, text=True, shell=use_shell)
        if res.returncode == 0:
            return res.stdout.strip().split('\n')[0].split()[substr_idx]
    except Exception:
        pass
    return None

def system_health():
    print(f"  {BOLD}┌─── System Health ──────────────────────────────────────────┐{RESET}")
    
    py_ver = sys.version.split()[0]
    print(f"  {BOLD}│{RESET}  Python     {GREEN}✓ {py_ver:<40}{BOLD}│{RESET}")
    
    node_ver = get_sys_version(["node", "--version"])
    if node_ver:
        print(f"  {BOLD}│{RESET}  Node.js    {GREEN}✓ {node_ver:<40}{BOLD}│{RESET}")
    else:
        print(f"  {BOLD}│{RESET}  Node.js    {RED}✗ Not found (required for frontend)      {BOLD}│{RESET}")
        
    npm_ver = get_sys_version(["npm", "--version"])
    if npm_ver:
        print(f"  {BOLD}│{RESET}  npm        {GREEN}✓ {npm_ver:<40}{BOLD}│{RESET}")
    else:
        print(f"  {BOLD}│{RESET}  npm        {RED}✗ Not found (required for frontend)      {BOLD}│{RESET}")

    print(f"  {BOLD}└────────────────────────────────────────────────────────────┘{RESET}\n")

def check_api_keys():
    env_file = ROOT / ".env"
    groq_keys: int = 0
    gem_keys: int = 0
    if env_file.exists():
        lines = env_file.read_text('utf-8').splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = line.split("=", 1)
            if len(parts) == 2:
                k, v = parts[0].strip(), parts[1].strip()
                v_clean = v.strip('"').strip("'").strip()
                
                # Strict key validation to ignore placeholders
                is_placeholder = any(p in v_clean.lower() for p in ["your_", "api_here", "optional"])
                if len(v_clean) > 15 and not is_placeholder:
                    if k.startswith("GROQ_API_KEY"): groq_keys += 1
                    if k.startswith("GEMINI_API_KEY"): gem_keys += 1
                    
    print(f"  {BOLD}┌─── API Keys ───────────────────────────────────────────────┐{RESET}")
    g_status = f"{GREEN}✓ {groq_keys} keys loaded{RESET}" if groq_keys else f"{YELLOW}⚠ 0 keys (add to .env){RESET}"
    gm_status = f"{GREEN}✓ {gem_keys} keys loaded{RESET}" if gem_keys else f"{DIM}0 keys (optional){RESET}"
    
    # Simple manual padding to handle ANSI codes properly.
    if groq_keys > 0:
        g_status += ' ' * 30
    else:
        g_status += ' ' * 21
    if gem_keys > 0:
        gm_status += ' ' * 30
    else:
        gm_status += ' ' * 26
        
    print(f"  {BOLD}│{RESET}  ⚡ Groq       {g_status} {DIM}(primary) {RESET}{BOLD}│{RESET}")
    print(f"  {BOLD}│{RESET}  🔷 Gemini     {gm_status} {DIM}(fallback){RESET} {BOLD}│{RESET}")
    print(f"  {BOLD}│{RESET}  Total:  {groq_keys + gem_keys} keys in ladder{' ' * 31}{BOLD}│{RESET}")
    print(f"  {BOLD}└────────────────────────────────────────────────────────────┘{RESET}\n")

def animated_step(label, func):
    print(f"  {CYAN}▶{RESET} {label}…")
    start = time.time()
    try:
        func()
        end = time.time()
        print(f"    {GREEN}✓ DONE{RESET}  [{end-start:.1f}s]\n")
    except subprocess.CalledProcessError as e:
        print(f"    {RED}✗ FAILED{RESET}\n{e}")
        sys.exit(1)

def build_venv():
    if not VENV_DIR.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    # Install dependencies from requirements.txt
    subprocess.run(
        [str(PYTHON_VENV), "-m", "pip", "install", "-r",
         str(BACKEND / "requirements.txt"), "--quiet"],
        check=True,
    )

def build_npm():
    if not (FRONTEND / "node_modules").exists():
        use_shell = sys.platform == "win32"
        subprocess.run(["npm", "install", "--silent"], cwd=str(FRONTEND), shell=use_shell, check=True)

def run_backend():
    subprocess.run([str(UVICORN), "main:app", "--reload", "--port", "8000"], cwd=str(BACKEND), check=True)

def run_frontend():
    use_shell = sys.platform == "win32"
    subprocess.run(["npm", "run", "dev"], cwd=str(FRONTEND), shell=use_shell, check=True)

def start_docker():
    """Starts the PostgreSQL and Redis containers via Docker (Optional)."""
    if not (ROOT / "docker-compose.yml").exists():
        return
    
    use_shell = sys.platform == "win32"
    print(f"    {DIM}Checking for Docker services...{RESET}")
    try:
        subprocess.run(["docker-compose", "up", "-d"], cwd=str(ROOT), shell=use_shell, check=True, capture_output=True)
    except Exception:
        try:
            subprocess.run(["docker", "compose", "up", "-d"], cwd=str(ROOT), shell=use_shell, check=True, capture_output=True)
        except Exception:
            # Check if we are using SQLite fallback
            env_file = ROOT / ".env"
            if env_file.exists() and "sqlite" in env_file.read_text():
                print(f"    {YELLOW}⚠ Docker not found. Proceeding with Local SQLite/Memory fallback.{RESET}")
            else:
                print(f"\n{RED}✗ Failed to start Docker containers.{RESET}")
                print(f"{YELLOW}Please ensure Docker Desktop is running OR change DATABASE_URL to 'sqlite+aiosqlite:///./insightflow.db' in .env{RESET}\n")
                sys.exit(1)

def run_migrations():
    """Validates database schema and auto-migrates if necessary."""
    use_shell = sys.platform == "win32"
    try:
        # Give PostgreSQL a second to accept connections
        time.sleep(2)
        subprocess.run([str(PYTHON_VENV), "-m", "alembic", "upgrade", "head"], cwd=str(BACKEND), shell=use_shell, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print(f"    {DIM}Generating initial database schema...{RESET}")
        try:
            subprocess.run([str(PYTHON_VENV), "-m", "alembic", "revision", "--autogenerate", "-m", "Init"], cwd=str(BACKEND), shell=use_shell, check=True, capture_output=True)
            subprocess.run([str(PYTHON_VENV), "-m", "alembic", "upgrade", "head"], cwd=str(BACKEND), shell=use_shell, check=True, capture_output=True)
        except Exception as e:
            print(f"\n{RED}✗ Database migration failed. Ensure PostgreSQL is ready.{RESET}\n")
            sys.exit(1)

def check_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        ex = ROOT / ".env.example"
        if ex.exists():
            shutil.copy(ex, env_file)
        else:
            env_file.write_text("GROQ_API_KEY=\nGEMINI_API_KEY=\nALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n", encoding="utf-8")

if __name__ == "__main__":
    check_env()
    banner()
    system_health()
    check_api_keys()

    animated_step("Python virtual environment", build_venv)
    animated_step("Frontend dependencies", build_npm)
    animated_step("Docker infrastructure", start_docker)
    animated_step("Database migrations", run_migrations)

    print(f"  {CYAN}▶{RESET} Starting InsightFlow…\n")
    print(f"  {BOLD}┌─── Servers  ───────────────────────────────────────────────┐{RESET}")
    print(f"  {BOLD}│{RESET}  🔵 Backend   {CYAN}http://127.0.0.1:8000{RESET}   {GREEN}● RUNNING{RESET}           {BOLD}│{RESET}")
    print(f"  {BOLD}│{RESET}  🟢 Frontend  {CYAN}http://localhost:5173{RESET}   {GREEN}● RUNNING{RESET}           {BOLD}│{RESET}")
    print(f"  {BOLD}└────────────────────────────────────────────────────────────┘{RESET}\n")

    print(f"  {BOLD}┌─── Quick Actions ──────────────────────────────────────────┐{RESET}")
    print(f"  {BOLD}│{RESET}  → Open browser:  {CYAN}http://localhost:5173{RESET}                    {BOLD}│{RESET}")
    print(f"  {BOLD}│{RESET}  → API docs:      {CYAN}http://127.0.0.1:8000/docs{RESET}              {BOLD}│{RESET}")
    print(f"  {BOLD}│{RESET}  → Health check:  {CYAN}http://127.0.0.1:8000/health{RESET}            {BOLD}│{RESET}")
    print(f"  {BOLD}│{RESET}  → Press {RED}Ctrl+C{RESET} to stop                                    {BOLD}│{RESET}")
    print(f"  {BOLD}└────────────────────────────────────────────────────────────┘{RESET}\n")

    try:
        t1 = threading.Thread(target=run_backend, daemon=True)
        t2 = threading.Thread(target=run_frontend, daemon=True)
        t1.start()
        t2.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{RED}InsightFlow stopped.{RESET}")
        import sys
        sys.exit(0)
