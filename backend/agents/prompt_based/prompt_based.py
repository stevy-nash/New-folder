"""Prompt-based documentation generation approach.

Uses a curated static context (~6K chars) instead of injecting the full knowledge
base (~535K chars). The context contains only what the LLM needs: domain-to-screen
mappings, DSL syntax guide, naming conventions, and business terminology.

A few-shot example from a validated reference document anchors the expected output
style, length, and structure.

Pipeline:  Curated context (static) + few-shot example + code → Markdown documentation
"""
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.agents.config import config, get_openai_token_provider
from backend.agents.prompt_based.curated_context import CURATED_CONTEXT
from backend.agents.prompt_based.get_lookup import (
    TablePaths, resolve_table_paths,
    build_debdico_df, build_hopcode_values_section, build_motif_context_table,
    build_anomaly_messages_section, _filter_table_by_trait, get_rule_status, extract_rule_name,
    load_standard_rule_code, compute_rule_diff,
)

# ---------------------------------------------------------------------------
# System prompt — instructions + DSL reference (placed BEFORE any context)
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
Tu es un expert en documentation fonctionnelle SIRH Horoquartz (HQ Time).
Tu produis des fiches métier concises destinées aux utilisateurs RH non techniques,
à partir de règles de calcul écrites en langage DSL Horoquartz.

Utilise le référentiel ci-dessous pour interpréter correctement le code DSL,
identifier les domaines, les écrans et les libellés officiels des données.

{context}

---

### Règles de production (à respecter strictement)

0. Utilise TOUJOURS des guillemets droits (") dans tout le texte généré.
   N'utilise JAMAIS de guillemets français (« »)

1. Tu génères UNIQUEMENT le contenu narratif de la section
   « 2. Règle de gestion / Règle de calcul ».
   NE génère PAS les sections 1 et 3 (elles sont produites automatiquement).
   NE génère PAS le titre « # 2. Règle de gestion / Règle de calcul ».

2. Longueur cible : 3 à 5 paragraphes courts, 150 à 300 mots au total.
   Chaque paragraphe couvre une étape ou un thème distinct (initialisation,
   calcul quotidien, clôture de période, gestion des cas particuliers…).
   Chaque paragraphe contient 2 à 3 phrases maximum.
   PAS de sous-sections numérotées, PAS de listes à puces.
   Phrases courtes et directes (20 mots maximum par phrase).
   Une idée par phrase. Évite les accumulations de virgules et les
   subordonnées imbriquées.

3. Décris ce que le système fait du point de vue de l'utilisateur RH.
   Pas de pseudo-code, pas de SI/ALORS, pas de références au DSL.
   Exemple correct : "Le système vérifie si le salarié a posé un bloc minimum
   de 12 jours consécutifs entre mai et octobre."
   Exemple incorrect : SI HJOU_IJRNBCOFRA >= LOCA_PLAFOND ALORS …

4. Les noms de variables (HJOU_*, PARD_*, HORC_*, etc.) n'apparaissent
   JAMAIS dans le texte narratif.

5. Lorsqu'une anomalie est mentionnée, tu DOIS obligatoirement inclure son libellé officiel
   entre guillemets droits, suivi de son code entre parenthèses.
   Le libellé est fourni dans la section « 6. ANOMALIES DÉCLENCHÉES PAR LA RÈGLE » du contexte.
   INTERDIT d'écrire uniquement le code sans le libellé si le libellé est disponible dans le contexte.
   Utilise UNIQUEMENT des guillemets droits (") — jamais de guillemets français (« »).
   Format OBLIGATOIRE : une anomalie "<Libellé de l'anomalie>" (XXXX) est déclenchée
   Exemple : une anomalie "Solde repos N-1 négatif" (0202) est déclenchée.
   UNIQUEMENT si le libellé est absent du contexte, écris : une anomalie (XXXX) est déclenchée.

6. Lorsqu'une consigne ou un motif est mentionné, utilise son libellé officiel fourni
   , suivi de son code entre parenthèses.
   Utilise UNIQUEMENT des guillemets droits (") — jamais de guillemets français (« »).
   Format attendu : la consigne "<Libellé de la consigne>" (CODE) est appliquée.
   Exemple : la consigne "Crédit exceptionnel" (XCRE) est appliquée.
   Si le libellé n'est pas disponible, écris uniquement le code entre parenthèses :
   la consigne (XCRE) est appliquée.

7. Français uniquement. Langage métier RH accessible et concis. Utilise UNIQUEMENT des guillemets droits (") — jamais de guillemets français (« »).

Voici un exemple complet du format, du style et de la longueur attendus.
Reproduis ce style pour chaque règle.

<exemple>
Resumé narratif de la règle de calcul, rédigé en français clair, sans aucune référence au code DSL ni à des variables techniques. Le texte doit être fluide et accessible aux professionnels RH, en évitant tout jargon technique ou pseudo-code. Par exemple : "Le système vérifie si le salarié a posé un bloc minimum de 12 jours"
</exemple>
"""

# ---------------------------------------------------------------------------
# Message template — 3 messages: system, context reminder, code
# ---------------------------------------------------------------------------
DOC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human",
     "Génère la documentation fonctionnelle pour la règle suivante.\n\n"
     "```\n{code}\n```"),
])

# ---------------------------------------------------------------------------
# Diff prompt — compares standard vs client rule and produces a summary
# ---------------------------------------------------------------------------
_DIFF_SYSTEM_PROMPT = """\
Tu es un expert en documentation fonctionnelle SIRH Horoquartz.
Tu reçois :
- La version standard de la règle DSL et la version client
- Le diff (unified diff, standard → client)
- La documentation fonctionnelle déjà générée pour la règle client
- Les tables de référence de la règle client (variables, valeurs codées, motifs, anomalies)
Utilise l'ensemble de ces informations pour comprendre les changements dans leur contexte fonctionnel.
Décris en 2 à 4 phrases courtes les modifications apportées, du point de vue fonctionnel RH.

### Règles de formatage (à respecter strictement)

1. Les noms de variables DSL (HJOU_*, PARD_*, HORC_*, etc.) n'apparaissent JAMAIS dans le texte.
   Ne mentionne pas non plus les domaines techniques ni le code source.

2. Lorsqu'une anomalie est mentionnée, tu DOIS obligatoirement inclure son libellé officiel
   entre guillemets droits, suivi de son code entre parenthèses.
   Le libellé est fourni dans la section « Anomalies déclenchées » ci-dessous.
   INTERDIT d'écrire uniquement le code sans le libellé si le libellé est disponible.
   Format OBLIGATOIRE : une anomalie "<Libellé de l'anomalie>" (XXXX) est déclenchée
   Exemple : une anomalie "Solde repos N-1 négatif" (0202) est déclenchée.
   UNIQUEMENT si le libellé est absent, écris : une anomalie (XXXX) est déclenchée.

3. Lorsqu'un motif ou une consigne est mentionné, utilise son libellé officiel entre guillemets
   droits, suivi de son code entre parenthèses.
   Le libellé est fourni dans la section « Motifs référencés » ci-dessous.
   Format OBLIGATOIRE : le motif "<Libellé du motif>" (CODE) est utilisé.
   Exemple : le motif "Télétravail" (TT) est utilisé.

4. Utilise UNIQUEMENT des guillemets droits (") — jamais de guillemets français (« »).

5. Français uniquement. Langage métier RH accessible et concis.
"""

_DIFF_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _DIFF_SYSTEM_PROMPT),
    ("human",
     "### Version standard\n\n```\n{std_code}\n```\n\n"
     "### Version client\n\n```\n{client_code}\n```\n\n"
     "### Diff (standard → client)\n\n```diff\n{diff}\n```\n\n"
     "### Documentation fonctionnelle générée (règle client)\n\n{section2}\n\n"
     "### Données déclarées (DEBDICO)\n\n{debdico_table}\n\n"
     "### Valeurs codées\n\n{hopcode_section}\n\n"
     "### Motifs référencés\n\n{motif_table}\n\n"
     "### Anomalies déclenchées\n\n{anomaly_section}"),
])


def _build_chain():
    _openai_auth = (
        {"azure_ad_token_provider": get_openai_token_provider()}
        if not config.azure_openai_api_key
        else {"api_key": config.azure_openai_api_key}
    )
    llm = AzureChatOpenAI(
        azure_endpoint=config.azure_openai_endpoint,
        api_version=config.azure_openai_api_version,
        azure_deployment=config.azure_openai_deployment,
        **_openai_auth,
    )
    prompt = DOC_PROMPT
    return prompt | llm | StrOutputParser()


def _build_diff_chain():
    _openai_auth = (
        {"azure_ad_token_provider": get_openai_token_provider()}
        if not config.azure_openai_api_key
        else {"api_key": config.azure_openai_api_key}
    )
    llm = AzureChatOpenAI(
        azure_endpoint=config.azure_openai_endpoint,
        api_version=config.azure_openai_api_version,
        azure_deployment=config.azure_openai_deployment,
        **_openai_auth,
    )
    return _DIFF_PROMPT | llm | StrOutputParser()


class PromptBasedApproach:
    """Documentation generator using curated static context + few-shot example."""

    def __init__(self, version: str | None = None, table_paths: TablePaths | None = None):
        self._chain = _build_chain()
        self._diff_chain = _build_diff_chain()
        if table_paths is not None:
            self._table_paths: TablePaths | None = table_paths
            src = "client ZIP"
        else:
            self._table_paths = resolve_table_paths(version) if version else None
            src = f"v15 Sources spécifique" if version == "v15" else (version or "v16.3 standard")
        print(f"[prompt-based] Using curated static context ({len(CURATED_CONTEXT):,} chars). Tables: {src}.")

    def generate_documentation(self, code: str) -> str:
        """Generate Markdown documentation for *code*."""
        tp = self._table_paths
        # Build the merged debdico DataFrame once — reused for context, inputs, and outputs
        debdico_df = build_debdico_df(code, tp)
        debdico_table = debdico_df.to_markdown(index=False) if debdico_df is not None else ""

        hopcode_section = build_hopcode_values_section(code, tp)
        motif_table = build_motif_context_table(code, tp)
        anomaly_section = build_anomaly_messages_section(code, tp)
        context = CURATED_CONTEXT
        if debdico_table:
            context += (
                "\n\n3. DONNÉES DE LA RÈGLE (issues du bloc DEBDICO)\n"
                "-------------------------------------------------\n"
                "Voici les données déclarées dans cette règle, avec leur libellé officiel,\n"
                "leur domaine fonctionnel et l'écran où elles apparaissent :\n\n"
                + debdico_table
                + "\n"
            )
        if hopcode_section:
            context += (
                "\n\n4. VALEURS CODÉES DES PARAMÈTRES\n"
                "--------------------------------\n"
                "Voici les valeurs possibles (codes et libellés) pour les paramètres de cette règle :\n\n"
                + hopcode_section
                + "\n"
            )
        if motif_table:
            context += (
                "\n\n5. MOTIFS RÉFÉRENCÉS DANS LA RÈGLE\n"
                "-----------------------------------\n"
                "Voici les motifs d'absence utilisés dans cette règle :\n\n"
                + motif_table
                + "\n"
            )
        if anomaly_section:
            context += (
                "\n\n6. ANOMALIES DÉCLENCHÉES PAR LA RÈGLE\n"
                "--------------------------------------\n"
                "Voici les messages d'anomalie que cette règle peut déclencher :\n\n"
                + anomaly_section
                + "\n"
            )

        # LLM generates only the section 2 narrative
        section2_text = self._chain.invoke({"code": code, "context": context})

        # Reuse the already-built debdico_df to filter inputs (C) and outputs (V)
        inputs_md = _filter_table_by_trait(debdico_df, "C") if debdico_df is not None else ""
        outputs_md = _filter_table_by_trait(debdico_df, "V") if debdico_df is not None else ""

        rule_name = extract_rule_name(code)

        active_label, compil_label, ordre, libelle = get_rule_status(rule_name, tp) if rule_name else ("", "", "", "")
        status_badges = " et ".join(filter(None, [active_label, compil_label]))

        parts = []
        if rule_name:
            title = f"# {rule_name}"
            if libelle:
                title += f" — {libelle}"
            if ordre:
                title += f" ({ordre})"
            if status_badges:
                title += f" — {status_badges}"
            parts.append(title)
        parts.append("## 1. Éléments en entrée")
        parts.append(inputs_md or "_Aucune donnée en entrée identifiée._")
        parts.append("## 2. Règle de calcul")
        parts.append(section2_text.strip())
                # --- Section 2.1: comparison with standard version (only when a standard exists) ---
        if rule_name and tp and tp.standard_hopprog_path and rule_name.startswith("S"):
            std_code = load_standard_rule_code(rule_name, tp.standard_hopprog_path)
            if std_code is not None:
                diff = compute_rule_diff(code, std_code)
                if diff.strip():
                    comparison_text = self._diff_chain.invoke({
                        "diff": diff,
                        "std_code": std_code,
                        "client_code": code,
                        "section2": section2_text.strip(),
                        "debdico_table": debdico_table or "_Aucune donnée._",
                        "hopcode_section": hopcode_section or "_Aucune valeur codée._",
                        "motif_table": motif_table or "_Aucun motif._",
                        "anomaly_section": anomaly_section or "_Aucune anomalie._",
                    })
                    parts.append("### Modifications par rapport à la version standard")
                    parts.append(comparison_text.strip())
        parts.append("## 3. Éléments en sortie")
        parts.append(outputs_md or "_Aucun compteur en sortie identifié._")

        return "\n\n".join(parts)
