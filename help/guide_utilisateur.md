Cantus permet de choisir les chants d’une célébration et de produire un
PowerPoint pour la projection, une feuille pour téléphone ou un PDF à imprimer.
Chaque format se crée et se télécharge séparément, à partir de la même liste de chants.

Choisissez une rubrique ci-dessus ou parcourez le guide complet. Vous pouvez
revenir à l’onglet **Préparer la célébration** pour poursuivre votre préparation.

## Démarrer en quelques étapes

1. Dans **Préparer la célébration**, choisissez la **Date de la célébration**.
   Le nom de la messe et le psaume sont récupérés sur l’AELF. Vous pouvez aussi
   renseigner librement le **Nom de la célébration**.
2. Choisissez un chant dans **Choisir un chant à ajouter**, puis cliquez sur
   **Ajouter le chant**. Répétez pour chaque chant.
3. Dans **Ordre des chants**, utilisez **Monter**, **Descendre** et **Retirer**
   pour ajuster la liste.
4. Ouvrez **Aperçu des paroles** pour vérifier le contenu et l’ordre des parties.
5. Cliquez sur **Créer le PowerPoint**, **Créer la feuille de chants** ou
   **Créer la version à imprimer**, puis sur le bouton de téléchargement correspondant.

Pour partager une feuille par lien ou QR code, créez d’abord la feuille pour
téléphone, puis suivez la rubrique **Publier une feuille et partager son QR code**.

## Récupérer le nom de la messe et le psaume sur AELF

Choisissez la **Date de la célébration**, en haut de la préparation : l’application
interroge l’API AELF pour cette date et remplit le **Nom de la célébration**, année
liturgique comprise. Le titre reste modifiable. Pour charger les textes de la date
déjà affichée au démarrage, cliquez sur **Récupérer le nom et le psaume sur AELF**.

Si plusieurs messes ou psaumes sont proposés pour cette date, choisissez celui
qui correspond à la célébration. Dépliez le titre du psaume pour lire son refrain
et ses strophes, puis cliquez sur **Utiliser le psaume du jour**. Le psaume remplace
celui déjà présent dans la liste ou s’ajoute avant l’acclamation et les chants
suivants. Il est disponible pour le PowerPoint et les feuilles téléphone,
imprimable et publiée. Les fichiers du carnet, y compris les psaumes avec des
syllabes soulignées, ne sont pas modifiés.

Le champ `intro_lue` de la lecture qui précède le psaume apparaît en gras avant
son titre, et celui de la lecture suivante apparaît en gras après ses paroles.
Ces introductions sont conservées dans les exports et les feuilles publiées,
même si certaines strophes sont décochées. Aucun texte n’est ajouté si le champ
est absent ou vide dans la réponse AELF.

L’`intro_lue` de la section `evangile` de la même messe apparaît en gras après
le chant affecté à **Acclamation de l’Évangile** (Alléluia). Si l’API propose aussi
un Évangile en forme brève, l’introduction n’est affichée qu’une fois. Elle est
conservée avec le psaume importé et retrouvée à la réouverture de la feuille.

Les introductions sont aussi mémorisées pour la célébration : après avoir
récupéré les textes AELF, vous pouvez garder un psaume du carnet (notamment
avec des syllabes soulignées). Les introductions figureront dans la publication
et seront restaurées à sa réouverture, sans remplacer les paroles du carnet.

Après un chant affecté au moment **Anamnèse**, le titre **Notre Père** est ajouté
automatiquement en gras, dans le même style que les introductions des lectures.
Ces introductions et **Notre Père** ont la même taille de police que les titres
des chants sur les feuilles pour téléphone et à imprimer.
Il apparaît dans l’aperçu, le PowerPoint et les feuilles téléphone, imprimable
et publiée, sans nécessiter de récupération AELF.

Si un psaume importé est déjà utilisé, changer la date ou la messe AELF le met
également à jour. Les textes correspondent au jour exact sélectionné : pour une
messe anticipée du dimanche, choisissez la date du dimanche.

La feuille publiée conserve le titre, le texte du psaume importé et le choix de
ses strophes. À sa réouverture, aucun nouvel appel AELF n’est nécessaire pour
retrouver ces textes. Si l’AELF est indisponible lors d’une récupération, un message
le signale et le nom ainsi que la liste des chants en cours sont conservés.

## Choisir et ordonner les chants

Le menu **Choisir un chant à ajouter** contient les chants du catalogue.
Vous pouvez saisir une partie du titre pour retrouver un chant dans la liste.
Sélectionnez-le, puis cliquez sur **Ajouter le chant**.

Un même chant peut être ajouté plusieurs fois, par exemple s’il est repris à
plusieurs moments de la célébration. Les boutons **Monter** et **Descendre**
déplacent uniquement l’occurrence choisie ; **Retirer** la supprime de la liste.

Sous chaque chant, la liste **Couplets à garder** propose une case à cocher pour
chaque couplet. Décochez les couplets que vous ne souhaitez pas chanter.
Seuls les paragraphes précédés d’un tag `<!-- couplet: C1 -->` (ou C2, C3…)
sont proposés. Les paragraphes sans ce tag restent toujours inclus, même
s’ils sont séparés par `---`, comme dans le Gloria de la messe de saint Augustin.
Lorsqu’un chant n’a qu’un seul couplet, la liste est masquée et ce couplet est
conservé automatiquement.
Toutes les cases sont cochées au départ ; le début des paroles
permet de les reconnaître. Le choix s’applique au PowerPoint et aux feuilles pour téléphone,
à publier et à imprimer, sans modifier le chant du carnet. Les refrains suivent
les couplets conservés et les ponts restent présents. La numérotation des couplets
dans le PDF conserve les numéros d’origine.

Les choix restent attachés à chaque occurrence lorsque vous déplacez les chants.
Vous pouvez donc garder des couplets différents pour deux occurrences du même chant.
**Aperçu des paroles** montre le contenu retenu pour les feuilles.
Le PowerPoint contient uniquement les couplets cochés, avec les refrains et les ponts.
Si vous modifiez les couplets, cliquez à nouveau sur **Créer le PowerPoint** avant
de le télécharger.

Après une modification des couplets, de la sélection, de son ordre ou du nom de la célébration,
créez à nouveau les fichiers souhaités pour télécharger une version à jour.

## Consulter les paroles d’un chant

1. Ouvrez l’onglet **carnet de chants**.
2. Dans **Choisir un chant à consulter**, saisissez une partie du titre et
   sélectionnez le chant souhaité dans le catalogue.
3. Vérifiez les paroles affichées. Les parties sont séparées par un trait et
   suivent l’ordre de projection, avec les reprises du refrain.

Vous pouvez consulter tous les chants du catalogue sans les ajouter à une
célébration. La consultation conserve votre préparation en cours. Pour
signaler une correction sans accès à l’édition, indiquez le titre du chant au responsable du catalogue.

## Modifier un chant

1. Dans **carnet de chants**, choisissez un chant puis cliquez sur **Modifier**.
2. Modifiez le document dans la zone **Contenu Markdown**. Elle contient
   l’ensemble du fichier, y compris le titre et les paroles.
3. Conservez les repères de parties et les séparateurs `---` pour organiser
   la projection. Le contenu saisi est enregistré tel quel.
4. Cliquez sur **Enregistrer**. Un message confirme l’enregistrement et propose un lien
   vers la modification sur GitHub.

**Annuler** ferme le formulaire sans enregistrer. Si le bouton **Modifier** est
désactivé, demandez au responsable de configurer l’accès GitHub.
Une connexion Internet est nécessaire pour modifier un chant.

Si une autre personne a modifié le chant entre-temps, vos changements ne sont
pas envoyés. Copiez vos corrections, cliquez sur **Annuler**, puis sur
**Modifier** pour les reporter sur la dernière version. En cas d’erreur réseau,
vérifiez le lien du dépôt avec le responsable avant de réessayer.

La préparation de la célébration est conservée. Après modification, créez à
nouveau ses exports. Les feuilles déjà publiées conservent leurs anciennes paroles.
Le gras et le soulignement sont repris dans les feuilles et les PowerPoint.
Les accords et les autres informations sont conservés dans le carnet ; ils ne
figurent pas dans les paroles projetées.

## Consulter les feuilles publiées

L’onglet **Feuilles publiées** affiche le site des feuilles de chants dans Cantus.
Choisissez une paroisse, puis une date pour consulter une feuille. Faites défiler
la page dans le cadre pour parcourir son contenu.

Le bouton **Ouvrir le site dans un nouvel onglet** permet aussi de consulter le
site dans une page séparée. Une connexion Internet est nécessaire.

## Repartir d’une feuille existante

1. Ouvrez **Repartir d’une feuille existante**.
2. Dans **Choisir une feuille de chants existante**, choisissez la paroisse et
   la date souhaitées.
3. La sélection remplace immédiatement la liste actuelle par les chants de la
   feuille, dans le même ordre, y compris les chants présents plusieurs fois.
   Les couplets mémorisés lors de la publication sont également cochés : par
   exemple, les couplets 1, 2 et 8 restent les seuls sélectionnés à la réouverture.
4. Le nom de la célébration mémorisé dans la feuille est restauré automatiquement.
   Ajustez les chants et modifiez ce nom si nécessaire.
   Pour la publication, choisissez également sa nouvelle date.

Les anciennes feuilles publiées sans mémorisation des couplets chargent tous
les couplets par défaut. Sélectionnez les couplets souhaités puis republiez
la feuille pour conserver ce choix lors des prochaines ouvertures.
Les feuilles publiées avant la mémorisation du titre ne remplacent pas le nom
de célébration en cours. Republiez-les avec le titre souhaité pour le conserver.

Au démarrage, les feuilles disponibles sont celles présentes dans la copie
du projet utilisée par l’application. Le bouton **↻**, à droite de la liste,
récupère les feuilles publiées sur GitHub, notamment les publications récentes.

Si un chant manque dans le catalogue ou si plusieurs chants correspondent au
même titre, un message indique le problème et la liste actuelle reste intacte.
Demandez au responsable du catalogue de vérifier les chants concernés.

## Créer le PowerPoint

Cliquez sur **Créer le PowerPoint**, puis sur **Télécharger le PowerPoint**.
Le nombre de diapositives est indiqué sous le bouton de téléchargement.

Le diaporama est au format paysage 16:9, avec des paroles blanches centrées
sur fond bleu nuit et la police Comic Sans MS. Une diapositive vide sépare
chaque chant du suivant. Le texte marqué en gras dans le chant reste en gras.

La taille du texte diminue automatiquement pour les passages longs.
**Vérifiez le rendu dans PowerPoint ou LibreOffice avant la projection**,
en particulier les chants comportant de longues lignes.

## Créer une feuille pour téléphone

Dans **Feuille de chants pour téléphone**, choisissez la **Date de la célébration**,
puis cliquez sur **Créer la feuille de chants**,
puis sur **Télécharger la feuille de chants (.html)**.
La date apparaît dans le titre de la feuille et sert aussi à sa publication sur GitHub Pages.
Le **Moment de la messe** choisi dans l’ordre des chants apparaît au-dessus du titre
de chaque chant, sur la feuille pour téléphone comme sur la feuille à publier.
Les moments implicites **Gloire à Dieu**, **Psaume**, **Acclamation de l’Évangile**,
**Sanctus**, **Anamnèse** et **Agneau de Dieu** ne sont pas affichés.
Tous les moments choisis sont respectés, y compris au début et à la fin de la
liste. **Non renseigné** n’affiche aucun libellé. Les moments sont conservés
dans la feuille publiée et restaurés à sa réouverture.
Si vous changez la date ou un moment, recréez la feuille avant de la télécharger
et préparez à nouveau la publication.

Transférez le fichier sur le téléphone et ouvrez-le avec un navigateur.
Les chants se suivent directement, sans sommaire. Les paroles s’affichent sur
une seule colonne adaptée à la largeur de l’écran.

Une fois téléchargé, le fichier contient les paroles et leur mise en forme :
il peut être consulté sans connexion Internet. L’ordre des chants et des
parties est le même que dans le PowerPoint.

Pour que les participants ouvrent la feuille avec un lien ou un QR code,
utilisez la publication décrite dans la rubrique suivante.

## Publier une feuille et partager son QR code

1. Choisissez la **Date de la célébration**, puis cliquez sur **Créer la feuille de chants** pour faire apparaître
   **Partager avec GitHub Pages**.
2. Choisissez la **Paroisse**. Vérifiez
   l’**Adresse du site GitHub Pages** avec le responsable de l’application.
3. Cliquez sur **Préparer pour GitHub Pages**. Le lien prévu et le QR code apparaissent.
4. Saisissez le **Code de publication** fourni par l’organisateur, puis cliquez
   sur **Publier sur GitHub Pages**.
5. Attendez le déploiement du site, puis utilisez **Ouvrir la feuille après déploiement**
   pour vérifier les paroles avant de diffuser le lien ou le QR code.
6. Cliquez sur **Télécharger le QR code à imprimer (.svg)** pour l’insérer
   dans un document ou l’imprimer.

**Préparer pour GitHub Pages** calcule le lien et le QR code ; la feuille est
envoyée sur GitHub au clic sur **Publier sur GitHub Pages**. Le message de succès
confirme l’envoi, mais le site peut encore être en cours de déploiement.
Le responsable peut suivre **pages build and deployment** dans l’onglet
**Actions** du dépôt GitHub.

Le bouton **Toutes les feuilles de la paroisse**, proposé après publication,
ouvre la liste des célébrations, de la plus récente à la plus ancienne.
Les participants n’ont pas besoin du code de publication pour lire les feuilles.

Une même paroisse et une même date correspondent à la même adresse.
Pour corriger une feuille déjà publiée, préparez sa nouvelle version, cochez
**Remplacer la feuille existante pour cette paroisse et cette date**, puis
publiez à nouveau. Le lien et le QR code restent les mêmes.

Les feuilles publiées sont des copies : modifier ensuite le catalogue ne
met pas leurs paroles à jour. Conservez les anciennes publications pour que
leurs liens et QR codes restent accessibles.

Si la publication directe est désactivée, contactez le responsable de
l’application pour sa configuration.

## Créer et imprimer un PDF

Dans **Ordre des chants**, choisissez le **Moment de la messe** pour chaque chant,
y compris le premier et le dernier :
entrée, préparation pénitentielle, Gloire à Dieu, psaume, acclamation de l’Évangile,
prières universelles, offertoire, Sanctus, anamnèse, Agneau de Dieu, communion ou envoi.
Le type du carnet est proposé automatiquement lorsqu’il est connu. Vous pouvez
le remplacer pour cette célébration, y compris si un même chant est utilisé deux fois.
Les propositions **Chant d’entrée** et **Envoi** aux extrémités d’une liste chargée
ne remplacent jamais un type connu. Un Kyrie placé en dernier reste une préparation
pénitentielle. Les moments choisis suivent les chants après un déplacement.
**Non renseigné** conserve uniquement le titre du chant dans le PDF.
Les rubriques choisies apparaissent au-dessus des titres et des paroles ; deux chants
consécutifs du même moment partagent une rubrique. Seuls les moments utilisés sont
imprimés. Les boutons **Monter** et **Descendre** permettent de suivre la trame souhaitée.

Dans le **carnet de chants**, **Modifier** permet de renseigner le **Type du chant
dans le carnet**, puis de l’enregistrer avec les paroles. Les types évidents tels que
Kyrie, Gloria et Sanctus sont reconnus d’après le titre. Les chants dont l’usage varie
restent à renseigner. Le type enregistré est conservé dans une ligne
`<!-- type: Gloire à Dieu -->`, qui n’apparaît pas dans les paroles ni les projections.

1. Dans **Feuille de chants à imprimer**, choisissez la **Taille du texte imprimé** :
   **9 ou 10 points** pour une feuille plus compacte, **11 points** par défaut
   ou **12 points** pour des caractères plus grands.
2. Cliquez sur **Créer la version à imprimer**. Le nombre de pages est affiché.
3. Cliquez sur **Télécharger la version à imprimer (.pdf)**.
4. Imprimez à **taille réelle (100 %)**, avec **une page par face**, en
   **recto verso, retournement sur le bord long**.

Le PDF est au format A4 portrait, en deux colonnes, avec des marges de 12 mm
et du texte noir sur fond blanc. Les couplets sont numérotés. Chaque refrain
est écrit en gras à sa première occurrence, puis indiqué par « Refrain » lors
des reprises. L’ordre prévu des parties et les ponts sont conservés.

Chaque chant forme un bloc : sa rubrique et son titre occupent toute la largeur,
puis ses paroles sont réparties en deux colonnes. Le bloc du chant suivant commence
en dessous des deux colonnes du précédent, jamais à côté. Les couplets restent
ensemble lorsqu’ils tiennent dans une colonne ; les chants longs peuvent se
poursuivre sur plusieurs pages.
Si nécessaire, le document ajoute des pages sans réduire la taille du texte choisie.
Après un changement de taille, créez à nouveau le PDF.

## Comprendre les paroles et les refrains

Les paroles proviennent du catalogue de chants. La préparation dans Streamlit
permet de choisir et d’ordonner les chants ; les corrections de paroles se font
dans les fichiers du catalogue par son responsable.

Dans ces fichiers, une ligne contenant uniquement `---` sépare deux parties.
Les retours à la ligne sont conservés. Le texte entre `**` ou `__` apparaît en gras.

Un bloc marqué `<!-- refrain -->` reste à sa place et est répété entre deux
couplets successifs. Il n’est pas ajouté automatiquement après le dernier couplet.
Un pont marqué `<!-- pont -->` reste à sa place sans provoquer de reprise
automatique autour de lui. Sans refrain marqué, les parties suivent le fichier.

Le responsable peut fixer précisément l’ordre avec une directive telle que
`<!-- ordre: R C1 R C2 R -->` : refrain, couplet 1, refrain, couplet 2, refrain.
Dans ce cas, seules les parties prévues par cette directive sont jouées, sans
refrain supplémentaire. L’aperçu et le PowerPoint utilisent ce même ordre.

## Résoudre les difficultés courantes

### Un bouton de création est désactivé

Ajoutez au moins un chant dans **Ordre des chants**.

### Un bouton de téléchargement a disparu après une modification

Créez à nouveau le format concerné. Les téléchargements sont proposés pour
la sélection et les réglages qui ont servi à les générer.

### Une feuille récente n’apparaît pas dans les feuilles existantes

Cliquez sur **↻** dans **Repartir d’une feuille existante**. Si l’actualisation
échoue, transmettez le message affiché au responsable de l’application.

### La publication est désactivée ou le code est refusé

Demandez le code à l’organisateur. Si la publication est désactivée, le
responsable doit configurer l’accès GitHub et le code côté serveur.

### La feuille existe déjà ou une publication concurrente est signalée

Vérifiez la paroisse et la date. Pour une correction volontaire, cochez le
remplacement avant de publier. Si une autre publication a modifié le dépôt
pendant l’envoi, vérifiez la version en ligne avant de réessayer.

### Le lien ou le QR code n’ouvre pas encore la feuille

Vérifiez que vous avez cliqué sur **Publier sur GitHub Pages** après la
préparation. Attendez la fin du déploiement et testez le lien avant de distribuer
le QR code. Si le problème persiste, contactez le responsable du site.

### Le texte est trop petit ou déborde

Pour le PDF, essayez **12 points** et recréez le fichier.
Pour la projection, vérifiez le PowerPoint et demandez au responsable du
catalogue de répartir les passages trop longs sur plusieurs diapositives.
