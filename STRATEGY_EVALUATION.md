# Karkinos Strategy Evaluation

This document evaluates three different approaches for managing parallel Claude Code development.

## Current State: Karkinos (Git Worktrees)

### Architecture
- **Isolation:** Git worktrees at `../<project>-<branch-slug>` (sibling directories)
- **Execution:** `claude --print --dangerously-skip-permissions "<task>"`
- **Monitoring:** Dedicated TUI (`karkinos watch`) with 5s auto-refresh
- **Workflow:** Spawn → Monitor → Auto-PR → Auto-merge → Cleanup
- **Branch Management:** One branch per worker, fully isolated

### Strengths
✅ **Complete isolation** - Workers can't interfere with each other or main branch
✅ **Structured workflow** - Clear lifecycle from spawn to cleanup
✅ **Visual monitoring** - TUI provides real-time status of all workers
✅ **Git integration** - Natural PR creation, auto-merge, branch tracking
✅ **Safe experimentation** - Easy rollback, failed workers don't affect main
✅ **Multiple simultaneous tasks** - Each worker truly independent
✅ **Works with existing projects** - No special setup needed

### Weaknesses
❌ **Heavy abstraction** - Multiple layers (CLI, skills, worktrees, TUI)
❌ **Disk overhead** - Each worktree duplicates the repository
❌ **Context switching** - Workers can't see each other's changes
❌ **Cleanup burden** - Must manually manage worktree lifecycle
❌ **Complexity** - More moving parts = more things that can break
❌ **Sequential integration** - Workers must merge in order if changes conflict

### Best For
- Large, complex tasks requiring full isolation
- Multiple independent features in parallel
- Teams needing PR-based workflows
- Projects where safety > speed

---

## Option 1: Tmux for Subagents

### Architecture
- **Isolation:** Tmux sessions/windows (terminal-level, not file-level)
- **Execution:** `tmux new-session -d -s worker-1 "claude --print ..."`
- **Monitoring:** `tmux ls`, `tmux attach`, or custom watcher script
- **Workflow:** Session → Detach → Monitor → Attach → Review
- **Branch Management:** Optional - could use same branch or separate branches

### Strengths
✅ **Lightweight** - No disk duplication, just terminal multiplexing
✅ **Fast switching** - `tmux attach` to jump between workers
✅ **Persistent sessions** - Survive terminal disconnects, SSH drops
✅ **Simple model** - Just background processes, minimal abstraction
✅ **Shared filesystem** - Workers can see each other's changes immediately
✅ **Flexible** - Can combine with worktrees or use same directory
✅ **Standard tool** - Tmux widely known, no custom tooling needed

### Weaknesses
❌ **No file isolation** - Workers can conflict if touching same files
❌ **Manual coordination** - Developer must orchestrate merge conflicts
❌ **Less structure** - No built-in PR workflow or cleanup
❌ **Terminal-only** - No visual dashboard without custom scripting
❌ **Session management** - Must track which session is which worker
❌ **Merge conflicts** - Higher risk if workers touch overlapping code

### Best For
- Quick parallel tasks on different parts of codebase
- Developers comfortable with tmux
- Tasks where shared state is beneficial
- Rapid iteration without PR overhead

### Implementation Notes
```bash
# Spawn worker
tmux new-session -d -s worker-feat-auth "claude --print 'Add OAuth support'"

# Monitor
tmux ls                    # List sessions
tmux attach -t worker-*    # Jump to worker

# Cleanup
tmux kill-session -t worker-*
```

Could build lightweight wrapper:
- `/tmux-worker <task>` - spawn in new session
- `/tmux-workers` - list all worker sessions
- `/tmux-cleanup` - kill completed workers

---

## Option 2: Steipete's Strategy

### Architecture
- **Isolation:** Tmux grid (3x3 terminal layout), mostly same folder
- **Execution:** 3-8 Claude instances running in parallel
- **Monitoring:** Visual grid, all instances visible at once
- **Workflow:** "Just talk to it" - minimal abstraction
- **Branch Management:** Minimal - reverted from worktrees/PRs to simple setup

### Philosophy
> "I run between 3-8 Claude Code CLI instances in parallel in a 3x3 terminal grid with most of them in the same folder. I experimented with worktrees and PRs but reverted to this setup as it **gets stuff done the fastest**."

Key principles:
- **Blast radius thinking** - Know how long a change takes, how many files it touches
- **CLI tools over MCPs** - Avoid persistent context pollution
- **Minimal abstraction** - Just tmux + Claude, nothing fancy
- **Same folder** - Shared state, immediate integration

### Strengths
✅ **Maximum speed** - Steipete's own words: "fastest"
✅ **Minimal overhead** - No worktrees, no custom tooling, just tmux
✅ **Continuous integration** - Workers see each other's changes live
✅ **Visual awareness** - 3x3 grid shows all workers at once
✅ **Flexible scope** - Small bombs to Fat Man, adjust blast radius
✅ **No cleanup** - No worktrees to remove, branches to delete
✅ **Battle-tested** - Steipete ships production code this way

### Weaknesses
❌ **High merge risk** - Multiple writers to same files guaranteed conflicts
❌ **Requires expertise** - Need good "blast radius" intuition
❌ **Manual conflict resolution** - Developer must orchestrate all merges
❌ **No safety rails** - Easy to overwrite or lose work
❌ **Grid complexity** - 3x3 layout needs tmux proficiency
❌ **Limited to 8-9 workers** - Grid size constrains parallelism

### Best For
- Experienced developers with strong intuition
- Fast iteration on well-understood codebases
- Solo developers (not teams needing PR reviews)
- Shipping features > perfect isolation

### Implementation Notes
```bash
# Create 3x3 tmux layout
tmux new-session \; \
  split-window -h \; split-window -h \; \
  select-pane -t 0 \; split-window -v \; split-window -v \; \
  select-pane -t 3 \; split-window -v \; split-window -v \; \
  select-pane -t 6 \; split-window -v \; split-window -v

# Launch Claudes in each pane
tmux send-keys -t 0 "claude --print 'Add auth'" C-m
tmux send-keys -t 1 "claude --print 'Add tests'" C-m
# ... etc
```

Could build wrapper:
- `/steipete-grid <task1> <task2> ...` - spawn N workers in grid
- Auto-layout based on worker count

---

## Comparative Analysis

| Dimension | Karkinos (Current) | Tmux Subagents | Steipete |
|-----------|-------------------|----------------|----------|
| **Isolation** | Complete (worktrees) | None (same dir) | None (same dir) |
| **Speed** | Slower (disk I/O) | Fast | **Fastest** |
| **Safety** | **Highest** | Medium | Lowest |
| **Complexity** | High | Low | **Minimal** |
| **Scalability** | 10+ workers | Unlimited | 8-9 (grid) |
| **Disk Usage** | N × repo size | 1 × repo size | 1 × repo size |
| **Conflict Risk** | None | Medium | **High** |
| **Learning Curve** | Medium | Low | **Requires mastery** |
| **Team Friendly** | Yes (PRs) | Maybe | No (solo) |
| **Integration** | Sequential (PRs) | Gradual | **Immediate** |

---

## Recommendations

### Keep Karkinos If:
- You value **safety and isolation** above all
- You work in a **team** requiring PR reviews
- You run **many parallel tasks** (10+)
- Your tasks are **large and complex**
- You want **visual monitoring** without tmux expertise

### Switch to Tmux Subagents If:
- You want **lightweight parallelism**
- You're **comfortable with tmux**
- Your tasks touch **different files**
- You want **flexibility** (can combine with worktrees)
- You prefer **standard tools** over custom abstractions

### Adopt Steipete's Strategy If:
- You prioritize **raw speed** over safety
- You're a **solo developer** or have full autonomy
- You have **strong "blast radius" intuition**
- You're **proficient with tmux**
- You can **handle merge conflicts** confidently
- You ship fast and iterate

---

## Hybrid Approaches

### 1. Karkinos + Tmux
Keep worktree isolation but use tmux for monitoring instead of TUI:
```bash
# Each worker in its own tmux session + worktree
tmux new-session -d -s worker-1 "cd ../myproject-feat-1 && claude --print '...'"
```

**Benefit:** Persistence + isolation
**Tradeoff:** Still have worktree overhead

### 2. Smart Routing
Use strategy based on task characteristics:
- **Large, risky tasks** → Karkinos (worktrees)
- **Quick parallel tasks** → Tmux subagents (same dir)
- **Rapid iteration** → Steipete grid (same dir)

### 3. Steipete Lite
Use 2x2 or 2x3 grid (4-6 workers) instead of 3x3:
- Lower conflict risk
- Easier to manage
- Still faster than worktrees

---

## Conclusion

**Current Karkinos strategy is ideal for:**
- Teams needing structured workflows
- Large projects with high complexity
- Scenarios where safety > speed
- Developers who want visual monitoring

**Consider tmux if:**
- You want lightweight parallelism
- You're comfortable orchestrating manually
- Speed matters but you still want some structure

**Adopt Steipete's approach if:**
- You're an experienced solo developer
- Shipping speed is paramount
- You have strong intuition for code structure
- You're willing to accept higher conflict risk for faster iteration

**Bottom line:** Karkinos optimizes for **safety and structure**. Steipete optimizes for **speed and simplicity**. Choose based on your risk tolerance, team size, and development philosophy.

---

## Next Steps for Karkinos

If sticking with current strategy:
1. ✅ Keep worktree isolation
2. ✅ Keep TUI monitoring
3. ✅ Keep PR workflow
4. ⚡ Add tmux session support for persistence
5. ⚡ Add "quick mode" flag that skips worktree creation
6. ⚡ Add auto-rebase to reduce conflict resolution burden

If pivoting to tmux:
1. Create `/tmux-worker` command as lightweight alternative
2. Keep Karkinos for complex tasks, tmux for quick ones
3. Let users choose based on task size

If experimenting with Steipete:
1. Create `/grid-worker` that spawns N Claudes in tmux grid
2. Document "blast radius" thinking in README
3. Add conflict detection warnings
4. Make it opt-in for advanced users
