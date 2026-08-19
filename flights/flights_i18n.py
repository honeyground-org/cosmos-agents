"""항공권 도우미가 사람에게 하는 말 — **영어가 원문이고 번역은 여기 모인다**.

## 왜 이 파일이 있나

이 에이전트가 코스모스 저장소 안에 있던 동안에는 문구가 코어 카탈로그
(`cosmos/i18n/*.json`)에 살았고, 코어의 그물이 *"다섯 언어에 답이 있는가"* 를
검사해 주었다. 마켓으로 나온 지금 그 그물의 눈은 코어 소스만 본다 — 즉 ★여기서
새 문구를 쓰면 아무도 검사하지 않고, 그 언어 사용자는 조용히 영어를 본다★.

그래서 번역을 **에이전트가 지고 다닌다**(쇼핑·Lingua가 하는 것과 같다).
검사도 함께 온다: `tests/test_i18n.py`가 이 표와 실제 호출을 대조한다.

## 구조 — 코어와 **같은 규칙**이다

    영어 원문이 키 · 언어별 표가 값 · 없으면 **영어가 그대로** 나온다

빈칸으로 두지 않는 이유: 빈 문자열은 사용자가 **고장으로 읽는다**.

## 코어에도 있는 문구를 여기 **함께** 두는 이유

`Previous`·`Show the next ones` 같은 것은 화면 어휘라 코어에도 있다. 그래도 우리
표에 함께 둔다 — 코어를 믿고 비워 두면, 코어가 언젠가 그 줄을 치웠을 때 ★아무도
모르게★ 영어로 돌아간다. 우리 표에 없는 것만 코어에게 묻는다.
"""
from __future__ import annotations

LANGUAGES = ("ko", "ja", "de", "es", "fr")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ko": {
        "Round trip": "왕복",
        "One way": "편도",
        "return": "왕복",
        "nonstop": "직항",
        "I found {count} flights, but none on {airline}.":
            "항공편 {count}개를 찾았는데 {airline} 편은 없었어요.",
        "I found {count} flights, but none of them are nonstop.":
            "항공편 {count}개를 찾았는데 직항은 없었어요.",
        "I found {count} flights, but none of them are nonstop on {airline}. Shall I drop one of those?":
            "항공편 {count}개를 찾았는데 {airline} 직항은 없었어요. 조건 하나를 뺄까요?",
        "Best now: {what}, {stops}.": "지금 제일 나은 건 {what}, {stops}.",
        "Best pick": "추천",
        "Cheapest": "최저가",
        "Cheapest of the ones with {stops}.": "{stops} 중에서는 가장 쌉니다.",
        "Could not save the screen state: {detail}": "화면 상태를 저장하지 못했어요: {detail}",
        "Fare trend": "값 흐름",
        "Go and look": "보러 가기",
        "Got it — I will stop bringing up {route}.": "알겠어요 — {route} 이야기는 그만 꺼낼게요.",
        "Got it — you booked {route}. I will stop watching the fare.":
            "알겠어요 — {route} 예약하셨군요. 값은 그만 볼게요.",
        "Got it — {route} is still open. I will keep an eye on the fare.":
            "알겠어요 — {route} 은(는) 아직 열려 있네요. 값은 계속 볼게요.",
        "I am not tracking {route}.": "{route} 은(는) 지켜보고 있지 않아요.",
        "I booked it": "예약했어요",
        "I could not find flights for {route}. Try naming the airports, or a different date.":
            "{route} 항공편을 못 찾았어요. 공항 이름을 대거나 다른 날짜로 해 보세요.",
        "I found nothing for {route}.": "{route} 은(는) 아무것도 못 찾았어요.",
        "I lined up {count} of them on the screen.": "화면에 {count}개를 나란히 놓았어요.",
        "I was not tracking {route}.": "{route} 은(는) 원래 안 보고 있었어요.",
        "I will stop tracking {route}.": "{route} 은(는) 그만 볼게요.",
        "It has been a while since you looked at this one. ": "이건 보신 지 꽤 됐네요. ",
        "Nonstop": "직항",
        "Now {price} with {airline}, {stops}.": "지금 {airline} {price}, {stops}.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "전체 {total}개 중 {first}~{last}번, {pages}쪽 중 {page}쪽이에요.",
        "Previous": "이전",
        "Price unknown": "가격 모름",
        "Routes you have been watching:": "지켜보고 계신 노선:",
        "Say 'show the next ones' for more.": "더 보시려면 '다음 보기'라고 하세요.",
        "Show me": "보여 줘",
        "Show the next ones": "다음 보기",
        "Tell me where you want to fly to.": "어디로 가시는지 말씀해 주세요.",
        "Tell me which route to stop tracking.": "어느 노선을 그만 볼지 말씀해 주세요.",
        "That is already the first page.": "여기가 이미 첫 쪽이에요.",
        "That is the last page.": "여기가 마지막 쪽이에요.",
        "That route is down {amount} since you last looked. ":
            "그 노선은 지난번보다 {amount} 내렸어요. ",
        "That route is up {amount} since you last looked. ": "그 노선은 지난번보다 {amount} 올랐어요. ",
        "The flight search did not work: {detail}": "항공권 검색이 안 됐어요: {detail}",
        "There is nothing on the screen to page through yet.": "아직 넘겨 볼 것이 화면에 없어요.",
        "This route is down {amount} since you last looked. Did you book it?":
            "이 노선은 지난번보다 {amount} 내렸어요. 예약하셨나요?",
        "This route is up {amount} since you last looked.": "이 노선은 지난번보다 {amount} 올랐어요.",
        "Where do you want to fly? Ask me out loud and I will compare the options here.":
            "어디로 가시겠어요? 말로 물어보시면 여기에 나란히 놓고 견줘 드릴게요.",
        "Which trip do you mean?": "어느 여행 말씀이세요?",
        "You booked this one — I am not watching the fare any more.":
            "이건 예약하셨죠 — 값은 이제 안 봐요.",
        "You have not looked at any flights with me yet.": "아직 저와 함께 본 항공편이 없어요.",
        "You said you booked this one. ": "이건 예약했다고 하셨죠. ",
        "flight ticket price": "항공권 가격",
        "last seen at {price}": "마지막으로 본 값 {price}",
        "the airline": "항공사",
        "{h}h": "{h}시간",
        "{h}h {m}m": "{h}시간 {m}분",
        "{m}m": "{m}분",
        "{n} stop": "{n}회 경유",
        "{n} stops": "{n}회 경유",
        "{route} is {amount} cheaper than when you looked.":
            "{route} 이(가) 보셨을 때보다 {amount} 싸졌어요.",
    },
    "ja": {
        "Round trip": "往復",
        "One way": "片道",
        "return": "往復",
        "nonstop": "直行",
        "I found {count} flights, but none on {airline}.":
            "{count}件見つかりましたが、{airline}の便はありませんでした。",
        "I found {count} flights, but none of them are nonstop.":
            "{count}件見つかりましたが、直行便はありませんでした。",
        "I found {count} flights, but none of them are nonstop on {airline}. Shall I drop one of those?":
            "{count}件見つかりましたが、{airline}の直行便はありませんでした。条件を一つ外しますか。",
        "Best now: {what}, {stops}.": "今のいちばんは {what}、{stops}。",
        "Best pick": "おすすめ",
        "Cheapest": "最安",
        "Cheapest of the ones with {stops}.": "{stops}の中ではいちばん安いです。",
        "Could not save the screen state: {detail}": "画面の状態を保存できませんでした: {detail}",
        "Fare trend": "運賃の推移",
        "Go and look": "見に行く",
        "Got it — I will stop bringing up {route}.": "了解です — {route} の話はもうしません。",
        "Got it — you booked {route}. I will stop watching the fare.":
            "了解です — {route} を予約されたのですね。運賃はもう見ません。",
        "Got it — {route} is still open. I will keep an eye on the fare.":
            "了解です — {route} はまだ検討中ですね。運賃を見ておきます。",
        "I am not tracking {route}.": "{route} は見ていません。",
        "I booked it": "予約しました",
        "I could not find flights for {route}. Try naming the airports, or a different date.":
            "{route} の便が見つかりませんでした。空港名を指定するか、別の日付でお試しください。",
        "I found nothing for {route}.": "{route} は何も見つかりませんでした。",
        "I lined up {count} of them on the screen.": "画面に{count}件を並べました。",
        "I was not tracking {route}.": "{route} は追っていませんでした。",
        "I will stop tracking {route}.": "{route} を追うのをやめます。",
        "It has been a while since you looked at this one. ": "これはご覧になってからしばらく経っています。",
        "Nonstop": "直行便",
        "Now {price} with {airline}, {stops}.": "現在 {airline} {price}、{stops}。",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "全{total}件のうち{first}〜{last}番、{pages}ページ中{page}ページ目です。",
        "Previous": "前へ",
        "Price unknown": "価格不明",
        "Routes you have been watching:": "見ている路線:",
        "Say 'show the next ones' for more.": "続きは「次を見る」と言ってください。",
        "Show me": "見せて",
        "Show the next ones": "次を見る",
        "Tell me where you want to fly to.": "どこへ行きたいか教えてください。",
        "Tell me which route to stop tracking.": "どの路線を追うのをやめるか教えてください。",
        "That is already the first page.": "すでに最初のページです。",
        "That is the last page.": "これが最後のページです。",
        "That route is down {amount} since you last looked. ":
            "その路線は前回より {amount} 下がっています。",
        "That route is up {amount} since you last looked. ": "その路線は前回より {amount} 上がっています。",
        "The flight search did not work: {detail}": "航空券の検索ができませんでした: {detail}",
        "There is nothing on the screen to page through yet.": "まだ画面にめくるものがありません。",
        "This route is down {amount} since you last looked. Did you book it?":
            "この路線は前回より {amount} 下がりました。予約されましたか。",
        "This route is up {amount} since you last looked.": "この路線は前回より {amount} 上がりました。",
        "Where do you want to fly? Ask me out loud and I will compare the options here.":
            "どこへ行きますか。声で聞いていただければ、ここで見比べられるようにします。",
        "Which trip do you mean?": "どの旅行のことですか。",
        "You booked this one — I am not watching the fare any more.":
            "これは予約済みですね — 運賃はもう見ていません。",
        "You have not looked at any flights with me yet.": "まだ一緒に見た航空券はありません。",
        "You said you booked this one. ": "これは予約済みとおっしゃっていました。",
        "flight ticket price": "航空券 価格",
        "last seen at {price}": "最後に見た価格 {price}",
        "the airline": "航空会社",
        "{h}h": "{h}時間",
        "{h}h {m}m": "{h}時間{m}分",
        "{m}m": "{m}分",
        "{n} stop": "{n}回乗り継ぎ",
        "{n} stops": "{n}回乗り継ぎ",
        "{route} is {amount} cheaper than when you looked.":
            "{route} がご覧になった時より {amount} 安くなりました。",
    },
    "de": {
        "Round trip": "Hin und zurück",
        "One way": "Nur Hinflug",
        "return": "Rückflug",
        "nonstop": "nonstop",
        "I found {count} flights, but none on {airline}.":
            "Ich habe {count} Flüge gefunden, aber keinen mit {airline}.",
        "I found {count} flights, but none of them are nonstop.":
            "Ich habe {count} Flüge gefunden, aber keinen ohne Zwischenstopp.",
        "I found {count} flights, but none of them are nonstop on {airline}. Shall I drop one of those?":
            "Ich habe {count} Flüge gefunden, aber keinen Nonstop-Flug mit {airline}. Soll ich eine der Bedingungen weglassen?",
        "Best now: {what}, {stops}.": "Am besten jetzt: {what}, {stops}.",
        "Best pick": "Beste Wahl",
        "Cheapest": "Günstigste",
        "Cheapest of the ones with {stops}.": "Das Günstigste unter denen mit {stops}.",
        "Could not save the screen state: {detail}":
            "Der Bildschirmzustand konnte nicht gespeichert werden: {detail}",
        "Fare trend": "Preisverlauf",
        "Go and look": "Ansehen",
        "Got it — I will stop bringing up {route}.":
            "Verstanden — ich spreche {route} nicht mehr an.",
        "Got it — you booked {route}. I will stop watching the fare.":
            "Verstanden — Sie haben {route} gebucht. Ich beobachte den Preis nicht mehr.",
        "Got it — {route} is still open. I will keep an eye on the fare.":
            "Verstanden — {route} ist noch offen. Ich behalte den Preis im Auge.",
        "I am not tracking {route}.": "Ich verfolge {route} nicht.",
        "I booked it": "Ich habe gebucht",
        "I could not find flights for {route}. Try naming the airports, or a different date.":
            "Ich konnte keine Flüge für {route} finden. Nennen Sie die Flughäfen oder ein anderes Datum.",
        "I found nothing for {route}.": "Für {route} habe ich nichts gefunden.",
        "I lined up {count} of them on the screen.":
            "Ich habe {count} davon auf dem Bildschirm aufgereiht.",
        "I was not tracking {route}.": "Ich habe {route} gar nicht verfolgt.",
        "I will stop tracking {route}.": "Ich verfolge {route} nicht mehr.",
        "It has been a while since you looked at this one. ":
            "Das ist eine Weile her, seit Sie hier geschaut haben. ",
        "Nonstop": "Nonstop",
        "Now {price} with {airline}, {stops}.": "Jetzt {price} mit {airline}, {stops}.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "Nummern {first} bis {last} von {total}, Seite {page} von {pages}.",
        "Previous": "Zurück",
        "Price unknown": "Preis unbekannt",
        "Routes you have been watching:": "Strecken, die Sie beobachten:",
        "Say 'show the next ones' for more.": "Sagen Sie „Die nächsten zeigen“ für mehr.",
        "Show me": "Zeig mir",
        "Show the next ones": "Die nächsten zeigen",
        "Tell me where you want to fly to.": "Sagen Sie mir, wohin Sie fliegen möchten.",
        "Tell me which route to stop tracking.":
            "Sagen Sie mir, welche Strecke ich nicht mehr verfolgen soll.",
        "That is already the first page.": "Das ist bereits die erste Seite.",
        "That is the last page.": "Das ist die letzte Seite.",
        "That route is down {amount} since you last looked. ":
            "Diese Strecke ist seit Ihrem letzten Blick um {amount} günstiger. ",
        "That route is up {amount} since you last looked. ":
            "Diese Strecke ist seit Ihrem letzten Blick um {amount} teurer. ",
        "The flight search did not work: {detail}":
            "Die Flugsuche hat nicht funktioniert: {detail}",
        "There is nothing on the screen to page through yet.":
            "Auf dem Bildschirm gibt es noch nichts zum Blättern.",
        "This route is down {amount} since you last looked. Did you book it?":
            "Diese Strecke ist um {amount} günstiger als beim letzten Blick. Haben Sie gebucht?",
        "This route is up {amount} since you last looked.":
            "Diese Strecke ist um {amount} teurer als beim letzten Blick.",
        "Where do you want to fly? Ask me out loud and I will compare the options here.":
            "Wohin möchten Sie fliegen? Fragen Sie laut, und ich vergleiche die Optionen hier.",
        "Which trip do you mean?": "Welche Reise meinen Sie?",
        "You booked this one — I am not watching the fare any more.":
            "Diese haben Sie gebucht — ich beobachte den Preis nicht mehr.",
        "You have not looked at any flights with me yet.":
            "Sie haben mit mir noch keine Flüge angeschaut.",
        "You said you booked this one. ": "Sie sagten, diese hätten Sie gebucht. ",
        "flight ticket price": "Flugticket Preis",
        "last seen at {price}": "zuletzt gesehen für {price}",
        "the airline": "der Fluggesellschaft",
        "{h}h": "{h} Std.",
        "{h}h {m}m": "{h} Std. {m} Min.",
        "{m}m": "{m} Min.",
        "{n} stop": "{n} Zwischenstopp",
        "{n} stops": "{n} Zwischenstopps",
        "{route} is {amount} cheaper than when you looked.":
            "{route} ist {amount} günstiger als beim letzten Blick.",
    },
    "es": {
        "Round trip": "Ida y vuelta",
        "One way": "Solo ida",
        "return": "vuelta",
        "nonstop": "sin escalas",
        "I found {count} flights, but none on {airline}.":
            "He encontrado {count} vuelos, pero ninguno de {airline}.",
        "I found {count} flights, but none of them are nonstop.":
            "He encontrado {count} vuelos, pero ninguno sin escalas.",
        "I found {count} flights, but none of them are nonstop on {airline}. Shall I drop one of those?":
            "He encontrado {count} vuelos, pero ninguno sin escalas de {airline}. ¿Quito una de esas condiciones?",
        "Best now: {what}, {stops}.": "Lo mejor ahora: {what}, {stops}.",
        "Best pick": "Mejor opción",
        "Cheapest": "Más barato",
        "Cheapest of the ones with {stops}.": "El más barato entre los de {stops}.",
        "Could not save the screen state: {detail}":
            "No se pudo guardar el estado de la pantalla: {detail}",
        "Fare trend": "Evolución de la tarifa",
        "Go and look": "Ir a ver",
        "Got it — I will stop bringing up {route}.":
            "Entendido — dejaré de mencionar {route}.",
        "Got it — you booked {route}. I will stop watching the fare.":
            "Entendido — reservaste {route}. Dejaré de vigilar la tarifa.",
        "Got it — {route} is still open. I will keep an eye on the fare.":
            "Entendido — {route} sigue abierta. Vigilaré la tarifa.",
        "I am not tracking {route}.": "No estoy siguiendo {route}.",
        "I booked it": "Ya lo reservé",
        "I could not find flights for {route}. Try naming the airports, or a different date.":
            "No he encontrado vuelos para {route}. Prueba a nombrar los aeropuertos o con otra fecha.",
        "I found nothing for {route}.": "No he encontrado nada para {route}.",
        "I lined up {count} of them on the screen.":
            "He puesto {count} de ellos en la pantalla.",
        "I was not tracking {route}.": "No estaba siguiendo {route}.",
        "I will stop tracking {route}.": "Dejaré de seguir {route}.",
        "It has been a while since you looked at this one. ":
            "Hace tiempo que no mirabas esta. ",
        "Nonstop": "Sin escalas",
        "Now {price} with {airline}, {stops}.": "Ahora {price} con {airline}, {stops}.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "Números {first} a {last} de {total}, página {page} de {pages}.",
        "Previous": "Anterior",
        "Price unknown": "Precio desconocido",
        "Routes you have been watching:": "Rutas que estás siguiendo:",
        "Say 'show the next ones' for more.": "Di «ver los siguientes» para más.",
        "Show me": "Muéstramelo",
        "Show the next ones": "Ver los siguientes",
        "Tell me where you want to fly to.": "Dime a dónde quieres volar.",
        "Tell me which route to stop tracking.": "Dime qué ruta debo dejar de seguir.",
        "That is already the first page.": "Esta ya es la primera página.",
        "That is the last page.": "Esta es la última página.",
        "That route is down {amount} since you last looked. ":
            "Esa ruta ha bajado {amount} desde la última vez que la miraste. ",
        "That route is up {amount} since you last looked. ":
            "Esa ruta ha subido {amount} desde la última vez que la miraste. ",
        "The flight search did not work: {detail}":
            "La búsqueda de vuelos no funcionó: {detail}",
        "There is nothing on the screen to page through yet.":
            "Todavía no hay nada en la pantalla para pasar página.",
        "This route is down {amount} since you last looked. Did you book it?":
            "Esta ruta ha bajado {amount} desde la última vez. ¿La reservaste?",
        "This route is up {amount} since you last looked.":
            "Esta ruta ha subido {amount} desde la última vez.",
        "Where do you want to fly? Ask me out loud and I will compare the options here.":
            "¿A dónde quieres volar? Pregúntamelo en voz alta y compararé las opciones aquí.",
        "Which trip do you mean?": "¿A qué viaje te refieres?",
        "You booked this one — I am not watching the fare any more.":
            "Este ya lo reservaste — ya no vigilo la tarifa.",
        "You have not looked at any flights with me yet.":
            "Todavía no has mirado ningún vuelo conmigo.",
        "You said you booked this one. ": "Dijiste que ya reservaste este. ",
        "flight ticket price": "billete de avión precio",
        "last seen at {price}": "visto por última vez a {price}",
        "the airline": "la aerolínea",
        "{h}h": "{h} h",
        "{h}h {m}m": "{h} h {m} min",
        "{m}m": "{m} min",
        "{n} stop": "{n} escala",
        "{n} stops": "{n} escalas",
        "{route} is {amount} cheaper than when you looked.":
            "{route} está {amount} más barato que cuando lo miraste.",
    },
    "fr": {
        "Round trip": "Aller-retour",
        "One way": "Aller simple",
        "return": "retour",
        "nonstop": "sans escale",
        "I found {count} flights, but none on {airline}.":
            "J'ai trouvé {count} vols, mais aucun avec {airline}.",
        "I found {count} flights, but none of them are nonstop.":
            "J'ai trouvé {count} vols, mais aucun sans escale.",
        "I found {count} flights, but none of them are nonstop on {airline}. Shall I drop one of those?":
            "J'ai trouvé {count} vols, mais aucun sans escale avec {airline}. Dois-je lever une de ces conditions ?",
        "Best now: {what}, {stops}.": "Le meilleur maintenant : {what}, {stops}.",
        "Best pick": "Meilleur choix",
        "Cheapest": "Le moins cher",
        "Cheapest of the ones with {stops}.": "Le moins cher parmi ceux avec {stops}.",
        "Could not save the screen state: {detail}":
            "Impossible d'enregistrer l'état de l'écran : {detail}",
        "Fare trend": "Évolution du tarif",
        "Go and look": "Aller voir",
        "Got it — I will stop bringing up {route}.":
            "Compris — je ne mentionnerai plus {route}.",
        "Got it — you booked {route}. I will stop watching the fare.":
            "Compris — vous avez réservé {route}. J'arrête de surveiller le tarif.",
        "Got it — {route} is still open. I will keep an eye on the fare.":
            "Compris — {route} est toujours ouvert. Je garde un œil sur le tarif.",
        "I am not tracking {route}.": "Je ne suis pas {route}.",
        "I booked it": "J'ai réservé",
        "I could not find flights for {route}. Try naming the airports, or a different date.":
            "Je n'ai pas trouvé de vols pour {route}. Essayez de nommer les aéroports ou une autre date.",
        "I found nothing for {route}.": "Je n'ai rien trouvé pour {route}.",
        "I lined up {count} of them on the screen.": "J'en ai aligné {count} à l'écran.",
        "I was not tracking {route}.": "Je ne suivais pas {route}.",
        "I will stop tracking {route}.": "Je cesse de suivre {route}.",
        "It has been a while since you looked at this one. ":
            "Cela fait un moment que vous n'avez pas regardé celui-ci. ",
        "Nonstop": "Sans escale",
        "Now {price} with {airline}, {stops}.":
            "Maintenant {price} avec {airline}, {stops}.",
        "Numbers {first} to {last} of {total}, page {page} of {pages}.":
            "Numéros {first} à {last} sur {total}, page {page} sur {pages}.",
        "Previous": "Précédent",
        "Price unknown": "Prix inconnu",
        "Routes you have been watching:": "Itinéraires que vous suivez :",
        "Say 'show the next ones' for more.": "Dites « voir les suivants » pour la suite.",
        "Show me": "Montre-moi",
        "Show the next ones": "Voir les suivants",
        "Tell me where you want to fly to.": "Dites-moi où vous voulez aller.",
        "Tell me which route to stop tracking.":
            "Dites-moi quel itinéraire je dois cesser de suivre.",
        "That is already the first page.": "C'est déjà la première page.",
        "That is the last page.": "C'est la dernière page.",
        "That route is down {amount} since you last looked. ":
            "Cet itinéraire a baissé de {amount} depuis votre dernière visite. ",
        "That route is up {amount} since you last looked. ":
            "Cet itinéraire a augmenté de {amount} depuis votre dernière visite. ",
        "The flight search did not work: {detail}":
            "La recherche de vols n'a pas fonctionné : {detail}",
        "There is nothing on the screen to page through yet.":
            "Il n'y a encore rien à faire défiler à l'écran.",
        "This route is down {amount} since you last looked. Did you book it?":
            "Cet itinéraire a baissé de {amount} depuis la dernière fois. L'avez-vous réservé ?",
        "This route is up {amount} since you last looked.":
            "Cet itinéraire a augmenté de {amount} depuis la dernière fois.",
        "Where do you want to fly? Ask me out loud and I will compare the options here.":
            "Où voulez-vous aller ? Demandez-le à voix haute et je comparerai les options ici.",
        "Which trip do you mean?": "De quel voyage parlez-vous ?",
        "You booked this one — I am not watching the fare any more.":
            "Vous avez réservé celui-ci — je ne surveille plus le tarif.",
        "You have not looked at any flights with me yet.":
            "Vous n'avez encore consulté aucun vol avec moi.",
        "You said you booked this one. ": "Vous aviez dit avoir réservé celui-ci. ",
        "flight ticket price": "billet d'avion prix",
        "last seen at {price}": "vu pour la dernière fois à {price}",
        "the airline": "la compagnie",
        "{h}h": "{h} h",
        "{h}h {m}m": "{h} h {m} min",
        "{m}m": "{m} min",
        "{n} stop": "{n} escale",
        "{n} stops": "{n} escales",
        "{route} is {amount} cheaper than when you looked.":
            "{route} est {amount} moins cher que lors de votre dernière visite.",
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
