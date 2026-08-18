"""쇼핑이 사람에게 하는 말 — **영어가 원문이고 번역은 여기 모인다**.

## 왜 이 파일이 있나

쇼핑이 코스모스 저장소 안에 있던 동안에는 문구가 코어 카탈로그(`cosmos/i18n/*.json`)에
살았고, 코어의 그물이 *"다섯 언어에 답이 있는가"* 를 검사해 주었다. 마켓으로 나온
지금 그 그물의 눈은 코어 소스만 본다 — 즉 ★여기서 새 문구를 쓰면 아무도 검사하지
않고, 그 언어 사용자는 조용히 영어를 본다★.

그래서 번역을 **에이전트가 지고 다닌다**(Lingua가 `lingua_i18n.py`로 하는 것과 같다).
검사도 함께 온다: `tests/test_i18n.py`가 이 파일의 표와 실제 호출을 대조한다.

## 구조 — 코어와 **같은 규칙**이다

    영어 원문이 키 · 언어별 표가 값 · 없으면 **영어가 그대로** 나온다

빈칸으로 두지 않는 이유: 빈 문자열은 사용자가 **고장으로 읽는다**.

## 모르는 문구는 코어에게 물어본다

`Unknown`·`Price unknown` 같은 것은 화면 어휘라 코어에도 있다. 두 벌로 적으면
언젠가 한쪽만 고쳐지므로, 우리 표에 없으면 **코어 카탈로그로 넘긴다**.
"""
from __future__ import annotations

LANGUAGES = ("ko", "ja", "de", "es", "fr")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ko": {
        "Alright, I will stop bringing up {title}.": "알겠어요, {title}은(는) 이제 안 꺼낼게요.",
        "Best pick": "추천",
        "Cheapest": "최저가",
        "Could not remember the checkout: {detail}": "결제 기록을 못 남겼어요: {detail}",
        "Could not save the screen state: {detail}": "화면 상태를 못 저장했어요: {detail}",
        "Could not tidy old candidates: {detail}": "옛 후보를 못 정리했어요: {detail}",
        "Could not tidy the candidates: {detail}": "후보를 못 정리했어요: {detail}",
        "Could not write down what you decided: {detail}": "말씀하신 걸 못 적었어요: {detail}",
        "Go and look": "보러 가기",
        "Got it -- {title} is yours. I will stop watching that price.":
            "네, {title} 사셨군요. 그 값은 이제 안 지켜볼게요.",
        "Help me buy the best pick": "추천 상품 결제 도와줘",
        "I could not find '{query}'. Could you say it a little differently?":
            "'{query}'을(를) 못 찾았어요. 조금 다르게 말씀해 주시겠어요?",
        "I could not write that down.": "그건 못 적었어요.",
        "I do not have a link for {title}.": "{title}의 주소를 갖고 있지 않아요.",
        "I lined up {count} of them on the screen.": "화면에 {count}개를 늘어놨어요.",
        "I lost track of that one — search again and I will line them up.":
            "그건 놓쳤어요 — 다시 찾으면 늘어놓을게요.",
        "I tidied the results for '{query}' onto the screen.":
            "'{query}' 결과를 화면에 정리했어요.",
        "Last time you went to checkout for {title}. Did you get it?":
            "지난번에 {title} 결제까지 가셨어요. 사셨나요?",
        "Noted -- still looking at {title}.": "알겠어요 — {title}은(는) 아직 보는 중이시군요.",
        "Now {price} at {seller}.": "지금 {seller}에서 {price}이에요.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "{total}개 중 {first}~{last}번이에요. {pages}쪽 중 {page}쪽.",
        "Opened {title}.": "{title}을(를) 열었어요.",
        "Previous": "이전",
        "Price trend": "가격 흐름",
        "Price unknown": "가격 모름",
        "Say 'show the next ones' for more.": "더 보시려면 '다음 보기'라고 말씀하세요.",
        "Search failed: {detail}": "검색이 실패했어요: {detail}",
        "Show me": "보여줘",
        "Show the next ones": "다음 보기",
        "Tell me what to look for.": "무엇을 찾을지 말씀해 주세요.",
        "That is the last of them.": "이게 마지막이에요.",
        "There is no list open yet — tell me what to look for.":
            "아직 펼쳐 둔 목록이 없어요 — 무엇을 찾을지 말씀해 주세요.",
        "This is already the first page.": "이미 첫 쪽이에요.",
        "What shall I look for? Ask me out loud and I will compare the options here.":
            "무엇을 찾아 드릴까요? 말로 시키시면 여기서 견줘 드릴게요.",
        "Which one? Search for it and I will line them up.":
            "어느 것 말씀이세요? 찾아보시면 늘어놓을게요.",
        # ★검색어도 언어를 탄다★ 한국어 낱말을 박아 두면 다른 언어 사용자는 엉뚱한
        # 결과를 받는다 — 표시문이 아니라 **기능**이 언어에 묶인 것이다.
        "buy price review": "구매 가격 후기",
        "the shop": "그 판매처",
        "{title} is not showing up right now.": "{title}이(가) 지금은 안 보여요.",
        "{title} is {amount} cheaper than when you looked.":
            "{title}, 보셨을 때보다 {amount} 내렸어요.",
        "{title} went up by {amount}.": "{title}이(가) {amount} 올랐어요.",
        "{title}, which you were looking at last time, went down by {amount}.":
            "지난번에 보시던 {title}, {amount} 내렸어요.",
    },
    "ja": {
        "Alright, I will stop bringing up {title}.": "わかりました、{title}はもう出しません。",
        "Best pick": "おすすめ",
        "Cheapest": "最安",
        "Could not remember the checkout: {detail}": "決済の記録を残せませんでした: {detail}",
        "Could not save the screen state: {detail}": "画面の状態を保存できませんでした: {detail}",
        "Could not tidy old candidates: {detail}": "古い候補を整理できませんでした: {detail}",
        "Could not tidy the candidates: {detail}": "候補を整理できませんでした: {detail}",
        "Could not write down what you decided: {detail}": "お返事を記録できませんでした: {detail}",
        "Go and look": "見に行く",
        "Got it -- {title} is yours. I will stop watching that price.":
            "了解です、{title}を購入されたのですね。価格の見張りはやめます。",
        "Help me buy the best pick": "おすすめの購入を手伝って",
        "I could not find '{query}'. Could you say it a little differently?":
            "「{query}」が見つかりませんでした。少し言い方を変えていただけますか？",
        "I could not write that down.": "それは記録できませんでした。",
        "I do not have a link for {title}.": "{title}のリンクを持っていません。",
        "I lined up {count} of them on the screen.": "画面に{count}件並べました。",
        "I lost track of that one — search again and I will line them up.":
            "それは見失いました — もう一度探せば並べます。",
        "I tidied the results for '{query}' onto the screen.":
            "「{query}」の結果を画面にまとめました。",
        "Last time you went to checkout for {title}. Did you get it?":
            "前回 {title} の決済まで進みました。購入されましたか？",
        "Noted -- still looking at {title}.": "了解です — {title}はまだ検討中ですね。",
        "Now {price} at {seller}.": "今は{seller}で{price}です。",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "{total}件中 {first}〜{last}番目です。{pages}ページ中 {page}ページ目。",
        "Opened {title}.": "{title}を開きました。",
        "Previous": "前へ",
        "Price trend": "価格の推移",
        "Price unknown": "価格不明",
        "Say 'show the next ones' for more.": "もっと見るには「次を見せて」と言ってください。",
        "Search failed: {detail}": "検索に失敗しました: {detail}",
        "Show me": "見せて",
        "Show the next ones": "次を見せて",
        "Tell me what to look for.": "何を探すか教えてください。",
        "That is the last of them.": "これで最後です。",
        "There is no list open yet — tell me what to look for.":
            "まだ開いているリストがありません — 何を探すか教えてください。",
        "This is already the first page.": "すでに最初のページです。",
        "What shall I look for? Ask me out loud and I will compare the options here.":
            "何をお探ししましょう？話しかけていただければ、ここで見比べます。",
        "Which one? Search for it and I will line them up.":
            "どれのことでしょう？探せば並べます。",
        "buy price review": "購入 価格 レビュー",
        "the shop": "その店",
        "{title} is not showing up right now.": "{title}は今は見当たりません。",
        "{title} is {amount} cheaper than when you looked.":
            "{title}、ご覧になった時より{amount}安くなっています。",
        "{title} went up by {amount}.": "{title}が{amount}上がりました。",
        "{title}, which you were looking at last time, went down by {amount}.":
            "前回ご覧になっていた{title}、{amount}下がりました。",
    },
    "de": {
        "Alright, I will stop bringing up {title}.": "Gut, ich bringe {title} nicht mehr zur Sprache.",
        "Best pick": "Empfehlung",
        "Cheapest": "Günstigster",
        "Could not remember the checkout: {detail}": "Konnte den Kauf nicht festhalten: {detail}",
        "Could not save the screen state: {detail}": "Konnte den Bildschirmzustand nicht sichern: {detail}",
        "Could not tidy old candidates: {detail}": "Konnte alte Kandidaten nicht aufräumen: {detail}",
        "Could not tidy the candidates: {detail}": "Konnte die Kandidaten nicht aufräumen: {detail}",
        "Could not write down what you decided: {detail}": "Konnte deine Entscheidung nicht notieren: {detail}",
        "Go and look": "Ansehen",
        "Got it -- {title} is yours. I will stop watching that price.":
            "Alles klar — {title} gehört dir. Ich beobachte den Preis nicht weiter.",
        "Help me buy the best pick": "Hilf mir, die Empfehlung zu kaufen",
        "I could not find '{query}'. Could you say it a little differently?":
            "Ich konnte „{query}“ nicht finden. Kannst du es etwas anders sagen?",
        "I could not write that down.": "Das konnte ich nicht notieren.",
        "I do not have a link for {title}.": "Für {title} habe ich keinen Link.",
        "I lined up {count} of them on the screen.": "Ich habe {count} davon auf dem Bildschirm aufgereiht.",
        "I lost track of that one — search again and I will line them up.":
            "Das habe ich aus den Augen verloren — such noch einmal, dann reihe ich sie auf.",
        "I tidied the results for '{query}' onto the screen.":
            "Ich habe die Ergebnisse zu „{query}“ auf den Bildschirm sortiert.",
        "Last time you went to checkout for {title}. Did you get it?":
            "Beim letzten Mal warst du bei {title} an der Kasse. Hast du es gekauft?",
        "Noted -- still looking at {title}.": "Notiert — du schaust dir {title} noch an.",
        "Now {price} at {seller}.": "Jetzt {price} bei {seller}.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "Nummern {first} bis {last} von {total}, Seite {page} von {pages}.",
        "Opened {title}.": "{title} geöffnet.",
        "Previous": "Zurück",
        "Price trend": "Preisverlauf",
        "Price unknown": "Preis unbekannt",
        "Say 'show the next ones' for more.": "Sag „Zeig die nächsten“, um mehr zu sehen.",
        "Search failed: {detail}": "Die Suche ist fehlgeschlagen: {detail}",
        "Show me": "Zeig mir",
        "Show the next ones": "Zeig die nächsten",
        "Tell me what to look for.": "Sag mir, wonach ich suchen soll.",
        "That is the last of them.": "Das war der letzte.",
        "There is no list open yet — tell me what to look for.":
            "Es ist noch keine Liste offen — sag mir, wonach ich suchen soll.",
        "This is already the first page.": "Das ist bereits die erste Seite.",
        "What shall I look for? Ask me out loud and I will compare the options here.":
            "Wonach soll ich suchen? Sag es laut, dann vergleiche ich hier.",
        "Which one? Search for it and I will line them up.":
            "Welches denn? Such danach, dann reihe ich sie auf.",
        "buy price review": "kaufen Preis Test",
        "the shop": "dem Shop",
        "{title} is not showing up right now.": "{title} taucht gerade nicht auf.",
        "{title} is {amount} cheaper than when you looked.":
            "{title} ist {amount} günstiger als beim letzten Blick.",
        "{title} went up by {amount}.": "{title} ist um {amount} gestiegen.",
        "{title}, which you were looking at last time, went down by {amount}.":
            "{title}, das du dir zuletzt angesehen hast, ist um {amount} gefallen.",
    },
    "es": {
        "Alright, I will stop bringing up {title}.": "De acuerdo, dejaré de mencionar {title}.",
        "Best pick": "Recomendación",
        "Cheapest": "Más barato",
        "Could not remember the checkout: {detail}": "No pude guardar el pago: {detail}",
        "Could not save the screen state: {detail}": "No pude guardar el estado de la pantalla: {detail}",
        "Could not tidy old candidates: {detail}": "No pude ordenar los candidatos antiguos: {detail}",
        "Could not tidy the candidates: {detail}": "No pude ordenar los candidatos: {detail}",
        "Could not write down what you decided: {detail}": "No pude anotar tu decisión: {detail}",
        "Go and look": "Ir a verlo",
        "Got it -- {title} is yours. I will stop watching that price.":
            "Entendido: {title} ya es tuyo. Dejo de vigilar ese precio.",
        "Help me buy the best pick": "Ayúdame a comprar la recomendación",
        "I could not find '{query}'. Could you say it a little differently?":
            "No encontré «{query}». ¿Puedes decirlo de otra manera?",
        "I could not write that down.": "Eso no pude anotarlo.",
        "I do not have a link for {title}.": "No tengo un enlace para {title}.",
        "I lined up {count} of them on the screen.": "He puesto {count} en la pantalla.",
        "I lost track of that one — search again and I will line them up.":
            "Perdí el rastro de ese — busca otra vez y los pongo en fila.",
        "I tidied the results for '{query}' onto the screen.":
            "He ordenado los resultados de «{query}» en la pantalla.",
        "Last time you went to checkout for {title}. Did you get it?":
            "La última vez llegaste al pago de {title}. ¿Lo compraste?",
        "Noted -- still looking at {title}.": "Anotado: sigues mirando {title}.",
        "Now {price} at {seller}.": "Ahora {price} en {seller}.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "Números {first} a {last} de {total}, página {page} de {pages}.",
        "Opened {title}.": "He abierto {title}.",
        "Previous": "Anterior",
        "Price trend": "Evolución del precio",
        "Price unknown": "Precio desconocido",
        "Say 'show the next ones' for more.": "Di «muéstrame los siguientes» para ver más.",
        "Search failed: {detail}": "La búsqueda falló: {detail}",
        "Show me": "Muéstramelo",
        "Show the next ones": "Muéstrame los siguientes",
        "Tell me what to look for.": "Dime qué buscar.",
        "That is the last of them.": "Ese es el último.",
        "There is no list open yet — tell me what to look for.":
            "Todavía no hay ninguna lista abierta — dime qué buscar.",
        "This is already the first page.": "Esta ya es la primera página.",
        "What shall I look for? Ask me out loud and I will compare the options here.":
            "¿Qué busco? Pídemelo en voz alta y comparo las opciones aquí.",
        "Which one? Search for it and I will line them up.":
            "¿Cuál? Búscalo y los pongo en fila.",
        "buy price review": "comprar precio opiniones",
        "the shop": "la tienda",
        "{title} is not showing up right now.": "{title} no aparece en este momento.",
        "{title} is {amount} cheaper than when you looked.":
            "{title} está {amount} más barato que cuando lo miraste.",
        "{title} went up by {amount}.": "{title} subió {amount}.",
        "{title}, which you were looking at last time, went down by {amount}.":
            "{title}, que mirabas la última vez, bajó {amount}.",
    },
    "fr": {
        "Alright, I will stop bringing up {title}.": "D'accord, je ne reparlerai plus de {title}.",
        "Best pick": "Recommandation",
        "Cheapest": "Le moins cher",
        "Could not remember the checkout: {detail}": "Je n'ai pas pu noter le paiement : {detail}",
        "Could not save the screen state: {detail}": "Je n'ai pas pu enregistrer l'état de l'écran : {detail}",
        "Could not tidy old candidates: {detail}": "Je n'ai pas pu ranger les anciens candidats : {detail}",
        "Could not tidy the candidates: {detail}": "Je n'ai pas pu ranger les candidats : {detail}",
        "Could not write down what you decided: {detail}": "Je n'ai pas pu noter ta décision : {detail}",
        "Go and look": "Aller voir",
        "Got it -- {title} is yours. I will stop watching that price.":
            "Compris — {title} est à toi. J'arrête de surveiller ce prix.",
        "Help me buy the best pick": "Aide-moi à acheter la recommandation",
        "I could not find '{query}'. Could you say it a little differently?":
            "Je n'ai pas trouvé « {query} ». Peux-tu le dire autrement ?",
        "I could not write that down.": "Ça, je n'ai pas pu le noter.",
        "I do not have a link for {title}.": "Je n'ai pas de lien pour {title}.",
        "I lined up {count} of them on the screen.": "J'en ai aligné {count} à l'écran.",
        "I lost track of that one — search again and I will line them up.":
            "J'ai perdu celui-là de vue — relance la recherche et je les aligne.",
        "I tidied the results for '{query}' onto the screen.":
            "J'ai rangé les résultats de « {query} » à l'écran.",
        "Last time you went to checkout for {title}. Did you get it?":
            "La dernière fois tu es allé jusqu'au paiement de {title}. Tu l'as acheté ?",
        "Noted -- still looking at {title}.": "Noté — tu regardes encore {title}.",
        "Now {price} at {seller}.": "Maintenant {price} chez {seller}.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "Numéros {first} à {last} sur {total}, page {page} sur {pages}.",
        "Opened {title}.": "{title} ouvert.",
        "Previous": "Précédent",
        "Price trend": "Évolution du prix",
        "Price unknown": "Prix inconnu",
        "Say 'show the next ones' for more.": "Dis « montre les suivants » pour en voir plus.",
        "Search failed: {detail}": "La recherche a échoué : {detail}",
        "Show me": "Montre-moi",
        "Show the next ones": "Montre les suivants",
        "Tell me what to look for.": "Dis-moi quoi chercher.",
        "That is the last of them.": "C'est le dernier.",
        "There is no list open yet — tell me what to look for.":
            "Aucune liste n'est ouverte pour l'instant — dis-moi quoi chercher.",
        "This is already the first page.": "C'est déjà la première page.",
        "What shall I look for? Ask me out loud and I will compare the options here.":
            "Que dois-je chercher ? Demande-le à voix haute et je compare ici.",
        "Which one? Search for it and I will line them up.":
            "Lequel ? Cherche-le et je les aligne.",
        "buy price review": "acheter prix avis",
        "the shop": "la boutique",
        "{title} is not showing up right now.": "{title} n'apparaît pas en ce moment.",
        "{title} is {amount} cheaper than when you looked.":
            "{title} est moins cher de {amount} qu'au moment où tu l'as regardé.",
        "{title} went up by {amount}.": "{title} a augmenté de {amount}.",
        "{title}, which you were looking at last time, went down by {amount}.":
            "{title}, que tu regardais la dernière fois, a baissé de {amount}.",
    },
}


def t(text: str, /, lang: str | None = None, **params) -> str:
    """영어 원문을 사용자의 언어로. 모르면 **영어가 그대로** 나온다.

    ★빈칸으로 두지 않는다★ 빈 문자열은 사용자가 고장으로 읽는다.

    ★우리 표에 없으면 코어에게 물어본다★ `Unknown`처럼 화면 어휘에 이미 있는 것은
    두 벌로 적지 않는다 — 두 벌이 되면 언젠가 한쪽만 고쳐진다.
    """
    from cosmos.core import i18n as core
    code = lang or core.active()
    row = TRANSLATIONS.get(code, {})
    if text in row:
        return row[text].format(**params) if params else row[text]
    return core.t(text, lang=code, **params)
