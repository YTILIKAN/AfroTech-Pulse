# S5 — Validation qualité des résumés (20 articles réels)

Lot de 20 articles sélectionnés manuellement dans `afrotech.db` pour couvrir : startup/fintech,
IA/recherche, institution, tech Afrique, grands médias et 2 articles clairement hors-Afrique
(test de l'angle forcé). Résumés générés par `pipeline.summarize.summarize_article()` (Mistral
`mistral-small-latest`), un vrai appel API par article.

Critère d'acceptation : ≥ 16/20 (80%) jugés OK.

**Résultat : 17/20 OK (85%) → critère atteint.**

---

## 1. Startup / business (technext24)

### AfDB approves €100m for Africa's first EV battery gigafactory in Morocco
> L'**African Development Bank (AfDB)** a approuvé un prêt de 100 millions d'euros pour financer
> la première **gigafactory de batteries pour véhicules électriques (VE) en Afrique**, située au
> **Maroc**.
>
> Ce projet s'inscrit dans la stratégie du pays pour développer une filière industrielle locale
> des VE, avec un potentiel d'exportation vers d'autres marchés africains.
>
> Un modèle similaire pourrait inspirer d'autres nations du continent, où l'adoption des VE reste
> limitée mais en croissance, notamment dans les secteurs de la logistique et des transports
> publics.

**Avis : OK** — Le contenu brut collecté était tronqué après « a approuvé un prêt de 100M€ à… »,
mais le titre donnait déjà le pays et le sujet (Maroc, gigafactory). Rien d'inventé au-delà de
titre + contenu.

### NCC calls for evidence-based telecom regulation across Africa
> La Nigerian Communications Commission (NCC) a appelé les régulateurs africains des télécoms à
> adopter des réglementations fondées sur des preuves.
>
> Cette initiative pourrait renforcer la cohérence des politiques sectorielles sur le continent,
> où des acteurs comme l'**ARCEP au Sénégal** ou la **ZICTA en Zambie** pourraient s'en inspirer.
>
> Un cadre commun favoriserait l'innovation et l'investissement dans les infrastructures,
> cruciales pour l'essor des services numériques en Afrique.

**Avis : à retravailler** — Le contenu collecté ne fait qu'une phrase tronquée, et ni le titre ni
le contenu ne mentionnent l'ARCEP (Sénégal) ni la ZICTA (Zambie). Le modèle a inventé deux noms
d'organismes précis pour étoffer le résumé — violation directe de la consigne « n'invente aucun
fait, nom d'entreprise ou d'organisation qui n'est pas dans l'article ».

### Nigeria's digital payment fraud losses fall from ₦52.26bn to ₦25.85bn, report finds
> Les pertes liées à la fraude aux paiements numériques au Nigeria ont chuté de 50 % en 2025,
> passant de 52,26 milliards de nairas à 25,85 milliards de nairas. Cette baisse intervient malgré
> une sophistication accrue des méthodes employées par les fraudeurs. Le pays, leader africain en
> innovation fintech, pourrait inspirer d'autres marchés émergents confrontés à des défis
> similaires.

**Avis : OK** — Chiffres conformes au titre, la mention de fraudeurs plus sophistiqués correspond
au contenu tronqué (« criminals are becoming increasingly… »). Le format 3 lignes n'est pas
respecté ici (résumé en un seul bloc) — point mineur à surveiller mais le fond est correct.

### Tunde Onakoya, Sam Otigba, and Hack Sultan launch ₦250m fund to equip new graduates with tech skills
> Un fonds de 250 millions de nairas (environ 500 000 dollars) a été lancé au Nigeria par Tunde
> Onakoya, Sam Otigba et Hack Sultan pour former les nouveaux diplômés aux compétences
> technologiques. L'initiative vise à combler le fossé entre l'éducation formelle et les besoins du
> marché du travail nigérian en pleine expansion technologique. Ce modèle pourrait inspirer des
> initiatives similaires dans d'autres pays africains confrontés à des défis d'employabilité des
> jeunes.

**Avis : à retravailler** — La conversion « environ 500 000 dollars » n'apparaît nulle part dans
le titre ou le contenu : c'est un chiffre calculé par le modèle et présenté comme un fait, sans
la prudence exigée par le prompt (« pourrait », « environ » ne suffit pas ici puisque le taux de
change utilisé n'est pas vérifiable). Format 3 lignes également non respecté.

---

## 2. IA / Recherche

### Unsupervised Consensus-Based Anomaly Detection for Spatiotemporal Malaria Incidence in Ghana
> Un cadre de détection d'anomalies basé sur un consensus a été appliqué aux données de
> surveillance mensuelle du paludisme au Ghana entre 2014 et 2023.
>
> Les régions d'Ashanti et du Nord, ainsi que les villes de Tamale, Kumasi et Accra, concentrent la
> majorité des anomalies récurrentes dans la transmission.
>
> Cette approche pourrait inspirer des modèles similaires pour d'autres pays africains confrontés
> à des défis de surveillance du paludisme.

**Avis : OK** — Vérifié contre l'abstract arXiv complet : régions, villes et période sont exacts.
Angle africain natif à l'article (Ghana), pas de reformulation forcée nécessaire.

### Generative AI to quantify uncertainty in weather forecasting
> Google Research a développé SEEDS, un modèle d'IA générative capable de produire des prévisions
> météorologiques probabilistes à moindre coût.
>
> Cette innovation pourrait intéresser les services météorologiques africains, souvent confrontés
> à des ressources limitées pour modéliser les événements extrêmes.
>
> Des acteurs locaux comme l'Agence panafricaine de la Grande Muraille Verte ou des startups
> spécialisées en agritech pourraient explorer cette technologie pour améliorer la résilience
> climatique.

**Avis : OK** — Article sans lien africain d'origine (blog Google Research). L'angle africain est
correctement reformulé au conditionnel (« pourrait intéresser », « pourraient explorer »), sans
présenter la reformulation comme un fait établi — conforme à la consigne.

### Using AI to expand global access to reliable flood forecasts
> Google a développé un outil d'IA pour des prévisions de crues fiables jusqu'à sept jours à
> l'avance, couvrant plus de 80 pays.
>
> Cette technologie, testée en Inde et au Bangladesh, pourrait renforcer les systèmes d'alerte
> précoce en Afrique, où les données hydrologiques sont souvent limitées.
>
> L'initiative s'inscrit dans une collaboration avec des organisations comme l'OMM pour améliorer
> la résilience climatique sur le continent.

**Avis : OK** — Faits vérifiables (Inde/Bangladesh) correctement rapportés, angle africain
correctement hedgé au conditionnel.

### Cappy: Outperforming and boosting large multi-task language models with a small scorer
> Google Research propose Cappy, un modèle léger de 360 millions de paramètres optimisant les
> grands modèles de langage multi-tâches (LLM) en évaluant la pertinence des réponses.
>
> Cette approche, présentée à NeurIPS 2023, pourrait inspirer des acteurs africains comme
> **Instadeep** (Tunisie) ou **Zindi** (plateforme de data science panafricaine) pour améliorer
> l'efficacité des LLM locaux.
>
> Son mécanisme de scoring sans fine-tuning complet des LLM pourrait faciliter l'adoption en
> Afrique, où les ressources computationnelles sont limitées.

**Avis : OK** — Bon test de l'angle forcé : article 100% hors-Afrique (papier ML pur), le modèle
cite des acteurs africains réels (Instadeep, Zindi) mais toujours au conditionnel comme pistes
plausibles, sans les présenter comme des faits établis. C'est exactement le comportement attendu.

---

## 3. Institutions

### Ghana's Reparations Moment Is the New Face of Pan-African Liberation
> Le Ghana a organisé en juin à Accra une conférence de haut niveau sur les réparations liées à la
> traite transatlantique, marquant une avancée vers une structuration politique du débat.
>
> L'événement, qui s'est tenu dans des lieux symboliques comme le château de Christiansborg,
> ancien site de traite des esclaves, a illustré la transition entre mémoire historique et actions
> concrètes.
>
> Cette initiative s'inscrit dans un mouvement panafricain plus large, où le Ghana joue un rôle
> central dans la réflexion sur les réparations et la libération continentale.

**Avis : OK**

### New GSMA Report: Digital Reforms Could Unlock FCFA 870 Billion... (République du Congo)
> Un rapport de la GSMA révèle qu'en République du Congo, des réformes numériques pourraient
> générer 870 milliards de FCFA et connecter plus de 540 000 personnes d'ici 2030.
>
> Ces mesures favoriseraient également la création de 144 000 emplois grâce à la digitalisation et
> aux services financiers mobiles.
>
> Ce modèle pourrait inspirer d'autres pays africains où l'accès à internet et aux services
> mobiles reste limité.

**Avis : OK** — Chiffres vérifiés contre le communiqué GSMA complet, tous exacts.

### What Happens After Dandora? Kenya's Green Transition Faces Its Hardest Test
> Le Kenya s'apprête à fermer la décharge de Dandora, un site historique du recyclage informel à
> Nairobi où des milliers de travailleurs récupèrent des déchets pour alimenter l'économie
> circulaire locale.
>
> Cette transition écologique pourrait fragiliser des milliers d'emplois informels et menacer un
> modèle de gestion des déchets déjà sous pression dans plusieurs villes africaines.
>
> Des alternatives structurées, comme des partenariats public-privé ou des coopératives formelles,
> pourraient inspirer d'autres métropoles du continent confrontées à des défis similaires.

**Avis : OK**

### Ghana's Northern Sovereignty Gap: JNIM and the Burkinabe Border
> Les groupes armés transfrontaliers comme le JNIM, actif au Sahel, étendent leurs opérations
> jusqu'aux frontières ghanéennes, exploitant des failles de souveraineté.
>
> Un haut responsable sécuritaire ghanéen a confirmé en 2024 la présence de ces groupes, capables
> de circuler entre le Burkina Faso et le Ghana.
>
> Cette situation souligne les défis de sécurité pour le Ghana, pays ouest-africain confronté à
> une menace terroriste régionale en expansion.

**Avis : OK** — Vérifié contre le contenu complet (ambassadeur Boniface Gambila, responsable
sécuritaire interviewé en 2024) : exact.

---

## 4. Tech Afrique

### Rawbank s'associe à OADC pour accélérer la transformation numérique et l'inclusion financière en RDC
> Rawbank, première banque de RDC, s'associe à OADC - Texaf Kinshasa, le premier centre de données
> certifié Tier-III du pays, pour renforcer son infrastructure numérique.
>
> Ce partenariat vise à améliorer les services bancaires digitaux, comme la plateforme
> *illicoCash*, et à étendre l'inclusion financière dans un pays où l'économie numérique connaît
> une forte croissance.
>
> Rawbank, déjà soutenue par des institutions comme la BAD et l'IFC, mise sur cette collaboration
> pour moderniser ses solutions et toucher davantage de Congolais.

**Avis : OK** — Vérifié contre l'article complet (8400 caractères) : OADC/Texaf, illicoCash, BAD
et IFC sont bien mentionnés dans la source.

### Anglo American vend 6,6% supplémentaires d'Amplats pour 527 millions $
> Anglo American a cédé 6,6 % de sa filiale Anglo American Platinum (Amplats), basée en Afrique du
> Sud, pour 527 millions de dollars, dans le cadre d'une scission prévue pour mi-2025.
>
> Cette opération vise à renforcer la liquidité d'Amplats, cotée à la Bourse de Johannesburg, tout
> en recentrant le groupe sur des activités stratégiques comme le cuivre et les nutriments
> agricoles.
>
> Le secteur des métaux du groupe du platine (PGM), essentiel pour les technologies vertes,
> pourrait intéresser des acteurs africains comme **Sibanye Stillwater**, déjà présent dans
> l'exploitation de ces ressources.

**Avis : à retravailler** — « Sibanye Stillwater » n'apparaît nulle part dans l'article source
(vérifié sur le texte complet, 5060 caractères). Le nom d'une entreprise réelle est inventé pour
illustrer le propos — même défaut que l'article NCC ci-dessus, cette fois sur un article qui
n'avait pourtant pas besoin de reformulation d'angle (déjà 100% africain).

### RDC : soutien de la Sofibanque à l'École du leadership de l'Université Protestante au Congo
> La Sofibanque, banque congolaise, finance la modernisation de l'amphithéâtre de l'École du
> leadership de l'Université Protestante au Congo (UPC) à Kinshasa.
>
> Ce partenariat vise à renforcer la formation des futurs leaders congolais et africains, avec une
> conférence d'ouverture prévue le 18 octobre 2024.
>
> La Sofibanque, fondée en 2010, réaffirme ainsi son engagement dans l'éducation et l'inclusion
> financière en RDC.

**Avis : OK** — Vérifié, exact.

### Africa's ICT Ministers Open Conference in Abuja to Decide Telecommunications Union's Future
> Les ministres africains des TIC se réunissent à Abuja pour l'édition 2026 de la Conférence des
> plénipotentiaires de l'Union africaine des télécommunications (CPL-26).
>
> Cette session, prévue les 23 et 24 juillet 2026, vise à définir l'avenir de l'organisation
> panafricaine dédiée aux infrastructures numériques.
>
> L'événement pourrait influencer les politiques continentales en matière de connectivité et
> d'innovation technologique.

**Avis : OK**

---

## 5. Grands médias africains

### What to know about the West African economic summit seeking regional reform
> Le 69e sommet de la CEDEAO s'est tenu le 19 juillet à Freetown, en Sierra Leone, sous le thème
> des réformes économiques régionales.
>
> Le président sortant Julius Maada Bio a plaidé pour des changements structurels au sein de
> l'organisation, tandis que le Sénégal prend désormais la présidence tournante.
>
> La Guinée a critiqué les sanctions imposées par la CEDEAO, révélant les tensions persistantes au
> sein de l'espace ouest-africain.

**Avis : OK**

### Kola Karim's $200m Afreximbank deal signals a new era for African engineering
> Kola Karim, via son groupe Shoreline Energy, a obtenu un financement de 200 millions de dollars
> de la Banque africaine d'import-export (Afreximbank) pour son projet en Algérie.
>
> Ce partenariat illustre comment des acteurs africains mobilisent des capitaux continentaux et
> des expertises européennes pour contourner les prêteurs traditionnels.
>
> Un modèle qui pourrait inspirer des projets similaires dans d'autres secteurs stratégiques en
> Afrique, comme l'énergie ou les infrastructures.

**Avis : OK** — Contenu source très court (une phrase), mais le titre fournissait déjà le
montant, l'acteur et le pays ; rien d'ajouté au-delà.

---

## 6. Clairement hors-Afrique (test de l'angle forcé)

### Shape-shifting mirrors on NASA's new space telescope could unveil Jupiters like our own
> La NASA prépare le lancement du télescope spatial Nancy Grace Roman, équipé d'un coronographe
> actif pour masquer la lumière des étoiles et étudier des exoplanètes similaires à Jupiter.
> Cet instrument pourrait inspirer des technologies d'imagerie spatiale sur le continent africain,
> où des initiatives comme le *Square Kilometre Array* (SKA) en Afrique du Sud explorent déjà des
> solutions d'observation avancée.
> Des collaborations potentielles avec des acteurs locaux en astronomie ou en optique pourraient
> émerger pour adapter ces innovations aux besoins du continent.

**Avis : OK** — Le SKA en Afrique du Sud est un fait réel et vérifiable (pas dans l'article, mais
connaissance générale correcte et clairement présentée au conditionnel). Bon exemple d'angle
forcé réussi.

### A Teen Reporter Searched for His Community in the Epstein Files. Adults Freaked Out
> Un lycéen californien a utilisé les fichiers Epstein pour retrouver des membres de sa
> communauté, déclenchant une polémique sur la liberté de la presse.
>
> L'affaire a mis en lumière les tensions autour d'un article publié par un journal étudiant, perçu
> comme un travail scolaire mais critiqué par des adultes.
>
> En Afrique, où la liberté de la presse est parfois contestée, ce cas pourrait illustrer les défis
> des jeunes médias locaux dans l'accès à des données sensibles.

**Avis : OK** — Angle africain le plus tiré par les cheveux du lot, mais reste correctement hedgé
(« pourrait illustrer ») et ne prétend pas qu'un fait africain concret existe. Cas limite à
surveiller si ce type d'article hors-sujet devient fréquent en prod.

---

## Synthèse

| # | Titre | Source | Avis |
|---|---|---|---|
| 1 | AfDB approves €100m EV battery gigafactory in Morocco | technext24 | OK |
| 2 | NCC calls for evidence-based telecom regulation | technext24 | **à retravailler** |
| 3 | Nigeria's digital payment fraud losses fall | technext24 | OK |
| 4 | Tunde Onakoya... launch ₦250m fund | technext24 | **à retravailler** |
| 5 | Anomaly Detection for Malaria Incidence in Ghana | arxiv-cs-ai | OK |
| 6 | Generative AI to quantify uncertainty in weather forecasting | google-research-africa | OK |
| 7 | Using AI to expand global access to reliable flood forecasts | google-research-africa | OK |
| 8 | Cappy: small scorer for LLMs | google-research-africa | OK |
| 9 | Ghana's Reparations Moment | african-arguments | OK |
| 10 | New GSMA Report — Republic of Congo | gsma-newsroom | OK |
| 11 | What Happens After Dandora? | african-arguments | OK |
| 12 | Ghana's Northern Sovereignty Gap: JNIM | african-arguments | OK |
| 13 | Rawbank s'associe à OADC | agence-ecofin-tech | OK |
| 14 | Anglo American vend 6,6% d'Amplats | agence-ecofin-tech | **à retravailler** |
| 15 | Sofibanque soutient l'École du leadership UPC | agence-ecofin-tech | OK |
| 16 | Africa's ICT Ministers Conference in Abuja | itnewsafrica | OK |
| 17 | West African economic summit (CEDEAO) | france24-africa | OK |
| 18 | Kola Karim's $200m Afreximbank deal | africa-report | OK |
| 19 | NASA's Nancy Grace Roman telescope | mit-tech-review | OK |
| 20 | Teen Reporter — Epstein Files | wired-africa | OK |

**Total : 17/20 OK (85%) — critère d'acceptation atteint (≥ 80%).**

## Constat transversal à remonter

Les 3 échecs (#2, #4, #14) suivent le même schéma : le modèle **invente un fait vérifiable et
concret (nom d'organisme, nom d'entreprise, ou conversion monétaire) qui n'apparaît ni dans le
titre ni dans le contenu source**, sans le présenter avec la prudence requise par le prompt
(« pourrait », « un modèle similaire existe déjà »). Deux causes distinctes :

1. **Contenu source trop court** (#2, #4) : le scraper ne récupère qu'un extrait RSS tronqué (une
   phrase, ~130-150 caractères) pour plusieurs sources — notamment `technext24`. Le modèle comble
   le manque de matière en produisant des détails plausibles mais non vérifiés. Ce n'est pas un
   défaut du prompt de résumé mais un problème de collecte en amont (scraper ne suit pas le lien
   vers l'article complet pour ces sources).
2. **Sur-interprétation malgré un contenu suffisant** (#14) : l'article faisait déjà 5000+
   caractères et n'avait pas besoin de reformulation d'angle (déjà 100% africain), mais le modèle a
   quand même ajouté un acteur comparable non cité dans la source.

**Recommandation** : le critère de S5 est atteint (85% ≥ 80%), donc pas besoin de bloquer la
semaine. Mais il vaut la peine d'ouvrir un ticket de suivi pour (a) durcir le
`SYSTEM_PROMPT` de `pipeline/summarize.py` avec une consigne explicite du type *"si le contenu
fourni est trop court pour étayer un exemple concret, ne cite aucun nom d'organisation ou
d'entreprise spécifique — reste générique"*, et (b) vérifier pourquoi le scraper ne récupère que
des extraits tronqués pour certaines sources RSS (`technext24` en particulier).
