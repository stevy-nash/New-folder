"""LLM evaluation pipeline for RetroDoc documentation quality — powered by DeepEval.

For each generated markdown in ``outputs/``, the pipeline:

1. Resolves the matching DSL rule source:
   - Prefers ``inputs/<RULE>.txt`` (original, with ``*`` comment lines).
   - Falls back to ``inputs/<RULE>_sans_commentaire.txt`` if not found.
2. Builds a DeepEval ``LLMTestCase`` where:
   - ``input``         = DSL rule source (with comments when available)
   - ``actual_output`` = generated Markdown documentation
3. Runs 5 ``GEval`` metrics against each test case using Azure OpenAI as judge.
4. Writes all scores to ``outputs/eval/eval_results.csv``.

Metrics (DeepEval GEval, score 0–1 each)
-----------------------------------------
- faithfulness  : doc accurately reflects what the DSL rule does
- coverage      : section 2 mentions the concepts behind all input/output variables (tables passed raw to the LLM judge)
- no_leakage    : section 2 contains no raw DSL variable names (HJOU_*, PARD_*, …)
- clarity       : RH-accessible French, no technical jargon or pseudo-code

Usage
-----
  # Evaluate all docs in outputs/
  python -m backend.eval.llm_eval

  # Evaluate a single rule
  python -m backend.eval.llm_eval --rule IACQCP

  # Custom inputs/outputs paths
  python -m backend.eval.llm_eval --inputs-dir inputs/ --outputs-dir outputs/
"""
from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import dataclass, fields, asdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd
from langchain_openai import AzureChatOpenAI
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from backend.agents.config import config, get_openai_token_provider

# ---------------------------------------------------------------------------
# Paths (resolved relative to this file's location)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_INPUTS_DIR = _REPO_ROOT / "inputs"
_DEFAULT_OUTPUTS_DIR = _REPO_ROOT / "outputs"
_EVAL_DIR = _DEFAULT_OUTPUTS_DIR / "eval"
_HOPPROG_CSV = _REPO_ROOT / "backend" / "assets" / "tables" / "hopprog.csv"


# ---------------------------------------------------------------------------
# Rule title lookup from hopprog.csv
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_rule_titles() -> dict[str, str]:
    """Return {REGLE: title} extracted from ``* Titre     : …`` comment lines."""
    if not _HOPPROG_CSV.exists():
        return {}
    df = pd.read_csv(_HOPPROG_CSV, sep=";", quotechar='"', dtype=str)
    titre_rows = df[df["INST"].str.startswith("* Titre", na=False)][["REGLE", "INST"]]
    result: dict[str, str] = {}
    for _, row in titre_rows.iterrows():
        rule = str(row["REGLE"]).strip().strip('"')
        # "* Titre     : Calcul des heures de dimanche"
        raw = str(row["INST"]).strip().strip('"')
        title = raw.split(":", 1)[-1].strip() if ":" in raw else raw
        if rule and title:
            result[rule] = title
    return result


def get_rule_title(rule_name: str) -> str:
    """Return the human-readable title for *rule_name*, or the rule name itself."""
    return _load_rule_titles().get(rule_name, rule_name)


@lru_cache(maxsize=None)
def _load_dsl_from_csv(rule_name: str) -> str:
    """Return the DSL source for *rule_name* reconstructed from hopprog.csv.

    Joins the INST column values in LIG order.
    """
    if not _HOPPROG_CSV.exists():
        raise FileNotFoundError(f"hopprog.csv not found at {_HOPPROG_CSV}")
    df = pd.read_csv(_HOPPROG_CSV, sep=";", quotechar='"', dtype=str)
    rule_df = df[df["REGLE"].str.strip().str.strip('"') == rule_name].copy()
    if rule_df.empty:
        raise ValueError(f"Rule '{rule_name}' not found in {_HOPPROG_CSV.name}")
    rule_df = rule_df.sort_values("LIG")
    lines = rule_df["INST"].fillna("").str.strip('"').tolist()
    return "\n".join(lines)


def _extract_io_tables(doc: str) -> str:
    """Return the raw markdown of sections 1 and 3 (input/output tables).

    These sections are produced deterministically (no LLM) and contain the
    canonical list of input and output variables.  Passed verbatim as
    ``expected_output`` so the LLM judge can read the tables directly.
    """
    s1 = re.search(r"^(.*?)(?=^#{1,3}\s+2\.)", doc, re.MULTILINE | re.DOTALL)
    s3 = re.search(r"(^#{1,3}\s+3\..*)", doc, re.MULTILINE | re.DOTALL)
    parts = [m.group(1).strip() for m in (s1, s3) if m]
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Azure OpenAI wrapper for DeepEval
# ---------------------------------------------------------------------------
class _AzureOpenAIJudge(DeepEvalBaseLLM):
    """Thin wrapper around AzureChatOpenAI for use as a DeepEval judge model."""

    def __init__(self) -> None:
        auth = (
            {"azure_ad_token_provider": get_openai_token_provider()}
            if not config.azure_openai_api_key
            else {"api_key": config.azure_openai_api_key}
        )
        self._model = AzureChatOpenAI(
            azure_endpoint=config.azure_openai_endpoint,
            api_version=config.azure_openai_api_version,
            azure_deployment=config.azure_openai_deployment,
            **auth,
        )

    def load_model(self):
        return self._model

    def generate(self, prompt: str) -> str:
        return self.load_model().invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        res = await self.load_model().ainvoke(prompt)
        return res.content

    def get_model_name(self) -> str:
        return f"Azure OpenAI — {config.azure_openai_deployment}"


# ---------------------------------------------------------------------------
# GEval metric definitions
# ---------------------------------------------------------------------------
def _build_metrics(judge: _AzureOpenAIJudge) -> dict[str, GEval]:
    """Return the five GEval metrics keyed by criterion name."""
    return {
        "faithfulness": GEval(
            name="Fidelite",
            evaluation_steps=[
                "Reponds uniquement en francais pour la justification.",
                "Lis attentivement la regle DSL fournie dans 'input', y compris les lignes de commentaire (lignes commencant par *).",
                "Verifie si le texte narratif dans 'actual output' (section 2) decrit fidelement ce que fait la regle d'un point de vue metier.",
                "Penalise toute affirmation qui contredit la logique DSL ou qui n'y apparait pas.",
                "Penalise fortement toute regle metier hallucinee qui n'a aucun fondement dans la source DSL.",
            ],
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=judge,
            async_mode=False,
        ),
        "coverage": GEval(
            name="Couverture des variables",
            evaluation_steps=[
                "Reponds uniquement en francais pour la justification.",
                "'context' contient les tableaux markdown des sections 1 (Elements en entree) et 3 (Elements en sortie), avec toutes les variables d'entree et de sortie et leur libelle fonctionnel (colonne Libelle).",
                "Lis ces tableaux et identifie le libelle fonctionnel de chaque variable (deuxieme colonne).",
                "Lis le texte narratif dans 'actual output' (section 2 de la documentation).",
                "Pour chaque libelle de variable, verifie si le concept correspondant est clairement explique ou mentionne dans le narratif.",
                "Accepte la paraphrase: la variable n'a pas besoin d'apparaitre mot a mot, mais le concept sous-jacent doit etre traite.",
                "Penalise proportionnellement chaque concept important totalement absent du narratif.",
            ],
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.CONTEXT],
            model=judge,
            async_mode=False,
        ),
        "no_leakage": GEval(
            name="Absence de fuite DSL",
            evaluation_steps=[
                "Reponds uniquement en francais pour la justification.",
                "Analyse la section narrative (section 2 — Regle de calcul / Regle de gestion) de 'actual output' pour detecter des noms de variables DSL bruts.",
                "Les noms de variables DSL suivent des motifs comme HJOU_IJRDCOFRAC, PARD_IDICALFRAC, HORC_IHIMOACQCP, EMPL_*, CONF_*, TEMP_*, etc.",
                "Attribue 1.0 si aucun identifiant de ce type n'apparait dans le texte narratif.",
                "Deduis proportionnellement pour chaque variable DSL divulguee; meme une seule occurrence doit entrainer une penalite significative.",
            ],
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            model=judge,
            async_mode=False,
        ),
        "clarity": GEval(
            name="Clarite",
            evaluation_steps=[
                "Reponds uniquement en francais pour la justification.",
                "Evalue si la section 2 de 'actual output' est redigee dans un francais clair, professionnel et accessible a des praticiens RH.",
                "Verifie que le texte evite les constructions de pseudo-code (SI ... ALORS ..., IF/THEN, POUR ..., etc.).",
                "Verifie l'absence de jargon technique dans le narratif (mots-cles de syntaxe DSL, noms de tables, identifiants de code).",
                "Evalue la fluidite: le texte doit se lire comme des paragraphes coherents, pas comme une liste a puces ou des etapes numerotees.",
            ],
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            model=judge,
            async_mode=False,
        ),
    }


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class EvalResult:
    rule_name: str
    rule_title: str              # human-readable label from hopprog.csv
    dsl_file: str
    doc_file: str
    faithfulness_score: float
    faithfulness_reason: str
    coverage_score: float
    coverage_reason: str
    no_leakage_score: float
    no_leakage_reason: str
    clarity_score: float
    clarity_reason: str
    overall_score: float         # arithmetic mean of the 5 criteria (0–1)
    error: str                   # non-empty when evaluation failed
    timestamp: str


# ---------------------------------------------------------------------------
# File resolution helpers
# ---------------------------------------------------------------------------
def _find_dsl_file(rule_name: str, inputs_dir: Path) -> tuple[Path, bool]:
    """Return (path, has_comments).

    Looks first for ``<RULE>.txt`` (with comments), then for
    ``<RULE>_sans_commentaire.txt``.
    """
    commented = inputs_dir / f"{rule_name}.txt"
    if commented.exists():
        return commented, True

    sans = inputs_dir / f"{rule_name}_sans_commentaire.txt"
    if sans.exists():
        return sans, False

    raise FileNotFoundError(
        f"No DSL source file found for rule '{rule_name}' in {inputs_dir}. "
        f"Tried: {commented.name}, {sans.name}"
    )


def _iter_doc_files(outputs_dir: Path) -> list[tuple[str, Path]]:
    """Yield (rule_name, path) for every doc_*.md in *outputs_dir* (non-recursive)."""
    pairs = []
    for f in sorted(outputs_dir.glob("doc_*.md")):
        # doc_IACQCP_sans_commentaire.md → IACQCP
        stem = f.stem  # doc_IACQCP_sans_commentaire
        rule = stem.removeprefix("doc_").removesuffix("_sans_commentaire")
        pairs.append((rule, f))
    return pairs


# ---------------------------------------------------------------------------
# Main evaluation logic
# ---------------------------------------------------------------------------
class LLMEvaluator:
    def __init__(self) -> None:
        self._judge = _AzureOpenAIJudge()
        self._metrics = _build_metrics(self._judge)

    def evaluate_one(
        self,
        rule_name: str,
        inputs_dir: Path,
        outputs_dir: Path,
    ) -> EvalResult:
        """Evaluate a single rule's documentation with all 5 GEval metrics."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Resolve files
        try:
            doc_path = outputs_dir / f"doc_{rule_name}_sans_commentaire.md"
            if not doc_path.exists():
                doc_path = outputs_dir / f"doc_{rule_name}.md"
            if not doc_path.exists():
                raise FileNotFoundError(
                    f"Generated doc not found for rule '{rule_name}' in {outputs_dir}"
                )
            dsl_source = _load_dsl_from_csv(rule_name)
        except (FileNotFoundError, ValueError) as exc:
            return EvalResult(
                rule_name=rule_name, rule_title=get_rule_title(rule_name),
                dsl_file="", doc_file="",
                faithfulness_score=0.0, faithfulness_reason="",
                coverage_score=0.0, coverage_reason="",
                no_leakage_score=0.0, no_leakage_reason="",
                clarity_score=0.0, clarity_reason="",
                overall_score=0.0, error=str(exc), timestamp=timestamp,
            )

        generated_doc = doc_path.read_text(encoding="utf-8")

        # Extract section 2 narrative; pass sections 1 & 3 tables raw for coverage
        section2 = generated_doc.split("#")[2]
        io_tables = [generated_doc.split("#")[1], generated_doc.split("#")[-1]]

        test_case = LLMTestCase(
            input=dsl_source,
            actual_output=section2,   # evaluate section 2 only
            context=io_tables, # raw markdown tables from sections 1 & 3
        )
    
        scores: dict[str, tuple[float, str]] = {}
        for name, metric in self._metrics.items():
            try:
                metric.measure(test_case)
                scores[name] = (metric.score, metric.reason or "")
            except Exception as exc:  # noqa: BLE001
                scores[name] = (0.0, f"ERROR: {exc}")

        overall = round(
            sum(s for s, _ in scores.values()) / len(scores), 4
        )

        return EvalResult(
            rule_name=rule_name,
            rule_title=get_rule_title(rule_name),
            dsl_file=f"hopprog.csv:{rule_name}",
            doc_file=str(doc_path.relative_to(_REPO_ROOT)) if doc_path.is_relative_to(_REPO_ROOT) else doc_path.name,
            faithfulness_score=scores["faithfulness"][0],
            faithfulness_reason=scores["faithfulness"][1],
            coverage_score=scores["coverage"][0],
            coverage_reason=scores["coverage"][1],
            no_leakage_score=scores["no_leakage"][0],
            no_leakage_reason=scores["no_leakage"][1],
            clarity_score=scores["clarity"][0],
            clarity_reason=scores["clarity"][1],
            overall_score=overall,
            error="",
            timestamp=timestamp,
        )

    def evaluate_all(
        self,
        inputs_dir: Path,
        outputs_dir: Path,
        delay_between_calls: float = 1.0,
    ) -> list[EvalResult]:
        """Evaluate every generated doc found in *outputs_dir*."""
        pairs = _iter_doc_files(outputs_dir)
        if not pairs:
            print(f"[eval] No doc_*.md files found in {outputs_dir}")
            return []

        results = []
        for i, (rule_name, _) in enumerate(pairs, 1):
            print(f"[eval] ({i}/{len(pairs)}) Evaluating {rule_name} …", end=" ", flush=True)
            result = self.evaluate_one(rule_name, inputs_dir, outputs_dir)
            if result.error:
                print(f"ERROR: {result.error}")
            else:
                print(f"overall={result.overall_score:.3f}")
            results.append(result)
            if i < len(pairs):
                time.sleep(delay_between_calls)

        return results


# ---------------------------------------------------------------------------
# CSV persistence
# ---------------------------------------------------------------------------
def save_csv(results: list[EvalResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [f.name for f in fields(EvalResult)]
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    print(f"\n[eval] Results written -> {output_path}")


def print_summary(results: list[EvalResult]) -> None:
    """Print a compact leaderboard to stdout (scores are 0–1)."""
    valid = [r for r in results if not r.error]
    if not valid:
        print("[eval] No valid results to summarise.")
        return

    col_w = 36
    header = (
        f"{'Rule (title)':<{col_w}} {'Faith':>6} {'Cover':>6} {'NoLeak':>7} "
        f"{'Clarity':>8} {'Overall':>8}"
    )
    print("\n=== Documentation Evaluation Results \u2014 Section 2 only (0\u20131) ===")
    print(header)
    print("-" * len(header))
    for r in sorted(valid, key=lambda x: x.overall_score, reverse=True):
        label = f"{r.rule_name} \u2014 {r.rule_title}" if r.rule_title != r.rule_name else r.rule_name
        print(
            f"{label:<{col_w}} "
            f"{r.faithfulness_score:>6.3f} "
            f"{r.coverage_score:>6.3f} "
            f"{r.no_leakage_score:>7.3f} "
            f"{r.clarity_score:>8.3f} "
            f"{r.overall_score:>8.3f}"
        )

    avg = sum(r.overall_score for r in valid) / len(valid)
    print("-" * len(header))
    print(f"{'Average':<{col_w}} {'':>6} {'':>6} {'':>7} {'':>8} {avg:>8.3f}")

    errors = [r for r in results if r.error]
    if errors:
        print(f"\n[eval] {len(errors)} rule(s) failed: {', '.join(r.rule_name for r in errors)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM-as-a-judge evaluation for RetroDoc documentation."
    )
    parser.add_argument(
        "--rule",
        default=None,
        help="Evaluate a single rule by name (e.g. IACQCP). Omit to evaluate all.",
    )
    parser.add_argument(
        "--inputs-dir",
        default=str(_DEFAULT_INPUTS_DIR),
        help=f"Directory containing DSL rule files (default: {_DEFAULT_INPUTS_DIR})",
    )
    parser.add_argument(
        "--outputs-dir",
        default=str(_DEFAULT_OUTPUTS_DIR),
        help=f"Directory containing generated doc_*.md files (default: {_DEFAULT_OUTPUTS_DIR})",
    )
    parser.add_argument(
        "--out-csv",
        default=str(_EVAL_DIR / "eval_results.csv"),
        help="Path for the output CSV (default: outputs/eval/eval_results.csv)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between LLM calls (default: 1.0)",
    )
    args = parser.parse_args()

    inputs_dir = Path(args.inputs_dir)
    outputs_dir = Path(args.outputs_dir)
    out_csv = Path(args.out_csv)

    evaluator = LLMEvaluator()

    if args.rule:
        result = evaluator.evaluate_one(args.rule, inputs_dir, outputs_dir)
        results = [result]
    else:
        results = evaluator.evaluate_all(inputs_dir, outputs_dir, delay_between_calls=args.delay)

    print_summary(results)
    save_csv(results, out_csv)


if __name__ == "__main__":
    main()
