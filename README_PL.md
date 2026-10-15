# Deco Access Control — instrukcja PL (BETA)

Celem jest docelowo blokowanie/odblokowywanie dostępu przez Wi-Fi wybranych urządzeń Deco. **Obecna wersja beta nie zapewnia potwierdzonej skutecznej blokady na M4R 1.8.2 w trybie AP.**

**UWAGA: brak potwierdzonej zgodności z Twoją konfiguracją fizyczną.** Testy jednostkowe są symulowane.

## Instalacja
1. W HA wybierz HACS → ⋮ → Niestandardowe repozytoria.
2. Wklej `https://github.com/infoprojektps-web/ha-deco-access-control`, wybierz `Integration`, dodaj i pobierz.
3. Wyłącz poprzednią integrację `deco_manager`, uruchom HA ponownie.
4. Ustawienia → Urządzenia i usługi → Dodaj integrację → `Deco Access Control`.
5. Host: `192.168.0.205` (sprawdź czy to główne Deco); użytkownik: `admin`; hasło: aktualne hasło logowania właściciela do panelu WWW; interwał: `60`.
6. Po połączeniu wejdź w Ustawienia → Urządzenia i usługi → Encje; znajdź `Dostęp Wi-Fi` i włącz jedną encję urządzenia testowego. Wszystkie przełączniki są domyślnie wyłączone dla bezpieczeństwa.
7. Przetestuj OFF (blokuj), sprawdź listę blokad w aplikacji Deco; następnie ON (odblokuj).

Pierwszego testu nie wykonuj na sprzęcie używanym do zarządzania siecią lub dostępem do Home Assistant. Zanotuj obecne blokady. **Uwaga:** przełącznik potwierdza jedynie wpis na liście blokad. W testach M4R 1.8.2 urządzenie nadal korzystało z internetu mimo tego wpisu.

## Jeśli instalacja zgłasza błąd
Ustawienia → System → Dzienniki → filtr `deco_access_control`. Udostępniaj wyłącznie typ wyjątku/ogólny komunikat, bez haseł, ciastek, tokenów i danych prywatnych.

## Dodatkowe informacje
Wymagany HA 2026.10+ i Python 3.14+. Wersja beta — żadnych testów na rzeczywistym M4/X50. Nie gwarantuje działania na wszystkich firmware. Stare hasło TP-Link było widoczne na zrzucie, więc je zmień.


## Diagnostyka blokowania w wersji 0.1.0-beta.2

Jeśli przełącznik wyłączy urządzenie, ale internet nadal działa, NIE oznacza to sukcesu. Podstawowa lista `admin/client → black_list` może różnić się od funkcji `Wi-Fi Access Control → apply_list`, używanej przez aplikację Deco. Do czasu identyfikacji różnicy integracja nadal zapisuje tylko na pierwszej liście.

1. Po aktualizacji przez HACS i restarcie HA wyszukaj encję **Deco — diagnostyka kontroli Wi-Fi**.
2. Otwórz jej szczegóły i zapisz: stan, `endpoint_status`, `active_mode`, `response_fields`, `configuration_signature` i `error_type` (jeśli wystąpił). Nie wysyłaj haseł, tokenów ani numerów MAC.
3. Zrób jeden test blokowania HA na urządzeniu testowym. Zanotuj, czy wartość `configuration_signature` zmieniła się po odświeżeniu.
4. Usuń ten wpis i dodaj to samo urządzenie ręcznie do skutecznej listy blokad w aplikacji Deco. Ponownie zapisz wartość `configuration_signature` po odświeżeniu i sprawdź internet.
5. Podaj wyniki oraz dokładną nazwę ekranu Deco, na którym ręcznie blokujesz urządzenie.

**Ważne:** Suma wpisów na `black_list` nie jest pomiarem faktycznej dostępności internetu. Ten diagnostyczny odczyt nie modyfikuje konfiguracji sieci. Nie jest to jeszcze naprawa samej blokady.


## Wersja 0.1.0-beta.3 — bezpieczna diagnostyka

Aktualizuj przez HACS i uruchom HA ponownie. Nie usuwaj wpisu integracji ani haseł. Dodano odczytowe sensory:

- `Deco — diagnostyka kontroli Wi-Fi` — status i numeryczny `error_code` dla `admin/client apply_list/get`.
- `Deco — diagnostyka NRD black_list` — liczba wpisów z osobnego `admin/nrd black_list/list`, jeśli dostępna.
- `Deco — diagnostyka Wi-Fi access_refuse` — status odczytu app-only listy odmów.

Nie wyświetlamy haseł, sesji ani danych urządzeń, tylko kod błędu, nazwę wyjątku, nazwy pól oraz ograniczony skrót odpowiedzi. Stan błędu `api_error` nie jest już mylony z reserved HA `unavailable`.

**Nie zmieniono funkcji blokowania!** Kontrola zapisu listy MAC nie oznacza skutecznej blokady Wi-Fi. Nie jest bezpieczne wywoływanie nieznanych zapisów `apply_list/set` na mieszanej sieci M4/X50 AP bez sprawdzenia szczegółów.

Do dalszej analizy wyślij jedynie stan i atrybuty trzech sensorów, bez prywatnych MAC. Jeśli `error_code` jest niezerowe, można sprawdzić odpowiedź API, ale nie należy zgadywać parametrów zapisu.


## Diagnostyka firmware Deco M4R 1.8.2 (beta.4)

Dotyczy głównego Deco M4R 192.168.0.205, firmware 1.8.2 Build 20251027 Rel. 36869, w trybie AP. X50 nie jest jeszcze podłączony.

Nowy, wyłącznie odczytowy atrybut `firmware_client_blocked` w istniejących przełącznikach pokazuje wartość pola `blocked` z odpowiedzi `admin/client → client_list`. To **inna informacja niż członkostwo w `black_list`**:

- `true` — firmware zgłasza flagę blokady klienta;
- `false` — firmware zgłasza jej brak;
- `unknown` — pole nieobecne lub ma nierozpoznaną wartość;
- `not_listed` — klient nie występuje na surowej liście klientów;
- `read_error` — dodatkowy odczyt listy klientów się nie udał.

Odczyt flagi nie potwierdza sam w sobie, że klient stracił internet. Aby ustalić różnicę, porównaj atrybuty `blocked`, `firmware_client_blocked` i `online` **tego samego przełącznika** w dwóch stanach: gdy blokada dodana przez HA jest nieskuteczna, oraz gdy ręczna blokada w aplikacji Deco skutecznie odcina internet. Nie udostępniaj MAC ani IP urządzenia testowego.

Beta.4 nie wprowadza nowych operacji zapisu, nie rozłącza klientów ani nie zmienia ustawień samego Deco.


## Porównanie blokady HA i aplikacji Deco (beta.5)

Dla **Deco M4R 1.8.2 Build 20251027 Rel. 36869** (AP; X50 nadal niepodłączone)
dodano dwa odczytowe atrybuty do przełączników urządzeń:

- `blacklist_record_fields` — same nazwy pól (bez ich wartości) surowego
  wpisu `admin/client → black_list/list`;
- `blacklist_record_signature` — krótki skrót SHA-256 rekordu z pominięciem MAC.
  Skrót porównuje strukturę i wartości wpisu, ale nie pokazuje samej nazwy klienta,
  jego MAC, IP ani surowych danych.

Atrybut `enforcement_verified: false` przypomina, że `blocked: true`
potwierdza tylko obecność na liście, a **nie odcięcie internetu**.

Aby porównać blokady, aktualizuj przez HACS i uruchom HA ponownie.
Dla jednego testowego urządzenia odczytaj poniższe atrybuty przy blokadzie
zapisanej przez HA i skutecznej blokadzie wykonanej przez aplikację Deco:
`blocked`, `firmware_client_blocked`, `blacklist_record_fields`,
`blacklist_record_signature`. Odczekaj około minutę na odświeżenie encji.

Interpretacja:
- Różne skróty/pola: aplikacja zapisuje inny rekord na liście; dalej analizować format.
- Identyczne skróty/pola: prawdopodobnie dochodzi dodatkowe żądanie albo
  różni się obsługa sesji, aplikacji lub firmware; sam wpis tego nie pokaże.
- Brak skrótu mimo wpisu: sprawdź stan bazowego odczytu, nie wnioskuj o skutecznej blokadzie.

**Nie podmieniamy automatycznie komend na `client_access/write` czy
`block/write`, ponieważ dostępne materiały nie podają zweryfikowanych
parametrów dla tej wersji M4R.** Nie dodano żadnych nowych operacji zapisu.


## Wersja 0.1.0-beta.6 — znaleziony osobny interfejs API aplikacji

Oprócz `admin/client` inne repozytorium przeznaczone dla Deco M4
([oliver006/deco](https://github.com/oliver006/deco/blob/main/admin_mobile_app.go))
dokumentuje drugi kontroler `admin/mobile_app/client` z operacjami
`black_list/list`, `black_list/block` i `black_list/unblock`.
Na M4R 1.8.2 zgodność tego drugiego interfejsu **nie jest jeszcze potwierdzona**.

Beta.6 dodaje **TYLKO ODCZYT** drugiej listy:
- nowa encja `Deco — black_list aplikacji mobilnej`; odczytaj jej stan,
  `endpoint_status`, `error_type`, `error_code`, `entry_count`;
- nowe pole `mobile_black_list` na istniejących przełącznikach klientów:
  `True` jeśli MAC występuje w liście mobilnej, `False` jeśli nie,
  `None` jeśli odczyt się nie powiódł lub odpowiedź była nieznana.

Wprowadzenie zmian nie modyfikuje metody blokowania: podstawowy przełącznik
nadal wywołuje `admin/client → black_list/block`. Nie traktuj stanu
`blocked: true` jako dowodu skutecznego odcięcia internetu.

Zaktualizuj integrację przez HACS, uruchom ponownie Home Assistant i
wykonaj następujący *bezpieczny* szablon:

```jinja2
{% for s in states.switch if 'mi-tv-stick' in s.name | lower %}
URZĄDZENIE: {{ s.name }}
Black_list: {{ s.attributes.get('blocked') }}
Mobile black_list: {{ s.attributes.get('mobile_black_list') }}
Internet: sprawdź ręcznie
{% endfor %}

{% for s in states.sensor if 'deco' in s.entity_id and 'black_list_aplikacji' in s.entity_id %}
MOBILNE API: {{ s.state }}
Status: {{ s.attributes.get('endpoint_status') }}
Kod błędu: {{ s.attributes.get('error_code') }}
Typ błędu: {{ s.attributes.get('error_type') }}
Liczba wpisów: {{ s.attributes.get('entry_count') }}
{% endfor %}
```

Porównaj najpierw stan **bez wykonywania nowej blokady**.
Jeżeli mobilny endpoint nie odpowiada, nie eksperymentuj z żądaniami
`block` / `unblock` ani z formatami danych.


## Wersja 0.1.0-beta.7 — kod błędu HTTP bez ujawniania tokenu

Znaleziono źródło `TransportError` w `tplink-deco-api==2.0.0`:
biblioteka udostępnia numer HTTP przez `exception.status_code`, ale
komunikat wyjątku może zawierać pełny adres z tokenem sesji.
Dlatego beta.7 pokazuje tylko atrybut `http_status_code`, bez surowego
komunikatu. Dla `Deco — black_list aplikacji mobilnej` interpretuj:
- `404` — nie znaleziono ścieżki, nie próbuj wysyłać poleceń zapisu na nią;
- `401` / `403` — serwer odmawia dostępu, sprawdź autoryzację;
- `None` — np. timeout lub problem transportowy bez odpowiedzi HTTP;
- inne — sprawdź numer, bez założenia że operacja jest wspierana.

To nadal tylko diagnostyka i **nie naprawia wykonywania blokady**.
Nie wysyłaj dzienników zawierających `stok`, ciasteczka ani hasła.


## Wersja 0.1.0-beta.8 — niezależna lista blokad `/admin/black_list`

Repozytorium [eduardo-moreira/ha-deco-manager](https://github.com/eduardo-moreira/ha-deco-manager)
deklaruje testy na M4R v2 z firmware 1.8.2 Build 20251027. Autor
używa `/admin/black_list?form=black_list` z operacjami
`read` i `write` (`black_list` jako lista MAC).

Jest to **inna ścieżka** niż dotychczasowe `/admin/client?form=black_list`.
Beta.8 tylko ją **odczytuje** (`operation: read`) i dodaje:
- sensor `Deco — black_list osobna ścieżka` z atrybutami
  `endpoint_status`, `http_status_code`, `error_code`, `entry_count`;
- atrybut `direct_black_list` na przełączniku urządzenia:
  `True`, `False` lub `None` (brak możliwości ustalenia).

Ani blokowanie, ani odblokowywanie nie korzysta jeszcze z tej ścieżki.
**Nie kopiujemy procedury zapisu całej listy** z obcego repozytorium,
ponieważ grozi ona usunięciem blokad innych urządzeń i wymagałaby
atomowej weryfikacji/bezpiecznej obsługi współbieżnych zmian.

Po instalacji beta.8 przez HACS i ponownym uruchomieniu HA, uruchom w
Narzędziach deweloperskich → Szablony:

```jinja2
{% for s in states.sensor
   if 'black_list osobna ścieżka' in s.name | lower %}
=== NOWY ENDPOINT /admin/black_list ===
Stan: {{ s.state }}
Status: {{ s.attributes.get('endpoint_status') }}
HTTP: {{ s.attributes.get('http_status_code') }}
API: {{ s.attributes.get('error_code') }}
Liczba wpisów: {{ s.attributes.get('entry_count') }}
{% endfor %}

{% for s in states.switch
   if 'mi-tv-stick' in s.name | lower %}
=== MI-TV-STICK ===
Lista dotychczasowa: {{ s.attributes.get('blocked') }}
Lista nowa: {{ s.attributes.get('direct_black_list') }}
{% endfor %}
```

Interpretuj status i listę ostrożnie: obsługa `read` nie dowodzi, że
`write` będzie działać na tym samym firmware, a wpis na liście nie
stanowi dowodu skutecznego odcięcia internetu.
