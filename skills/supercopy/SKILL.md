---
name: supercopy
description: |
  Nettoie un texte de ce qui trahit une écriture générée par IA : tiret cadratin remplacé selon sa fonction, retournements, triades, fausses confidences, autorité non sourcée, chutes artificielles, euphémismes corporate. Réécrit directement et explique ce qui a été retiré. Typographie française d'abord, anglais géré aussi. Utilise cette compétence dès que l'utilisateur demande de relire, réécrire, corriger, nettoyer, désIAiser ou humaniser un texte, dit qu'un texte fait trop IA, trop LinkedIn ou pas naturel, veut supprimer les tirets cadratins, ou fait relire un post, un email ou un article avant publication.
  Also triggers on: humanize, de-AI, remove em dashes, sounds like ChatGPT, AI slop, proofread before posting.
---

# supercopy

Un texte écrit par une IA se reconnaît rarement à une faute. Il se reconnaît à des réflexes : une ponctuation qui n'existait pas dans le français courant il y a cinq ans, des figures de style répétées jusqu'à l'épuisement, une émotion affichée que personne n'éprouve. Cette compétence retire ces réflexes et rend le texte à quelqu'un.

Le principe de travail : **on coupe, on ne remplace pas par un autre effet.** Un retournement supprimé ne devient pas une métaphore. Il devient une phrase qui dit ce qu'elle a à dire.

## Comportement par défaut

Réécris directement. L'utilisateur reçoit dans cet ordre :

1. **Le texte nettoyé**, prêt à copier, sans commentaire à l'intérieur.
2. **Ce qui a été retiré**, en trois à six puces courtes, chacune nommant le tic et citant le fragment concerné.

Pas de préambule, pas de « voici votre texte révisé ». Le texte d'abord.

Deux exceptions à la réécriture directe :

- L'utilisateur demande explicitement un diagnostic (« qu'est-ce qui cloche », « analyse »). Alors liste les tics sans réécrire.
- Le texte est d'un tiers et l'utilisateur veut comprendre plutôt que publier. Même traitement.

Quand une coupe fait perdre une information réelle, ne coupe pas : reformule. La règle est de retirer l'effet, jamais le fond.

## Le tiret cadratin

C'est le signe le plus reconnaissable, et le seul qui se traite mécaniquement. Le tiret cadratin `—` et le demi-cadratin `–` sont massivement surutilisés par les modèles de langage, alors qu'ils sont rares sous une plume française.

Le remplacement dépend de la fonction du tiret dans la phrase, pas d'une règle unique :

| Position | Fonction | Remplacement |
|---|---|---|
| Deux tirets encadrant un segment | Incise | Deux virgules |
| Un tiret suivi de *et, mais, ou, donc, car* | Ajout coordonné | Virgule |
| Un tiret suivi d'une proposition complète | Rupture ou révélation | Point, parfois deux-points |
| Un tiret introduisant une explication | Développement | Deux-points |
| En début de ligne | Liste ou dialogue | Tiret court suivi d'une espace |
| Entre deux nombres | Intervalle | « à », ou tiret court |

Le script `scripts/nettoyer.py` applique ces règles automatiquement et signale les cas où le contexte ne permet pas de trancher.

```bash
python3 scripts/nettoyer.py texte.txt
python3 scripts/nettoyer.py texte.txt --sortie propre.txt
echo "mon texte" | python3 scripts/nettoyer.py -
```

Il traite aussi les autres marqueurs typographiques : guillemets courbes vers guillemets français, points de suspension en caractère unique, espaces insécables devant les ponctuations doubles, puces décoratives en début de ligne.

Lance-le systématiquement avant la réécriture : il évacue le mécanique, tu te concentres sur le rhétorique.

## Les tics rhétoriques

Chacun se repère à sa forme, indépendamment du sujet. Le catalogue complet, avec les variantes et des exemples avant/après, est dans `references/tics.md`. Voici les plus fréquents.

### Le retournement

*« Ce n'est pas l'IA qui a vidé nos feeds. C'est nous qui n'en avions plus besoin. »*

Une négation suivie d'une révélation. La structure promet une profondeur que le contenu ne tient presque jamais. Variantes : « Le problème n'est pas X, c'est Y », « Ce n'est pas une question de X. C'est une question de Y ».

Réécriture : garde l'affirmation, jette la négation. *« Nous n'avions plus besoin d'âme pour publier. »*

### La triade

*« Pas plus intelligent. Pas plus sincère. Il est juste plus rapide. »*

Trois éléments parce que trois sonne complet, pas parce qu'il y a trois choses à dire. Le troisième est souvent un remplissage.

Réécriture : garde le terme qui porte l'information, supprime les deux autres. *« Le process est juste plus rapide. »*

### L'escalier décroissant

*« Du contenu. Du volume. Du vide. »*

Trois fragments isolés sur trois lignes, de plus en plus courts, vers une chute abstraite. C'est de la mise en scène typographique.

Réécriture : une phrase. *« On produit du volume, et ce volume est vide. »*

### La fausse confidence

*« Honnêtement ? Je ne me souviens plus du dernier post qui m'a vraiment touché. »*

Un marqueur d'intimité posé au début pour simuler la sincérité. « Honnêtement ? », « Soyons clairs », « Je vais être franc », « On ne va pas se mentir », « Entre nous ».

Réécriture : supprime le marqueur. Ce qui suit est vrai ou ne l'est pas, l'annonce n'y change rien. *« Je ne me souviens pas du dernier post qui m'a touché. »*

### L'autorité non sourcée

*« Les experts sont formels. »*

Une source invoquée sans jamais être nommée. « Des études montrent », « Les observateurs s'accordent », « Il est largement admis ».

Réécriture : cite la source réelle, ou assume l'opinion, ou supprime. Jamais d'autorité empruntée à personne.

### La chute artificielle

*« Et voici le vrai problème : »*

Un annonceur de révélation qui prépare une phrase ordinaire. « Et c'est là que tout bascule », « Ce que personne ne dit », « La vérité, c'est que ».

Réécriture : supprime l'annonce, garde la phrase. Si elle ne tient pas debout seule, c'est qu'il n'y avait pas de révélation.

### La métaphore filée

*« L'IA n'a pas tué nos feeds. Elle a pris le volant, et personne n'a remarqué qu'il n'y avait plus personne à bord. »*

Une image mécanique, souvent automobile ou nautique, étirée sur deux propositions pour produire une chute. Copilote, volant, gouvernail, cockpit, radeau.

Réécriture : dis la chose. *« Nos feeds tournent sans que personne les lise. »*

### L'euphémisme corporate

*« On ne produit pas moins de sens. On optimise la cadence de publication. »*

Un terme de gestion posé sur une réalité banale pour la rendre respectable. Optimiser, cadencer, adresser un sujet, activer un levier, industrialiser.

Réécriture : le mot simple. *« On publie plus souvent. »*

### Le symbolisme gonflé

*« La riche tapisserie de nos échanges numériques. »*

Tapisserie, mosaïque, symphonie, danse, voyage, écho. Une métaphore décorative qui n'apporte aucune information.

Réécriture : le nom commun. *« Nos échanges numériques. »*

### La chute en dégradé

Trois lignes finales de plus en plus courtes, la dernière tenant en quatre mots. *« Je ne dis pas que ces posts sont mauvais. / Je dis qu'ils n'existent pour personne. / Pas même pour celui qui les a publiés. »*

Réécriture : garde la ligne qui dit quelque chose, supprime les deux autres.

## Après la réécriture

Relis avec une question simple : **est-ce que quelqu'un pourrait avoir écrit ça en parlant ?**

Trois vérifications qui rattrapent l'essentiel :

**Le texte a-t-il gardé une voix ?** Retirer les tics sans rien mettre à la place donne un communiqué. Un texte humain a des opinions, des hésitations, des phrases de longueurs inégales. Si tout fait la même longueur, casse le rythme.

**Reste-t-il des mots que l'utilisateur n'emploie pas ?** Chaque auteur a un vocabulaire. Un mot juste mais étranger à sa plume sonne aussi faux qu'un tic.

**Le texte dit-il encore la même chose ?** Compare les informations d'origine et celles qui restent. Une coupe ne doit jamais emporter un fait.

## Ce qu'il ne faut pas faire

**Ne pas sur-corriger.** Un tiret cadratin justifié reste. Une énumération de trois éléments réels reste. Le but est de retirer les réflexes, pas d'appauvrir.

**Ne pas ajouter de fautes pour faire humain.** Les erreurs volontaires, l'oralité forcée et les « bref » posés au hasard sont un autre genre de tic.

**Ne pas commenter dans le texte.** Les remarques vont dans la liste qui suit, jamais entre parenthèses au milieu du paragraphe.

**Ne pas moraliser.** L'utilisateur veut un texte publiable, pas une leçon sur l'écriture assistée.

## Anglais

Les mêmes tics existent, avec leurs formulations propres : *It's not about X, it's about Y*, *Let's be honest*, *Here's the thing*, *the rich tapestry of*, *delve*, *leverage*, *seamless*, *game-changer*, *in today's rapidly evolving landscape*.

La typographie diffère : l'em dash anglais s'écrit sans espaces autour, et son usage y est plus légitime qu'en français. Sois moins systématique sur le tiret, aussi strict sur le reste. Le détail est dans `references/tics.md`.

## Fichiers

- `references/tics.md` : catalogue complet, variantes, exemples avant/après, section anglaise
- `scripts/nettoyer.py` : passe typographique automatique et signalement des tics rhétoriques
