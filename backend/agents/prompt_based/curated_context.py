"""Curated static context for the prompt-based documentation generator.

This replaces the full 535K knowledge base injection with a ~6K char
condensed reference containing only what the LLM needs to produce
accurate HR-facing documentation from DSL rules.
"""

CURATED_CONTEXT = r"""
=== RÉFÉRENTIEL HQ TIME — CONTEXTE POUR DOCUMENTATION FONCTIONNELLE ===

1. DOMAINES ET ÉCRANS ASSOCIÉS
-------------------------------
Les domaines correspondent aux tables de la base eTemptation. Chaque variable
dans une règle DSL est préfixée par son domaine (ex: HJOU_IJRDCOFRAC).

Domaines principaux et leurs écrans dans l'application :

| Domaine | Description                          | Fonction    | Écran dans l'application                        | Modifiable par règle |
|---------|--------------------------------------|-------------|--------------------------------------------------|----------------------|
| HJOU    | Informations journalières employé    | JOU         | Corrections journalières (onglets personnalisés) | Oui (lecture/écriture)|
| HORC    | Code horaire                         | HOR         | Code horaire (onglets personnalisés)             | Non (lecture seule)  |
| PARD    | Paramètres datés                     | CFG         | Configuration générale – Données globales datées | Non (lecture seule)  |
| CONF    | Constantes globales                  | CFG         | Configuration générale – Données globales        | Non (lecture seule)  |
| EMPL    | Informations générales employé       | EMP         | Fiche individuelle employé                       | Oui (lecture/écriture)|
| PROF    | Définition des profils horaires      | PRO         | Profil horaire                                   | Non (lecture seule)  |
| MOTI    | Définition des activités/consignes   | ACT         | Activités et consignes                           | Non (lecture seule)  |
| TEMP    | Données temporaires                  | (aucun)     | Non visible — calculs intermédiaires uniquement  | Oui (lecture/écriture)|
| CTRA    | Période d'emploi                     | CTR         | Contrats individuels                             | Oui (lecture/écriture)|
| SECH    | Section                              | SEH         | Sections                                         | Non (lecture seule)  |
| HABS    | Historique des activités             | (aucun)     | Accessible uniquement dans POUR ACTIVITES        | Non (lecture seule)  |
| CADM    | Contrat administratif                | (aucun)     | Contrats administratifs                          | Non (lecture seule)  |

Note : HJOU est le domaine le plus utilisé. Ses données sont historisées (une valeur par jour).
EMPL n'est pas historisé (une seule valeur courante).
TEMP contient des données non historisées et non visualisables.

Sous-écrans courants de la fonction JOU (Corrections journalières) :
- Congés : compteurs de droit, pris, solde pour CP, fractionnement, ancienneté, etc.
- Compteurs hebdomadaires / périodiques / annuels
- Présence et temps de travail
- Heures supplémentaires

2. CONVENTION DE NOMMAGE DES DONNÉES
--------------------------------------
Le nom d'une donnée fait 2 à 10 caractères, préfixé par le domaine.
Les 3 premiers caractères après le préfixe de domaine suivent une norme :

1er caractère — Nature :
  I = donnée industrielle (standard package)
  S = donnée spécifique (client)

2ème caractère — Domaine :
  J = HJOU, H = HORC, D = PARD, E = EMPL, T = TEMP, G = CONF,
  P = PROF, A = CADM, C = CTRA, S = SECH, M = MOTI

3ème caractère — Type :
  R = reporté (cumul sur période)
  Q = quotidien (remis à zéro chaque jour)
  G = glissant
  I = indicateur (constante)

Exemple : HJOU_IJRDCOFRAC
  → HJ = domaine HJOU, I = industrielle, J = HJOU, R = reporté
  → DCOFRAC = abréviation de "Droit congé fractionnement"

3. SYNTAXE DSL — GUIDE DE LECTURE
-----------------------------------
Le code est une règle de calcul HQ Time en langage DSL Horoquartz.

Structure d'une règle :
  - En-tête avec commentaires (* en début de ligne)
  - DEBDICO … FINDICO : dictionnaire des données utilisées.
    Chaque ligne déclare une variable :
    DOMAINE_NOM;modifiable;type+longueur;format;min;max;filtre;contrôle;report;code_traitement;"Libellé";
    Le libellé entre guillemets est le libellé officiel de la donnée.
  - DEF LOCA_xxx : déclaration de variable locale (interne au calcul, invisible utilisateur)
  - Corps de la règle : instructions de calcul

Instructions principales :
  SI condition          → début de condition
  OU condition          → condition alternative (suit immédiatement un SI ou un autre OU)
  SINON                 → branche alternative
  FINSI                 → fin de condition
  POUR ACTIVITES        → boucle sur les activités/motifs de la journée
  FINPOUR               → fin de boucle
  LIREVALPRE p1 p2      → lire la valeur de p2 à J-1 (veille) dans p1
  ANOMALIE N            → déclencher une alerte métier numéro N

Opérateurs : = (affectation), +, -, *, /, % (modulo)
Comparaisons : =, <>, <, >, <=, >=

Variables d'activité (accessibles dans POUR ACTIVITES) :
  HABS_MOTIF    → code du motif d'absence/présence
  HABS_VALORIS  → valorisation : "J" (journée), "M" (matin), "A" (après-midi), "H" (heures), "N" (nombre)
  HABS_MOTYPE   → type du motif : "A" (absence), "P" (présence), "C" (consigne)
  HABS_MOTINBR  → valeur numérique associée au motif (pour consignes de forçage)

Données de date :
  HJOU_DATE     → date du jour au format AAAAMMJJ
  HJOU_DATE(1:4) → année, HJOU_DATE(5:4) → MMJJ
  HJOU_JOUR     → jour de la semaine : "1" = lundi … "6" = samedi, "7" = dimanche

Comment déterminer entrées vs sorties :
  - Une variable lue mais jamais affectée (à gauche de =) est une ENTRÉE
  - Une variable affectée (à gauche de =) est une SORTIE
  - LOCA_* et TEMP_* sont des variables internes, pas des entrées/sorties utilisateur
  - PARD_* et HORC_* sont toujours des entrées (lecture seule par les règles)

4. CONSIGNES DE GESTION
-------------------------
Les consignes sont des motifs spéciaux utilisés pour ajuster manuellement les compteurs.
Convention de nommage des consignes :
  X… = mise à jour (ajout d'une valeur)
  Z… = initialisation (remplacement de la valeur)
  Y… = transfert (déplacement entre compteurs, ex: vers CET)

Exemples courants :
  XDCF / ZDCF → mise à jour / initialisation du droit congé fractionnement
  XCCF / ZCCF → mise à jour / initialisation du pris congé fractionnement
  YCFCET      → transfert congé fractionnement vers CET (Compte Épargne-Temps)
  XJOU / ZJOU → forçage des heures totales
  XEFF / ZEFF → forçage des heures effectives

5. RÉSUMÉ DES SOURCES DE LA BASE DE CONNAISSANCE
---------------------------------------------------
La base de connaissance provient de 4 documents. Voici ce que chacun apporte
pour la génération de documentation fonctionnelle à partir de règles DSL.

a) Documentation eTAide.pdf — Référence complète du langage DSL
   Définit toute la syntaxe : SI/FINSI, POUR ACTIVITES/FINPOUR,
   DEBDICO/FINDICO, LIREVALPRE, DATDIFF, DATAJT, AJOUTER/ENLEVER,
   ANOMALIE, PLAGE, ANALYSE, conversions (<<, CONVTPS), et toutes les
   variantes de boucle (POUR POINTAGES, POUR PERIODES, POUR CONTRATS,
   POUR ENFANTS, etc.). Documente la structure du dictionnaire de données
   (type, format, longueur, code traitement), les niveaux de règle
   (niveau 2 = badgeuse 2000-2999, niveau 3 = cumuls 3000-9999) et les
   variables système TEMP (TEMP_NXJOUR, TEMP_DATPRE, TEMP_DATSUI, etc.).
   → Utiliser pour : interpréter les instructions DSL, comprendre le
   rôle de chaque mot-clé, et décoder les préfixes de domaine.

   Contenu condensé — Instructions DSL complémentaires :
   - DEBDICO … FINDICO : déclare les données en début de règle.
     Syntaxe par ligne :
     DOMAINE_NOM;modifiable(O/N);type+longueur,décimales;format(I/L/X);
       min;max;filtre;contrôle;report;code_traitement;"Libellé";
     Exemple : HJOU_SJRTPSM;N;T6,2;I;;;789;SJRTPSM;V3;"Temps mensuel";
   - DEBANO … FINANO : déclare des anomalies en début de règle.
     Syntaxe : Numéro;gravité;"Libellé du message";
   - DATDIFF Date1 Heure1 Date2 Heure2 [Unité] [Calendrier]
     → calcule écart entre 2 dates. Résultats dans TEMP_NXJOUR,
       TEMP_NXHEURE, TEMP_NXSEMAIN, TEMP_NXMOIS, TEMP_NXANNEE.
     Unité : "O" = jours ouvrés, "S" = jours ouvrables.
   - DATAJT Date Heure Type Valeur [Unité] [Calendrier]
     → ajoute une durée à une date. Résultat dans TEMP_DXFINPER.
     Type : "H" heures, "J" jours, "S" semaines, "M" mois, "A" années.
   - CONVTPS param1 [param2] : convertit heure alphanumérique (HHMM)
     en temps. Résultat dans TEMP_HREDEB, TEMP_HREFIN, TEMP_HIPRE.
   - Oper1 << Oper2 : conversion type A/Z/D → N (ou inverse).
   - AJOUTER Motif Valoris Durée [Hdeb] [Hfin] : ajoute un motif.
     Toujours précéder d'un ENLEVER pour éviter les doublons au recalcul.
   - ENLEVER Motif [Valoris] : supprime un motif. Interdit dans POUR ACTIVITES.
   - ANOMALIE N / SUPANOM N : génère / supprime une anomalie numéro N.
   - PLAGE Code [rang] [type_valeur] : recherche une plage dans le profil
     horaire. Résultat dans TEMP_TYPPLA, TEMP_HREDEB, TEMP_HREFIN, etc.
   - ANALYSE Heure1 Heure2 / ANALYSE_R Heure1 Heure2 : analyse présence
     sur une tranche horaire. Résultat dans TEMP_HIPRE (présence),
     TEMP_HIABS (absence), TEMP_HIPOIN (nb badgeages dans l'intervalle).
     Uniquement dans règles niveau 2.
   - CALENDRIER "code" : teste si la date appartient à un calendrier.
     Résultat dans TEMP_CALEND, TEMP_CALENDPRE, TEMP_CALENDSUI.
   - PROC nom … FINPROC : définit une procédure (en fin de règle, après FIN).
     FAIRE nom : appelle la procédure.
   - Niveaux de règle :
     Niveau 2 (2000-2999) : calculs liés aux badgeages. Variables de
       niveau 2 modifiables. Exécuté uniquement si badgeage modifié.
     Niveau 3+ (3000-9999) : compteurs de cumul, motifs, activités.
       Variables de niveau 2 testables mais non modifiables.
   - Variables système TEMP auto-alimentées :
     TEMP_DATJOU = date du jour, TEMP_DATPRE = date précédente,
     TEMP_DATSUI = date suivante, TEMP_NXACT = nombre d'activités,
     TEMP_NXPOIN = nombre de badgeages, TEMP_NXPER = nombre de périodes.

b) HQA_Personnalisation.pptx — Formation à la personnalisation
   Présentation didactique couvrant dictionnaire (DIC), écrans (PER) et
   programmation de règles (PRG) avec exercices pratiques (tickets
   restaurant, repos 11h). Fournit les tables de capacité par écran
   (HODABS2→ABS, HODACTx→ACT, HODCTRx→CTR) et détaille champ par champ
   le dictionnaire (type, longueur, décimales, format interne, code
   traitement, report, contrôle liste/index/coche).
   → Utiliser pour : associer un domaine à son écran d'affichage
   (colonne « Ecran » des tableaux de sortie).

   Contenu condensé — Table des écrans personnalisables :
   Fonction → Domaine → Nom des écrans (capacité en caractères)
   ABS (Saisie absences)       → 500 car, 1 écran  : HODABS2
   ACT (Activités/consignes)   → 900 car, 10 écrans : HODACTx (x=1-9,A)
   CFG (Configuration générale)→ 6000 car, 11 écrans : HODPARx
     (HODPAR1 = données globales, autres = données globales datées)
   CTR (Contrats individuels)  → 3000 car, 20 écrans : HODCTRx + HODADMx
   DIJ (Détail individuel jour) → 500 car, 1 écran  : HODDIJ1
   EMP (Fiche individuelle)    → 4500 car, 21 écrans : HODEMPPx
   HOR (Code horaire)          → 1500 car, 10 écrans : HODHORx
   JOU (Corrections journal.)  → 6000 car, 37 écrans : HODJOUBPx + HODJOUHPx
   PRO (Profil horaire)        → 1500 car, 10 écrans : HODPROx
   SEH (Sections)              → 3000 car, 10 écrans : HODSEHx
   Note : JOU est associé au domaine HJOU mais peut afficher des données
   EMPL (compteurs prévisionnels). CFG affiche CONF et PARD.

c) LES ETAPES DE LA PERSONNALISATION.docx — Guide procédural
   Guide étape par étape du cycle de personnalisation. Contient la
   matrice d'accessibilité des domaines la plus complète : domaines en
   lecture/écriture (HJOU, EMPL, CTRA, TEMP) vs lecture seule (CONF,
   PROF, MOTI, SECH) vs non accessibles (AFFE, BESN, PERS). Détaille
   le comportement de report (RAZ si non paramétré), les compteurs
   glissants (durée, base, opération), et les boucles POUR POINTAGES.
   → Utiliser pour : déterminer si une variable est entrée (lecture
   seule / paramètre) ou sortie (calculée par la règle), et comprendre
   la logique de réinitialisation des compteurs.

   Contenu condensé — Matrice d'accessibilité des domaines :
   NON MODIFIABLES, NON ACCESSIBLES par règles :
     ATTR, CYCL, HMAT, QUAR
   NON MODIFIABLES, ACCESSIBLES (lecture seule) par règles :
     ACTI, CPTG, CRPL, EMPS, ENFT, EVEN, HABS, HCTR, MPEN,
     POIN, PRES, TAUX, WABS, ZEVE
   NON MODIFIABLES par DIC, ACCESSIBLES et MODIFIABLES par règles :
     HPEN (exposition pénibilité)
   MODIFIABLES par DIC, NON ACCESSIBLES par règles :
     AFFE, BESN, DISP, EVNT, EVOC, PERS, PROJ, RESS, STRU
   MODIFIABLES par DIC, ACCESSIBLES en LECTURE SEULE par règles :
     CADM, CONF, HORC, MOTI, PARD, POST, PROF, PSTE, SECH
   MODIFIABLES par DIC, ACCESSIBLES et MODIFIABLES par règles :
     HJOU, EMPL, CTRA, TEMP

   Code traitement (détermine la modifiabilité) :
   - Valeur système (*n) : données noyau, non modifiables.
   - Constante (Cn) : testable en règle, non modifiable sauf si n=0.
   - Variable (Vn) : testable et modifiable par règle.
     Autorisé uniquement pour HJOU, EMPL, CTRA, TEMP.
   - Compteur glissant : testable mais non modifiable par règle.

   Report : à l'ouverture de journée, toutes les variables sont
   remises à 0 SAUF si un report est défini (dans ce cas, la variable
   reprend la valeur de la donnée reportée). Tous les compteurs
   cumulés se reportent sur eux-mêmes.

d) Package PRIVE V16.3.docx — Spécifications fonctionnelles métier
   Description thème par thème de toute la logique métier du package
   standard : calcul du temps (présence, heures totales/effectives/
   payées, écrêtage), HS/HC (seuils, taux), RTT (acquisition,
   abattement, consommation, transfert CET), CP (acquisition légale/
   mensuelle, bascule, chaînage, reliquats), fractionnement, ancienneté,
   forfait jours, annualisation, crédit/débit, télétravail, astreintes,
   CET, mandats CSE, contraintes légales (repos 11h, amplitude).
   Pour chaque thème : paramètres CFG/PRO/ACT, noms de compteurs
   (ex: IJQTT, IJRPLFAFJ), codes d'anomalie (0130, 0132, 0135) et
   codes de consigne (XCRH/ZCRH, XNUI/ZNUI) avec leur signification.
   → Utiliser pour : traduire un compteur ou une consigne en description
   métier RH (ex: IJRPLFAFJ = « plafond annuel forfait jours »),
   identifier les conditions déclencheuses, et rédiger la section
   « Règle de gestion » en langage utilisateur.

   Contenu condensé — Compteurs, consignes et anomalies par thème :

   TEMPS DE TRAVAIL (compteurs journaliers) :
   - Présence badgée = somme entrées/sorties validées (RAZ quotidienne)
   - Présence badgée validée = présence badgée – pauses + écarts plages
   - Heures totales = présence validée + activités créditées ± pauses
     Consignes : XJOU/ZJOU. Anomalies : 0116 (>max), 0117 (<min)
   - Heures effectives = présence validée + motifs « travail effectif »
     Consignes : XEFF/ZEFF. Non calculé dans le futur.
   - Heures payées = présence validée + motifs participant aux HS/HC
     Consignes : XHPA/ZHPA

   CRÉDIT/DÉBIT (horaire variable) :
   - C/D jour = heures totales – théorie du jour
   - C/D cumulé = cumul quotidien du C/D jour sur la période
   - C/D permanent = bascule du C/D cumulé en fin de période
     Consignes : XCRE/ZCRE
     Anomalies : 0104 (écrêtage C/D jour), 0108 (débit < min),
       0109 (crédit > max), 0112/0113 (limitation permanent)

   HEURES SUPPLÉMENTAIRES / COMPLÉMENTAIRES (HS/HC) :
   - HS = temps complets, HC = temps partiels
   - Seuils/taux dans CFG ou HOR (HOR prioritaire)
   - Calcul en fin de période : heures payées vs seuils → HS taux 1/2
   - HC : seuil 1 = théorie période, seuil 2 = théorie + 10%
     Consignes : ZPAY, Z25P, Z50P, Z25R, Z50R, ZHCP, ZCOP, XCOP,
       ZCOP2, XCOP2, ZCOR, XCOR, ZCOR2, XCOR2
     Transfert : YHSREC (payées→récup), YHSPAY (récup→payées)
     Anomalies : 0225 (max HC atteint), 0171 (dépassement horaire TP)
   - Cumul annuel : ZCHS/XCHS (payées), ZRHA/XRHA (récupérées)
   - Solde récup HS/HC : ZRHS/XRHS. Anomalie 0226 (solde insuffisant)

   COR (Compensation Obligatoire de Repos) :
   - Acquisition : chaque dimanche si cumul HS > contingent annuel
     ≤20 salariés : 30min/HS, >20 salariés : 1h/HS
   - Consignes : ZARC (acquis), XSRC/ZSRC (solde)

   CONTRAINTES LÉGALES :
   - 0130 : durée hebdo > maximum. 0131 : moyenne 12 sem > légal
   - 0132 : repos quotidien < 11h. 0133 : amplitude jour > max
   - 0159 : > 6 jours consécutifs. 0161/0162 : pause obligatoire
   - 0180 : minimum temps partiel non respecté
   - 0183 : repos hebdomadaire (35h) non respecté

   PAUSES :
   - Pause badgée : motif PA, PLAGE dans profil, comparaison au seuil
     Anomalies : 0140/0153 (retrait complément), 0141/0154 (crédit),
       0142/0152 (absence de badgeage pause)
   - Pause forfaitaire : déduite/ajoutée selon paramètre (0-3)
     0138/0150 (retrait), 0139/0151 (crédit)

   RETARDS :
   - Seuil de tolérance + type de contrôle dans PRO
     Type 1 = temps total absence plages obligatoires
     Type 2 = temps de retard + nombre de retards
   - Consigne : ZABS (forçage total absence plage)

   RTT :
   - Acquisition : en heures ou en jours selon paramétrage
   - Abattement : réduction du droit en fonction des absences
   - Consommation : motif paramétrable dans CFG
   - Transfert CET : consignes YRTTCET
   - Consignes : XRTT/ZRTT (droit), XPRT/ZPRT (pris)

   CONGÉS PAYÉS (CP) :
   - Acquisition légale : 2.5 j ouvrables (ou 2.08 j ouvrés) / mois
   - Période de référence : 1er juin → 31 mai (sauf convention)
   - Bascule : transfert acquis → principal à la date de bascule
   - Chaînage : CP principal → CP ancienneté → CP supplémentaire
   - Compteurs prévisionnels : solde à fin de période N et N+1
   - Consignes type : XDCP/ZDCP (droit), XCCP/ZCCP (pris),
     YCPCET (transfert vers CET)

   CONGÉ FRACTIONNEMENT :
   - Vérifie bloc ≥12 j ouvrables (10 ouvrés) posé entre mai-octobre
   - Calcule reliquat 5ème semaine → attribution 0, 1 ou 2 jours
   - Exécution au 1er novembre, RAZ annuelle
   - Consignes : XDCF/ZDCF (droit), XCCF/ZCCF (pris), YCFCET

   ANNUALISATION EN JOURS (FORFAIT JOURS) :
   - Population : forfait jour badgeant, déclarant, conforme théorie
   - IJRPLFAFJ = plafond annuel forfait jours
   - IJRJTEAFJ = nb jours travail effectif
   - IJRJEAAFJ = nb jours travail effectif assimilé
   - IJRSCTFJ = écart plafond (plafond – jours effectifs)

   CET (Compte Épargne-Temps) :
   - Alimentation par transfert (consignes Y…CET)
   - Consommation par motif paramétrable

   MANDATS SOCIAUX (CSE) :
   - Droit en heures ou en jours, période traitement paramétrable
   - Mutualisation du crédit d'heures entre élus
   - Consignes de consommation spécifiques

   PRÉPAIE — PRIMES ET MAJORATIONS :
   - Prime de jour, panier jour, prime de nuit, panier nuit
   - Heures majorées : nuit, dimanche, samedi, férié
   - Ticket restaurant : attribution sur journée, matin, ou demi-journée

   COLLECTE DE LA PRÉSENCE :
   - Badgeant : séquence plages interdite/autorisée/obligatoire
     Anomalies : 0103 (absent sans justif), 0106 (badgeages insuffisants),
       0125/0126 (absent matin/AM sans justif), 0118/0119/0120 (badgeage
       pour absent), 0127 (badgeage pour non-badgeant)
   - Conforme théorie : pas de badgeage, présence = théorie profil
   - Déclarant : Self-Service, consigne XPRES (jour/demi-journée)

6. THÉMATIQUES MÉTIER DU PACKAGE PRIVÉ V16.3
----------------------------------------------
Le package Privé V16.3 couvre les thématiques suivantes :
- Collecte de la présence (badgeage, conforme à la théorie, déclaratif)
- Calcul du temps de travail (présence badgée, heures totales, effectives, payées)
- Coupure déjeuner et gestion des pauses
- Gestion des retards
- Horaire variable (Crédit/Débit)
- Heures supplémentaires et complémentaires (HS/HC)
- Compensation obligatoire de repos (COR)
- Gestion des RTT (acquisition, abattement, consommation, transfert)
- Gestion du télétravail
- Congés ancienneté (acquisition, consommation)
- Congés payés (acquisition, bascule, consommation, chaînage, transfert CET)
- Congé fractionnement (acquisition, consommation, transfert CET)
- Congé supplémentaire, congé enfant malade
- Gestion de la maternité
- Annualisation (en heures, en jours / forfait jours)
- Gestion des astreintes
- Compte épargne-temps (CET)
- Don d'absence
- Mandats sociaux (CSE, délégué syndical)

Vocabulaire métier clé :
- Jours ouvrables = lundi à samedi (6 jours/semaine)
- Jours ouvrés = lundi à vendredi (5 jours/semaine)
- Forfait jours = salarié dont le temps de travail est décompté en jours, pas en heures
- CET = Compte Épargne-Temps
- CP = Congés Payés
- 5ème semaine = jours de CP au-delà de 4 semaines (au-delà de 24 ouvrables ou 20 ouvrés)
- Période de référence CP = du 1er juin au 31 mai (sauf convention contraire)
- Date de bascule = date à laquelle les compteurs CP sont transférés (acquis → principal)
"""
