


# Welcome to Namida Translations

### Here you can contribute by translating to official [Namida](https://github.com/namidaco/namida)

<a href="https://translate.codeberg.org/engage/namida-translations/">
<img src="https://translate.codeberg.org/widget/namida-translations/namicomponent/287x66-grey.png" alt="Translation status" />
</a>

## 🧾 Steps:
1. **Head over [Namida Weblate](https://translate.codeberg.org/projects/namida-translations)**
2. **Start translating!** ([**READ HERE FOR ICU KEYS GUIDE**](#ICU-Message-Format))
3. **After finishing, open an issue here with ur language details so it gets added to the final app**

## ICU Message Format

### Plain strings

The easy ones. Just translate the text, nothing special here.

```
"addMoreFromToQueue": "Add more from {media} to queue"
```

`{media}` is a **placeholder**, the app fills it in at runtime. Leave it as-is, but feel free to move it around to fit your language's word order:

```
// french example
"addMoreFromToQueue": "Ajouter plus de {media} à la file d'attente"
```

---

### Plural forms

```
"countAlbums": "{count, plural, one{{count} Album} other{{count} Albums}}"
```

Structure: `{variable, plural, form{message} form{message}}`

- `one{...}` → singular
- `other{...}` → plural (also the fallback)
- `{count}` inside each form is the number itself

Some languages need more than two forms, Russian for example has 3:

```
"{count, plural, one{{count} Альбом} few{{count} Альбома} other{{count} Альбомов}}"
```

All possible forms are: `zero` `one` `two` `few` `many` `other`, just use whatever your language actually needs.

---

### Plural with a separate display variable

```
"importedNPlaylistsSuccessfully": "{number, plural, one{Imported {numberText} playlist successfully} other{Imported {numberText} playlists successfully}}"
```

This one has two variables that look similar but do different things. `{number}` is the raw number used to pick the right plural form, and `{numberText}` is what actually gets shown in the text. Just keep both as-is and translate around them:

```
// french example
"importedNPlaylistsSuccessfully": "{number, plural, one{Importé {numberText} playlist avec succès} other{Importé {numberText} playlists avec succès}}"
```

---

### Things to keep in mind

1. **Never translate** anything inside `{}`.. that's code, not text
2. `other` is always required, it's the fallback when nothing else matches
3. Don't remove plural forms from the original, and add any extra ones your language needs
4. Placeholders can be moved anywhere in the sentence to fit your grammar

### Specialito:
By translating, you are implying that you are a nice, great and specialito person, this will be helping the project a lot, thank you so much !


## kawaii translators:

| Language | Country | Contributors | Translation |
|---|---|---|---|
| Afrikaans | South Africa | [@BosnianPrince97](https://github.com/BosnianPrince97) | [`af.json`](translations/af.json) |
| Afrikaans  | South Africa | [@BosnianPrince97](https://github.com/BosnianPrince97) | [`af.json`](translations/af.json) |
| Bangla  | Bangladesh | [@chayanforyou](https://github.com/chayanforyou), [@sagorxzx](https://github.com/sagorxzx) | [`bn.json`](translations/bn.json) |
| Bosnian  | Bosnia | [@BosnianPrince97](https://github.com/BosnianPrince97) | [`bs.json`](translations/bs.json) |
| Dutch  | Netherlands | [@Vistaus](https://github.com/Vistaus) | [`nl_NL.json`](translations/nl_NL.json) |
| English  | United States | [@MSOB7YY](https://github.com/MSOB7YY) | [`en_US.json`](translations/en_US.json) |
| Español  | Spain | [@alexwithstars](https://translate.codeberg.org/user/alexwithstars), [@UpsideDownCak3](https://translate.codeberg.org/user/UpsideDownCak3), [@galahad_wpx](https://translate.codeberg.org/user/galahad_wpx). [@abn1227](https://translate.codeberg.org/user/abn1227) | [`es.json`](translations/es.json) |
| Español  | Colombia | [@xqsart](https://github.com/xqsart) | [`es_CO.json`](translations/es_CO.json) |
| Esperanto  | Global | [@BosnianPrince97](https://github.com/BosnianPrince97) | [`eo.json`](translations/eo.json) |
| Finnish  | Finland | [@Cocobo1](https://translate.codeberg.org/user/Cocobo1), [BorisB82](https://translate.codeberg.org/user/BorisB82), [Ricky-Tigg](https://translate.codeberg.org/user/Ricky-Tigg) | [`fi.json`](translations/fi.json) |
| Français  | France | [@yannouuuu](https://github.com/yannouuuu) | [`fr_FR.json`](translations/fr_FR.json) |
| German  | Germany | [@Maxitendo1](https://github.com/Maxitendo1) | [`de_DE.json`](translations/de_DE.json) |
| Hindi  | India | [@Debu72](https://github.com/Debu72) | [`hi_IN.json`](translations/hi_IN.json) |
| Indonesian  | Indonesia | [@firmw4](https://github.com/firmw4) | [`id_ID.json`](translations/id_ID.json) |
| Italian  | Italy | [@LegendaryITA](https://github.com/LegendaryITA) | [`it_IT.json`](translations/it_IT.json) |
| Japanese  | Japan | [@taxi13245](https://github.com/taxi13245) | [`ja_JP.json`](translations/ja_JP.json) |
| Korean  | Korea | [@onlydev](https://translate.codeberg.org/user/onlydev) | [`ko.json`](translations/ko.json) |
| Persian  | Iran | [@Stamili](https://github.com/Stamili) | [`fa_IR.json`](translations/fa_IR.json) |
| Polish  | Poland | [@pantin](https://translate.codeberg.org/user/pantin), [@KOXXPL](https://github.com/KOXXPL) | [`pl_PL.json`](translations/pl_PL.json) |
| Português  | Brasil | [@mbdpym](https://github.com/mbdpym) | [`pt_BR.json`](translations/pt_BR.json) |
| Romanian  | Romanian | [@far-se](https://translate.codeberg.org/user/far-se) | [`ro.json`](translations/ro.json) |
| Russian  | Russia | [@sodiel](https://github.com/sodiel), [@Lowara1243](https://github.com/Lowara1243), [@VerySweetBread](https://github.com/VerySweetBread) | [`ru_RU.json`](translations/ru_RU.json) |
| Serbian  | Serbia | [@nexi](https://translate.codeberg.org/user/nexi) | [`sr_RS.json`](translations/sr_RS.json) |
| Slovenian  | Slovenia | [@BosnianPrince97](https://github.com/BosnianPrince97) | [`sl.json`](translations/sl.json) |
| Tamil  | India | [@srshankar](https://translate.codeberg.org/user/srshankar) | [`ta.json`](translations/ta.json) |
| Turkish  | Turkey | [@jericho909](https://github.com/jericho909) | [`tr_TR.json`](translations/tr_TR.json) |
| Українська  | Ukraine | [@sweeteBatata](https://github.com/sweeteBatata) | [`uk_UA.json`](translations/uk_UA.json) |
| Ukrainian  | Ukraine | [@Batata](https://translate.codeberg.org/user/Batata), [@SomeTr](https://translate.codeberg.org/user/SomeTr) | [`uk_UA.json`](translations/uk_UA.json) |
| Urdu  | Pakistan | [@rehan5039](https://github.com/rehan5039) | [`ur_PK.json`](translations/ur_PK.json) |
| Vietnamese  | Vietnam | [@MikazukiReina 🌺](https://github.com/MikazukiReina) | [`vi_VN.json`](translations/vi_VN.json) |
| 繁體中文  | Taiwan | [@xqsart](https://github.com/xqsart) | [`zh_tw.json`](translations/zh_tw.json) |
| 简体中文  | China | [@xqsart](https://github.com/xqsart), [@monstorix](https://github.com/monstorix) | [`zh_cn.json`](translations/zh_cn.json) |
---

<a href="https://translate.codeberg.org/engage/namida-translations/">
<img src="https://translate.codeberg.org/widget/namida-translations/namicomponent/multi-auto.svg" alt="Translation status" />
</a>
