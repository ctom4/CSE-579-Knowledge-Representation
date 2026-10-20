import os
import re
import subprocess
from pathlib import Path

import google.generativeai as genai

# -------------------------------
# Gemini Configuration
# -------------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro")

# =========================
# Config (Iteration 3 additions)
# =========================
MODEL_NAME = "gemini-2.5-pro"
INSTANCE_FILE = "inst1.asp"
OUTPUT_DOMAIN_FILE = "warehouse_domain3.lp"

MAX_T = 20
MAX_ITERS = 6  # number of repair attempts before giving up
CLINGO_CMD = ["clingo"]  # or ["python", "-m", "clingo"] if clingo isn't on PATH

# =========================================================
# STEP 1: REASONING CALIBRATION (NO OUTPUT SAVED)
# =========================================================
step1_prompt = """
You are an expert in Answer Set Programming (ASP) using Clingo.

The following examples are provided ONLY to calibrate your reasoning style.
They demonstrate correct syntax and structure for CSP encodings.

These examples are STANDALONE problems.
DO NOT assume future problems are standalone.

-----------------------------------
EXAMPLE 1: 8-Queens with Center Restriction
-----------------------------------
Problem:
Use clingo to find all solutions to the 8 queens problem such that:
- Exactly one queen per row
- No two queens share the same column
- No two queens share the same diagonal
- No queen is placed in the central 4x4 region (rows 3–6, columns 3–6)

% --------------------------------------------------
% Define the board size
% Rows and columns are numbered from 1 to 8
% --------------------------------------------------

% --------------------------------------------------
% Rule 1: Exactly one queen in each row
% For every row R (1..8), choose exactly one column C (1..8)
% such that queen(R,C) is true.
% The "1 { ... } 1" construct enforces exactly one choice.
% --------------------------------------------------
1 { queen(R,C) : C = 1..8 } 1 :- R = 1..8.

% --------------------------------------------------
% Rule 2: No two queens can be in the same column
% This is an integrity constraint (:- ...)
% If two different rows R1 and R2 have queens in the same column C,
% the solution is rejected.
% --------------------------------------------------
:- queen(R1,C), queen(R2,C), R1 != R2.

% --------------------------------------------------
% Rule 3: No two queens can be on the same diagonal
% Two queens are on the same diagonal if:
%   |row difference| == |column difference|
% If this condition holds for any pair of queens in different rows,
% the solution is invalid.
% --------------------------------------------------
:- queen(R1,C1), queen(R2,C2),
   R1 != R2,
   |R1 - R2| == |C1 - C2|.

% --------------------------------------------------
% Rule 4: No queen may be placed in the central 4x4 region
% The central region is defined as:
%   Rows 3 to 6 AND Columns 3 to 6
% Any queen placed inside this region causes the solution to be rejected.
% --------------------------------------------------
:- queen(R,C),
   R >= 3, R <= 6,
   C >= 3, C <= 6.

-----------------------------------
EXAMPLE 2: World's Hardest Sudoku
-----------------------------------
Problem:
Solve a 9x9 Sudoku such that:
- Each number 1–9 appears exactly once per row
- Each number 1–9 appears exactly once per column
- Each number 1–9 appears exactly once per 3x3 subgrid
- Pre-filled values must be respected

% --------------------------------------------------
% Define the Sudoku grid
% Rows (R), Columns (C), and Numbers (N) range from 1 to 9
% --------------------------------------------------

% --------------------------------------------------
% Rule 1: Exactly one number per cell
% For every cell at position (R,C), choose exactly one number N (1..9).
% This guarantees that every cell is filled with one value.
% --------------------------------------------------
1 { cell(R,C,N) : N = 1..9 } 1 :- R = 1..9, C = 1..9.

% --------------------------------------------------
% Rule 2: No cell can contain two different numbers
% If a cell (R,C) is assigned two distinct numbers N1 and N2,
% the solution is invalid.
% (This rule is mostly redundant due to Rule 1, but helps clarity.)
% --------------------------------------------------
:- cell(R,C,N1), cell(R,C,N2), N1 != N2.

% --------------------------------------------------
% Rule 3: Row constraint
% Each number N must appear at most once in each row R.
% If the same number N appears in two different columns
% within the same row, the solution is rejected.
% --------------------------------------------------
:- cell(R,C1,N), cell(R,C2,N), C1 != C2.

% --------------------------------------------------
% Rule 4: Column constraint
% Each number N must appear at most once in each column C.
% If the same number N appears in two different rows
% within the same column, the solution is rejected.
% --------------------------------------------------
:- cell(R1,C,N), cell(R2,C,N), R1 != R2.

% --------------------------------------------------
% Rule 5: 3x3 subgrid constraint
% Each number N must appear at most once in each 3x3 subgrid.
%
% (R-1)/3 and (C-1)/3 compute the subgrid index (0..2).
% If two different cells belong to the same subgrid
% and contain the same number N, the solution is invalid.
% --------------------------------------------------
:- cell(R1,C1,N), cell(R2,C2,N),
   (R1-1)/3 == (R2-1)/3,
   (C-1)/3 == (C2-1)/3,
   (R1,C1) != (R2,C2).

% --------------------------------------------------
% Pre-filled Sudoku clues
% These facts enforce the initial values of the puzzle.
% The solver must respect these assignments.
% --------------------------------------------------

cell(1,1,8).

cell(3,2,7).
cell(4,2,5).
cell(9,2,9).

cell(2,3,3).
cell(7,3,1).
cell(8,3,8).

cell(2,4,6).
cell(6,4,1).
cell(8,4,5).

cell(3,5,9).
cell(5,5,4).

cell(4,6,7).
cell(5,6,5).

cell(3,7,2).
cell(5,7,7).
cell(9,7,4).

cell(6,8,3).
cell(7,8,6).
cell(8,8,1).

cell(7,9,8).

-----------------------------------
EXAMPLE 3: Offset Sudoku
-----------------------------------
Problem:
Solve an Offset Sudoku where:
- Standard row and column constraints apply
- Each offset 3x3 block must contain numbers 1–9 exactly once
- Pre-filled values must be respected

% --------------------------------------------------
% Define the Offset Sudoku grid
% Rows (R), Columns (C), and Numbers (N) range from 1 to 9
% --------------------------------------------------

% --------------------------------------------------
% Rule 1: Exactly one number per cell
% For every cell at position (R,C), select exactly one number N (1..9).
% This ensures the grid is completely filled.
% --------------------------------------------------
1 { cell(R,C,N) : N = 1..9 } 1 :- R = 1..9, C = 1..9.

% --------------------------------------------------
% Rule 2: A cell cannot contain two different numbers
% If a single cell (R,C) is assigned two distinct numbers,
% the solution is rejected.
% (Redundant due to Rule 1, but improves readability.)
% --------------------------------------------------
:- cell(R,C,N1), cell(R,C,N2), N1 != N2.

% --------------------------------------------------
% Rule 3: Row constraint
% Each number N may appear at most once in each row R.
% If the same number appears in two different columns
% within the same row, the solution is invalid.
% --------------------------------------------------
:- cell(R,C1,N), cell(R,C2,N), C1 != C2.

% --------------------------------------------------
% Rule 4: Column constraint
% Each number N may appear at most once in each column C.
% If the same number appears in two different rows
% within the same column, the solution is rejected.
% --------------------------------------------------
:- cell(R1,C,N), cell(R2,C,N), R1 != R2.

% --------------------------------------------------
% Rule 5: Offset 3x3 block constraint
% Unlike standard Sudoku, the 3x3 blocks are "offset".
% Two cells belong to the same block if:
%   floor(R / 3) is equal AND floor(C / 3) is equal.
%
% Integer division (/) groups rows and columns differently
% compared to standard Sudoku ((R-1)/3).
% If the same number N appears twice in the same offset block,
% the solution is invalid.
% --------------------------------------------------
:- cell(R1,C1,N), cell(R2,C2,N),
   R1 / 3 == (R2 / 3),
   C1 / 3 == (C2 / 3),
   (R1,C1) != (R2,C2).

% --------------------------------------------------
% Pre-filled Offset Sudoku clues
% These facts define the given puzzle values.
% The solver must respect these assignments.
% --------------------------------------------------

cell(1,3,7).
cell(1,7,8).

cell(2,2,2).
cell(2,8,4).

cell(3,1,8).
cell(3,3,4).
cell(3,5,2).
cell(3,7,5).
cell(3,9,1).

cell(4,5,7).

cell(5,3,8).
cell(5,4,3).
cell(5,5,6).
cell(5,6,4).
cell(5,7,2).

cell(6,5,9).

cell(7,1,3).
cell(7,3,2).
cell(7,5,8).
cell(7,7,7).
cell(7,9,4).

cell(8,2,7).
cell(8,8,8).

cell(9,3,6).
cell(9,7,9).
"""

# Run Step 1 (calibration only)
model.generate_content(step1_prompt)

# =========================================================
# Helpers (Iteration 3 additions)
# =========================================================
def read_instance_excerpt(inst_path: Path, max_lines: int = 160) -> str:
    text = inst_path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()
    return "\n".join(lines[:max_lines])


def extract_clingo_code(raw_text: str) -> str:
    """
    Tries hard to extract only clingo/ASP code.
    Handles:
      - fenced blocks ``` ... ```
      - accidental explanations before/after
      - stray markdown
    """
    if not raw_text:
        return ""

    t = raw_text.strip()

    # Prefer fenced code blocks if present
    fence = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*([\s\S]*?)\s*```", t)
    if fence:
        t = fence[0].strip()

    # Remove common markdown artifacts
    t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t).strip()
    t = re.sub(r"\s*```$", "", t).strip()

    # If model still wrote prose, try to keep from first ASP-looking line onward
    lines = t.splitlines()
    keep = []
    started = False
    asp_markers = (
        "#const", "time(", "step(", ":-", "{", "}", "#show", "#minimize",
        "robot(", "shelf(", "product(", "pstation(", "order(", "init("
    )
    for line in lines:
        if not started and any(m in line for m in asp_markers):
            started = True
        if started:
            keep.append(line)

    t2 = "\n".join(keep).strip() if keep else t

    # Final cleanup: remove obvious non-code lines (very conservative)
    cleaned = []
    for line in t2.splitlines():
        if line.strip().lower().startswith(("here is", "sure,", "note:", "explanation", "i will", "this program")):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


def run_clingo(domain_path: Path, inst_path: Path) -> tuple[int, str, str]:
    """
    Returns (exit_code, stdout, stderr)
    """
    cmd = CLINGO_CMD + [str(domain_path), str(inst_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def looks_like_solution(stdout: str, stderr: str = "") -> bool:
    """
    Success if clingo produced at least one model ("Answer:").
    Reject UNSAT and grounding/parse errors.
    Note: clingo can return nonzero exit codes (e.g., 30) even when it finds models.
    """
    if "UNSATISFIABLE" in stdout:
        return False

    combined = (stdout + "\n" + (stderr or "")).lower()
    if "error:" in combined:
        return False

    return "Answer:" in stdout


# =========================================================
# Prompt builder (Iteration 3 additions)
# =========================================================
def build_base_prompt(inst_excerpt: str) -> str:
    return f"""
You are an expert in Answer Set Programming (ASP) using Clingo.

Your task: Generate a DOMAIN-LEVEL warehouse encoding that will be combined with DIFFERENT instance files.

IMPORTANT:
- The instance uses init/2 facts with schemas shown below.
- Your domain encoding MUST derive all objects ONLY from init/2.
- Output ONLY valid Clingo code (no markdown, no backticks, no explanations, no comments).

INSTANCE EXCERPT (schema reference):
{inst_excerpt}

STRICT RULES (must follow):
1) Output ONLY valid Clingo code. No markdown. No backticks. No explanations. No comments.
2) Do NOT hardcode robots, shelves, products, grid size, orders, picking stations, highways, or actions.
3) ALL objects MUST be derived from init/2 facts.
4) Do NOT include any ground occurs(...) facts.
5) Time must be symbolic: use #const maxT = {MAX_T} and time(0..maxT). Use step(T) :- time(T), T < maxT.
6) Do NOT use arithmetic inside predicate arguments (e.g., at(robot,R,X+DX,Y,T)).
7) Do NOT use tuple comparisons like (X,Y)!=(X2,Y2).
8) Do NOT use disjunctions inside rule bodies like (a; b).
9) Use auxiliary variables for arithmetic (NX = X + DX).
10) Use only safe variables. No undefined predicates.

MANDATORY object extraction patterns (must include):
robot(R)     :- init(object(robot,R),_).
shelf(S)     :- init(object(shelf,S),_).
product(PR)  :- init(object(product,PR),_).
pstation(P)  :- init(object(pickingStation,P),_).
order(O)     :- init(object(order,O),_).
node(X,Y)    :- init(object(node,_), value(at,pair(X,Y))).
highway(X,Y) :- init(object(highway,_), value(at,pair(X,Y))).

Initial state patterns (must include):
at(robot,R,X,Y,0) :- init(object(robot,R), value(at,pair(X,Y))).
onfloor(S,X,Y,0)  :- init(object(shelf,S), value(at,pair(X,Y))).
at(pstation,P,X,Y) :- init(object(pickingStation,P), value(at,pair(X,Y))).

Order/product patterns (must include):
order_station(O,P) :- init(object(order,O), value(pickingStation,P)).
order_line(O,PR,Q) :- init(object(order,O), value(line,pair(PR,Q))).
inv(PR,S,Q)        :- init(object(product,PR), value(on,pair(S,Q))).

ACTIONS (MUST USE ONLY THESE PREDICATES; EXACT ARITY):
move(R,DX,DY,T)
pickup(R,S,T)
putdown(R,S,T)
deliver(R,S,O,P,T)

CRITICAL SEMANTICS (must satisfy):
A) Shelf location model must distinguish floor vs carried.
   onfloor(S,X,Y,T) and carrying(R,S,T).
   Define derived shelf position:
   at(shelf,S,X,Y,T) :- onfloor(S,X,Y,T).
   at(shelf,S,X,Y,T) :- carrying(R,S,T), at(robot,R,X,Y,T).

B) Co-location rule:
   Robots may share a cell with a shelf ONLY if the robot is carrying that shelf
   OR is executing pickup/putdown with that shelf at that time.
   Do NOT add an over-strong constraint that makes valid plans UNSAT.

C) pickup/putdown:
   pickup(R,S,T) requires robot and shelf co-located, shelf onfloor at T, robot not already carrying.
   putdown(R,S,T) requires carrying(R,S,T) and results in onfloor(S, robot_pos, T+1).

D) Movement:
   move(R,DX,DY,T) allows 4-neighborhood + wait (0,0).
   Use auxiliary NX = X + DX, NY = Y + DY. Require node(NX,NY).

E) Collisions & swaps:
   No two robots in same cell at same time.
   No robot swaps positions in one timestep.
   No two shelves overlap at any time (including carried via at(shelf,...)).
   One shelf per robot; no shelf carried by two robots.

F) Highway restriction:
   No shelf may be at any highway cell at any time, including while carried:
   :- at(shelf,S,X,Y,T), highway(X,Y).

G) Orders & delivery:
   deliver(R,S,O,P,T) allowed only if robot at picking station P at time T AND carrying(R,S,T)
   AND order_station(O,P).
   Each delivery with shelf S contributes product quantities to order O based on inv(PR,S,QINV).
   You may treat shelf inventory as not depleted across deliveries.
   All order lines must be satisfied by time maxT.

   IMPORTANT: Only allow a delivery if the order still needs product from that shelf.
   Use a helper predicate like need_from_shelf(O,S,T) that checks delivered_amount
   is still below the required quantity for at least one product on that shelf.
   Forbid deliver actions where need_from_shelf does not hold.

H) Inertia:
   Add frame axioms for at(robot,...), onfloor/4, carrying/3.

   CRITICAL: deliver does NOT drop the shelf. Only putdown drops the shelf.
   The carrying inertia rule must be:
   carrying(R,S,T+1) :- carrying(R,S,T), not putdown(R,S,T), step(T).
   Do NOT include "not deliver(R,S,_,_,T)" in the carrying inertia rule.
   The robot keeps holding the shelf after delivery so it can deliver the same
   shelf to multiple orders without extra pickup/putdown cycles.

OPTIMIZATION (must implement exactly):
- Define goal_met(T): all order lines satisfied at time T.
- Enforce goal_met(maxT).
- Define first_goal(T): earliest T such that goal_met(T).
- Use exactly: #minimize {{ T@1 : first_goal(T) }}.

OUTPUT CONTROL:
- Include #show for move/4, pickup/3, putdown/3, deliver/5, first_goal/1.

Now output ONLY the Clingo code.
""".strip()


def build_repair_prompt(previous_code: str, clingo_stdout: str, clingo_stderr: str) -> str:
    return f"""
You previously generated a warehouse domain encoding, but clingo failed or did not produce a solution.

You must output a corrected FULL domain encoding as valid clingo code ONLY.
No markdown. No backticks. No explanations. No comments.

REQUIREMENTS (do not violate):
- Keep the same init/2 schema usage; derive objects only from init/2.
- Keep action signatures EXACTLY:
  move/4, pickup/3, putdown/3, deliver/5
- Keep #const maxT = {MAX_T}, time(0..maxT), step(T) :- time(T), T < maxT.
- Keep derived at(shelf,...) and highway restriction on at(shelf,...).
- Keep #minimize {{ T@1 : first_goal(T) }}.
- Use safe variables. No arithmetic inside predicate arguments.
- CRITICAL: deliver does NOT drop the shelf. Only putdown drops.
  carrying(R,S,T+1) :- carrying(R,S,T), not putdown(R,S,T), step(T).
  Do NOT add "not deliver(...)" to the carrying inertia rule.
- Only allow deliver if the order still needs product from that shelf
  (use need_from_shelf helper predicate).

PREVIOUS CODE:
{previous_code}

CLINGO STDOUT:
{clingo_stdout}

CLINGO STDERR:
{clingo_stderr}

Now output ONLY the corrected clingo code.
""".strip()


# =========================================================
# STEP 2 + STEP 3: GENERATE DOMAIN, VERIFY WITH CLINGO, REPAIR LOOP
# =========================================================
def main() -> None:
    inst_path = Path(INSTANCE_FILE)
    if not inst_path.exists():
        raise FileNotFoundError(f"Instance file not found: {INSTANCE_FILE}")

    inst_excerpt = read_instance_excerpt(inst_path, max_lines=160)
    base_prompt = build_base_prompt(inst_excerpt)

    code = ""
    for attempt in range(1, MAX_ITERS + 1):
        if attempt == 1:
            resp = model.generate_content(base_prompt)
        else:
            # run clingo on last attempt code and feed back errors
            domain_path = Path(OUTPUT_DOMAIN_FILE)
            domain_path.write_text(code, encoding="utf-8")

            rc, out, err = run_clingo(domain_path, inst_path)

            # If it yields at least one model, we are done (even if rc != 0)
            if looks_like_solution(out, err):
                print(f"[OK] Clingo produced a solution on attempt {attempt-1}.")
                print(f"[OK] Domain written to {OUTPUT_DOMAIN_FILE}")
                return

            repair_prompt = build_repair_prompt(code, out, err)
            resp = model.generate_content(repair_prompt)

        raw = getattr(resp, "text", "") or ""
        code = extract_clingo_code(raw)

        Path(OUTPUT_DOMAIN_FILE).write_text(code, encoding="utf-8")
        print(f"[INFO] Wrote {OUTPUT_DOMAIN_FILE} (attempt {attempt}/{MAX_ITERS}).")

        # Quick verify each attempt
        rc, out, err = run_clingo(Path(OUTPUT_DOMAIN_FILE), inst_path)

        if looks_like_solution(out, err):
            print(f"[OK] Clingo produced a solution on attempt {attempt}.")
            print(f"[OK] Domain written to {OUTPUT_DOMAIN_FILE}")
            return

        # Print compact diagnostics so you can see what's going on
        print(f"[INFO] clingo exit code: {rc}")
        if err.strip():
            print("[INFO] clingo stderr (first 25 lines):")
            print("\n".join(err.splitlines()[:25]))
        else:
            print("[INFO] clingo stdout (first 25 lines):")
            print("\n".join(out.splitlines()[:25]))

    print(f"[FAIL] Could not get a working solution after {MAX_ITERS} attempts.")
    print(f"[FAIL] Last domain left at: {OUTPUT_DOMAIN_FILE}")


if __name__ == "__main__":
    main()