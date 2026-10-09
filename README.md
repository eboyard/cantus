# Présentations de chants

Le script crée un fichier PowerPoint (`.pptx`) au format paysage 16:9, avec
des paroles blanches centrées sur fond bleu nuit (`#000040`), en police
Comic Sans MS, comme dans `diaporamas/messe-2026-rameaux.pptx`.
Chaque ligne contenant uniquement
`---` (avec éventuellement des espaces) commence une nouvelle diapositive.
Les parties vides sont ignorées et les retours à la ligne sont conservés.

Pour identifier un refrain, placer `<!-- refrain -->` sur une ligne au début
de son bloc. Le script conserve ce bloc à sa position dans le fichier et le
répète entre chaque paire de couplets successifs. Un bloc sans marque est
considéré comme un couplet ; `<!-- couplet -->` est aussi accepté.

Un pont peut être identifié par `<!-- pont -->` : il reste à sa place et
n'entraîne pas l'ajout d'un refrain autour de lui. Ces marques ne sont pas
affichées sur les diapositives. Un seul bloc peut être marqué comme refrain.
Sans refrain marqué, le découpage reste celui du fichier Markdown.

Exemple :

```markdown
<!-- refrain -->
Paroles du refrain

---

Paroles du premier couplet

---

Paroles du deuxième couplet

---

<!-- pont -->
Paroles du pont
```

Cet exemple produit : refrain → couplet 1 → refrain → couplet 2 → pont.
Le refrain n'est pas ajouté automatiquement après le dernier couplet.

Depuis la racine du projet, sous PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/markdown_to_pptx.py chants/notre_pere_glorious.md -o diaporamas/notre_pere_glorious.pptx
```

Le résultat est `diaporamas/notre_pere_glorious.pptx`. Sans l'option `-o`,
le fichier PowerPoint est créé à côté du fichier source.

Pour choisir le fichier de sortie et la taille maximale du texte :

```powershell
.\.venv\Scripts\python.exe scripts/markdown_to_pptx.py chants/notre_pere_glorious.md -o diaporamas/notre_pere_glorious.pptx --font-size 44
```

La taille diminue automatiquement lorsque le texte est long. Cet ajustement
est une estimation : vérifier le rendu dans PowerPoint ou LibreOffice avant
projection, notamment pour les chants comportant de longues lignes.
Les titres Markdown, le gras, l'italique et les liens sont convertis en texte
simple ; les tableaux, images et blocs de code ne sont pas interprétés.

Pour générer le diaporama d'une messe à partir de son index :

```powershell
.\.venv\Scripts\python.exe scripts/markdown_to_pptx.py feuilles_de_chant/index_28eme_dimanche_a.md --index -o diaporamas/messe_28eme_dimanche_a.pptx
```

## Application web

Installer les dépendances puis lancer l'application en local :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Pour la publier sur Streamlit Community Cloud, connecter le dépôt GitHub,
choisir la branche et indiquer `app.py` comme fichier principal. Régler les
droits d'accès de l'application selon les utilisateurs prévus.

L'option `--index` lit les lignes du tableau dans leur ordre, puis assemble
les chants liés dans la dernière colonne. Les chemins sont relatifs au fichier
index. Les refrains marqués sont répétés à l'intérieur de chaque chant.
Une diapositive vide sur fond bleu nuit sépare chaque entrée de la suivante,
sans diapositive vide au début ni à la fin du diaporama.
Une entrée sans lien produit une diapositive contenant seulement son titre ;
un lien vers un fichier absent provoque une erreur.

Dans VS Code, ouvrir le dossier du projet puis appuyer sur **Ctrl+Maj+B**
(ou choisir **Terminal → Exécuter la tâche → Messe : générer le diaporama**).
Saisir le chemin de l'index, relatif au projet ou absolu, sans guillemets,
par exemple `feuilles_de_chant/index_28eme_dimanche_a.md`.

La tâche utilise le Python de `.venv` installé ci-dessus et génère
`diaporamas/messe_28eme_dimanche_a.pptx` pour cet exemple. Le nom est déduit
de celui de l'index : le préfixe `index_` est remplacé par `messe_` ; sans
préfixe `index_`, `messe_` est ajouté. Une nouvelle exécution remplace le
diaporama du même nom. Le terminal affiche le résultat ou l'erreur.

L'option `--output-dir diaporamas` permet aussi de choisir ce dossier depuis
la ligne de commande, avec le même nom automatique.
