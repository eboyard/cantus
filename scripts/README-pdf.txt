EXTRACTION DE TEXTE PDF

Installation (Python 3.10 ou plus récent) :
  python -m pip install -r requirements-pdf.txt

Partition avec paroles syllabées :
  python extract_pdf.py "C:\_dev\my_projects\cantus\temp\a.007.gloire.au.christ-.parole..ternelle.pdf" --mode partition

PDF ordinaire :
  python extract_pdf.py "document.pdf"

Tout un dossier (sans sous-dossiers) :
  python extract_pdf.py "C:\chemin\dossier" --mode partition -o "output/text"

Chaque PDF produit un TXT UTF-8. Les originaux ne sont pas modifiés.
Les TXT existants sont protégés ; --force autorise leur remplacement.
Deux PDF de même nom dans un même traitement provoquent une erreur de collision.
Les pages sont séparées par un saut de page (caractère form feed).

MODE PARTITION
Le script utilise la position des lettres pour retrouver les lignes.
Il exclut plusieurs polices musicales connues, retire les lignes d'accords
et réunit les syllabes avec un tiret suivi d'un espace :
  Pa- role -> Parole
  Lu- mière é- ter- nel- le -> Lumière éternelle
  Dieu - vi- vant! -> Dieu vivant !
Les accents proviennent du PDF, sans correction lexicale automatique.
Pour une autre police musicale : --exclude-font "NomDePolice"

Limites : le nettoyage repose sur des heuristiques. Un mot composé avec un
tiret suivi d'un espace peut être fusionné à tort. Les colonnes, couplets
répartis sur plusieurs portées et réponses alignées avec un couplet restent
dans l'ordre visuel des lignes. Les mentions Tous/Soliste ne sont pas déplacées
et le refrain n'est pas automatiquement séparé des couplets.
Utiliser --mode text pour conserver le texte sans nettoyage musical.

OCR OPTIONNEL POUR LES SCANS
Par défaut --ocr auto tente l'OCR sur une page sans texte exploitable.
Pour activer cette possibilité, installer également :
  python -m pip install pytesseract
Installer Tesseract OCR séparément, avec les données de langue française
(fra.traineddata), et rendre sa commande tesseract accessible dans le PATH.
Le rendu d'image utilise le moteur fourni avec pdfplumber (pypdfium2).

  --ocr never   : aucune reconnaissance d'image
  --ocr auto    : OCR si le texte extrait est vide
  --ocr always  : OCR sur toutes les pages, même avec une couche texte
  --language fra+eng : plusieurs langues (données à installer)
  --dpi 300     : résolution OCR, entre 72 et 600

Une page scannée avec un en-tête textuel peut échapper au déclenchement
automatique : utiliser --ocr always dans ce cas. L'OCR des partitions peut
confondre symboles et lettres et nécessite une vérification. Aucune donnée
n'est envoyée à un service distant.

Le code de sortie vaut 0 si tous les traitements ont réussi, 1 en cas
d'échec d'au moins un PDF. Un échec OCR est explicite, sans TXT de réussite.
Une page vide est signalée dans le TXT et dans la console.
