# ui/tui.py
from __future__ import annotations
import curses, json, io, sys, time, traceback
from pathlib import Path
from typing import List
from ..kernel.runtime import run_bytecode
from ..kernel.packaging import make_aiox
from ..kernel.replay import replay_aiox
from ..kernel.undo import undo_last_run
from ..kernel.meters import CarbonCostMeter

BORDER = 1

def read_text(p: Path, fallback: str = "") -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return fallback

def read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

class ActivityUI:
    def __init__(self, stdscr, root: Path):
        self.stdscr = stdscr
        self.root = root.resolve()
        self.sbx = self.root / "sandbox"
        self.plan_path = self.root / "apps" / "forge" / "plan.apl.json"
        self.bc_path   = self.root / "apps" / "forge" / "bytecode.json"
        self.pkg_path  = self.sbx / "packages" / "forge.aiox"
        self.status = "Ready."
        self.log_lines: List[str] = []
        self.selected_panel = 0  # 0=Plan, 1=Bytecode, 2=Preview/Out, 3=Meters/Quota, 4=Logs
        self.show_plan_dag = False  # Toggle for plan DAG visualization
        self.meter = CarbonCostMeter(self.sbx)
        curses.curs_set(0)
        self.stdscr.nodelay(False)
        self.stdscr.keypad(True)

    # --------------- draw ---------------

    def draw(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        # Ensure minimum terminal size
        if h < 20 or w < 60:
            self.stdscr.addstr(h//2, w//2 - 10, "Terminal too small!")
            self.stdscr.refresh()
            return

        # layout - 5 panels now (plan left, 4 right)
        left_w = max(38, int(w * 0.36))
        right_w = w - left_w - 3  # more buffer

        # ensure we have enough space for 4 right panels
        min_panel_h = 4
        available_h = h - 6  # header + footer + borders
        panel_h = max(min_panel_h, available_h // 4)

        # Safe panel creation with bounds checking
        try:
            plan_win = self.stdscr.subwin(h - 3, left_w, 1, 1)

            y_offset = 1
            bc_win = self.stdscr.subwin(panel_h, right_w, y_offset, left_w + 3)

            y_offset += panel_h + 1
            prev_win = self.stdscr.subwin(panel_h, right_w, y_offset, left_w + 3)

            y_offset += panel_h + 1
            policy_win = self.stdscr.subwin(panel_h, right_w, y_offset, left_w + 3)

            y_offset += panel_h + 1
            remaining_h = h - y_offset - 2
            logs_win = self.stdscr.subwin(max(3, remaining_h), right_w, y_offset, left_w + 3)
        except Exception:
            # Fallback to simple layout
            self.stdscr.addstr(h//2, w//2 - 15, "Layout error - terminal too small")
            self.stdscr.refresh()
            return

        # titles
        self._box(plan_win, " PLAN (APL) [1] ")
        self._box(bc_win,   " BYTECODE [2] ")
        self._box(prev_win, " PREVIEW / OUTPUT [3] ")
        self._box(policy_win, " METERS & QUOTAS [4] ")
        self._box(logs_win, " SYSLOG [5] ")

        # content
        self._render_plan(plan_win)
        self._render_bc(bc_win)
        self._render_preview(prev_win)
        self._render_policy(policy_win)
        self._render_logs(logs_win)

        # Header with carbon footprint
        current_stats = self.meter.get_current_run_stats()
        co2_grams = current_stats.get('total_co2_grams', 0) if current_stats["status"] == "active_run" else 0
        cost_usd = current_stats.get('total_cost_usd', 0) if current_stats["status"] == "active_run" else 0

        # Create header with carbon info
        header_text = " AI-OS :: Task-Agnostic Automation Platform "
        carbon_info = f" CO2: {co2_grams:.1f}g | Cost: ${cost_usd:.4f} "

        # Center main header
        self.stdscr.addstr(0, 2, header_text.center(w-4))

        # Add carbon info in top-right if there's space
        if len(carbon_info) < w - len(header_text) - 4:
            try:
                self.stdscr.addstr(0, w - len(carbon_info) - 2, carbon_info)
            except curses.error:
                pass

        # footer
        footer = "[g]enerate plan [v]iew DAG [d]ry-run [e]xecute [p]ack [r]eplay [u]ndo [c]ost analysis [q]uit"
        self.stdscr.addstr(h-1, 1, (self.status + "  " + footer)[:w-2])

        self.stdscr.refresh()

    def _box(self, win, title: str):
        win.box()
        try:
            win.addstr(0, 2, title)
        except curses.error:
            pass

    # --------------- data providers ---------------

    def _render_plan(self, win):
        plan = read_json(self.plan_path, {})
        y, x = 1, 2
        def add(line: str = "", bold=False):
            nonlocal y
            try:
                if bold: win.attron(curses.A_BOLD)
                win.addstr(y, x, line[:win.getmaxyx()[1]-4])
                if bold: win.attroff(curses.A_BOLD)
            except curses.error:
                pass
            y += 1

        add(f"File: {self._rel(self.plan_path)}", bold=True)

        # Show planner info
        metadata = plan.get("metadata", {}) or plan.get("_planner_metadata", {})
        planner_type = metadata.get("planner_type", "unknown")

        if planner_type == "llm":
            add("Planner: LLM-based (Claude)", bold=True)
            model = metadata.get("llm_model", "unknown")
            add(f"Model: {model}")
            task_type = metadata.get("task_type", "general")
            complexity = metadata.get("complexity", "medium")
            add(f"Type: {task_type} | Complexity: {complexity}")
        elif planner_type == "fallback":
            add("Planner: Fallback (rule-based)", bold=True)
        else:
            add("Planner: Unknown", bold=True)
        add()

        if self.show_plan_dag:
            # Show DAG visualization
            add("[DAG VIEW]", bold=True)
            self._render_plan_dag(win, plan, y, x)
        else:
            # Show normal plan view
            goal = plan.get('goal','<missing>')
            if len(goal) > 40:
                goal = goal[:37] + "..."
            add(f"Goal: {goal}")

            caps = ", ".join(plan.get("capabilities", []))
            if caps:
                caps_display = caps[:30] + "..." if len(caps) > 30 else caps
                add(f"Caps: {caps_display}")
            else:
                add("Caps: <none>")
            add()

            steps = plan.get("steps", [])
            add(f"Steps: {len(steps)}", bold=True)
            for i, s in enumerate(steps[:win.getmaxyx()[0]-12]):
                op = s.get('op', '?')
                desc = s.get('description', '')
                if desc and len(desc) > 20:
                    desc = desc[:17] + "..."
                line = f"{i+1:02d}. {op}"
                if desc:
                    line += f" - {desc}"
                add(line)

            # Show generation info if from LLM
            if planner_type == "llm" and y < win.getmaxyx()[0] - 3:
                add()
                generated_at = plan.get("_generated_at", "")
                if generated_at:
                    date_part = generated_at.split("T")[0] if "T" in generated_at else generated_at
                    add(f"Generated: {date_part}")

            # Show toggle hint
            if y < win.getmaxyx()[0] - 2:
                y += 1
                add("[v] Toggle DAG view", bold=False)

    def _render_plan_dag(self, win, plan, start_y, start_x):
        """Render DAG visualization for the execution plan"""
        y = start_y
        x = start_x
        max_h, max_w = win.getmaxyx()

        def add_dag_line(line: str = "", bold=False, indent=0):
            nonlocal y
            if y >= max_h - 1:
                return
            try:
                if bold: win.attron(curses.A_BOLD)
                display_line = line[:max_w - start_x - 2]
                win.addstr(y, x + indent, display_line)
                if bold: win.attroff(curses.A_BOLD)
            except curses.error:
                pass
            y += 1

        # Get steps and metadata
        steps = plan.get("steps", [])
        metadata = plan.get("metadata", {}) or plan.get("_planner_metadata", {})

        # Show plan info
        goal = plan.get('goal', '<missing>')
        if len(goal) > max_w - x - 10:
            goal = goal[:max_w - x - 13] + "..."
        add_dag_line(f"Goal: {goal}")

        planner_type = metadata.get('planner_type', 'unknown')
        if planner_type == "llm":
            add_dag_line("Planner: LLM-based (Claude)", bold=True)
            model = metadata.get('llm_model', 'unknown')
            if "claude" in model:
                model = model.split('-')[-1] if '-' in model else model  # Show just the date part
            add_dag_line(f"Model: {model}")
        else:
            add_dag_line(f"Planner: {planner_type.title()}")

        task_type = metadata.get('task_type', metadata.get('template', 'general'))
        complexity = metadata.get('complexity', 'unknown')
        add_dag_line(f"Type: {task_type} | Complexity: {complexity}")
        add_dag_line()

        # Show DAG structure
        add_dag_line("Execution DAG:", bold=True)

        for i, step in enumerate(steps[:max_h - y - 2]):
            # Determine connection character
            if i == len(steps) - 1:
                connector = "└->"
            else:
                connector = "├->"

            # Show step
            op = step.get('op', step.get('id', '?'))
            description = step.get('description', '')[:max_w - x - 20]

            add_dag_line(f"{connector} {op}")

            # Show step details if there's space
            if y < max_h - 3:
                if description:
                    add_dag_line(f"   |  {description}", indent=0)

                # Show inputs/outputs compactly
                step_in = step.get('in', {})
                step_out = step.get('out', {})

                if isinstance(step_in, str):
                    add_dag_line(f"   |  in: {step_in}", indent=0)
                elif isinstance(step_in, dict) and step_in:
                    in_str = ", ".join(f"{k}={v}" for k, v in step_in.items())[:max_w - x - 15]
                    add_dag_line(f"   |  in: {in_str}", indent=0)

                if isinstance(step_out, str):
                    add_dag_line(f"   |  out: {step_out}", indent=0)
                elif isinstance(step_out, dict) and step_out:
                    out_str = ", ".join(f"{k}={v}" for k, v in step_out.items())[:max_w - x - 15]
                    add_dag_line(f"   |  out: {out_str}", indent=0)

            # Add connection line between steps
            if i < len(steps) - 1 and y < max_h - 2:
                add_dag_line("   |")

        # Show toggle hint
        if y < max_h - 2:
            add_dag_line()
            add_dag_line("[v] Toggle to list view")

    def _render_bc(self, win):
        bc = read_json(self.bc_path, {})
        prog = bc.get("program", [])
        y, x = 1, 2
        try:
            win.addstr(y, x, f"File: {self._rel(self.bc_path)}", curses.A_BOLD); y += 1
        except curses.error:
            pass
        for i, ins in enumerate(prog[:win.getmaxyx()[0]-3]):
            line = f"{i:02d} {ins[0]} {ins[1:]}"
            try:
                win.addstr(y, x, line[:win.getmaxyx()[1]-4])
            except curses.error:
                pass
            y += 1

    def _render_preview(self, win):
        # Show quick facts: out file list + report head if present
        y, x = 1, 2
        out_dir = self.sbx / "out"
        try:
            win.addstr(y, x, f"Sandbox out: {self._rel(out_dir)}", curses.A_BOLD); y += 1
        except curses.error:
            pass
        files = sorted([p.relative_to(self.sbx) for p in out_dir.rglob("*") if p.is_file()]) if out_dir.exists() else []
        if not files:
            self._add_line(win, y, x, "(no artifacts yet — run [d] or [e])"); y += 1
        else:
            for p in files[:10]:
                self._add_line(win, y, x, f"• {p}"); y += 1
        # preview report head
        rpt = out_dir / "report.md"
        if rpt.exists():
            y += 1
            self._add_line(win, y, x, "report.md (head):", bold=True); y += 1
            head = "\n".join(read_text(rpt).splitlines()[:8])
            for line in head.splitlines():
                self._add_line(win, y, x, line); y += 1

    def _render_policy(self, win):
        # show carbon/cost meters and quota usage
        y, x = 1, 2
        def add(line: str = "", bold=False):
            nonlocal y
            if y >= win.getmaxyx()[0] - 1:
                return
            self._add_line(win, y, x, line[:win.getmaxyx()[1]-4], bold=bold)
            y += 1

        # Current run metrics
        current_stats = self.meter.get_current_run_stats()
        add("CURRENT RUN METRICS", bold=True)

        if current_stats["status"] == "active_run":
            add(f"Run ID: {current_stats['run_id'][:12]}...")
            add(f"Tools: {current_stats['tools_executed']}")
            add(f"Cost: ${current_stats['total_cost_usd']:.6f}")
            add(f"CO2: {current_stats['total_co2_grams']:.2f}g")
            add(f"Tokens: {current_stats['total_tokens']}")
            add(f"Cache: {current_stats['cache_hit_rate']:.1f}%")
            runtime = current_stats.get('runtime_seconds', 0)
            add(f"Runtime: {runtime:.1f}s")
        else:
            add("  No active run")
        add()

        # Historical totals
        historical = self.meter.get_historical_stats(limit=5)
        totals = historical.get("totals", {})
        add("HISTORICAL TOTALS", bold=True)
        add(f"Total runs: {totals.get('runs_analyzed', 0)}")
        add(f"Total cost: ${totals.get('total_cost_usd', 0):.6f}")
        add(f"Total CO2: {totals.get('total_co2_grams', 0):.2f}g")
        add(f"Avg cost/run: ${totals.get('avg_cost_per_run', 0):.6f}")
        add(f"Avg CO2/run: {totals.get('avg_co2_per_run', 0):.2f}g")
        add()

        # Efficiency indicators
        add("EFFICIENCY", bold=True)
        cache_rate = current_stats.get('cache_hit_rate', 0) if current_stats["status"] == "active_run" else 0
        if cache_rate >= 80:
            add(f"Cache: {cache_rate:.1f}% EXCELLENT")
        elif cache_rate >= 50:
            add(f"Cache: {cache_rate:.1f}% GOOD")
        elif cache_rate > 0:
            add(f"Cache: {cache_rate:.1f}% POOR")
        else:
            add(f"Cache: {cache_rate:.1f}% NONE")

        # CO2 impact rating
        co2 = current_stats.get('total_co2_grams', 0) if current_stats["status"] == "active_run" else 0
        if co2 < 1:
            add("Impact: LOW")
        elif co2 < 10:
            add("Impact: MEDIUM")
        else:
            add("Impact: HIGH")

    def _render_logs(self, win):
        # show last ~100 lines from tx.jsonl (compact)
        tx = self.sbx / "logs" / "tx.jsonl"
        lines: List[str] = []
        if tx.exists():
            for line in tx.read_text(encoding="utf-8").splitlines()[-100:]:
                try:
                    rec = json.loads(line)
                    op = rec.get("op","")
                    msg = ""
                    if op in ("READ_CSV","WRITE_FILE","WRITE_JSON","ZIP","VERIFY_ZIP","ASSERT_GE","RUN_START","RUN_END","MAKE_DIR","VERIFY_CLI","WRITE_CHECKSUMS"):
                        msg = " ".join([f"{k}={v}" for k,v in rec.items() if k not in ("ts","dry_run","run_id")])
                    else:
                        msg = line
                    lines.append(msg)
                except Exception:
                    lines.append(line)
        else:
            lines.append("(no transactions yet)")
        y, x = 1, 2
        for ln in lines[-(win.getmaxyx()[0]-2):]:
            self._add_line(win, y, x, ln[:win.getmaxyx()[1]-4]); y += 1

    def _add_line(self, win, y, x, s: str, bold=False):
        try:
            if bold: win.attron(curses.A_BOLD)
            win.addstr(y, x, s)
            if bold: win.attroff(curses.A_BOLD)
        except curses.error:
            pass

    def _rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root))
        except Exception:
            return str(p)

    # --------------- actions ---------------

    def action_dryrun(self):
        self.status = "Dry-run in progress…"
        self.draw(); self.stdscr.refresh()
        try:
            run_bytecode(self.bc_path, self.sbx, dry_run=True, auto_yes=True)
            self.status = "Dry-run completed."
        except Exception as e:
            self.status = f"Dry-run ERROR: {e}"
        self.draw()

    def action_execute(self):
        self.status = "Execute in progress…"
        self.draw()
        try:
            run_bytecode(self.bc_path, self.sbx, dry_run=False, auto_yes=True)
            self.status = "Execute completed."
        except Exception as e:
            self.status = f"Execute ERROR: {e}"
        self.draw()

    def action_pack(self):
        self.status = "Packing…"
        self.draw()
        try:
            make_aiox(self.plan_path, self.bc_path, self.sbx, self.pkg_path, name="forge")
            self.status = f"Packed → {self._rel(self.pkg_path)}"
        except Exception as e:
            self.status = f"Pack ERROR: {e}"
        self.draw()

    def action_replay(self):
        if not self.pkg_path.exists():
            self.status = "Replay ERROR: package not found (run [p] first)."
            self.draw(); return
        self.status = "Replaying…"
        self.draw()
        ok, diffs = replay_aiox(self.pkg_path, self.sbx, auto_yes=True, clean_out=True)
        if ok:
            self.status = "Deterministic replay PASSED."
        else:
            self.status = f"Replay FAILED: {len(diffs)} diffs (see logs)."
        self.draw()

    def action_undo(self):
        n = undo_last_run(self.sbx)
        self.status = f"Undo removed {n} paths (if any)."
        self.draw()

    def action_open_report(self):
        rpt = self.sbx / "out" / "report.md"
        if rpt.exists():
            self.status = f"Opened: {self._rel(rpt)}"
        else:
            self.status = "No report yet."
        self.draw()

    def action_toggle_dag(self):
        self.show_plan_dag = not self.show_plan_dag
        view_type = "DAG" if self.show_plan_dag else "list"
        self.status = f"Plan view switched to {view_type}"
        self.draw()

    def action_cost_analysis(self):
        """Show cost analysis and pruning suggestions"""
        try:
            suggestions = self.meter.suggest_pruning_opportunities()
            historical = self.meter.get_historical_stats()

            if not suggestions:
                self.status = "No pruning opportunities found"
            else:
                # Show first few suggestions in status
                first_suggestion = suggestions[0]
                if first_suggestion["type"] == "cache_opportunity":
                    self.status = f"Prune: {first_suggestion['tool']} called {first_suggestion['count']}x - cache candidate"
                elif first_suggestion["type"] == "expensive_operation":
                    self.status = f"Prune: {first_suggestion['tool']} high cost (${first_suggestion['cost']:.4f})"
                else:
                    self.status = f"Found {len(suggestions)} pruning opportunities"

        except Exception as e:
            self.status = f"Cost analysis error: {e}"
        self.draw()

    def action_generate_plan(self):
        """Generate a new plan using LLM planner"""
        self.status = "Generating plan with LLM..."
        self.draw()
        try:
            from ..kernel.tools import ToolRegistry
            from ..planner.core import PlanGenerator
            from ..planner.apl_converter import APLConverter

            # Initialize components
            registry = ToolRegistry(self.root / "tools")
            registry.discover_tools()
            planner = PlanGenerator(registry, self.sbx)
            converter = APLConverter()

            # Use a sample goal for demonstration
            goal = "Analyze sample data and generate insights report"
            execution_plan = planner.generate_plan(goal=goal, input_csv="data.csv")

            # Convert to APL and save
            apl_data = converter.convert_to_apl(execution_plan)

            # Ensure directory exists
            self.plan_path.parent.mkdir(parents=True, exist_ok=True)
            self.plan_path.write_text(json.dumps(apl_data, indent=2), encoding="utf-8")

            planner_type = execution_plan.metadata.get('planner_type', 'unknown')
            self.status = f"Plan generated ({planner_type}) - {len(execution_plan.steps)} steps"

        except Exception as e:
            self.status = f"Generate error: {str(e)[:50]}..."
        self.draw()

    # --------------- event loop ---------------

    def loop(self):
        while True:
            self.draw()
            ch = self.stdscr.getch()
            if ch in (ord('q'), 27):  # q or ESC
                break
            elif ch == ord('g'):
                self.action_generate_plan()
            elif ch == ord('v'):
                self.action_toggle_dag()
            elif ch == ord('d'):
                self.action_dryrun()
            elif ch == ord('e'):
                self.action_execute()
            elif ch == ord('p'):
                self.action_pack()
            elif ch == ord('r'):
                self.action_replay()
            elif ch == ord('u'):
                self.action_undo()
            elif ch == ord('c'):
                self.action_cost_analysis()
            elif ch == ord('o'):
                self.action_open_report()
            elif ch in (ord('1'), ord('2'), ord('3'), ord('4')):
                self.selected_panel = int(chr(ch)) - 1
            else:
                self.status = "Keys: [g]enerate [v]iew DAG [c]ost analysis [d]ry-run [e]xecute [p]ack [r]eplay [u]ndo [q]uit"

def main(root: Path):
    def _wrap(stdscr):
        ui = ActivityUI(stdscr, root)
        ui.loop()
    curses.wrapper(_wrap)