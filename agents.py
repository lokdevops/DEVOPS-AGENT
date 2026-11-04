"""Deterministic agentic engineering workflow with dependency graph and approval gate.
The agents below are rule-driven specialists, not autonomous LLMs.
"""
import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent

@dataclass
class Task:
    name: str
    dependencies: tuple
    action: object

class RequirementAgent:
    def run(self, ctx):
        raw = ctx["requirement"]
        kind = "brownfield" if any(x in raw.lower() for x in ("existing", "fix", "refactor", "enhance")) else "greenfield"
        ambiguities = ["Expected traffic and latency SLO are unspecified", "Retention and privacy requirements for analytics are unspecified"]
        if len(raw.split()) < 7 or "fast" in raw.lower():
            ambiguities.append("Clarify the meaning of performance and acceptance criteria")
        return {"normalized":raw.strip(), "type":kind, "ambiguities":ambiguities, "assumptions":["HTTP(S) only", "Single-node SQLite prototype", "Anonymous aggregate click counts"]}

class PlanningAgent:
    def run(self, ctx):
        return {"tasks":[{"id":"design","depends_on":["requirements"]},{"id":"implementation","depends_on":["design"]},{"id":"tests","depends_on":["implementation"]},{"id":"review","depends_on":["tests"]}]}

class ArchitectureAgent:
    def run(self, ctx):
        return {"components":["FastAPI", "SQLite", "links table", "clicks table"], "endpoints":["POST /api/links", "GET /{code}", "GET /api/links/{code}/analytics"], "decision":"SQLite is suitable for demo; use PostgreSQL and async events at scale"}

class CodeAgent:
    def run(self, ctx):
        files = ["app/main.py", "requirements.txt"]
        return {"artifacts":files, "verified_present":all((ROOT / x).exists() for x in files), "mode":"prebuilt reviewed template; no runtime code generation"}

class TestAgent:
    def run(self, ctx):
        result = subprocess.run([sys.executable,"-m","pytest","-q","tests"],cwd=ROOT,capture_output=True,text=True,timeout=60)
        return {"passed":result.returncode==0,"exit_code":result.returncode,"output":(result.stdout+result.stderr)[-3000:]}

class ReviewAgent:
    def run(self, ctx):
        return {"accepted":ctx["tests"]["passed"] and ctx["implementation"]["verified_present"],"risks":["SQLite cannot support high write throughput across replicas", "Synchronous click recording adds redirect latency", "Public analytics endpoint lacks authorization", "No rate limiting, abuse detection, or URL safety scanning"],"limitations":["No model-based reasoning or dynamic code generation", "Brownfield source inspection is not implemented", "Approval is CLI-driven"]}

class Orchestrator:
    def __init__(self, tasks):
        self.tasks={t.name:t for t in tasks}
    def run(self, ctx):
        pending=set(self.tasks)
        ctx["execution_log"]=[]
        while pending:
            ready=sorted(n for n in pending if all(d in ctx for d in self.tasks[n].dependencies))
            if not ready:
                raise RuntimeError("Cycle or missing dependency: "+str(pending))
            for name in ready:
                try:
                    ctx[name]=self.tasks[name].action.run(ctx)
                    ctx["execution_log"].append({"task":name,"status":"completed"})
                except Exception as e:
                    ctx["execution_log"].append({"task":name,"status":"failed","error":str(e)})
                    raise
                pending.remove(name)
                if name=="tests" and not ctx[name]["passed"]:
                    ctx["execution_log"].append({"task":"review","status":"blocked","reason":"tests failed"})
                    return ctx
        return ctx

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("requirement", nargs="?", default="Build a scalable URL shortener service with APIs, persistence, and analytics")
    parser.add_argument("--approve", action="store_true", help="Explicitly approve result after review")
    args=parser.parse_args()
    tasks=[Task("requirements",(),RequirementAgent()),Task("plan",("requirements",),PlanningAgent()),Task("design",("plan",),ArchitectureAgent()),Task("implementation",("design",),CodeAgent()),Task("tests",("implementation",),TestAgent()),Task("review",("tests",),ReviewAgent())]
    ctx=Orchestrator(tasks).run({"requirement":args.requirement})
    ctx["human_approval"]="approved" if args.approve and ctx.get("review",{}).get("accepted") else "pending"
    (ROOT/"engineering_report.json").write_text(json.dumps(ctx,indent=2))
    print(json.dumps(ctx,indent=2))
    if not ctx.get("tests",{}).get("passed"):
        sys.exit(1)

if __name__=="__main__":
    main()
