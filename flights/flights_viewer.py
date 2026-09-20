"""Flight workspace: stable HTML, bounded state, no network in the iframe."""
from functools import lru_cache
from pathlib import Path

LANGS = ('en', 'ko', 'ja', 'de', 'es', 'fr')
COPY = {
 'settings': ('Search settings', '검색 설정', '検索設定', 'Sucheinstellungen', 'Ajustes de búsqueda', 'Paramètres de recherche'),
 'currency': ('Currency', '통화', '通貨', 'Währung', 'Moneda', 'Devise'),
 'currency_auto': ('Listing default', '목록의 기본 통화', '一覧の既定通貨', 'Standard der Flugliste', 'Predeterminada del listado', 'Devise de la liste'),
 'currency_help': ('Applies to the next search. Existing fares keep their original currency; no conversion is made.', '다음 검색부터 적용됩니다. 기존 가격의 통화는 바뀌지 않으며 환산하지 않습니다.', '次の検索から適用。既存の運賃の通貨は変更・換算しません。', 'Gilt ab der nächsten Suche. Bestehende Tarife behalten ihre Währung; keine Umrechnung.', 'Se aplica a la próxima búsqueda. Las tarifas existentes conservan su moneda; no se convierten.', 'Applicable à la prochaine recherche. Les tarifs existants gardent leur devise, sans conversion.'),
 'settings_save': ('Save currency', '통화 저장', '通貨を保存', 'Währung speichern', 'Guardar moneda', 'Enregistrer la devise'),
 'settings_saved': ('Currency saved for the next search.', '다음 검색에 사용할 통화를 저장했습니다.', '次の検索に使う通貨を保存しました。', 'Währung für die nächste Suche gespeichert.', 'Moneda guardada para la próxima búsqueda.', 'Devise enregistrée pour la prochaine recherche.'),
 'settings_invalid': ('Choose a currency from the list.', '목록에서 통화를 선택해 주세요.', '一覧から通貨を選択してください。', 'Bitte eine Währung aus der Liste wählen.', 'Elige una moneda de la lista.', 'Choisissez une devise dans la liste.'),
 'settings_stale': ('Currency changed elsewhere. Reopen search settings before saving again.', '다른 곳에서 통화가 변경되었습니다. 검색 설정을 닫았다 열고 다시 저장해 주세요.', '別の画面で通貨が変わりました。検索設定を開き直して保存してください。', 'Währung wurde anderswo geändert. Sucheinstellungen vor dem Speichern erneut öffnen.', 'La moneda cambió en otro lugar. Vuelve a abrir los ajustes antes de guardar.', 'La devise a changé ailleurs. Rouvrez les paramètres avant d’enregistrer.'),

 'back_options': ('Choose another flight', '다른 항공편 보기', '別の便を見る', 'Anderen Flug wählen', 'Elegir otro vuelo', 'Choisir un autre vol'),
 'memory_error': ('Results are shown, but this trip could not be saved to memory. Try again before relying on reminders.', '검색 결과는 표시했지만 여행을 기억에 저장하지 못했습니다. 알림을 기대하기 전에 다시 시도해 주세요.', '結果は表示していますが、旅程を記憶に保存できませんでした。通知を使う前に再試行してください。', 'Ergebnisse angezeigt, Reise aber nicht gespeichert. Vor Nutzung der Hinweise erneut versuchen.', 'Se muestran resultados, pero no se guardó el viaje. Reintenta antes de depender de avisos.', 'Résultats affichés, mais voyage non mémorisé. Réessayez avant de compter sur les alertes.'),
 'title': ('A little closer to takeoff.', '떠나는 날에 한 걸음 더.', '出発の日へ、もう一歩。', 'Dem Abflug ein Stück näher.', 'Un paso más cerca de despegar.', 'Un peu plus près du départ.'),
 'intro': ('Find a fare. Keep your time.', '좋은 가격을 찾고, 여행의 시간을 지키세요.', 'よい運賃で、旅の時間を大切に。', 'Guter Preis. Mehr Zeit für die Reise.', 'Encuentra tu tarifa. Cuida tu tiempo.', 'Le bon tarif. Du temps pour voyager.'),
 'origin': ('From', '출발', '出発', 'Von', 'Desde', 'Départ'),
 'destination': ('To', '도착', '到着', 'Nach', 'Hasta', 'Arrivée'),
 'depart': ('Departure', '가는 날', '出発日', 'Hinflug', 'Ida', 'Aller'),
 'return_on': ('Return · optional', '오는 날 · 선택', '帰国日・任意', 'Rückflug · optional', 'Vuelta · opcional', 'Retour · facultatif'),
 'airline': ('Airline · optional', '항공사 · 선택', '航空会社・任意', 'Airline · optional', 'Aerolínea · opcional', 'Compagnie · facultative'),
 'nonstop': ('Nonstop only', '직항만', '直行便のみ', 'Nur Direktflüge', 'Solo directos', 'Vols directs'),
 'search': ('Find flights', '항공편 찾기', '航空便を探す', 'Flüge finden', 'Buscar vuelos', 'Chercher des vols'),
 'swap': ('Swap airports', '출발·도착 바꾸기', '出発と到着を交換', 'Flughäfen tauschen', 'Intercambiar aeropuertos', 'Inverser les aéroports'),
 'journey': ('YOUR NEXT JOURNEY', '다음 여행', '次の旅', 'IHRE NÄCHSTE REISE', 'TU PRÓXIMO VIAJE', 'VOTRE PROCHAIN VOYAGE'),
 'schematic': ('Route illustration · not to scale', '여정 도식 · 실제 거리 비율 아님', '旅程の模式図・縮尺なし', 'Routenskizze · nicht maßstabsgetreu', 'Esquema de ruta · sin escala', 'Schéma du trajet · sans échelle'),
 'options': ('Choose your way there', '어떻게 떠나고 싶으세요?', 'どの便で出発しますか？', 'Wählen Sie Ihren Flug', 'Elige cómo llegar', 'Choisissez votre trajet'),
 'price': ('Fare comparison', '운임 한눈에 보기', '運賃を比較', 'Tarifvergleich', 'Comparación de tarifas', 'Comparer les tarifs'),
 'price_help': ('Visible fares · grouped by currency and fare basis · from zero', '현재 쪽 · 같은 통화·운임 범위끼리 · 0부터 비교', '表示中・同じ通貨と運賃範囲別・ゼロ基準', 'Sichtbare Tarife · gleiche Währung und Tarifart · ab Null', 'Tarifas visibles · misma moneda y tipo · desde cero', 'Tarifs affichés · même devise et type · base zéro'),
 'selected': ('Your selected flight', '지금 살펴보는 항공편', '選択した航空便', 'Ihr ausgewählter Flug', 'Tu vuelo seleccionado', 'Votre vol sélectionné'),
 'local': ('Times as listed · local clocks; confirm arrival date at source', '목록에 표시된 현지 시각 · 도착 날짜는 원문에서 확인', '掲載の現地時刻・到着日は掲載元で確認', 'Ortszeiten laut Angebot · Ankunftsdatum an der Quelle prüfen', 'Horas locales del anuncio · confirma la fecha de llegada', 'Heures locales indiquées · vérifiez la date d’arrivée'),
 'duration': ('Travel time', '총 소요 시간', '所要時間', 'Reisezeit', 'Duración', 'Durée'),
 'stops': ('Stops', '경유', '経由', 'Umstiege', 'Escalas', 'Escales'),
 'unknown': ('Not listed', '표시되지 않음', '記載なし', 'Nicht angegeben', 'Sin indicar', 'Non indiqué'),
 'basis_unknown': ('Fare basis unconfirmed', '편도·왕복 범위 미확인', '片道・往復は未確認', 'Tarifart unbestätigt', 'Tipo de tarifa sin confirmar', 'Type de tarif non confirmé'),
 'one_way': ('One way', '편도', '片道', 'Einfach', 'Solo ida', 'Aller simple'),
 'round_trip': ('Round trip', '왕복', '往復', 'Hin und zurück', 'Ida y vuelta', 'Aller-retour'),
 'open': ('Check this fare', '이 운임 원문 확인', 'この運賃を確認', 'Diesen Tarif prüfen', 'Consultar esta tarifa', 'Vérifier ce tarif'),
 'no_link': ('No source link was found for this flight.', '이 항공편의 원문 링크를 찾지 못했습니다.', 'この便の掲載元リンクがありません。', 'Kein Quelllink für diesen Flug.', 'No hay enlace de origen para este vuelo.', 'Aucun lien source pour ce vol.'),
 'source_note': ('Observed fares, not a quote. Check baggage, taxes and availability at source.', '확인 당시 운임입니다. 수하물·세금·잔여 좌석은 원문에서 확인하세요.', '確認時点の運賃です。手荷物・税金・空席は掲載元で確認してください。', 'Beobachtete Tarife. Gepäck, Steuern und Verfügbarkeit an der Quelle prüfen.', 'Tarifas observadas. Confirma equipaje, impuestos y plazas en origen.', 'Tarifs observés. Vérifiez bagages, taxes et places à la source.'),
 'nearby': ('Would another day work?', '하루쯤 달라도 괜찮다면', '別の日でもよければ', 'Passt auch ein anderer Tag?', '¿Te sirve otro día?', 'Et un autre jour ?'),
 'nearby_help': ('Compare departures with the same return date.', '오는 날은 그대로 두고, 가는 날의 가격을 비교합니다.', '帰国日を変えずに出発日を比較します。', 'Hinflugtage bei gleichem Rückflugdatum vergleichen.', 'Compara salidas manteniendo la fecha de vuelta.', 'Comparez les départs en gardant la même date de retour.'),
 'check_dates': ('Compare nearby dates', '주변 날짜 비교', '近い日付を比較', 'Nahe Termine vergleichen', 'Comparar fechas cercanas', 'Comparer les dates proches'),
 'date_needed': ('Choose a departure date and search first.', '가는 날을 정해 먼저 검색해 주세요.', '出発日を選んで検索してください。', 'Zuerst Abflugdatum wählen und suchen.', 'Elige una fecha de salida y busca primero.', 'Choisissez une date de départ puis lancez la recherche.'),
 'nearby_done': ('Select a date below to search with the same trip conditions.', '아래 날짜를 누르면 같은 여행 조건으로 다시 찾습니다.', '下の日付を選ぶと同じ条件で検索します。', 'Datum unten wählen, um mit denselben Bedingungen zu suchen.', 'Elige una fecha para buscar con las mismas condiciones.', 'Choisissez une date pour rechercher aux mêmes conditions.'),
 'nearby_unavailable': ('No comparable lower fares were obtained. This does not mean none exist.', '비교 가능한 더 낮은 운임을 확인하지 못했습니다. 더 싼 날이 없다는 뜻은 아닙니다.', '比較できる安い運賃を確認できませんでした。存在しないとは限りません。', 'Keine vergleichbaren günstigeren Tarife ermittelt. Es kann dennoch welche geben.', 'No se obtuvieron tarifas inferiores comparables. Puede que existan.', 'Aucun tarif inférieur comparable obtenu. Il peut en exister.'),
 'history': ('What changed since last time?', '지난번보다 얼마나 달라졌을까요?', '前回からどう変わった？', 'Was hat sich verändert?', '¿Qué cambió desde la última vez?', 'Qu’est-ce qui a changé ?'),
 'history_help': ('Observed route minimum · same trip, currency and fare basis · no forecast', '같은 여행·통화·운임 범위의 관측 최저가 · 예측값 아님', '同じ旅程・通貨・運賃範囲の確認済み最安値・予測なし', 'Beobachtetes Routenminimum · gleiche Reise, Währung und Tarifart · keine Prognose', 'Mínimo observado · mismo viaje, moneda y tipo · sin predicción', 'Minimum observé · même voyage, devise et type · sans prévision'),
 'no_history': ('Your next search will show what changed.', '다음 검색부터 가격의 변화를 이어 볼 수 있어요.', '次の検索で価格の変化がわかります。', 'Die nächste Suche zeigt die Veränderung.', 'La próxima búsqueda mostrará el cambio.', 'La prochaine recherche montrera l’évolution.'),
 'watch': ('Keep this trip in mind', '이 여행을 함께 기억해요', 'この旅を覚えておく', 'Diese Reise im Blick behalten', 'Mantener este viaje presente', 'Garder ce voyage en tête'),
 'watch_help': ('Mark your decision to stop fare reminders. You can undo it.', '결정을 알려 주면 운임 알림을 멈춥니다. 언제든 되돌릴 수 있어요.', '決定を伝えると運賃通知を停止。いつでも戻せます。', 'Entscheidung markieren, um Hinweise zu stoppen. Jederzeit rückgängig.', 'Marca tu decisión para detener avisos. Puedes deshacerla.', 'Indiquez votre décision pour arrêter les alertes. C’est réversible.'),
 'booked': ('I booked it', '예약했어요', '予約しました', 'Gebucht', 'Ya reservé', 'J’ai réservé'),
 'dropped': ('Trip cancelled', '이번엔 안 가요', '今回は行きません', 'Reise abgesagt', 'Viaje cancelado', 'Voyage annulé'),
 'still_looking': ('Still deciding', '아직 고민 중', 'まだ検討中', 'Noch unentschieden', 'Aún decidiendo', 'Encore en réflexion'),
 'prev': ('Previous', '이전', '前へ', 'Zurück', 'Anterior', 'Précédent'),
 'next': ('Next', '다음', '次へ', 'Weiter', 'Siguiente', 'Suivant'),
 'empty': ('Where would you like to go?', '어디로 떠나고 싶으세요?', 'どこへ出かけたいですか？', 'Wohin möchten Sie reisen?', '¿A dónde te gustaría ir?', 'Où aimeriez-vous partir ?'),
 'empty_help': ('Start with your destination. Add dates to compare the trip you actually want.', '목적지부터 알려 주세요. 날짜를 더하면 원하는 여행의 운임을 비교할 수 있어요.', 'まず目的地を入力。日付を加えると旅の運賃を比較できます。', 'Mit dem Ziel beginnen. Mit Daten vergleichen Sie Ihre konkrete Reise.', 'Empieza por el destino. Añade fechas para comparar tu viaje.', 'Commencez par la destination. Ajoutez les dates pour comparer votre voyage.'),
 'pending': ('Finding the details…', '꼼꼼히 확인하고 있어요…', '詳細を確認中…', 'Details werden geprüft…', 'Consultando los detalles…', 'Vérification des détails…'),
 'error': ('This action could not be completed. Try again; your previous results are kept.', '작업을 완료하지 못했습니다. 이전 결과는 보관했으니 다시 시도해 주세요.', '完了できませんでした。前の結果は保持しています。再試行してください。', 'Aktion fehlgeschlagen. Vorige Ergebnisse bleiben erhalten. Erneut versuchen.', 'No se completó la acción. Conservamos los resultados anteriores. Reintenta.', 'Action non terminée. Les résultats précédents sont conservés. Réessayez.'),
 'stale': ('The list has changed. Select the flight again.', '목록이 바뀌었습니다. 항공편을 다시 선택해 주세요.', '一覧が変わりました。便を選び直してください。', 'Liste geändert. Flug erneut wählen.', 'La lista cambió. Selecciona de nuevo.', 'La liste a changé. Sélectionnez à nouveau le vol.'),
 'dates_invalid': ('Return must be on or after departure.', '오는 날은 가는 날과 같거나 늦어야 합니다.', '帰国日は出発日以降にしてください。', 'Rückflug muss am oder nach dem Hinflug sein.', 'La vuelta debe ser el día de salida o después.', 'Le retour doit être le jour du départ ou après.'),
 'pause': ('Pause motion', '움직임 멈추기', '動きを停止', 'Bewegung pausieren', 'Pausar movimiento', 'Suspendre les animations'),
 'motion': ('Enable motion', '움직임 켜기', '動きを有効に', 'Bewegung aktivieren', 'Activar movimiento', 'Activer les animations'),
}

def copy_for(lang):
    return {k: v[LANGS.index(lang) if lang in LANGS else 0] for k, v in COPY.items()}

@lru_cache(maxsize=1)
def html():
    return (Path(__file__).parent / 'views/workspace.html').read_text(encoding='utf-8')

def block(state, *, lang='en', currency=''):
    preferred_currency = currency
    from flights_scout import page_of, money, duration_text, stops_text, cheapest_index, i18n
    c = copy_for(lang)
    items = state.get('items') or []
    shown, page, pages = page_of(items, state.get('page', 0))
    rows = []
    for index, r in enumerate(shown, page * 4 + 1):
        row = {k: str(r.get(k) or '')[:200] for k in ('airline','origin','destination','depart','leaves','arrives','seen_at','note','reason','currency','fare_type')}
        row.update(index=index, amount=r.get('price') or 0, price=money(r.get('price'),r.get('currency','')),
                   minutes=r.get('minutes') or 0, duration=duration_text(r.get('minutes'), lang=lang) or c['unknown'],
                   stops=r.get('stops'), stops_text=stops_text(r.get('stops'), lang=lang) or c['unknown'], can_open=bool(r.get('url')),
                   basis=c.get(r.get('fare_type'), c['basis_unknown']))
        if row["reason"]:
            row["reason"] = i18n.t("Cheapest of the ones with {stops}.", stops=stops_text(r.get("stops"), lang=lang), lang=lang)
        rows.append(row)
    low = cheapest_index(items)
    currency = items[low].get('currency', '') if low >= 0 else ''
    return {'type':'html', 'key':'flights-workspace-v1', 'height':1200, 'label':'Flights', 'html':html(),
            'state': {'copy':c, 'lang':lang, 'revision':state.get('revision',''),
                      'currency':preferred_currency,
                      'trip':{k:state.get(k,False if k=='nonstop' else '') for k in ('origin','destination','depart','return_on','airline','nonstop')},
                      'items':rows, 'page':page, 'pages':pages, 'total':len(items),
                      'notice':state.get('notice',''), 'outcome':state.get('outcome','still_looking'),
                      'nearby':[{**r,'price_text':money(r['price'],r['currency'])} for r in state.get('nearby',[])[:3]],
                      'history':[{'ts':r['ts'], 'amount':r['price'], 'price':money(r['price'],currency)} for r in state.get('history',[])[-24:]]}}
