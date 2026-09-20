"""Shopping comparison workspace; fixed HTML and bounded account-owned state."""
from functools import lru_cache
from pathlib import Path
from shopping_core import cheapest_index, money, page_of

LANGS = ('en', 'ko', 'ja', 'de', 'es', 'fr')
COPY = {
    'candidates': ('Candidates', '후보 비교', '候補の比較', 'Kandidaten', 'Candidatos', 'Candidats'),
    'official': ('Official seller', '공식 판매처', '公式販売店', 'Offizieller Händler', 'Vendedor oficial', 'Vendeur officiel'),
    'yes': ('Yes', '확인됨', '確認済み', 'Ja', 'Sí', 'Oui'),
    'no': ('No', '아니요', 'いいえ', 'Nein', 'No', 'Non'),
    'title': ('A good choice takes time', '잘 고르는 시간', '納得して選ぶ時間', 'Gut wählen braucht Zeit', 'Elegir bien lleva tiempo', 'Bien choisir prend du temps'),
    'intro': ('Compare what matters. Pick up where you left off.', '중요한 조건을 비교하고, 지난 고민에서 이어가세요.', '大切な条件を比べ、前回の続きから。', 'Vergleichen Sie, was zählt. Machen Sie dort weiter, wo Sie waren.', 'Compara lo que importa y retoma donde lo dejaste.', 'Comparez l’essentiel et reprenez votre réflexion.'),
    'query': ('What are you considering?', '무엇을 살까 고민 중인가요?', '何の購入を考えていますか？', 'Was möchten Sie kaufen?', '¿Qué piensas comprar?', 'Quel achat envisagez-vous ?'),
    'criteria': ('Criteria for this decision', '이번 선택의 조건', '今回の選択条件', 'Kriterien dieser Entscheidung', 'Criterios de esta decisión', 'Critères de cette décision'),
    'criteria_help': ('Leave blank to reuse saved criteria.', '비워두면 이 구매의 기존 조건을 사용합니다.', '空欄なら保存済みの条件を使用。', 'Leer lassen, um gespeicherte Kriterien zu nutzen.', 'Deja vacío para reutilizar los criterios guardados.', 'Laissez vide pour reprendre les critères enregistrés.'),
    'search': ('Compare', '비교하기', '比較する', 'Vergleichen', 'Comparar', 'Comparer'),
    'saved': ('This decision', '이어가는 구매 고민', '続けている検討', 'Diese Entscheidung', 'Esta decisión', 'Cette décision'),
    'empty': ('Search to start a comparison.', '검색하면 비교할 후보가 나타납니다.', '検索すると比較候補が表示されます。', 'Starten Sie einen Vergleich mit einer Suche.', 'Busca para iniciar una comparación.', 'Recherchez pour commencer à comparer.'),
    'none': ('No candidates in the latest search.', '최근 검색에서 후보를 찾지 못했습니다.', '最近の検索には候補がありません。', 'Keine Kandidaten in der letzten Suche.', 'No hay candidatos en la última búsqueda.', 'Aucun candidat lors de la dernière recherche.'),
    'basis': ('Order: rating, then price within the same currency. No commission ranking.', '평점 우선, 같은 통화에서는 가격순입니다. 수수료는 순위에 반영하지 않습니다.', '評価優先、同じ通貨では価格順。手数料は順位に無関係です。', 'Bewertung zuerst, dann Preis derselben Währung. Keine Provisionsrangfolge.', 'Primero valoración, luego precio en la misma moneda. Sin comisiones en el orden.', 'Note, puis prix dans la même devise. Sans classement par commission.'),
    'pick': ('First in this comparison', '이번 비교의 첫 후보', '今回の比較の先頭', 'Erster im Vergleich', 'Primero en esta comparación', 'Premier de cette comparaison'),
    'cheap': ('Lowest observed price', '확인한 후보 중 최저가', '確認候補の最安値', 'Niedrigster beobachteter Preis', 'Menor precio observado', 'Prix observé le plus bas'),
    'detail': ('Look closer', '선택한 후보 자세히 보기', '詳しく見る', 'Genauer ansehen', 'Ver de cerca', 'Voir en détail'),
    'unknown': ('Not recorded', '확인한 정보 없음', '記録なし', 'Nicht erfasst', 'Sin registrar', 'Non enregistré'),
    'rating': ('Rating', '평점', '評価', 'Bewertung', 'Valoración', 'Note'),
    'reviews': ('Reviews', '리뷰 수', 'レビュー数', 'Rezensionen', 'Reseñas', 'Avis'),
    'observed': ('Observed', '가격 확인 시각', '価格確認時刻', 'Beobachtet', 'Observado', 'Observé'),
    'before': ('Previous price', '지난 가격', '前回の価格', 'Vorheriger Preis', 'Precio anterior', 'Prix précédent'),
    'now': ('Latest price', '이번 가격', '今回の価格', 'Letzter Preis', 'Último precio', 'Dernier prix'),
    'open': ('Visit seller', '판매처 열기', '販売店を開く', 'Händler öffnen', 'Visitar vendedor', 'Voir le vendeur'),
    'bought': ('I bought it', '샀어요', '購入しました', 'Gekauft', 'Lo compré', 'Je l’ai acheté'),
    'dropped': ('Stop considering', '이 후보는 그만 볼게요', 'この候補をやめる', 'Nicht mehr erwägen', 'Dejar de considerar', 'Ne plus envisager'),
    'still_looking': ('Still considering', '아직 고민 중이에요', 'まだ検討中', 'Noch unentschieden', 'Sigo considerando', 'Encore en réflexion'),
    'prev': ('Previous', '이전', '前へ', 'Zurück', 'Anterior', 'Précédent'),
    'next': ('Next', '다음', '次へ', 'Weiter', 'Siguiente', 'Suivant'),
    'pending': ('Working…', '처리 중…', '処理中…', 'In Bearbeitung…', 'Procesando…', 'En cours…'),
    'error': ('Could not confirm the action. Check the conversation.', '결과를 확인하지 못했습니다. 대화를 확인하세요.', '実行結果を確認できません。会話をご確認ください。', 'Aktion nicht bestätigt. Prüfen Sie den Chat.', 'Acción sin confirmar. Revisa la conversación.', 'Action non confirmée. Consultez la conversation.'),
    'privacy': ('Criteria belong to this purchase, not your permanent preferences. Prices are observations; confirm at the seller before buying.', '조건은 이번 구매에만 연결됩니다. 영구적인 취향으로 기록하지 않습니다. 가격은 확인 당시 값이며 구매 전 판매처에서 다시 확인하세요.', '条件は今回の購入だけに保存。恒久的な好みではありません。価格は確認時点の値です。購入前に販売店で再確認してください。', 'Kriterien gehören zu diesem Kauf, nicht zu dauerhaften Vorlieben. Preise sind Momentaufnahmen; vor dem Kauf beim Händler prüfen.', 'Los criterios son de esta compra, no gustos permanentes. Confirma el precio con el vendedor antes de comprar.', 'Les critères concernent cet achat, pas des préférences permanentes. Confirmez le prix auprès du vendeur avant d’acheter.'),
}

COPY.update({'price_chart': ('Prices at a glance', '한눈에 보는 가격', '価格をひと目で', 'Preise im Überblick', 'Precios de un vistazo', 'Les prix en un regard'), 'price_scope': ('Shown candidates · same currency · zero baseline', '현재 쪽 후보 · 같은 통화 · 0부터 비교', '表示中の候補・同じ通貨・ゼロ基準', 'Angezeigte Kandidaten · gleiche Währung · ab Null', 'Candidatos visibles · misma moneda · desde cero', 'Candidats affichés · même devise · depuis zéro'), 'change': ('Observed price change', '확인한 가격의 변화', '確認した価格の変化', 'Beobachtete Preisänderung', 'Cambio de precio observado', 'Variation de prix observée'), 'change_help': ('Two observations of the same item. No interpolated history.', '동일 상품의 두 확인 시점입니다. 중간 가격을 추정하지 않습니다.', '同じ商品の2回の確認値。中間の履歴は推定しません。', 'Zwei Beobachtungen desselben Artikels. Keine geschätzte Historie.', 'Dos observaciones del mismo artículo. Sin historial estimado.', 'Deux observations du même article. Aucun historique estimé.'), 'no_history': ('A second observation will reveal the change.', '다음에 가격을 확인하면 변화를 볼 수 있습니다.', '次回確認すると変化が見られます。', 'Eine zweite Beobachtung zeigt die Änderung.', 'Otra observación mostrará el cambio.', 'Une seconde observation montrera la variation.'), 'no_image': ('Image unavailable', '이미지 없음', '画像なし', 'Kein Bild verfügbar', 'Imagen no disponible', 'Image indisponible'), 'pause': ('Pause motion', '움직임 멈추기', '動きを停止', 'Bewegung pausieren', 'Pausar movimiento', 'Suspendre les animations'), 'motion': ('Enable motion', '움직임 켜기', '動きを有効に', 'Bewegung aktivieren', 'Activar movimiento', 'Activer les animations')})

COPY.update({'settings_title': ('Price check settings', '가격 확인 설정', '価格チェック設定', 'Preisprüfung einstellen', 'Ajustes de precios', 'Réglages des prix'), 'price_checks': ('Check prices in the background', '백그라운드 가격 확인', 'バックグラウンドで価格確認', 'Preise im Hintergrund prüfen', 'Consultar precios en segundo plano', 'Vérifier les prix en arrière-plan'), 'check_hours': ('Check interval (hours)', '확인 간격 (시간)', '確認間隔（時間）', 'Prüfintervall (Stunden)', 'Intervalo (horas)', 'Intervalle (heures)'), 'drop_percent': ('Notify me after a drop of at least', '이 비율 이상 내리면 알림', 'この割合以上の値下げを通知', 'Melden ab einer Preissenkung von', 'Avisar a partir de una bajada del', 'Alerter à partir d’une baisse de'), 'settings_help': ('Checks run while Cosmos and this agent are on and background suggestions are allowed. Timing is approximate. KRW also requires a ₩3,000 drop; other currencies use the percentage. The same item is not alerted again within 3 days.', 'Cosmos와 이 에이전트가 켜져 있고 백그라운드 제안이 허용될 때 확인합니다. 정확한 시각을 보장하지 않아요. 원화는 3,000원 이상 인하도 필요하며, 다른 통화는 비율을 사용합니다. 같은 상품은 3일 안에 다시 알리지 않아요.', 'Cosmosとエージェントが有効で、バックグラウンド提案が許可されている間に確認します。時刻は目安です。KRWは3,000ウォン以上の値下げも必要です。他の通貨は割合で判定。同じ商品は3日間再通知しません。', 'Prüfungen erfolgen bei aktivem Cosmos und Agenten mit erlaubten Hintergrundvorschlägen. Zeiten sind ungefähr. Für KRW müssen auch 3.000 Won gespart werden, sonst gilt der Prozentsatz. Dasselbe Produkt wird 3 Tage lang nicht erneut gemeldet.', 'Se consulta con Cosmos y el agente activos y sugerencias permitidas. Los horarios son aproximados. KRW exige además una bajada de 3.000 wones; otras monedas usan el porcentaje. No se repite la alerta del mismo producto en 3 días.', 'Les vérifications nécessitent Cosmos et cet agent actifs, avec les suggestions autorisées. Horaires approximatifs. En KRW, une baisse de 3 000 wons est aussi requise ; sinon, le pourcentage suffit. Pas de nouvelle alerte pour le même produit sous 3 jours.'), 'settings_save': ('Save settings', '설정 저장', '設定を保存', 'Einstellungen speichern', 'Guardar ajustes', 'Enregistrer'), 'settings_saved': ('Price check settings saved.', '가격 확인 설정을 저장했어요.', '価格チェック設定を保存しました。', 'Preiseinstellungen gespeichert.', 'Ajustes de precios guardados.', 'Réglages des prix enregistrés.'), 'settings_stale': ('Settings changed elsewhere. Reopen the view before saving.', '다른 곳에서 설정이 바뀌었어요. 화면을 다시 열고 저장해 주세요.', '別の場所で設定が変更されました。画面を開き直してください。', 'Einstellungen wurden geändert. Öffnen Sie die Ansicht erneut.', 'Los ajustes cambiaron. Vuelve a abrir la vista.', 'Les réglages ont changé. Rouvrez la vue.'), 'settings_invalid': ('Choose valid price check settings.', '가격 확인 설정값을 확인해 주세요.', '有効な価格チェック設定を選んでください。', 'Wählen Sie gültige Preiseinstellungen.', 'Elige ajustes de precios válidos.', 'Choisissez des réglages valides.'), 'settings_unavailable': ('Price check settings could not be read. Try again before checking prices.', '가격 확인 설정을 읽지 못했어요. 다시 시도해 주세요.', '価格チェック設定を読み込めませんでした。再試行してください。', 'Preiseinstellungen konnten nicht gelesen werden. Versuchen Sie es erneut.', 'No se pudieron leer los ajustes. Inténtalo de nuevo.', 'Impossible de lire les réglages. Réessayez.')})

@lru_cache(maxsize=1)
def html():
    return (Path(__file__).parent / 'views/workspace.html').read_text(encoding='utf-8')


def block(state, *, lang='en'):
    copy = {k: row[LANGS.index(lang) if lang in LANGS else 0] for k, row in COPY.items()}
    items = state.get('items') or []
    shown, page, pages = page_of(items, state.get('page', 0))
    low = cheapest_index(items)
    rows = []
    for n, item in enumerate(shown, page * 4):
        # URLs stay behind the tool boundary; the view sends revision and index.
        row = {k: item.get(k, '') for k in ('title', 'seller', 'note', 'seen_at', 'outcome')}
        row.update(index=n + 1, price=money(item.get('price'), item.get('currency', 'KRW')),
                   amount=item.get('price') or 0, currency=item.get('currency', 'KRW'),
                   image=item.get('image_data', '') if str(item.get('image_data', '')).startswith('data:image/jpeg;base64,') and len(item.get('image_data', '')) <= 8192 else '',
                   signals=item.get('signals') or {}, can_open=bool(item.get('url')),
                   mark=copy['pick'] if n == 0 else copy['cheap'] if n == low else '')
        rows.append(row)
    history = state.get('history') or []
    currency = items[0].get('currency', 'KRW') if items else 'KRW'
    return {'type': 'html', 'key': 'shopping-workspace-v1', 'height': 1050, 'label': copy['title'], 'html': html(),
            'state': {'copy': copy, 'lang': lang, 'query': state.get('query', ''),
                      'criteria': state.get('criteria', ''), 'revision': state.get('revision', ''),
                      'items': rows, 'page': page, 'pages': pages, 'total': len(items),
                      'preferences': state.get('preferences', {}), 'open_settings': state.get('open_settings', False),
                      'notice': state.get('notice', ''), 'history_title': state.get('history_title', ''),
                      'history': [{'ts': r['ts'], 'price': money(r['price'], currency), 'amount': r['price']} for r in history]}}
