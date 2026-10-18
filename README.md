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

Pour choisir précisément l'ordre, ajouter une directive en tête du fichier :

```markdown
<!-- ordre: R C1 R C2 R -->

<!-- refrain -->
Paroles du refrain

---

<!-- couplet: C1 -->
Paroles du premier couplet

---

<!-- couplet: C2 -->
Paroles du deuxième couplet
```

Cet exemple produit : refrain → couplet 1 → refrain → couplet 2 → refrain.
Chaque partie est écrite une seule fois. La directive peut répéter, omettre
ou réordonner les parties ; aucun refrain supplémentaire n'est inséré.
`R` désigne le refrain, `C1`, `C2`, etc. les couplets, et `P1`, `P2`, etc.
les ponts (par exemple `<!-- pont: P1 -->`). Sans identifiant explicite,
les couplets et les ponts sont numérotés séparément dans leur ordre d'apparition.
Un identifiant utilisé dans l'ordre doit exister et être défini une seule fois.
Sans directive `ordre`, le comportement décrit plus haut est conservé.
L'aperçu Streamlit et le PowerPoint utilisent tous deux cet ordre.

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
Le texte entre `**…**` (ou `__…__`) apparaît en gras dans le PowerPoint,
y compris lorsqu'il ne concerne qu'une partie de la ligne.
Les titres Markdown, l'italique et les liens sont convertis en texte simple ;
les tableaux, images et blocs de code ne sont pas interprétés.

Pour générer le diaporama d'une messe à partir de son index :

```powershell
.\.venv\Scripts\python.exe scripts/markdown_to_pptx.py feuilles_de_chant/index_28eme_dimanche_a.md --index -o diaporamas/messe_28eme_dimanche_a.pptx
```

## Application web

### Feuille de chants à imprimer

Après avoir choisi et ordonné les chants, cliquer sur **Créer la version à imprimer**,
puis **Télécharger la version à imprimer (.pdf)**. Cette génération est indépendante
du PowerPoint et de la feuille pour téléphone.

Le PDF utilise le format A4 portrait, deux colonnes, des marges de 12 mm et du texte
noir sur fond blanc. Choisir **11 points** pour une feuille compacte ou **12 points**
pour des caractères plus grands. Les couplets sont numérotés ; chaque refrain est
écrit en gras à sa première occurrence, puis remplacé par « Refrain » aux reprises.
L'ordre explicite des parties et les ponts sont conservés. Les couplets sont gardés
ensemble lorsqu'ils tiennent dans une colonne.

Imprimer à **taille réelle (100 %)**, avec **une page par face**, en **recto verso,
retournement sur le bord long**. Le nombre de pages est affiché avant téléchargement :
le document ajoute des pages si nécessaire sans réduire la taille choisie.

La génération PDF utilise ReportLab, inclus dans `requirements.txt`, et ses polices
Unicode embarquées. Pour lancer les tests, y compris la vérification des PDF :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

### Feuille de chants pour téléphone

La section **Feuille de chants pour téléphone** permet de créer et télécharger
un fichier `.html` à partir des chants sélectionnés. La feuille possède un
sommaire cliquable, une seule colonne adaptée aux petits écrans et des paroles
en gras lorsque le Markdown le demande. L'ordre des chants et l'alternance
couplets/refrain sont les mêmes que pour le PowerPoint.

Transférer le fichier sur le téléphone, puis l'ouvrir avec un navigateur.
Le document contient son style et ses paroles : après téléchargement,
aucune connexion Internet n'est nécessaire. Le partage public utilise GitHub Pages,
avec une page HTML par paroisse et date.
La création de cette feuille est indépendante de celle du PowerPoint.

### Publier les feuilles avec GitHub Pages

GitHub Pages publie les feuilles depuis le dossier `docs` de `main`. Il n'est pas nécessaire
de déployer Streamlit pour la lecture des feuilles, ni de configurer une base de données.

Configuration initiale du dépôt `eboyard/cantus` :

1. Ouvrir **Settings → Pages** sur GitHub.
2. Choisir **Deploy from a branch**, la branche **main** et **/docs**.
3. Enregistrer. Ces réglages sont décrits dans la
   [documentation GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

Pour chaque célébration :

1. Préparer les chants dans Streamlit puis cliquer sur **Créer la feuille de chants**.
2. Dans **Partager avec GitHub Pages**, choisir **Boussy-saint-Antoine** ou
   **Quincy-sous-Sénart**, saisir la date et l'adresse du site, puis **Préparer pour GitHub Pages**.
3. Saisir le **Code de publication**, puis cliquer sur **Publier sur GitHub Pages**.
   L'application crée directement un commit contenant la feuille HTML et l'index
   de la paroisse sur `main`.
4. Attendre la fin du déploiement **pages build and deployment** dans l'onglet **Actions**,
   puis ouvrir le lien pour vérifier la feuille avant de distribuer le QR code.

L'adresse est de la forme
`https://eboyard.github.io/cantus/saint-pierre/2026-10-18/`.
Le fichier publié est `docs/saint-pierre/2026-10-18/index.html`. Le dossier `docs` ne figure
pas dans l'URL publique. Le QR code peut être téléchargé
dans Streamlit pour impression ; il n'est pas nécessaire de le publier dans le dépôt.

Chaque paroisse possède aussi une page regroupant ses feuilles, de la date la plus
récente à la plus ancienne :

- [Boussy-saint-Antoine](https://eboyard.github.io/cantus/boussy-saint-antoine/)
- [Quincy-sous-Sénart](https://eboyard.github.io/cantus/quincy-sous-senart/)

À chaque publication directe, cet index est reconstruit à partir des feuilles
présentes sur la branche GitHub et de la nouvelle feuille. Un remplacement ne crée
pas de doublon. La feuille et l'index sont publiés ensemble ; si la branche change
pendant l'envoi, la publication est refusée pour conserver les modifications concurrentes.
Le bouton **Toutes les feuilles de la paroisse** permet d'ouvrir cet index après publication.
L'enregistrement local met également l'index à jour à partir des feuilles locales.
Le ZIP contient uniquement la nouvelle feuille et son QR code : après un envoi manuel,
l'index distant sera actualisé lors de la prochaine publication directe pour cette paroisse.
Le lien affiché après préparation est une adresse prévue : seul le bouton **Publier**
envoie la feuille à GitHub. Le succès de l'envoi confirme le commit, pas la fin du déploiement Pages.

Une même paroisse et une même date donnent toujours la même adresse. Pour remplacer
une feuille, cocher le remplacement, puis cliquer à nouveau sur **Publier sur GitHub Pages**.
Sans cette case, une feuille existante n'est pas écrasée. Si le fichier change pendant
l'envoi, GitHub refuse la mise à jour concurrente et l'application affiche une erreur.
Conserver les dossiers des anciennes célébrations pour maintenir leurs liens actifs.
Les feuilles sont des copies HTML : modifier ensuite le catalogue des chants ne les change pas.
Pour plusieurs offices le même jour, utiliser des noms distincts comme « Saint-Pierre matin »
et « Saint-Pierre soir ». Le QR code SVG est téléchargeable pour impression.

La publication directe fonctionne aussi depuis Streamlit Community Cloud. Les options
de téléchargement ZIP et d'enregistrement local restent disponibles : elles créent
`docs/paroisse/date/index.html`, `qr.svg` dans le même dossier que la feuille, et `docs/.nojekyll`.
Extraire le ZIP à la racine du dépôt, pas à l'intérieur de `docs`. Si vous utilisez
ces options, l'envoi sur GitHub reste manuel. Les anciennes feuilles stockées à la racine
doivent être recopiées sous `docs` avec la même structure paroisse/date pour conserver
leurs adresses et QR codes après le changement de source Pages.

### Configurer la publication directe une seule fois

1. Dans GitHub, créer un **fine-grained personal access token** avec une expiration,
   limité au dépôt `eboyard/cantus`, et la permission **Contents: Read and write**.
   Aucun droit Workflows n'est nécessaire. Voir l'[API GitHub Contents](https://docs.github.com/en/rest/repos/contents).
2. Copier [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example) dans
   `.streamlit/secrets.toml` en local, ou coller la configuration dans **Settings → Secrets**
   de l'application Streamlit Community Cloud.

```toml
[github]
token = "VOTRE_JETON_GITHUB"
repository = "eboyard/cantus"
branch = "main"
publish_password = "UN_CODE_LONG_RESERVE_AUX_ORGANISATEURS"
```

Le jeton reste côté serveur et n'est jamais inclus dans la feuille, le ZIP ou le QR code.
Le code de publication protège le bouton si l'application est publique ; il n'est pas
demandé aux paroissiens. Ne pas versionner `.streamlit/secrets.toml` (il est ignoré par Git).
Sans jeton et sans code configurés, la publication directe est désactivée.
Les variables `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_BRANCH` et `SHEET_PUBLISH_PASSWORD`
peuvent remplacer ces réglages. Pour un autre dépôt ou un domaine personnalisé,
adapter également l'adresse du site dans l'application ou définir `GITHUB_PAGES_URL`.
La branche configurée doit être celle publiée par Pages et autoriser les commits du jeton.
L'application ne modifie pas les réglages Pages et ne contourne pas les protections de branche.

Les tests de publication simulent l'API GitHub : la première publication réelle doit
être faite après configuration du jeton. Aucun fichier n'est envoyé automatiquement au démarrage.

Pour personnaliser le nom affiché dans la liste des chants et l'aperçu,
ajouter un tag facultatif en tête du fichier Markdown :

```markdown
<!-- titre: Kyrie (Messe de Saint Augustin) -->
```

La casse, les accents et la ponctuation du titre sont conservés. Si le tag
est absent ou vide, le nom du fichier sert de titre comme auparavant.
Ce tag n'apparaît pas dans les paroles ni sur les diapositives. Il peut
précéder ou suivre la directive `ordre`, avant les paroles.

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
