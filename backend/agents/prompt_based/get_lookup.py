"""Dynamic variable lookup against affichage_ecran_clean.csv, hopdico.csv and hopmoti.csv.

Parses variable names from DSL rule code in two passes:
  1. DEBDICO block declarations (as before).
  2. Full-code scan for any DOMAIN_VARNAME token whose prefix belongs to a
     known domain (HJOU, HORC, PARD, CONF, EMPL, PROF, MOTI, TEMP, CTRA,
     SECH, CADM).  LOCA_ (local) and HABS_ (loop-only) are excluded.

Strips the domain prefix, then looks up the short name in the screen
reference table and the hopdico dictionary.

Also extracts hardcoded motif codes used in HABS_MOTIF comparisons and
looks them up in hopmoti.csv.

Code traitement values (from hopdico.csv TRAIT column):
  *n = valeur système de niveau n
  Cn = constante de niveau n
  Vn = variable de niveau n

Version routing
---------------
Call ``resolve_table_paths(version)`` to obtain a ``TablePaths`` for a specific
package version (e.g. "v15").  Pass the result as the ``table_paths`` keyword
argument to every public ``build_*`` / ``get_rule_status`` function.  When
``table_paths`` is omitted the legacy v16.3 standard tables are used.
"""
import os
import re
import pandas as pd
from dataclasses import dataclass
from functools import lru_cache

# Match any DOMAIN_VARNAME token in the rule body, excluding LOCA_ (local
# calculation vars) and TEMP_ (internal temporaries) which are not in the
# reference tables.
_DOMAIN_VAR_RE = re.compile(r'\b(?!(?:LOCA|MOTI|HABS)_)([A-Z][A-Z0-9]*)_([A-Z][A-Z0-9]+)\b')

_ASSETS_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))

# ---------------------------------------------------------------------------
# TablePaths — immutable set of resolved file paths for one package version
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TablePaths:
    """Resolved file paths for a specific package version's lookup tables."""
    ecran_csv: str
    hopdico_csv: str
    hopcode_csv: str
    hopmess_csv: str
    hopmoti_csv: str
    hopregl_csv: str
    standard_hopprog_path: str | None = None  # Sources standard/hopprog.bdd if available


def resolve_table_paths(version: str) -> TablePaths:
    """Return ``TablePaths`` for *version* (e.g. ``"v15"``).

    v15  → ``backend/assets/v15/Sources spécifique/``  (.bdd files, same CSV format)
    default / v16.3 → ``backend/assets/tables/v16.3/``
    """
    v = version.lower().strip()
    if v == "v15":
        d = os.path.join(_ASSETS_ROOT, "v15", "Sources spécifique")
        std_hopprog = os.path.join(_ASSETS_ROOT, "v15", "Sources standard", "hopprog.bdd")
        return TablePaths(
            ecran_csv=os.path.join(d, "affichage_ecran.csv"),
            hopdico_csv=os.path.join(d, "hopdico.bdd"),
            hopcode_csv=os.path.join(d, "hopcode.bdd"),
            hopmess_csv=os.path.join(d, "hopmess.bdd"),
            hopmoti_csv=os.path.join(d, "hopmoti.bdd"),
            hopregl_csv=os.path.join(d, "hopregl.bdd"),
            standard_hopprog_path=std_hopprog if os.path.isfile(std_hopprog) else None,
        )
    # Default: v16.3 standard tables (CSV)
    d = os.path.join(_ASSETS_ROOT, "tables", "v16.3")
    return TablePaths(
        ecran_csv=os.path.join(d, "affichage_ecran_clean.csv"),
        hopdico_csv=os.path.join(d, "hopdico.csv"),
        hopcode_csv=os.path.join(d, "hopcode.csv"),
        hopmess_csv=os.path.join(d, "hopmess.csv"),
        hopmoti_csv=os.path.join(d, "hopmoti.csv"),
        hopregl_csv=os.path.join(d, "hopregl.csv"),
    )


_DEFAULT_TABLE_PATHS = resolve_table_paths("v15")


@lru_cache(maxsize=8)
def _load_hopregl_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8", dtype=str)
    df["REGLE"] = df["REGLE"].str.strip('"').str.strip()
    df["LIBELLE"] = df["LIBELLE"].str.strip('"').str.strip()
    df["ACTIVE"] = df["ACTIVE"].str.strip('"').str.strip()
    df["COMPIL"] = df["COMPIL"].str.strip('"').str.strip()
    df["ORDRE"] = df["ORDRE"].str.strip('"').str.strip()
    return df[["REGLE", "LIBELLE", "ACTIVE", "COMPIL", "ORDRE"]]


def get_rule_status(rule_name: str, table_paths: TablePaths | None = None) -> tuple[str, str, str, str]:
    """Return (active_label, compil_label, ordre, libelle) for *rule_name* from hopregl table."""
    paths = table_paths or _DEFAULT_TABLE_PATHS
    try:
        df = _load_hopregl_table(paths.hopregl_csv)
    except FileNotFoundError:
        return "", "", "", ""
    row = df[df["REGLE"].str.upper() == rule_name.strip().upper()]
    if row.empty:
        return "", "", "", ""
    active = "Activé" if row.iloc[0]["ACTIVE"] == "1" else "Désactivé"
    compil = "Compilé" if row.iloc[0]["COMPIL"] == "1" else "Non compilé"
    ordre = row.iloc[0]["ORDRE"]
    libelle = row.iloc[0]["LIBELLE"]
    return active, compil, ordre, libelle


@lru_cache(maxsize=8)
def _load_ecran_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df = df.replace('N/D', pd.NaT)
    df['ECRAN'] = df['ECRAN']+' > '+df['ONGLET']
    df.drop(columns=['ONGLET'], inplace=True, errors='ignore')
    df = df.groupby(["DONNEE", "DOMAINE", "LIBELLE"])['ECRAN'].apply(lambda g: list(g)).reset_index()
    df['ECRAN'] = df['ECRAN'].str.join(", ")
    return df

@lru_cache(maxsize=8)
def _load_hopdico_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df["NOM"] = df["NOM"].str.strip('"').str.strip()
    df["TRAIT"] = df["TRAIT"].str.strip('"').str.strip()
    return df[["NOM", "TRAIT", "LIBELLE"]].drop_duplicates(subset=["NOM"])


@lru_cache(maxsize=8)
def _load_hopmoti_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df["MOTIF"] = df["MOTIF"].str.strip('"').str.strip()
    df["LIBELLE"] = df["LIBELLE"].str.strip('"').str.strip()
    df["MOTYPE"] = df["MOTYPE"].str.strip('"').str.strip()
    df["FAMILLE"] = df["FAMILLE"].str.strip('"').str.strip()
    return df[["MOTIF", "LIBELLE", "MOTYPE", "FAMILLE"]].drop_duplicates(subset=["MOTIF"])


@lru_cache(maxsize=8)
def _load_hopcode_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df["ELEMENT"] = df["ELEMENT"].str.strip('"').str.strip()
    df["CODE"] = df["CODE"].astype(str).str.strip('"').str.strip()
    df["LIBCODE"] = df["LIBCODE"].str.strip('"').str.strip()
    return df[["ELEMENT", "CODE", "LIBCODE"]]


@lru_cache(maxsize=8)
def _load_hopmess_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8", dtype=str)
    df = df[df["FONCT"] == "ANO"]
    df["NUMERO"] = df["NUMERO"].str.strip('"').str.strip()
    df["LIBS"] = df["LIBS"].str.strip('"').str.strip()
    return df[["NUMERO", "LIBS"]].drop_duplicates(subset=["NUMERO"])


def load_standard_rule_code(rule_name: str, hopprog_path: str) -> str | None:
    """Return rule code for *rule_name* client code from *hopprog_path* (standard version).

    Applies the same comment-stripping and label-blanking as prepare_inference.
    Returns None if the file is missing or the rule is not found.
    """
    rule_name = f"I{rule_name[1:]}"
    try:
        df = pd.read_csv(hopprog_path, sep=";", dtype=str)
    except FileNotFoundError:
        return None
    df["REGLE"] = df["REGLE"].str.strip('"').str.strip()
    mask = df["REGLE"].str.upper().apply(lambda r: r in rule_name.strip().upper())
    rule_df = df[mask].copy()
    lines = rule_df["INST"]
    return "\n".join(lines) if not rule_df.empty else None


def compute_rule_diff(client_code: str, standard_code: str) -> str:
    """Return a unified diff string (standard → client). Empty string if identical."""
    import difflib
    std_lines = standard_code.splitlines(keepends=True)
    cli_lines = client_code.splitlines(keepends=True)
    diff = list(difflib.unified_diff(std_lines, cli_lines, fromfile="standard", tofile="client", n=2))
    return "".join(diff)


def extract_anomaly_numbers(code: str) -> list[str]:
    """Return anomaly numbers declared in DEBANO blocks (e.g. '114', '115')."""
    numbers: list[str] = []
    in_debano = False
    for line in code.splitlines():
        stripped = line.strip()
        if stripped == "DEBANO":
            in_debano = True
            continue
        if stripped == "FINANO":
            in_debano = False
            continue
        if in_debano and stripped and not stripped.startswith("*"):
            # Format: <number>;<gravity>;"<message>";
            match = re.match(r'^(\d+)\s*;', stripped)
            if match:
                numbers.append(match.group(1).zfill(4))
    return numbers


def build_anomaly_messages_section(code: str, table_paths: TablePaths | None = None) -> str:
    """Return a markdown table of anomaly messages declared in DEBANO blocks.

    Columns: Numéro | Message
    Returns an empty string if hopmess table is missing or no anomalies match.
    """
    numbers = extract_anomaly_numbers(code)
    if not numbers:
        return ""

    paths = table_paths or _DEFAULT_TABLE_PATHS
    try:
        hopmess_df = _load_hopmess_table(paths.hopmess_csv)
    except FileNotFoundError:
        return ""

    matched = hopmess_df[hopmess_df["NUMERO"].isin(numbers)]
    if matched.empty:
        return ""

    return matched.rename(columns={"NUMERO": "Numéro", "LIBS": "Message"}).to_markdown(index=False)


def extract_debdico_variables(code: str) -> list[str]:
    """Return the full variable names (with domain prefix) declared in DEBDICO blocks."""
    variables = []
    in_debdico = False
    for line in code.splitlines():
        stripped = line.strip()
        if stripped == "DEBDICO":
            in_debdico = True
            continue
        if stripped == "FINDICO":
            in_debdico = False
            continue
        if in_debdico and stripped and not stripped.startswith("*"):
            token = stripped.split(";")[0].strip()
            if "_" in token:
                variables.append(token)
    return variables


def extract_all_variables(code: str) -> list[str]:
    """Return all full variable names (with domain prefix) found in *code*.

    Combines:
    - Variables declared in the DEBDICO block.
    - Variables referenced anywhere in the rule body whose domain prefix is
      one of the known HQ Time domains (HJOU, HORC, PARD, …).

    Preserves insertion order (DEBDICO first, then body-only extras).
    """
    debdico = extract_debdico_variables(code)
    debdico_set: set[str] = set(debdico)

    body_vars: dict[str, None] = {}  # preserves insertion order
    for prefix, suffix in _DOMAIN_VAR_RE.findall(code.split("FINDICO", 1)[-1]):
        body_vars[f"{prefix}_{suffix}"] = None

    # DEBDICO vars that are actually referenced in the body (DEBDICO order first),
    # then body-only vars not declared in DEBDICO.
    result: list[str] = []
    seen: set[str] = set()
    for var in debdico:
        if var in body_vars and var not in seen:
            result.append(var)
            seen.add(var)
    for var in body_vars:
        if var not in seen:
            result.append(var)
            seen.add(var)
    return result


def extract_motif_codes(code: str) -> list[str]:
    """Return hardcoded motif codes used in HABS_MOTIF comparisons in the rule body."""
    # Match: HABS_MOTIF = "XDCF" or HABS_MOTIF <> "MISS" etc.
    with_prefix = re.findall(r'HABS_MOTIF\s*(?:=|<>)\s*"([A-Z]{2}[A-Z0-9]*)"', code)
    # Match any comparison without HABS_MOTIF: other_var = "MISS" or <> "MISS" etc.
    without_prefix = re.findall(r'(?:=|<>)\s*"([A-Z]{2}[A-Z0-9]*)"', code)
    return list(dict.fromkeys(with_prefix + without_prefix))


def build_debdico_df(code: str, table_paths: TablePaths | None = None) -> "pd.DataFrame | None":
    """Return the merged ecran+hopdico DataFrame for all variables in *code*.

    Covers both DEBDICO-declared variables and any domain-prefixed variable
    referenced elsewhere in the rule body.
    Returns None if the tables are missing or no variables match.
    This is the single source of truth — call it once and reuse the result.
    """
    full_vars = extract_all_variables(code)
    if not full_vars:
        return None

    var_df = pd.DataFrame({"full": full_vars})
    var_df["Préfixe"] = var_df["full"].apply(lambda x: x.split("_", 1)[0])
    var_df["NOM"] = var_df["full"].apply(lambda x: x.split("_", 1)[1])

    paths = table_paths or _DEFAULT_TABLE_PATHS
    try:
        ecran_df = _load_ecran_table(paths.ecran_csv)
        hopdico_df = _load_hopdico_table(paths.hopdico_csv)
    except FileNotFoundError:
        return None

    matched = hopdico_df[hopdico_df["NOM"].isin(var_df["NOM"])].drop_duplicates(subset=["NOM"])
    if matched.empty:
        return None

    df = matched.merge(var_df[["NOM", "Préfixe"]], on="NOM", how="left")
    # df = df.merge(
    #     ecran_df[["DONNEE", "ECRAN"]], left_on="NOM", right_on="Données", how="left"
    # )[["NOM", "LIBELLE", "TRAIT", "ECRAN", "Préfixe"]].fillna("-")

    df = df.merge(
        ecran_df.drop(columns=['LIBELLE']), left_on=["NOM", "Préfixe"], right_on=["DONNEE", "DOMAINE"], how="left"
    ).drop(columns=['Préfixe'])[["NOM", "LIBELLE", "TRAIT", "ECRAN", "DOMAINE"]].fillna("-")

    df["ECRAN"] = df["ECRAN"].replace("-", "Non affiché")

    df = df.rename(columns={"NOM": "Données", "LIBELLE": "Libellé"})
    _type_map = {"I": "indicateur", "Q": "quotidien", "R": "reporté"}
    df["Type"] = df.apply(
        lambda row: _type_map.get(row["Données"][2], "-")
        if row["TRAIT"].startswith(("C", "V")) else "-",
        axis=1,
    )

    assigned_full = set(re.findall(r'^\s+([A-Z][A-Z0-9]*_[A-Z][A-Z0-9]+)\s*=(?![=<>])', code, re.MULTILINE))
    df["Comment ?"] = df.apply(
        lambda row: (
            "Calculé" if f"{row['DOMAINE']}_{row['Données']}" in assigned_full
            else ("Saisie" if row["Type"] == "indicateur" else "-")
        ) if row["TRAIT"].startswith(("C", "V")) else "-",
        axis=1,
    )
    return df[["Données", "Libellé", "TRAIT", "ECRAN", "DOMAINE", "Type", "Comment ?"]]


def build_debdico_context_table(code: str, table_paths: TablePaths | None = None) -> str:
    """Return a markdown table of DEBDICO variables enriched with screen and code traitement.

    Columns: Données | Libellé | Domaine | ECRAN | Code traitement
    Returns an empty string if the tables are missing or no variables match.
    """
    df = build_debdico_df(code, table_paths)
    if df is None:
        return ""
    return df.to_markdown(index=False)


def _filter_table_by_trait(df: "pd.DataFrame", trait_prefix: str) -> str:
    """Filter a pre-built debdico DataFrame by TRAIT prefix and return a markdown table.

    Columns: Données | Libellé | Domaine | ECRAN
    trait_prefix='C' → constantes (inputs), trait_prefix='V' → variables (outputs).
    Returns an empty string if no rows match.
    """
    filtered = df[df["TRAIT"].str.strip(" ").str.startswith(trait_prefix, na=False)].copy()
    if filtered.empty:
        return ""
    result = filtered[["Données", "Libellé", "DOMAINE", "ECRAN", "Type", "Comment ?"]]
    result = result if trait_prefix.startswith("C") else result.drop(columns=["Comment ?"])
    return result.to_markdown(index=False)


def build_inputs_table(code: str, table_paths: TablePaths | None = None) -> str:
    """Return markdown table of input (TRAIT=C*) variables from DEBDICO."""
    df = build_debdico_df(code, table_paths)
    if df is None:
        return ""
    return _filter_table_by_trait(df, "C")


def build_outputs_table(code: str, table_paths: TablePaths | None = None) -> str:
    """Return markdown table of output (TRAIT=V*) variables from DEBDICO."""
    df = build_debdico_df(code, table_paths)
    if df is None:
        return ""
    return _filter_table_by_trait(df, "V")


def build_hopcode_values_section(code: str, table_paths: TablePaths | None = None) -> str:
    """Return a markdown section listing coded value labels for each matched variable.

    For every variable present in hopcode table, emits a sub-table:
      Variable: <NOM>
      | Code | Libellé |
      |------|---------|
      | 0    | ...     |
    Returns an empty string if hopcode table is missing or no variables have coded values.
    """
    full_vars = extract_all_variables(code)
    if not full_vars:
        return ""

    suffixes = [v.split("_", 1)[1] for v in full_vars]

    paths = table_paths or _DEFAULT_TABLE_PATHS
    try:
        hopcode_df = _load_hopcode_table(paths.hopcode_csv)
    except FileNotFoundError:
        return ""

    relevant = hopcode_df[hopcode_df["ELEMENT"].isin(suffixes)]

    return relevant.set_index("ELEMENT").to_markdown()


def extract_rule_name(code: str) -> str:
    """Extract the rule name from the '* Règle : ...' comment line in DSL code."""
    match = re.search(r'^\*\s*R[èe]gle\s*:\s*(\S+)', code, re.IGNORECASE | re.MULTILINE)
    return match.group(1) if match else ""


def build_motif_context_table(code: str, table_paths: TablePaths | None = None) -> str:
    """Return a markdown table of motif codes referenced in HABS_MOTIF comparisons.

    Columns: Motif | Libellé | Type | Famille
    Returns an empty string if hopmoti table is missing or no motifs match.
    """
    motif_codes = extract_motif_codes(code)
    if not motif_codes:
        return ""

    paths = table_paths or _DEFAULT_TABLE_PATHS
    try:
        hopmoti_df = _load_hopmoti_table(paths.hopmoti_csv)
    except FileNotFoundError:
        return ""

    matched = hopmoti_df[hopmoti_df["MOTIF"].isin(motif_codes)].drop_duplicates(subset=["MOTIF"])
    if matched.empty:
        return ""

    return matched.to_markdown(index=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Lookup DEBDICO variables from a DSL rule file against the screen reference table."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=r"inputs\ICONGF_sans_commentaire.txt",
        help="Path to the DSL rule .txt file (default: inputs\\ICONGF_sans_commentaire.txt)",
    )
    parser.add_argument(
        "--variables-only",
        action="store_true",
        help="Print only the extracted variable names, without the lookup table.",
    )
    parser.add_argument(
        "--test-standard",
        metavar="RULE_NAME",
        default=None,
        help="Test load_standard_rule_code + compute_rule_diff for RULE_NAME against the v15 standard hopprog.",
    )
    args = parser.parse_args()

    # --test-standard: load standard rule code and diff against the client file
    if args.test_standard:
        tp = resolve_table_paths("v15")
        if not tp.standard_hopprog_path:
            print("ERROR: standard hopprog.bdd not found for v15.")
        else:
            print(f"\n--- Standard rule code for '{args.test_standard}' ---")
            std_code = load_standard_rule_code(args.test_standard, tp.standard_hopprog_path)
            if std_code is None:
                print("  Rule not found in standard hopprog.")
            else:
                print(std_code[:2000] + ("..." if len(std_code) > 2000 else ""))

            with open(args.input_file, encoding="utf-8", errors="replace") as f:
                client_code = f.read()

            if std_code is not None:
                diff = compute_rule_diff(client_code, std_code)
                print(f"\n--- Diff (standard → client) ---")
                print(diff if diff.strip() else "  (no differences)")
        print()


        code = f.read()

    variables = extract_all_variables(code)
    print(f"Variables found (DEBDICO + rule body) ({len(variables)}): {variables}\n")

    motifs = extract_motif_codes(code)
    print(f"Motif codes found ({len(motifs)}): {motifs}\n")

    if not args.variables_only:
        debdico_table = build_debdico_context_table(code)
        if debdico_table:
            print("--- Variables DEBDICO ---")
            print(debdico_table)
        else:
            print("No variable matches found.")

        print()
        hopcode_section = build_hopcode_values_section(code)
        if hopcode_section:
            print("--- Valeurs codées des paramètres ---")
            print(hopcode_section)
        else:
            print("No coded values found in hopcode.csv.")

        print()
        motif_table = build_motif_context_table(code)
        if motif_table:
            print("--- Motifs référencés ---")
            print(motif_table)
        else:
            print("No motif matches found.")
