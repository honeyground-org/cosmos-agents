"""YouTube 전용 작업 화면. HTML은 고정하고 확인한 결과만 사용자별 상태로 전달한다."""
from functools import lru_cache
from pathlib import Path

# 영어 원문이 기본. 동작/안내를 에이전트와 함께 배포한다.
LANGS = ("en", "ko", "ja", "de", "es", "fr")
COPY = {
    "title": ("Your channel, in context", "맥락이 쌓이는 내 채널", "文脈がつながる自分のチャンネル", "Ihr Kanal im Kontext", "Tu canal, en contexto", "Votre chaîne, en contexte"),
    "intro": ("Review what you published. Explore what to make next.", "올린 영상을 돌아보고, 다음 콘텐츠의 실마리를 찾아보세요.", "公開した動画を振り返り、次の制作を探りましょう。", "Veröffentlichungen ansehen und neue Ideen erkunden.", "Revisa lo publicado y explora qué crear después.", "Retrouvez vos publications et explorez vos prochaines idées."),
    "channel": ("My publications", "내 업로드 이력", "自分の公開履歴", "Meine Veröffentlichungen", "Mis publicaciones", "Mes publications"),
    "recorded": ("Only uploads recorded by Cosmos; not a live channel sync.", "코스모스가 기록한 업로드만 표시합니다. 실시간 채널 동기화가 아닙니다.", "Cosmosが記録したアップロードのみ。リアルタイム同期ではありません。", "Nur in Cosmos erfasste Uploads, keine Live-Synchronisierung.", "Solo subidas registradas por Cosmos; no es una sincronización en vivo.", "Uniquement les envois enregistrés par Cosmos, sans synchronisation en direct."),
    "empty_uploads": ("Your first recorded upload will appear here.", "첫 업로드를 기록하면 이곳에 표시됩니다.", "最初のアップロード記録がここに表示されます。", "Ihr erster erfasster Upload erscheint hier.", "Tu primera subida registrada aparecerá aquí.", "Votre premier envoi enregistré apparaîtra ici."),
    "upload_help": ("To upload, tell Cosmos the file, title and privacy. This view never publishes automatically.", "업로드하려면 대화에서 파일·제목·공개 범위를 알려주세요. 이 화면은 자동으로 게시하지 않습니다.", "アップロードするにはファイル・タイトル・公開範囲をCosmosに伝えてください。自動公開はしません。", "Nennen Sie Cosmos Datei, Titel und Sichtbarkeit. Diese Ansicht veröffentlicht nie automatisch.", "Indica a Cosmos el archivo, título y privacidad. Esta vista nunca publica automáticamente.", "Indiquez à Cosmos le fichier, le titre et la visibilité. Cette vue ne publie jamais automatiquement."),
    "research": ("Reference desk", "콘텐츠 탐색", "参考動画を探す", "Recherche", "Mesa de referencias", "Espace de recherche"),
    "query": ("Topic or YouTube URL", "주제 또는 YouTube 주소", "トピックまたはYouTube URL", "Thema oder YouTube-URL", "Tema o URL de YouTube", "Sujet ou URL YouTube"),
    "search": ("Search", "검색", "検索", "Suchen", "Buscar", "Rechercher"),
    "trending": ("Trending", "인기 영상", "急上昇", "Trends", "Tendencias", "Tendances"),
    "results": ("Latest results", "최근 결과", "最新の結果", "Letzte Ergebnisse", "Últimos resultados", "Derniers résultats"),
    "empty_results": ("Search to collect references here. Search results are not stored as interests.", "검색하면 참고할 영상이 나타납니다. 검색 목록을 관심사로 기억하지 않습니다.", "検索すると参考動画が表示されます。検索結果を興味として記憶しません。", "Suchen Sie nach Referenzen. Suchergebnisse werden nicht als Interessen gespeichert.", "Busca referencias aquí. Los resultados no se guardan como intereses.", "Recherchez des références ici. Les résultats ne sont pas mémorisés comme centres d’intérêt."),
    "no_results": ("The last search returned no videos.", "마지막 검색에서 영상을 찾지 못했습니다.", "前回の検索では動画が見つかりませんでした。", "Die letzte Suche ergab keine Videos.", "La última búsqueda no devolvió vídeos.", "La dernière recherche n’a donné aucune vidéo."),
    "detail": ("Selected reference", "선택한 참고 영상", "選択した参考動画", "Ausgewählte Referenz", "Referencia seleccionada", "Référence sélectionnée"),
    "choose": ("Select a result to read it alongside your channel.", "결과를 선택하면 채널 이력 옆에서 살펴볼 수 있습니다.", "結果を選ぶとチャンネル履歴と並べて確認できます。", "Wählen Sie ein Ergebnis neben Ihrem Kanal aus.", "Selecciona un resultado para verlo junto a tu canal.", "Sélectionnez un résultat pour le consulter à côté de votre chaîne."),
    "open": ("Open on YouTube", "YouTube에서 열기", "YouTubeで開く", "Auf YouTube öffnen", "Abrir en YouTube", "Ouvrir sur YouTube"),
    "info": ("Load details", "상세 정보 읽기", "詳細を読み込む", "Details laden", "Cargar detalles", "Charger les détails"),
    "summarize": ("Summarize description", "설명 기반 요약", "説明を要約", "Beschreibung zusammenfassen", "Resumir descripción", "Résumer la description"),
    "basis": ("Title and description only. No video or captions have been watched or retrieved.", "제목·설명만 활용합니다. 영상 시청이나 자막 수집은 하지 않습니다.", "タイトルと説明のみ。動画視聴や字幕取得はしていません。", "Nur Titel und Beschreibung. Kein Video angesehen, keine Untertitel abgerufen.", "Solo título y descripción. No se ve el vídeo ni se recuperan subtítulos.", "Titre et description uniquement. Aucune vidéo visionnée ni sous-titres récupérés."),
    "pending": ("Working…", "처리 중…", "処理中…", "In Bearbeitung…", "Procesando…", "En cours…"),
    "error": ("The action could not be confirmed. Check Cosmos chat before retrying.", "실행 결과를 확인하지 못했습니다. 다시 시도하기 전에 코스모스 대화를 확인하세요.", "実行結果を確認できません。再試行前にCosmosの会話を確認してください。", "Aktion nicht bestätigt. Prüfen Sie vor einem erneuten Versuch den Cosmos-Chat.", "No se confirmó la acción. Revisa el chat de Cosmos antes de reintentar.", "Action non confirmée. Vérifiez la conversation Cosmos avant de réessayer."),
    "missing_query": ("Enter a topic or YouTube URL first.", "주제 또는 YouTube 주소를 먼저 입력하세요.", "トピックまたはYouTube URLを入力してください。", "Geben Sie zuerst ein Thema oder eine YouTube-URL ein.", "Introduce primero un tema o URL de YouTube.", "Saisissez d’abord un sujet ou une URL YouTube."),
    "private": ("Only you", "나만 보기", "自分だけ", "Nur Sie", "Solo tú", "Vous uniquement"),
    "unlisted": ("People with the link", "링크가 있는 사람", "リンクを知る人", "Personen mit Link", "Personas con el enlace", "Personnes avec le lien"),
    "public": ("Anyone", "누구나", "全員", "Alle", "Cualquiera", "Tout le monde"),
    "unknown": ("Visibility not recorded", "공개 범위 기록 없음", "公開範囲の記録なし", "Sichtbarkeit nicht erfasst", "Visibilidad no registrada", "Visibilité non enregistrée"),
    "memory": ("Memory is unavailable. Channel history may be missing.", "기억을 사용할 수 없습니다. 채널 이력이 누락될 수 있습니다.", "記憶を利用できません。チャンネル履歴が欠けている可能性があります。", "Gedächtnis nicht verfügbar. Der Kanalverlauf kann fehlen.", "La memoria no está disponible. Puede faltar el historial del canal.", "La mémoire est indisponible. L’historique de la chaîne peut manquer."),
    "history": ("Repeated channel lookups", "반복해서 살펴본 채널", "繰り返し調べたチャンネル", "Wiederholt aufgerufene Kanäle", "Canales consultados varias veces", "Chaînes consultées plusieurs fois"),
    "history_help": ("Distinct videos per day, not verified watch time or a personal preference score.", "하루의 서로 다른 영상 조회 기록입니다. 시청 시간이나 취향 점수가 아닙니다.", "1日の異なる動画の照会記録です。視聴時間や好みの点数ではありません。", "Verschiedene Videos pro Tag, keine bestätigte Wiedergabezeit oder Vorliebenbewertung.", "Vídeos distintos por día, no tiempo de visualización ni puntuación de gustos.", "Vidéos distinctes par jour, pas une durée de visionnage ni un score de préférence."),
    "privacy": ("Latest results stay in your Cosmos account until replaced. Explicit lookups and uploads use your brain. Opening is not recorded as watching.", "최근 결과는 다음 결과로 교체될 때까지 내 코스모스 계정에 보관됩니다. 명시적인 조회와 업로드는 브레인에 기억합니다. 열기를 시청으로 기록하지 않습니다.", "最新結果は次の結果で置き換わるまでCosmosアカウントに保存されます。明示的な照会とアップロードは記憶されます。開くだけでは視聴扱いになりません。", "Letzte Ergebnisse bleiben bis zum Ersetzen im Cosmos-Konto. Gezielte Aufrufe und Uploads nutzen das Gedächtnis. Öffnen zählt nicht als Anschauen.", "Los últimos resultados se conservan en tu cuenta Cosmos hasta reemplazarse. Las consultas explícitas y subidas usan la memoria. Abrir no cuenta como ver.", "Les derniers résultats restent dans votre compte Cosmos jusqu’à leur remplacement. Les consultations explicites et envois utilisent la mémoire. Ouvrir ne signifie pas regarder."),
}


@lru_cache(maxsize=1)
def html():
    return (Path(__file__).parent / "views/workspace.html").read_text(encoding="utf-8")


def block(channel, latest, *, lang="en", warning="", memory_available=True):
    index = LANGS.index(lang) if lang in LANGS else 0
    copy = {key: row[index] for key, row in COPY.items()}
    # 코어의 JSON 상태 한도를 넘지 않도록 긴 API/기억 자료는 표시할 양만 보낸다.
    uploads = [{"title": str(row.get("title", ""))[:120],
                "privacy": row.get("privacy", ""), "uploaded_at": str(row.get("uploaded_at", ""))[:32],
                "tags": [str(tag)[:60] for tag in (row.get("tags") or [])[:8]]}
               for row in channel["uploads"][:12]]
    latest = dict(latest) if isinstance(latest, dict) else {}
    latest = {"action": str(latest.get("action", ""))[:20],
              "query": str(latest.get("query", ""))[:300],
              "updated_at": str(latest.get("updated_at", ""))[:32],
              "summary": str(latest.get("summary", ""))[:4000],
              "videos": [{key: str(row.get(key, ""))[:limit] for key, limit in
                          (("id", 11), ("title", 300), ("channel", 150), ("description", 700))}
                         for row in (latest.get("videos") or [])[:8] if isinstance(row, dict)]}
    return {"type": "html", "key": "youtube-workspace-v1", "label": copy["title"],
            "height": 1060, "html": html(), "state": {
                "lang": lang, "copy": copy, "uploads": uploads,
                "regulars": [{"channel": str(r["channel"])[:120], "count": int(r["count"])}
                             for r in channel["regulars"][:8]], "latest": latest,
                "warning": warning or ("" if memory_available else copy["memory"]),
            }}
