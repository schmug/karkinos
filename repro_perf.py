
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Mock data simulating what get_worktrees returns
# We replicate the current repo multiple times to simulate N workers
def get_mock_worktrees(n=10):
    # Get current branch
    res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    current_branch = res.stdout.strip()

    # Get current path
    res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    path = res.stdout.strip()

    return [{"path": path, "branch": current_branch} for _ in range(n)]

def original_get_worker_details(wt: dict) -> dict:
    """Enrich worktree with additional details."""
    branch = wt.get("branch", "")

    # Commits ahead of main
    result = subprocess.run(
        ["git", "rev-list", "--count", f"main..{branch}"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        try:
            wt["ahead"] = int(result.stdout.strip())
        except ValueError:
            wt["ahead"] = 0
    else:
        wt["ahead"] = 0

    # Last commit
    result = subprocess.run(
        ["git", "log", branch, "--oneline", "-1", "--format=%s"],
        capture_output=True,
        text=True,
    )
    wt["last_commit"] = result.stdout.strip()[:50] if result.returncode == 0 else ""

    # Status
    result = subprocess.run(
        ["git", "-C", wt["path"], "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        wt["status"] = "modified" if result.stdout.strip() else "clean"
    else:
        wt["status"] = "unknown"

    return wt

def optimized_refresh(worktrees):
    # 1. Batch fetch last commits
    branches = {wt["branch"] for wt in worktrees if wt.get("branch")}

    # In a real scenario, we might have many branches.
    # git for-each-ref refs/heads/ gives all, which is efficient.
    # For now let's just use what we have.

    # Simulate fetching all heads
    cmd = ["git", "for-each-ref", "--format=%(refname:short)|%(subject)", "refs/heads/"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    branch_commits = {}
    for line in result.stdout.strip().split("\n"):
        if "|" in line:
            b, subject = line.split("|", 1)
            branch_commits[b] = subject

    def process_one(wt):
        branch = wt.get("branch", "")
        # Use batched commit message
        wt["last_commit"] = branch_commits.get(branch, "")[:50]

        # Commits ahead
        res = subprocess.run(
            ["git", "rev-list", "--count", f"main..{branch}"],
            capture_output=True,
            text=True,
        )
        wt["ahead"] = int(res.stdout.strip()) if res.returncode == 0 else 0

        # Status
        res = subprocess.run(
            ["git", "-C", wt["path"], "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        wt["status"] = "modified" if res.returncode == 0 and res.stdout.strip() else "clean"
        return wt

    with ThreadPoolExecutor() as executor:
        return list(executor.map(process_one, worktrees))

def run_benchmark():
    worktrees = get_mock_worktrees(10) # Simulate 10 workers

    print(f"Benchmarking with {len(worktrees)} workers...")

    # Original
    start = time.time()
    results_orig = []
    for wt in worktrees:
        # We need to copy wt because it modifies in place
        results_orig.append(original_get_worker_details(wt.copy()))
    end = time.time()
    print(f"Original (sequential): {end - start:.4f}s")

    # Optimized
    start = time.time()
    results_opt = optimized_refresh([wt.copy() for wt in worktrees])
    end = time.time()
    print(f"Optimized (batch + parallel): {end - start:.4f}s")

if __name__ == "__main__":
    run_benchmark()
