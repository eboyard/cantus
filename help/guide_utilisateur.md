Cantus permet de choisir les chants d’une célébration et de produire un
PowerPoint pour la projection, une feuille pour téléphone ou un document Word à imprimer.
Chaque format se crée et se télécharge séparément, à partir de la même liste de chants.

Choisissez une rubrique ci-dessus ou parcourez le guide complet. Vous pouvez
revenir à l’onglet **Préparer la célébration** pour poursuivre votre préparation.

## Démarrer en quelques étapes

1. Dans **Préparer la célébration**, choisissez la **Date de la célébration**.
   Le nom de la messe et le psaume sont récupérés sur l’AELF. Vous pouvez aussi
   renseigner librement le **Nom de la célébration**.
2. Choisissez un chant dans **Choisir un chant à ajouter**, puis cliquez sur
   **Ajouter le chant**. Répétez pour chaque chant.
3. Dans **Ordre des chants et des textes**, utilisez **Monter**, **Descendre** et **Retirer**
   pour ajuster la liste.
4. Ouvrez **Aperçu des paroles** pour vérifier le contenu et l’ordre des parties.
5. Cliquez sur **Créer le PowerPoint**, **Créer la feuille de chants** ou
   **Créer la version à imprimer**, puis sur le bouton de téléchargement correspondant.

Pour partager une feuille par lien ou QR code, créez d’abord la feuille pour
téléphone, puis suivez la rubrique **Publier une feuille et partager son QR code**.

## Choisir les versets d’un psaume

Après avoir ajouté un psaume du carnet, du psautier ou de l’AELF à la célébration,
utilisez **Versets à garder** sous son titre pour décocher les parties à omettre.
Chaque case correspond à une strophe, qui peut regrouper plusieurs versets bibliques.
Les strophes sont repérées par `---` ou, dans les anciens psaumes sans balises,
par les lignes vides. Les cantiques de type **Cantique** offrent le même choix.

Le refrain identifié reste présent. Vous pouvez conserver seulement le refrain,
même si le psaume n’a qu’une seule strophe. Sans refrain, gardez au moins une
strophe ou utilisez **Retirer** pour enlever le psaume de la célébration.

Les choix suivent chaque occurrence du psaume lors des déplacements et sont
conservés dans la sauvegarde, le fichier `.cantus.json` et les feuilles publiées.
Ils s’appliquent à l’aperçu, au PowerPoint, au Word et aux feuilles pour téléphone.
Le gras et le soulignement des strophes conservées restent présents. Régénérez
les exports après un changement. Les paroles du carnet restent disponibles en entier.
Les anciens brouillons qui n’avaient aucun verset sélectionnable reprennent le psaume entier.

## Sauvegarder et reprendre une préparation

La préparation est sauvegardée automatiquement après chaque modification :
chants et textes, ordre, moments liturgiques, couplets choisis, titre et date.
Les textes AELF nécessaires sont également conservés. Une publication refusée
ou interrompue ne vide pas cette préparation.

Conservez l’adresse complète de la page (par exemple dans vos favoris) : elle
contient votre lien de reprise. Rouvrez cette adresse pour retrouver le brouillon
après une actualisation ou la fermeture de l’onglet. Ce lien est personnel :
toute personne qui le possède peut reprendre et modifier le brouillon.
Ouvrir Cantus sans ce lien commence une autre préparation.

Dans **Sauvegarder la préparation**, cliquez sur
**Télécharger la préparation (.json)** pour garder une copie sur votre
ordinateur, indépendante du serveur. Le nom du fichier contient la date de la messe, par exemple `preparation_cantus_2026_11_29.json`. Pour la reprendre, ouvrez **Repartir d’une
feuille existante**, choisissez **Un fichier JSON sauvegardé**, puis utilisez
**Charger un fichier JSON sauvegardé**. L’import remplace la sélection
en cours et crée un nouveau brouillon ; téléchargez d’abord la préparation actuelle
si vous souhaitez aussi la conserver. Un fichier invalide ou un chant manquant
est signalé sans remplacer votre sélection.

Si la sauvegarde automatique est indisponible, un avertissement apparaît :
téléchargez le fichier de secours avant de quitter la page. Les brouillons
automatiques dépendent du stockage du serveur ; gardez une copie téléchargée
pour retrouver votre travail même si ce stockage est réinitialisé.

Après un échec de publication, vous pouvez réessayer avec la sélection en cours.
En cas de coupure réseau, vérifiez d’abord la version en ligne : l’envoi peut avoir
abouti malgré l’absence de confirmation. Après reprise d’un brouillon, recréez la
feuille de chants puis préparez la publication ; vos choix sont déjà restaurés.

## Récupérer le nom de la messe et le psaume sur AELF

Choisissez la **Date de la célébration**, en haut de la préparation : l’application
interroge l’API AELF pour cette date et remplit le **Nom de la célébration**, année
liturgique comprise. La récupération est automatique au changement de date,
sans bouton supplémentaire. Le titre reste modifiable.

Si plusieurs messes ou psaumes sont proposés pour cette date, choisissez celui
qui correspond à la célébration. Le psaume est présélectionné dans la liste
**Choisir un psaume ou cantique à ajouter** de Psautier.org lorsque sa référence
y figure. Cliquez sur **Ajouter le psaume ou cantique** pour l’insérer dans les
chants, puis vérifiez son texte dans **Aperçu des paroles**.

### Ajouter plusieurs psaumes ou cantiques

Dans **Choisir un psaume ou cantique à ajouter**, recherchez une référence de
Psautier.org, puis cliquez sur **Ajouter le psaume ou cantique**. La liste reprend
les 217 pages du sélecteur du site : psaumes, cantiques de l’Ancien Testament (AT)
et du Nouveau Testament (NT).

Changer la date de la célébration ou la messe AELF présélectionne le psaume du
jour dans cette liste lorsque sa référence y figure. Vous pouvez modifier ce
choix avant de cliquer sur **Ajouter le psaume ou cantique**.

Chaque ajout conserve les chants déjà choisis. Vous pouvez ajouter plusieurs
psaumes ou cantiques, y compris plusieurs occurrences du même texte, puis les
déplacer et choisir leurs strophes comme pour les chants. Leur moment proposé
est **Psaume**, mais il reste modifiable. Pour un cantique, comme le Magnificat,
vous pouvez choisir **Cantique**, proposé juste après **Psaume** dans la liste
des moments.

Le texte complet est récupéré seulement au premier ajout et enregistré dans
`chants/psautier_<référence>.md`, sans écraser les versions de l’équipe. Le titre,
les strophes, les soulignements, le gras et la source sont conservés. Les
doxologies annexes et commentaires ne sont pas ajoutés. Ces fichiers rejoignent
le carnet et servent aux exports téléphone, imprimable, Word et PowerPoint.
Les ajouts suivants réutilisent le fichier local, y compris vos modifications.
Leur conservation sur un autre serveur nécessite de transférer ces fichiers
avec le carnet. L’import et les exports doivent être couverts par vos droits
de reproduction des textes.

### Ajouter les intitulés des lectures et de l’Évangile

Après avoir choisi la date et, si nécessaire, la messe AELF, utilisez les boutons
**Ajouter : Première lecture**, **Ajouter : Deuxième lecture** et **Ajouter : Évangile**.
Chaque clic ajoute uniquement l’intitulé correspondant (« Lecture du livre… »,
« Évangile de Jésus Christ… »), en gras, à la fin de la liste.
Un bouton est proposé seulement si cet intitulé est fourni par l’AELF.
Le champ **Moment de la messe** est renseigné automatiquement avec **Première lecture**,
**Deuxième lecture** ou **Évangile**. Ces choix sont aussi disponibles dans la liste
des moments et restent modifiables. Ils sont conservés lors de la sauvegarde et de la publication.

Dans **Ordre des chants et des textes**, utilisez **Monter**, **Descendre** ou
**Retirer** pour placer ou supprimer chaque intitulé indépendamment, comme un
chant. Aucun intitulé n’est inséré automatiquement avec le psaume ou l’Alléluia.
Les intitulés ajoutés et leur ordre sont conservés dans les aperçus, tous les
exports et lors de la réouverture d’une feuille publiée. Changer la date ou la
messe conserve les intitulés déjà ajoutés : retirez-les et ajoutez ceux de la
nouvelle célébration si nécessaire.

Le moment **Notre Père** se situe après **Anamnèse** et avant **Agneau de Dieu**
(ou Agnus). Un chant « Notre Père » du carnet est reconnu et inséré à cette place.
Quand aucun chant n'est affecté à ce moment, après **Anamnèse**, le titre **Notre Père** est ajouté
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

Le menu **Choisir un chant à ajouter** contient les chants du catalogue,
triés par titre et non par nom de fichier, sans tenir compte des majuscules.
Vous pouvez saisir une partie du titre pour retrouver un chant dans la liste.
Sélectionnez-le, puis cliquez sur **Ajouter le chant**. Les chants dont le type
est connu sont insérés dans l’ordre des moments de la messe : Gloria, psaume,
Alléluia, etc. Les chants sans type sont ajoutés à la fin. Vous pouvez ensuite
ajuster l’ordre avec **Monter** et **Descendre**.

Un même chant peut être ajouté plusieurs fois, par exemple s’il est repris à
plusieurs moments de la célébration. Les boutons **Monter** et **Descendre**
déplacent uniquement l’occurrence choisie ; **Retirer** la supprime de la liste.

Sous chaque chant, la liste **Couplets à garder** propose une case à cocher pour
chaque couplet. Décochez les couplets que vous ne souhaitez pas chanter.
Pour les chants autres que les psaumes et cantiques, seuls les paragraphes
précédés d’un tag `<!-- couplet: C1 -->` (ou C2, C3…)
sont proposés. Les paragraphes sans ce tag restent toujours inclus, même
s’ils sont séparés par `---`, comme dans le Gloria de la messe de saint Augustin.
Lorsqu’un chant n’a qu’un seul couplet, la liste est masquée et ce couplet est
conservé automatiquement.
Toutes les cases sont cochées au départ ; le début des paroles
permet de les reconnaître. Le choix s’applique au PowerPoint et aux feuilles pour téléphone,
à publier et à imprimer, sans modifier le chant du carnet. Les refrains suivent
les couplets conservés et les ponts restent présents. La numérotation des couplets
dans le document Word conserve les numéros d’origine.

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

## Ajouter un chant

1. Dans **carnet de chants**, cliquez sur **Ajouter un chant**.
2. Saisissez le **Titre du chant** et ses **Paroles (Markdown)**.
   Séparez les parties par `---` et identifiez les refrains avec
   `<!-- refrain -->` et les couplets avec `<!-- couplet: C1 -->`, puis C2, C3…
3. Choisissez si souhaité le **Type du chant dans le carnet**.
4. Saisissez le **Code de publication**, le même que pour GitHub Pages,
   puis cliquez sur **Enregistrer**. Le chant est enregistré sur GitHub, puis
   sélectionné dans le carnet. Vous pouvez ensuite le choisir dans la préparation.

**Annuler** ferme le formulaire sans créer de chant. Votre préparation en cours
est conservée. Si un chant utilise déjà le même nom de fichier, précisez
l'auteur ou la messe dans le titre pour distinguer cette nouvelle version.
En cas d'erreur, vos saisies restent affichées pour pouvoir les corriger ou les copier.

Une connexion Internet et l'accès GitHub configuré pour la modification des
chants sont nécessaires. Si **Ajouter un chant** est désactivé, demandez au
responsable de configurer cet accès et le code de publication.

## Modifier un chant

1. Dans **carnet de chants**, choisissez un chant puis cliquez sur **Modifier**.
2. Modifiez le document dans la zone **Contenu Markdown**. Elle contient
   l’ensemble du fichier, y compris le titre et les paroles.
3. Conservez les repères de parties et les séparateurs `---` pour organiser
   la projection. Le contenu saisi est enregistré tel quel.
4. Saisissez le **Code de publication**, le même que pour GitHub Pages,
   puis cliquez sur **Enregistrer**. Un message confirme l’enregistrement et propose un lien
   vers la modification sur GitHub.

**Annuler** ferme le formulaire sans enregistrer. Si le bouton **Modifier** est
désactivé, demandez au responsable de configurer l’accès GitHub et le code de publication.
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
2. Choisissez **Une feuille publiée**, puis la paroisse et la date souhaitées
   dans **Choisir une feuille de chants existante**.
3. La sélection remplace immédiatement la liste actuelle par les chants de la
   feuille, dans le même ordre, y compris les chants présents plusieurs fois.
   Les couplets mémorisés lors de la publication sont également cochés : par
   exemple, les couplets 1, 2 et 8 restent les seuls sélectionnés à la réouverture.
4. Le nom de la célébration mémorisé dans la feuille est restauré automatiquement.
   Ajustez les chants et modifiez ce nom si nécessaire.
   Pour la publication, choisissez également sa nouvelle date.

Pour reprendre un fichier enregistré sur votre ordinateur, choisissez plutôt
**Un fichier JSON sauvegardé**, puis **Charger un fichier JSON sauvegardé**.
Sélectionnez votre fichier `.cantus.json` : le titre, la date, les chants et textes,
leur ordre, les moments et les couplets sont restaurés. Vous pouvez ensuite
modifier la feuille. Un fichier invalide conserve la préparation actuelle.

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
affiche la feuille du jour ou la prochaine feuille publiée, selon la date locale
du navigateur. Sa date complète est indiquée au-dessus des paroles.
Les icônes gauche et droite, placées à droite du choix de la date,
permettent de consulter les autres feuilles. L’icône QR code, à gauche du chevron
précédent, affiche le QR code de la feuille sélectionnée et permet de le télécharger.
L’icône **Calendrier**, à droite des chevrons, permet de revenir à la feuille du jour
ou à la prochaine feuille publiée (à la dernière publiée si toutes sont passées).
Si toutes les célébrations sont passées, la dernière feuille est affichée avec
un message précisant qu’aucune feuille à venir n’est publiée.
Sans JavaScript, la liste des feuilles et leurs QR codes reste accessible.
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

## Créer une feuille Word et l’imprimer

Dans **Ordre des chants et des textes**, choisissez le **Moment de la messe** et les couplets à
garder pour chaque chant. Les boutons **Monter** et **Descendre** fixent leur ordre.
Les refrains et les ponts suivent la sélection. Les intitulés des lectures et
de l’Évangile sont des éléments séparés, ajoutés manuellement.

1. Dans **Feuille de chants à imprimer**, renseignez le **Lieu de la célébration**.
2. Choisissez la **Taille du texte imprimé** : **12 points** reprend le modèle ;
   **9, 10 ou 11 points** donnent une feuille plus compacte.
3. Cliquez sur **Créer la version à imprimer**.
4. Cliquez sur **Télécharger la version à imprimer (.docx)**.
5. Ouvrez le fichier dans Word. Vérifiez l’aperçu avant impression et ajustez la
   disposition si nécessaire. Imprimez en A4, à taille réelle, en recto verso
   avec retournement sur le bord long.

Le modèle reprend la feuille de Saint Pierre–Boussy : photo de l’église, date et
lieu, titre de la célébration, rubriques soulignées, titres des chants en italique,
refrains en gras et couplets courts côte à côte. Les paroles longues restent sur
la largeur disponible. Les accents et les soulignements des psaumes sont conservés.
Le refrain complet apparaît une fois ; les reprises sont indiquées par « Refrain ».
Les couplets gardent leurs numéros d’origine et l’ordre prévu des parties est respecté.

Le document Word remplace le PDF dans l’application. Il reste modifiable après
téléchargement. Word calcule le nombre de pages à l’ouverture et ajoute des pages
si nécessaire sans réduire automatiquement la taille du texte.
Après tout changement de date, de lieu, de taille ou de sélection, créez à nouveau
le document pour actualiser le téléchargement.

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

Ajoutez au moins un chant ou un texte dans **Ordre des chants et des textes**.

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

Pour la feuille Word, choisissez **12 points** et recréez le document.
Pour la projection, vérifiez le PowerPoint et demandez au responsable du
catalogue de répartir les passages trop longs sur plusieurs diapositives.
