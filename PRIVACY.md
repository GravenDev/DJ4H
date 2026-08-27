# Politique de confidentialité — DJ4H (Bot Discord)

**Dernière mise à jour : 15 juin 2026**

## 1. Introduction

DJ4H (le « Bot ») est un bot Discord dédié au serveur « Async - Community » (anciennement Graven - Développement). Il implémente un jeu de timing compétitif appelé « Le jeu des 4h », où les joueurs gagnent des points en envoyant des messages dans un salon dédié après un délai configurable, ainsi qu'un module de statistiques du jeu RNGdle. Cette politique de confidentialité décrit comment le Bot traite les données personnelles des utilisateurs.

## 2. Responsable du traitement

Le responsable du traitement est l'équipe de modération du serveur Discord « Async - Community ». Pour toute question relative à vos données, contactez la modération via le serveur : https://discord.gg/graven.

## 3. Données collectées

Le Bot collecte et traite les catégories de données suivantes :

| Catégorie | Données | Finalité |
|---|---|---|
| Identifiants Discord | ID utilisateur, ID de serveur (guild), ID de message, ID de salon | Attribution des points, classements, configuration du jeu, gestion par serveur |
| Données de jeu « 4h » | Score des utilisateurs, messages de suivi (auteur, horodatage) | Comptage des points, classement, historique du jeu |
| Données RNGdle | Pseudo RNGdle (`rng_username`), date, score, numéro tiré, nombre de badges, ID utilisateur Discord | Liaison du compte Discord au compte RNGdle, statistiques et classements RNGdle |

**Note : le Bot ne collecte ni le contenu des messages, ni les pièces jointes, ni aucun message privé.** Seuls les identifiants et horodatages des messages du salon de jeu sont traités.

## 4. Finalités du traitement

Les données sont traitées pour les seules finalités suivantes :

- **Comptage des points « 4h »** : attribuer un point à un joueur lorsqu'un message est envoyé dans le salon de jeu après le délai configuré.
- **Classements et statistiques** : générer les classements (image) et afficher les scores des joueurs et les statistiques RNGdle.
- **Configuration serveur** : stocker le salon de jeu, le délai configuré et le salon de classement RNGdle par serveur.
- **Liaison RNGdle** : associer un utilisateur Discord à son pseudo RNGdle afin de récupérer et stocker son historique de tirages.
- **Historique RNGdle** : enregistrer les tirages des utilisateurs enregistrés pour alimenter les profils et classements.

## 5. Base légale du traitement (RGPD)

Le traitement est fondé sur :

- **L'intérêt légitime** (Article 6.1.f RGPD) : permettre le fonctionnement du jeu et des classements demandés par les membres du serveur.
- **Le consentement** (Article 6.1.a RGPD) : pour le module RNGdle, la liaison d'un utilisateur Discord à son pseudo RNGdle est réalisée via la commande administrative `/rngdle-admin register` par les modérateurs, avec l'accord de l'utilisateur concerné.

## 6. Destinataires des données

Les données peuvent être transmises aux destinataires suivants :

- **Discord Inc.** : le Bot utilise l'API Discord pour enregistrer et afficher les messages, les scores et les classements. Consultez la [politique de confidentialité de Discord](https://discord.com/privacy).
- **RNGdle (service tiers)** : le Bot interroge l'API publique de [RNGdle](https://www.rngdle.com) (`rngdle.com/api/users/{pseudo}/rolls`) pour récupérer l'historique de tirages associé au pseudo RNGdle enregistré. Consultez la politique de confidentialité de RNGdle pour plus d'informations.
- **Équipe de modération du serveur** : les administrateurs peuvent consulter et modifier les scores via les commandes d'administration, et consulter les journaux du Bot via la commande `/admin dump_log`.

## 7. Stockage et conservation

Le Bot utilise une base de données SQLite locale (variable d'environnement `DATABASE_PATH`, par défaut `dj4h.db`) pour conserver les données de manière persistante :

| Table | Données | Conservation |
|---|---|---|
| `guilds` | Configuration du serveur (salon, délai) | Jusqu'à modification par les administrateurs |
| `users` | Scores « 4h » des utilisateurs | Jusqu'à suppression via `/jd4h-admin unset` |
| `messages` | Suivi des messages du jeu (auteur, horodatage) | Conservé temporairement pour la logique du jeu, remplacé à chaque message suivi |
| `rngdle` | Historique des tirages RNGdle | Indéterminée ; pas de mécanisme de purge automatique |
| `rngdleuser` | Liaison Discord ↔ pseudo RNGdle | Indéterminée ; suppression possible via la base de données |
| `rngdleguildconfig` | Salon de classement RNGdle | Jusqu'à modification par les administrateurs |

| Support | Durée de conservation |
|---|---|
| Base de données SQLite locale (`dj4h.db`) | Conservée par l'hébergeur du Bot, aucune durée prédéfinie |
| Journaux (`logs/bot.log`) | Rotation journalière, 30 sauvegardes conservées |
| Fichier de ressources RNGdle (`compressed_score_to_percent.json`) | Mise à jour hebdomadaire automatique ; ne contient aucune donnée personnelle |

La base de données SQLite n'est pas chiffrée et est hébergée localement sur l'infrastructure du Bot. Le fichier `compressed_score_to_percent.json` contient uniquement la table de correspondance score → pourcentage du jeu RNGdle (aucune donnée personnelle).

## 8. Sécurité

- Le token du Bot est stocké dans un fichier d'environnement (`bot.env` / `BOT_TOKEN`) et n'est jamais exposé.
- Les messages et l'API sont transmis via l'API Discord chiffrée (TLS).
- Les journaux (`logs/bot.log`) contiennent des identifiants utilisateur, des pseudos RNGdle et des scores. Ils ne sont accessibles que via la commande administrative `/admin dump_log` (réservée aux administrateurs).
- **Base de données non chiffrée** : `dj4h.db` contient des données personnelles en clair et doit être protégée par l'hébergeur du Bot.

## 9. Vos droits (RGPD)

Conformément au RGPD, vous disposez des droits suivants :

- **Droit d'accès** : demandez à la modération une copie des données vous concernant.
- **Droit de rectification** : votre pseudo RNGdle peut être modifié via `/rngdle-admin register` ; vos données Discord sont gérées via votre compte Discord.
- **Droit à l'effacement** : votre score « 4h » peut être supprimé via `/jd4h-admin unset` ; pour la suppression de l'historique RNGdle, contactez la modération qui peut purger la base de données.
- **Droit à la limitation du traitement** : vous pouvez cesser d'utiliser le Bot en ne participant pas au jeu et en demandant la suppression de votre liaison RNGdle.
- **Droit à la portabilité** : demandez une copie de vos données à la modération.
- **Droit d'opposition** : vous pouvez vous opposer au traitement en demandant à la modération la suppression de vos données.

Pour exercer ces droits, contactez la modération du serveur Discord « Async - Community » : https://discord.gg/graven.

## 10. Transferts hors UE

Les données sont traitées via l'infrastructure Discord, qui peut impliquer des transferts de données hors de l'Union européenne. Discord s'appuie sur les clauses contractuelles types (CCT) de la Commission européenne pour ces transferts. L'interrogation de l'API RNGdle peut également impliquer des transferts de données hors de l'UE selon l'hébergement de RNGdle. Consultez les [politiques de confidentialité de Discord](https://discord.com/privacy) et de RNGdle pour plus d'informations.

## 11. Modifications de la politique

Cette politique peut être mise à jour à tout moment. La date de « Dernière mise à jour » en tête de document indique la version en vigueur.
