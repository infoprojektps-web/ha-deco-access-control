# Deco Access Control — instrukcja PL (BETA)

Celem jest blokowanie/odblokowywanie dostępu przez Wi-Fi wybranych urządzeń w Deco M4/X50 pracujących jako AP.

**UWAGA: brak potwierdzonej zgodności z Twoją konfiguracją fizyczną.** Testy jednostkowe są symulowane.

## Instalacja
1. W HA wybierz HACS → ⋮ → Niestandardowe repozytoria.
2. Wklej `https://github.com/infoprojektps-web/ha-deco-access-control`, wybierz `Integration`, dodaj i pobierz.
3. Wyłącz poprzednią integrację `deco_manager`, uruchom HA ponownie.
4. Ustawienia → Urządzenia i usługi → Dodaj integrację → `Deco Access Control`.
5. Host: `192.168.0.205` (sprawdź czy to główne Deco); użytkownik: `admin`; hasło: aktualne hasło logowania właściciela do panelu WWW; interwał: `60`.
6. Po połączeniu wejdź w Ustawienia → Urządzenia i usługi → Encje; znajdź `Dostęp Wi-Fi` i włącz jedną encję urządzenia testowego. Wszystkie przełączniki są domyślnie wyłączone dla bezpieczeństwa.
7. Przetestuj OFF (blokuj), sprawdź listę blokad w aplikacji Deco; następnie ON (odblokuj).

Pierwszego testu nie wykonuj na sprzęcie używanym do zarządzania siecią lub dostępem do Home Assistant. Zanotuj obecne blokady. Blokada odłącza urządzenie od **Wi-Fi Deco**, nie tylko internetu.

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
