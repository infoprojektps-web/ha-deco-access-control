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
