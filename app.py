"""
Escape room — prezent-niespodzianka.

Jak to działa: etapy do wyboru z menu (w dowolnej kolejności). Za każdy
rozwiązany zapala się zielone światełko. Cały kod do sejfu pokazuje się
DOPIERO gdy wszystko jest rozwiązane. Uważaj na błędy — jest wspólny
"licznik" w postaci wisielca; jeśli dobije do końca, wszystko resetuje
się od zera. Wszystko, co trzeba zmienić, jest w sekcji KONFIGURACJA
poniżej — reszta pliku działa "z automatu".

Postęp zapisuje się automatycznie (w adresie URL i w pliku na serwerze),
więc jeśli zamknie telefon w połowie i wróci później, aplikacja sama
wznowi tam, gdzie było — nie trzeba niczego wpisywać ręcznie.

Uruchomienie lokalne:   streamlit run app.py
Instalacja zależności:  pip install -r requirements.txt

WAŻNE — reset postępu podczas testowania: otwórz aplikację z dopiskiem
?resetuj=tak na końcu adresu (np. https://twoja-appka.streamlit.app/?resetuj=tak).
Zrób to RAZ, tuż przed przekazaniem prezentu, żeby wyczyścić swoje testy.
"""

import json
import os
import time
from datetime import date

import requests
import streamlit as st
import streamlit.components.v1 as components

# ======================================================================
# 🔧🔧🔧  KONFIGURACJA — TU WSZYSTKO ZMIENIASZ NA SWOJE  🔧🔧🔧
# ======================================================================

IMIE = "Kochanie"  # <- imię Twojej dziewczyny
KOD_SEJFU = "2137"  # <- kod, który pokaże się na końcu, gdy rozwiąże WSZYSTKO

WIADOMOSC_KONCOWA = {
    "pl": """
Udało Ci się rozwiązać wszystko.

To był mój sposób, żeby Ci powiedzieć, jak wiele dla mnie znaczysz — nie
chciałem Ci tego po prostu powiedzieć, chciałem, żebyś to **poczuła**,
etap po etapie. Kod do sejfu jest poniżej. To, co w środku, czeka już
naprawdę na Ciebie. Kocham Cię. ❤️
""",
    "en": """
You solved everything.

This was my way of telling you how much you mean to me — I didn't want
to just say it, I wanted you to **feel** it, stage by stage. The safe
code is below. What's inside is really waiting for you now.
I love you. ❤️
""",
}

# Trudność mini-gry zręcznościowej — 3 poziomy, coraz trudniejsze.
# Obrazki do rebusu (zdjecia od uzytkownika, male i zakodowane w base64,
# zeby caly plik zostal jednym app.py bez osobnych zasobow do wgrania).
REBUS_OBRAZ_LAMPA = "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"
REBUS_OBRAZ_JAK = "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"

POZIOMY_GRY = [
    {"serca": 7, "czarne": 3, "kierunek": "dol", "predkosc": 130, "tempo": 650},
    {"serca": 10, "czarne": 5, "kierunek": "skos", "predkosc": 190, "tempo": 480},
    {"serca": 13, "czarne": 8, "kierunek": "gora", "predkosc": 230, "tempo": 340},
]

# Zagadka szachowa: białe mają wymusić mata w 3 posunięciach (każdy ruch
# zostawia czarnym dokładnie jedną legalną odpowiedź, trzeci to mat).
# Sekwencja zweryfikowana PROGRAMOWO (własny mini-silnik sprawdzający
# każdą legalną odpowiedź czarnych na każdym kroku, nie licząc na pamięć):
# start: białe Kc6, Hb1; czarne sam król na a8; białe zaczynają.
# 1.Kc7 Ka7(jedyna) 2.Hb6+ Ka8(jedyna) 3.Hb7#
# Odpowiedź to same ruchy białych, bez ruchów czarnych.

# ETAPY — każdy daje JEDNĄ cyfrę kodu do sejfu, ale cyfry pokazują się
# dopiero na ekranie końcowym, po rozwiązaniu WSZYSTKIEGO.
ETAPY = [
    {
        "klucz": "gra",
        "emoji": "❤️",
        "tytul": {"pl": "❤️ Refleks", "en": "❤️ Reflexes"},
        "typ": "gra",
    },
    {
        "klucz": "krzyzowka",
        "emoji": "🧩",
        "tytul": {"pl": "🧩 Krzyżówka", "en": "🧩 Crossword"},
        "typ": "krzyzowka",
        "info": {
            "pl": "Cztery angielskie zwroty — to dosłowne tłumaczenia polskich wyrażeń. Ułóż z puli słów poniżej każde z tych polskich wyrażeń.",
            "en": "Four English phrases — each a literal translation of a Polish expression. Arrange the Polish words below into each expression.",
        },
        # Jedna wspolna, duza pula slow dla wszystkich 4 pytan (nie musisz
        # "zuzywac" slowa - to samo slowo moze byc uzyte w wiecej niz jednym
        # pytaniu, bo kazda rozwijana lista jest niezalezna).
        "slowa_pula": [
            "już", "po", "wieś", "coś", "z", "górze", "tak", "ale", "dobrze",
            "ptakach", "nie", "raz", "jest", "spóźnione", "pozdrowienia", "u",
            "źle", "góry", "wsi", "to",
        ],
        "pytania": [
            {
                "typ": "ulozanka",
                "wskazowka": {"pl": "AFTER BIRDS", "en": "AFTER BIRDS"},
                "podpowiedz": {
                    "pl": "Coś się stało i nie da się tego cofnąć.",
                    "en": "Something happened and it can't be undone.",
                },
                "odpowiedz": ["po", "ptakach"],
            },
            {
                "typ": "ulozanka",
                "wskazowka": {"pl": "SOMETHING IS NO YES", "en": "SOMETHING IS NO YES"},
                "podpowiedz": {
                    "pl": "Gdy coś nie gra.",
                    "en": "When something's off.",
                },
                "odpowiedz": ["coś", "jest", "nie", "tak"],
            },
            {
                "typ": "ulozanka",
                "wskazowka": {"pl": "WHAT A VILLAGE", "en": "WHAT A VILLAGE"},
                "podpowiedz": {
                    "pl": "Coś wstydliwego.",
                    "en": "Something embarrassing.",
                },
                "odpowiedz": ["ale", "wieś"],
            },
            {
                "typ": "ulozanka",
                "wskazowka": {"pl": "GREETINGS FROM MOUNTAIN", "en": "GREETINGS FROM MOUNTAIN"},
                "podpowiedz": {
                    "pl": "Przedwczesne pozdrowienia.",
                    "en": "Premature greetings.",
                },
                "odpowiedz": ["pozdrowienia", "z", "góry"],
            },
        ],
    },
    {
        "klucz": "rebus",
        "emoji": "🖼️",
        "tytul": {"pl": "🖼️ Rebus", "en": "🖼️ Rebus"},
        "typ": "rebus",
        "info": {
            "pl": "Każdy obrazek to jedno słowo — po brzmieniu, nie po znaczeniu. Złóż je w całe hasło.",
            "en": "Each picture stands for one word — by how it sounds, not what it means. Put them together.",
        },
        # Twoje zdjecia (lampa + "jak") juz tu sa. Trzeci element zostawiam
        # jako emoji-placeholder — wizerunku Tuska nie uzyje w tej roli (patrz
        # wiadomosc), ale mozesz tu wstawic co innego (inne zdjecie tym samym
        # sposobem co ponizsze dwa, albo zwykle emoji) i dopasowac "odpowiedz".
        "elementy": [
            {"typ": "obraz", "dane": REBUS_OBRAZ_LAMPA},
            {"typ": "obraz", "dane": REBUS_OBRAZ_JAK},
            "❓",
        ],
        "odpowiedz": "lampa jak skurwysyn",
    },
    {
        "klucz": "wordle",
        "emoji": "🟩",
        "tytul": {"pl": "🟩 Wordle dnia", "en": "🟩 Today's Wordle"},
        "typ": "wordle",
        # Aplikacja SAMA pobiera dzisiejsze słowo z (angielskiego) NYT Wordle —
        # nie musisz nic wpisywać. Nie znalazłem podobnie niezawodnego,
        # udokumentowanego źródła dla polskiego odpowiednika (np. Literalnie),
        # dlatego ten etap zawsze odnosi się do angielskiego Wordle, niezależnie
        # od wybranego języka aplikacji. "odpowiedz" niżej to WYŁĄCZNIE awaryjny
        # ręczny kod na wypadek, gdyby pobieranie automatyczne zawiodło.
        "tresc": {
            "pl": "Zagraj dzisiaj w (angielskie) Wordle na nytimes.com/games/wordle i wpisz słowo, które odgadłaś. Aplikacja sama sprawdzi, czy to dzisiejsze słowo.",
            "en": "Play today's Wordle at nytimes.com/games/wordle and type the word you guessed. The app checks it automatically.",
        },
        "odpowiedz": "UZUPEŁNIJ",  # <- awaryjny kod ręczny, używany TYLKO gdy automatyczne pobranie zawiedzie
    },
    {
        "klucz": "data",
        "emoji": "📅",
        "tytul": {"pl": "📅 Dokładna data", "en": "📅 The exact date"},
        "typ": "data",
        "tresc": {
            "pl": "Jaka jest dokładna data, kiedy pierwszy raz jechałaś ze mną samochodem?",
            "en": "What's the exact date of the first time you rode in a car with me?",
        },
        "data": date(2026, 2, 24),
        "jedna_proba": True,
    },
    {
        "klucz": "szachy",
        "emoji": "♟️",
        "tytul": {"pl": "♟️ Szachy", "en": "♟️ Chess"},
        "typ": "szachy",
        "tresc": {
            "pl": (
                "Białe: król c6, hetman b1. Czarne: sam król, a8.\n\n"
                "Białe zaczynają. Znajdź 3 posunięcia białych, z których "
                "każde wymusza jedyną możliwą odpowiedź, a trzecie to mat."
            ),
            "en": (
                "White: King c6, Queen b1. Black: King alone, on a8.\n\n"
                "White to move. Find White's 3 moves, each forcing the "
                "only possible reply, with the third being checkmate."
            ),
        },
        "format_info": {
            "pl": "Zapisz same ruchy białych, oddzielone spacjami, np. Kc7 Qb6 Qb7",
            "en": "Write only White's moves, separated by spaces, e.g. Kc7 Qb6 Qb7",
        },
        "odpowiedz": ["kc7", "qb6", "qb7"],
    },
    {
        "klucz": "dron",
        "emoji": "🚁",
        "tytul": {"pl": "🚁 Dron", "en": "🚁 Drone"},
        "typ": "dron",
    },
    {
        "klucz": "zaba",
        "emoji": "🐸",
        "tytul": {"pl": "🐸 Żaba", "en": "🐸 Frog"},
        "typ": "zaba",
    },
    {
        "klucz": "memory",
        "emoji": "🧠",
        "tytul": {"pl": "🧠 Memory", "en": "🧠 Memory"},
        "typ": "memory",
    },
    {
        "klucz": "simon",
        "emoji": "🎵",
        "tytul": {"pl": "🎵 Simon", "en": "🎵 Simon"},
        "typ": "simon",
    },
    {
        "klucz": "historia",
        "emoji": "🐉",
        "tytul": {"pl": "🐉 Zagadka historyczna", "en": "🐉 History riddle"},
        "typ": "haslo",
        # Fakty zweryfikowane (kilka niezaleznych zrodel): dynastia Jin
        # (Dzurdzenowie) istniala 1115-1234, upadla pod naporem Mongolow.
        # X=1234, Y=119. UWAGA: matematycznie wzor ZAWSZE daje X (bo
        # (X+Y)^2-(X-Y)^2=4XY, podzielone przez 4Y zostaje X) - Y trzeba
        # i tak poprawnie znalezc zeby dobrze policzyc, ale samo dzialanie
        # tego nie zweryfikuje.
        "tresc": {
            "pl": (
                "W Chinach upadła dynastia Jin założona przez Dżurdżenów (ta sama, "
                "która wcześniej podbiła dynastię Liao) — ostatecznie pokonali ją "
                "Mongołowie.\n\n"
                "Znajdź:\n"
                "- X = rok jej upadku\n"
                "- Y = liczba lat, przez które panowała (od założenia do upadku)\n\n"
                "Oblicz:\n\n"
                "$$\\frac{(X+Y)^2 - (X-Y)^2}{4Y}$$\n\n"
                "Wynik (liczba) to hasło."
            ),
            "en": (
                "The Jurchen-founded Jin dynasty of China (the one that had earlier "
                "conquered the Liao dynasty) eventually fell to the Mongols.\n\n"
                "Find:\n"
                "- X = the year it fell\n"
                "- Y = how many years it reigned (from founding to fall)\n\n"
                "Compute:\n\n"
                "$$\\frac{(X+Y)^2 - (X-Y)^2}{4Y}$$\n\n"
                "The result (a number) is the password."
            ),
        },
        "odpowiedz": "1234",
    },
    {
        "klucz": "piano",
        "emoji": "🎹",
        "tytul": {"pl": "🎹 Piano Tiles", "en": "🎹 Piano Tiles"},
        "typ": "piano",
    },
    {
        "klucz": "spiderman",
        "emoji": "🕷️",
        "tytul": {"pl": "🕷️ Spider-Man", "en": "🕷️ Spider-Man"},
        "typ": "quiz",
        "prog": 1.0,
        "pytania": [
            {
                "pytanie": {
                    "pl": "Jak nazywa się ciotka, u której mieszka Peter Parker?",
                    "en": "What's the name of the aunt Peter Parker lives with?",
                },
                "opcje": [
                    {"pl": "Ciotka Rose", "en": "Aunt Rose"},
                    {"pl": "Ciotka May", "en": "Aunt May"},
                    {"pl": "Ciotka Helen", "en": "Aunt Helen"},
                ],
                "poprawna": 1,
            },
            {
                "pytanie": {
                    "pl": "Dla jakiej gazety Peter Parker pracuje jako fotograf?",
                    "en": "Which newspaper does Peter Parker work for as a photographer?",
                },
                "opcje": [
                    {"pl": "The Daily Planet", "en": "The Daily Planet"},
                    {"pl": "The New York Times", "en": "The New York Times"},
                    {"pl": "The Daily Bugle", "en": "The Daily Bugle"},
                ],
                "poprawna": 2,
            },
            {
                "pytanie": {
                    "pl": "Jak nazywa się szef Petera w redakcji, znany z krzyku „Parker!”?",
                    "en": "What's the name of Peter's boss at the paper, known for shouting \"Parker!\"?",
                },
                "opcje": [
                    {"pl": "J. Jonah Jameson", "en": "J. Jonah Jameson"},
                    {"pl": "Robbie Robertson", "en": "Robbie Robertson"},
                    {"pl": "Norman Osborn", "en": "Norman Osborn"},
                ],
                "poprawna": 0,
            },
            {
                "pytanie": {
                    "pl": "Który aktor zagrał Spider-Mana w filmie z 2002 roku w reżyserii Sama Raimiego?",
                    "en": "Which actor played Spider-Man in the 2002 film directed by Sam Raimi?",
                },
                "opcje": [
                    {"pl": "Andrew Garfield", "en": "Andrew Garfield"},
                    {"pl": "Tobey Maguire", "en": "Tobey Maguire"},
                    {"pl": "Tom Holland", "en": "Tom Holland"},
                ],
                "poprawna": 1,
            },
            {
                "pytanie": {
                    "pl": "Jak nazywa się rudowłosa dziewczyna Spider-Mana z klasycznych komiksów i filmów Raimiego?",
                    "en": "What's the name of Spider-Man's red-haired girlfriend from the classic comics and Raimi films?",
                },
                "opcje": [
                    {"pl": "Gwen Stacy", "en": "Gwen Stacy"},
                    {"pl": "Felicia Hardy", "en": "Felicia Hardy"},
                    {"pl": "Mary Jane Watson", "en": "Mary Jane Watson"},
                ],
                "poprawna": 2,
            },
            {
                "pytanie": {
                    "pl": "Jak nazywa się biznesmen, ojciec Harry'ego, zamieniający się w uzbrojonego w szybowiec zielonego złoczyńcę?",
                    "en": "What's the name of the businessman, Harry's father, who turns into a glider-riding green villain?",
                },
                "opcje": [
                    {"pl": "Norman Osborn", "en": "Norman Osborn"},
                    {"pl": "Otto Octavius", "en": "Otto Octavius"},
                    {"pl": "Flint Marko", "en": "Flint Marko"},
                ],
                "poprawna": 0,
            },
            {
                "pytanie": {
                    "pl": "Jak nazywa się nastoletni Spider-Man z równoległego wszechświata, bohater filmu „Spider-Man: Uniwersum”?",
                    "en": "What's the name of the teenage Spider-Man from a parallel universe, hero of \"Spider-Man: Into the Spider-Verse\"?",
                },
                "opcje": [
                    {"pl": "Miguel O'Hara", "en": "Miguel O'Hara"},
                    {"pl": "Miles Morales", "en": "Miles Morales"},
                    {"pl": "Peter B. Parker", "en": "Peter B. Parker"},
                ],
                "poprawna": 1,
            },
            {
                "pytanie": {
                    "pl": "Który aktor gra Spider-Mana w Marvel Cinematic Universe (od 2016 roku)?",
                    "en": "Which actor plays Spider-Man in the Marvel Cinematic Universe (since 2016)?",
                },
                "opcje": [
                    {"pl": "Andrew Garfield", "en": "Andrew Garfield"},
                    {"pl": "Tobey Maguire", "en": "Tobey Maguire"},
                    {"pl": "Tom Holland", "en": "Tom Holland"},
                ],
                "poprawna": 2,
            },
        ],
    },
]

PLIK_STANU = "stan_gry.json"

# ======================================================================
# TEKSTY INTERFEJSU (PL / EN)
# ======================================================================

TEKST = {
    "pl": {
        "rozpocznij": "Rozpocznij 🔓",
        "wroc_do_menu": "⬅ Powrót do menu",
        "sprawdz": "Sprawdź",
        "zatwierdz": "Zatwierdź (jedna próba!)",
        "twoja_odpowiedz": "Twoja odpowiedź:",
        "wybierz": "— wybierz —",
        "slowo": "Słowo",
        "zle_sprobuj": "To nie to. Spróbuj jeszcze raz.",
        "zle_jedna_proba": "To nie ta data. Ta zagadka jest już zamknięta — była tylko jedna próba.",
        "wybierz_date": "Wybierz datę:",
        "jedna_proba_info": "⚠️ Masz tylko JEDNĄ próbę — wybierz uważnie.",
        "wybierz_najpierw": "Najpierw wybierz pełną datę.",
        "dzien": "Dzień",
        "miesiac": "Miesiąc",
        "rok": "Rok",
        "poprawnych": "Poprawnych",
        "twoj_ruch": "Twój ruch:",
        "ukonczone_btn": "✅ Ukończone!",
        "wordle_brak_polaczenia": "Nie udało się automatycznie pobrać dzisiejszego słowa. Spróbuj ponownie za chwilę.",
        "wordle_sprobuj_pobrac": "🔄 Spróbuj pobrać ponownie",
        "rozwiazane_status": "✅ Rozwiązane",
        "zamkniete_status": "🔒 Zamknięte (zła próba — jedna szansa już wykorzystana)",
        "menu_tytul": "Wybierz etap",
        "wszystko_rozwiazane": "🎉 Rozwiązałaś wszystko!",
        "zobacz_kod": "Zobacz kod do sejfu 🔓",
        "przegrana_tytul": "Koniec gry",
        "przegrana_wiadomosc": "Pozdro, poćwicz 😏\n\nWisielec dobił do końca — wszystko zaczynasz od nowa.",
        "zacznij_od_nowa": "Zacznij od nowa",
        "wznow_naglowek": "Masz kod z jakiegoś etapu, a apka go nie zaliczyła? Wpisz go tutaj",
        "kod_label": "Kod:",
        "wznow_btn": "Zatwierdź kod",
        "wznow_ok": "Zaliczone!",
        "nie_rozpoznaje": "Nie rozpoznaję tego kodu.",
        "kod_do_sejfu": "Kod do sejfu:",
        "ukonczone_w": "Ukończone w",
        "min": "min",
    },
    "en": {
        "rozpocznij": "Start 🔓",
        "wroc_do_menu": "⬅ Back to menu",
        "sprawdz": "Check",
        "zatwierdz": "Confirm (one attempt!)",
        "twoja_odpowiedz": "Your answer:",
        "wybierz": "— choose —",
        "slowo": "Word",
        "zle_sprobuj": "Not quite. Try again.",
        "zle_jedna_proba": "Wrong date. This puzzle is now locked — you only got one attempt.",
        "wybierz_date": "Pick a date:",
        "jedna_proba_info": "⚠️ You only get ONE attempt — choose carefully.",
        "wybierz_najpierw": "Pick the full date first.",
        "dzien": "Day",
        "miesiac": "Month",
        "rok": "Year",
        "poprawnych": "Correct",
        "twoj_ruch": "Your move:",
        "ukonczone_btn": "✅ Done!",
        "wordle_brak_polaczenia": "Couldn't automatically fetch today's word. Try again in a moment.",
        "wordle_sprobuj_pobrac": "🔄 Try fetching again",
        "rozwiazane_status": "✅ Solved",
        "zamkniete_status": "🔒 Locked (wrong attempt — your one shot is used)",
        "menu_tytul": "Choose a stage",
        "wszystko_rozwiazane": "🎉 You solved everything!",
        "zobacz_kod": "See the safe code 🔓",
        "przegrana_tytul": "Game over",
        "przegrana_wiadomosc": "Nice try, go practice 😏\n\nThe hangman is complete — everything starts over.",
        "zacznij_od_nowa": "Start over",
        "wznow_naglowek": "Got a code from some stage that didn't register? Enter it here",
        "kod_label": "Code:",
        "wznow_btn": "Submit code",
        "wznow_ok": "Registered!",
        "nie_rozpoznaje": "I don't recognize that code.",
        "kod_do_sejfu": "Safe code:",
        "ukonczone_w": "Completed in",
        "min": "min",
    },
}


def t(klucz):
    jezyk = st.session_state.get("jezyk", "pl")
    return TEKST.get(jezyk, TEKST["pl"]).get(klucz, klucz)


def tt(dwujezyczny):
    """Zwraca wersję PL/EN danego tekstu jeśli to słownik {"pl":..,"en":..};
    zwykły string (np. celowo nietłumaczona zagadka 'po ptakach') zwraca wprost."""
    if isinstance(dwujezyczny, dict):
        jezyk = st.session_state.get("jezyk", "pl")
        return dwujezyczny.get(jezyk, dwujezyczny.get("pl", ""))
    return dwujezyczny


_POLSKIE_ZNAKI = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def znormalizuj(tekst):
    """Do porównywania odpowiedzi: małe litery, bez spacji na końcach, bez
    polskich znaków diakrytycznych — żeby "ale wieś" zaliczało się tak samo
    jak "ale wies" (łatwo pominąć ogonki, pisząc szybko na telefonie)."""
    return str(tekst).strip().lower().translate(_POLSKIE_ZNAKI)


# ======================================================================
# SZABLON MINI-GRY (HTML/CSS/JS) — nie musisz tu nic zmieniać.
# Trudność steruje się z góry pliku, przez POZIOMY_GRY. Uwaga: teksty
# wewnątrz tej mini-gry są na razie tylko po polsku.
# ======================================================================

SZABLON_GRY = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; touch-action: manipulation; }
  body {
    margin: 0;
    font-family: -apple-system, 'Poppins', sans-serif;
    background: radial-gradient(circle at 50% 0%, #241b3a 0%, #0d0d0d 70%);
    overflow: hidden;
  }
  #panel {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  .wycisz-btn {
    background: none;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 20px;
    color: #f5f5f0;
    font-size: 16px;
    padding: 2px 10px;
    cursor: pointer;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 420px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
  }
  .item {
    position: absolute;
    font-size: 34px;
    line-height: 1;
    cursor: pointer;
    transition: transform 0.15s ease, opacity 0.15s ease, filter 0.2s ease;
  }
  .item.zlapane {
    transform: scale(1.7);
    opacity: 0;
  }
  .item.zlapane-zle {
    transform: scale(1.4);
    filter: brightness(3) drop-shadow(0 0 14px #ff3b3b);
  }
  #nakladka {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
  }
  #nakladka h2 { font-size: 22px; margin: 0 0 8px; }
  #nakladka p { margin: 0 0 6px; font-size: 14px; opacity: 0.85; }
  #kodWygrany {
    font-size: 28px;
    letter-spacing: 4px;
    color: #fff;
    background: #1a1a2e;
    padding: 8px 18px;
    border-radius: 10px;
    border: 1px solid #d4af37;
    margin: 10px 0;
  }
  button.gra-btn {
    background: linear-gradient(135deg,#e6c15c,#d4af37);
    border: none;
    padding: 10px 26px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 10px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span id="poziomEtykieta">Poziom 1</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="nakladka">
      <h2 id="nakladkaTytul">Poziom 1</h2>
      <p id="nakladkaOpis"></p>
      <button class="gra-btn" id="nakladkaBtn">Graj ▶</button>
    </div>
  </div>

<script>
  var POZIOMY = __POZIOMY_JSON__;
  var KOLORY = ['❤️','💛','💚','💙','💜','🧡'];

  var gra = document.getElementById('gra');
  var nakladka = document.getElementById('nakladka');
  var nakladkaTytul = document.getElementById('nakladkaTytul');
  var nakladkaOpis = document.getElementById('nakladkaOpis');
  var nakladkaBtn = document.getElementById('nakladkaBtn');
  var poziomEtykieta = document.getElementById('poziomEtykieta');
  var wyciszBtn = document.getElementById('wyciszBtn');

  var aktualnyPoziom = 0;
  var poziom = null;
  var kolejka = [];
  var doZlapania = 0;
  var aktywneElementy = [];
  var interwalSpawn = null;
  var trwa = false;
  var ostatniCzas = null;
  var wyciszone = false;

  var audioCtx = null;
  var bipInterval = null;

  function losowo(min, max) { return Math.random() * (max - min) + min; }

  function inicjujDzwiek() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
    } catch (e) {
      audioCtx = null;
    }
  }

  function zagrajBip(czestotliwosc) {
    if (!audioCtx || wyciszone) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.value = czestotliwosc;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.22, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.2);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.2);
    } catch (e) {
      // dźwięk to dodatek — jego brak nie może zepsuć gry
    }
  }

  function startMuzyka(tempoMs) {
    zatrzymajMuzyke();
    var nuty = [220.00, 277.18, 329.63, 277.18];
    var i = 0;
    bipInterval = setInterval(function () {
      zagrajBip(nuty[i % nuty.length]);
      i++;
    }, tempoMs);
  }

  function zatrzymajMuzyke() {
    if (bipInterval) {
      clearInterval(bipInterval);
      bipInterval = null;
    }
  }

  function stworzElement(zly) {
    var el = document.createElement('div');
    el.className = 'item';
    el.textContent = zly ? '🖤' : KOLORY[Math.floor(Math.random() * KOLORY.length)];
    el.dataset.zly = zly ? '1' : '0';

    var szer = gra.clientWidth;
    var wys = gra.clientHeight;
    var predkosc = poziom.predkosc;
    var x, y, vx, vy;

    if (poziom.kierunek === 'gora') {
      x = szer + 30;
      y = wys + 30;
      vx = -predkosc * 0.85;
      vy = -predkosc;
    } else if (poziom.kierunek === 'skos') {
      x = losowo(10, szer - 40);
      y = -40;
      vx = losowo(-90, 90);
      vy = predkosc;
    } else {
      x = losowo(10, szer - 40);
      y = -40;
      vx = losowo(-25, 25);
      vy = predkosc;
    }

    el.style.left = x + 'px';
    el.style.top = y + 'px';
    el.dataset.x = x;
    el.dataset.y = y;
    el.dataset.vx = vx;
    el.dataset.vy = vy;

    el.addEventListener('click', function () {
      if (el.dataset.dotkniete) return;
      kliknieto(el);
    });
    el.addEventListener('touchstart', function (e) {
      e.preventDefault();
      el.dataset.dotkniete = '1';
      kliknieto(el);
      setTimeout(function () { delete el.dataset.dotkniete; }, 500);
    }, { passive: false });

    gra.appendChild(el);
    aktywneElementy.push(el);
  }

  function kliknieto(el) {
    if (!trwa || el.dataset.klik) return;
    el.dataset.klik = '1';
    var zly = el.dataset.zly === '1';

    if (zly) {
      el.classList.add('zlapane-zle');
      trwa = false;
      clearInterval(interwalSpawn);
      setTimeout(function () { zakonczPoziom(false, 'czarne'); }, 220);
    } else {
      el.classList.add('zlapane');
      setTimeout(function () { usunElement(el); }, 150);
      doZlapania -= 1;
      if (doZlapania <= 0) {
        trwa = false;
        clearInterval(interwalSpawn);
        setTimeout(function () { zakonczPoziom(true); }, 200);
      }
    }
  }

  function usunElement(el) {
    var idx = aktywneElementy.indexOf(el);
    if (idx > -1) aktywneElementy.splice(idx, 1);
    if (el.parentNode) el.remove();
  }

  function petlaAnimacji(czas) {
    if (!trwa) { ostatniCzas = null; return; }
    if (ostatniCzas === null) ostatniCzas = czas;
    var dt = (czas - ostatniCzas) / 1000;
    ostatniCzas = czas;

    var szer = gra.clientWidth;
    var wys = gra.clientHeight;

    for (var i = aktywneElementy.length - 1; i >= 0; i--) {
      var el = aktywneElementy[i];
      var x = parseFloat(el.dataset.x) + parseFloat(el.dataset.vx) * dt;
      var y = parseFloat(el.dataset.y) + parseFloat(el.dataset.vy) * dt;
      el.dataset.x = x;
      el.dataset.y = y;
      el.style.left = x + 'px';
      el.style.top = y + 'px';

      if (y < -60 || y > wys + 60 || x < -60 || x > szer + 60) {
        var bylZly = el.dataset.zly === '1';
        var zlapany = el.dataset.klik === '1';
        usunElement(el);
        if (!zlapany && !bylZly && trwa) {
          trwa = false;
          clearInterval(interwalSpawn);
          zakonczPoziom(false, 'ucieklo');
          return;
        }
      }
    }

    requestAnimationFrame(petlaAnimacji);
  }

  function startPoziom(indeks) {
    aktualnyPoziom = indeks;
    poziom = POZIOMY[indeks];
    poziomEtykieta.textContent = 'Poziom ' + (indeks + 1);

    var lista = [];
    var i;
    for (i = 0; i < poziom.serca; i++) lista.push(false);
    for (i = 0; i < poziom.czarne; i++) lista.push(true);
    for (i = lista.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = lista[i]; lista[i] = lista[j]; lista[j] = tmp;
    }
    kolejka = lista;
    doZlapania = poziom.serca;

    aktywneElementy.forEach(function (el) { el.remove(); });
    aktywneElementy = [];

    nakladka.style.display = 'none';
    trwa = true;
    ostatniCzas = null;

    interwalSpawn = setInterval(function () {
      if (kolejka.length === 0) { clearInterval(interwalSpawn); return; }
      stworzElement(kolejka.shift());
    }, poziom.tempo);

    requestAnimationFrame(petlaAnimacji);

    if (!wyciszone) {
      inicjujDzwiek();
      startMuzyka(poziom.tempo);
    }
  }

  function opisPoziomu(indeks) {
    if (indeks === 1) return 'Poziom 2 — szybciej i na ukos.';
    if (indeks === 2) return 'Poziom 3 — najszybciej, pod górę, od prawej do lewej.';
    return '';
  }

  function zakonczPoziom(wygrana, powod) {
    zatrzymajMuzyke();
    aktywneElementy.forEach(function (el) { el.remove(); });
    aktywneElementy = [];
    nakladka.style.display = 'flex';

    if (wygrana) {
      if (aktualnyPoziom >= POZIOMY.length - 1) {
        nakladkaTytul.textContent = '🎉 Wygrałaś!';
        nakladkaOpis.textContent = '';
        nakladkaBtn.style.display = 'none';
      } else {
        var nastepny = aktualnyPoziom + 1;
        nakladkaTytul.textContent = '🎉 Poziom ' + (aktualnyPoziom + 1) + ' ukończony!';
        nakladkaOpis.textContent = opisPoziomu(nastepny);
        nakladkaBtn.style.display = 'inline-block';
        nakladkaBtn.textContent = 'Graj ▶';
        nakladkaBtn.onclick = function () { inicjujDzwiek(); startPoziom(nastepny); };
      }
    } else {
      nakladkaTytul.textContent = powod === 'czarne' ? '🖤 Czarnych nie łapiemy!' : '💔 Uciekło Ci serduszko!';
      nakladkaOpis.textContent = 'Trzeba złapać wszystkie, bez pomyłek. Spróbuj ponownie.';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); startPoziom(aktualnyPoziom); };
    }
  }

  wyciszBtn.addEventListener('click', function () {
    wyciszone = !wyciszone;
    wyciszBtn.textContent = wyciszone ? '🔇' : '🔊';
    if (wyciszone) {
      zatrzymajMuzyke();
    } else if (trwa) {
      inicjujDzwiek();
      startMuzyka(poziom.tempo);
    }
  });

  nakladkaBtn.onclick = function () { inicjujDzwiek(); startPoziom(0); };
</script>
</body>
</html>
"""

# ======================================================================
# SZABLON MINI-GRY "DRON" (flappy-bird, ale z dronem) — nie musisz tu nic
# zmieniać. Trudność steruje się stałymi na górze bloku <script> (CEL_WYNIK,
# GRAWITACJA, SILA_SKOKU, PREDKOSC_START, ODSTEP_SPAWN_START, LUKA_START/MIN).
# Nie dało się tego przetestować "na żywo" w moim środowisku (brak
# przeglądarki) — koniecznie zagraj sam i dostrój liczby, jeśli trzeba.
# ======================================================================

SZABLON_DRONA = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; touch-action: manipulation; }
  body {
    margin: 0;
    font-family: -apple-system, 'Poppins', sans-serif;
    background: radial-gradient(circle at 50% 0%, #241b3a 0%, #0d0d0d 70%);
    overflow: hidden;
  }
  #panel {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  .wycisz-btn {
    background: none;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 20px;
    color: #f5f5f0;
    font-size: 16px;
    padding: 2px 10px;
    cursor: pointer;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 420px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
    cursor: pointer;
  }
  #dron {
    position: absolute;
    width: 34px;
    height: 34px;
    z-index: 5;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
  }
  #wynikNaEkranie {
    position: absolute;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 32px;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 2px 6px rgba(0,0,0,0.6);
    z-index: 4;
    pointer-events: none;
  }
  .przeszkoda {
    position: absolute;
    width: 50px;
    background: linear-gradient(180deg, #3a3050, #241b3a);
    border-left: 2px solid #d4af37;
    border-right: 2px solid #d4af37;
  }
  .przeszkoda-gora {
    top: 0;
    border-bottom: 5px solid #f0dfa8;
  }
  .przeszkoda-dol {
    border-top: 5px solid #f0dfa8;
  }
  #nakladka {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
  }
  #nakladka h2 { font-size: 22px; margin: 0 0 8px; }
  #nakladka p { margin: 0 0 6px; font-size: 14px; opacity: 0.85; }
  #kodWygrany {
    font-size: 28px;
    letter-spacing: 4px;
    color: #fff;
    background: #1a1a2e;
    padding: 8px 18px;
    border-radius: 10px;
    border: 1px solid #d4af37;
    margin: 10px 0;
  }
  button.gra-btn {
    background: linear-gradient(135deg,#e6c15c,#d4af37);
    border: none;
    padding: 10px 26px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 10px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span>🛸 Dron</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="wynikNaEkranie">0</div>
    <svg id="dron" viewBox="0 0 34 34">
      <line x1="6" y1="6" x2="28" y2="28" stroke="#9a9a9a" stroke-width="2"/>
      <line x1="28" y1="6" x2="6" y2="28" stroke="#9a9a9a" stroke-width="2"/>
      <circle cx="6" cy="6" r="4.5" fill="none" stroke="#d4af37" stroke-width="2"/>
      <circle cx="28" cy="6" r="4.5" fill="none" stroke="#d4af37" stroke-width="2"/>
      <circle cx="6" cy="28" r="4.5" fill="none" stroke="#d4af37" stroke-width="2"/>
      <circle cx="28" cy="28" r="4.5" fill="none" stroke="#d4af37" stroke-width="2"/>
      <rect x="11" y="11" width="12" height="12" rx="3" fill="#1a1a1a" stroke="#e6c15c" stroke-width="1.5"/>
      <circle cx="17" cy="17" r="1.6" fill="#ff4d4d"/>
    </svg>
    <div id="nakladka">
      <h2 id="nakladkaTytul">Dron</h2>
      <p id="nakladkaOpis"></p>
      <button class="gra-btn" id="nakladkaBtn">Graj ▶</button>
    </div>
  </div>

<script>
  var gra = document.getElementById('gra');
  var dron = document.getElementById('dron');
  var wynikNaEkranie = document.getElementById('wynikNaEkranie');
  var nakladka = document.getElementById('nakladka');
  var nakladkaTytul = document.getElementById('nakladkaTytul');
  var nakladkaOpis = document.getElementById('nakladkaOpis');
  var nakladkaBtn = document.getElementById('nakladkaBtn');
  var wyciszBtn = document.getElementById('wyciszBtn');

  var DRON_X = 0.25;
  var DRON_R = 14;
  var GRAWITACJA = 1400;
  var SILA_SKOKU = -380;
  var PREDKOSC_START = 150;
  var ODSTEP_SPAWN_START = 1.7;
  var SZEROKOSC_PRZESZKODY = 50;
  var LUKA_START = 145;
  var LUKA_MIN = 105;
  var CEL_WYNIK = 15;
  var MARGINES = 60;

  var dronY = 0;
  var dronVY = 0;
  var przeszkody = [];
  var wynik = 0;
  var trwa = false;
  var czasOstatni = null;
  var czasOdSpawnu = 0;
  var wyciszone = false;

  var audioCtx = null;

  function losowo(min, max) { return Math.random() * (max - min) + min; }

  function inicjujDzwiek() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
    } catch (e) {
      audioCtx = null;
    }
  }

  function zagrajTon(czestotliwosc, czasTrwania, typ) {
    if (!audioCtx || wyciszone) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = typ;
      osc.frequency.value = czestotliwosc;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.18, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + czasTrwania);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + czasTrwania);
    } catch (e) {
      // dzwiek to dodatek - jego brak nie moze zepsuc gry
    }
  }

  function zagrajDzwiek(typ) {
    if (typ === 'skok') zagrajTon(500, 0.08, 'square');
    else if (typ === 'punkt') zagrajTon(800, 0.12, 'sine');
    else if (typ === 'crash') zagrajTon(120, 0.35, 'sawtooth');
  }

  var interwalMuzyki = null;
  var NUTY_MUZYKI = [261.63, 329.63, 392.00, 523.25, 392.00, 329.63];
  function startMuzyke() {
    zatrzymajMuzyke();
    var i = 0;
    interwalMuzyki = setInterval(function () {
      zagrajTon(NUTY_MUZYKI[i % NUTY_MUZYKI.length], 0.22, 'triangle');
      i++;
    }, 340);
  }
  function zatrzymajMuzyke() {
    if (interwalMuzyki) {
      clearInterval(interwalMuzyki);
      interwalMuzyki = null;
    }
  }

  function skok() {
    if (!trwa) return;
    dronVY = SILA_SKOKU;
    zagrajDzwiek('skok');
  }

  function usunPrzeszkode(p) {
    if (p.elGora.parentNode) p.elGora.remove();
    if (p.elDol.parentNode) p.elDol.remove();
  }

  function stworzPrzeszkode(szer, wys, gapY, gapH) {
    var gora = document.createElement('div');
    gora.className = 'przeszkoda przeszkoda-gora';
    gora.style.height = (gapY - gapH / 2) + 'px';

    var dol = document.createElement('div');
    dol.className = 'przeszkoda przeszkoda-dol';
    dol.style.top = (gapY + gapH / 2) + 'px';
    dol.style.height = (wys - (gapY + gapH / 2)) + 'px';

    gra.appendChild(gora);
    gra.appendChild(dol);

    return { x: szer + 10, gapY: gapY, gapH: gapH, minieta: false, elGora: gora, elDol: dol };
  }

  function aktualizujWynik() {
    wynikNaEkranie.textContent = wynik;
  }

  function rysuj() {
    dron.style.left = (gra.clientWidth * DRON_X) + 'px';
    dron.style.top = dronY + 'px';
    var obrot = Math.max(-25, Math.min(70, dronVY / 8));
    dron.style.transform = 'translate(-50%, -50%) rotate(' + obrot + 'deg)';

    for (var i = 0; i < przeszkody.length; i++) {
      przeszkody[i].elGora.style.left = przeszkody[i].x + 'px';
      przeszkody[i].elDol.style.left = przeszkody[i].x + 'px';
    }
  }

  function petla(czas) {
    if (!trwa) { czasOstatni = null; return; }
    if (czasOstatni === null) czasOstatni = czas;
    var dt = Math.min((czas - czasOstatni) / 1000, 0.05);
    czasOstatni = czas;

    var szer = gra.clientWidth;
    var wys = gra.clientHeight;

    dronVY += GRAWITACJA * dt;
    dronY += dronVY * dt;

    var mnoznik = 1 + Math.min(wynik, 20) * 0.03;
    var predkoscAktualna = PREDKOSC_START * mnoznik;
    var lukaAktualna = Math.max(LUKA_MIN, LUKA_START - wynik * 2);

    czasOdSpawnu += dt;
    var odstepAktualny = ODSTEP_SPAWN_START / mnoznik;
    if (czasOdSpawnu >= odstepAktualny) {
      czasOdSpawnu = 0;
      var gapYMin = MARGINES + lukaAktualna / 2;
      var gapYMax = wys - MARGINES - lukaAktualna / 2;
      var gapY = losowo(gapYMin, gapYMax);
      przeszkody.push(stworzPrzeszkode(szer, wys, gapY, lukaAktualna));
    }

    var dronXpx = szer * DRON_X;

    for (var i = przeszkody.length - 1; i >= 0; i--) {
      var p = przeszkody[i];
      p.x -= predkoscAktualna * dt;

      if (p.x < dronXpx + DRON_R && p.x + SZEROKOSC_PRZESZKODY > dronXpx - DRON_R) {
        var krawedzGornej = p.gapY - p.gapH / 2;
        var krawedzDolnej = p.gapY + p.gapH / 2;
        if (dronY - DRON_R < krawedzGornej || dronY + DRON_R > krawedzDolnej) {
          zakonczGre(false);
          return;
        }
      }

      if (!p.minieta && p.x + SZEROKOSC_PRZESZKODY < dronXpx - DRON_R) {
        p.minieta = true;
        wynik += 1;
        zagrajDzwiek('punkt');
        aktualizujWynik();
        if (wynik >= CEL_WYNIK) {
          zakonczGre(true);
          return;
        }
      }

      if (p.x < -SZEROKOSC_PRZESZKODY) {
        usunPrzeszkode(p);
        przeszkody.splice(i, 1);
      }
    }

    if (dronY - DRON_R < 0 || dronY + DRON_R > wys) {
      zakonczGre(false);
      return;
    }

    rysuj();
    requestAnimationFrame(petla);
  }

  function rozpocznijGre() {
    przeszkody.forEach(function (p) { usunPrzeszkode(p); });
    przeszkody = [];
    wynik = 0;
    aktualizujWynik();
    dronY = gra.clientHeight / 2;
    dronVY = 0;
    czasOdSpawnu = 0;
    czasOstatni = null;
    nakladka.style.display = 'none';
    trwa = true;
    rysuj();
    requestAnimationFrame(petla);
    startMuzyke();
  }

  function zakonczGre(wygrana) {
    trwa = false;
    przeszkody.forEach(function (p) { usunPrzeszkode(p); });
    przeszkody = [];
    nakladka.style.display = 'flex';
    zatrzymajMuzyke();

    if (wygrana) {
      zagrajDzwiek('punkt');
      nakladkaTytul.textContent = '🎉 Udało się!';
      nakladkaOpis.textContent = '';
      nakladkaBtn.style.display = 'none';
    } else {
      zagrajDzwiek('crash');
      nakladkaTytul.textContent = '💥 Rozbity dron...';
      nakladkaOpis.textContent = 'Wynik: ' + wynik + ' / ' + CEL_WYNIK + '. Spróbuj jeszcze raz.';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
    }
  }

  var pominDrugiSkok = false;
  gra.addEventListener('click', function () {
    if (pominDrugiSkok) return;
    if (nakladka.style.display !== 'none') return;
    skok();
  });
  gra.addEventListener('touchstart', function (e) {
    if (nakladka.style.display !== 'none') return;
    e.preventDefault();
    pominDrugiSkok = true;
    skok();
    setTimeout(function () { pominDrugiSkok = false; }, 500);
  }, { passive: false });

  wyciszBtn.addEventListener('click', function () {
    wyciszone = !wyciszone;
    wyciszBtn.textContent = wyciszone ? '🔇' : '🔊';
  });

  nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
</script>
</body>
</html>
"""

# ======================================================================
# SZABLON MINI-GRY "ŻABA" (geometry dash, ale z żabą) — nie musisz tu nic
# zmieniać. Trudność steruje się stałymi na górze bloku <script>
# (CEL_WYNIK, GRAWITACJA, SILA_SKOKU, PREDKOSC_START, ODSTEP_SPAWN_START).
# Podobnie jak przy dronie: nie dało się tego przetestować "na żywo" bez
# przeglądarki — koniecznie zagraj sam i dostrój liczby, jeśli trzeba.
# Skacze tylko wtedy, gdy żaba stoi na ziemi (jak w prawdziwym Geometry
# Dash — nie ma podwójnego skoku w powietrzu).
# ======================================================================

SZABLON_ZABY = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; touch-action: manipulation; }
  body {
    margin: 0;
    font-family: -apple-system, 'Poppins', sans-serif;
    background: radial-gradient(circle at 50% 0%, #241b3a 0%, #0d0d0d 70%);
    overflow: hidden;
  }
  #panel {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  .wycisz-btn {
    background: none;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 20px;
    color: #f5f5f0;
    font-size: 16px;
    padding: 2px 10px;
    cursor: pointer;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 420px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
    cursor: pointer;
  }
  #podloze {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 8px;
    background: linear-gradient(90deg, #d4af37, #f0dfa8, #d4af37);
    z-index: 1;
  }
  #zaba {
    position: absolute;
    font-size: 34px;
    line-height: 1;
    z-index: 5;
  }
  #wynikNaEkranie {
    position: absolute;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 32px;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 2px 6px rgba(0,0,0,0.6);
    z-index: 4;
    pointer-events: none;
  }
  .przeszkoda-kontener {
    position: absolute;
    bottom: 8px;
    height: 0;
    z-index: 2;
  }
  .kolec {
    position: absolute;
    bottom: 0;
    width: 0;
    height: 0;
    border-left: 15px solid transparent;
    border-right: 15px solid transparent;
    border-bottom: 35px solid #d4af37;
    filter: drop-shadow(0 0 4px rgba(212,175,55,0.4));
  }
  .kolec-wysoki {
    border-bottom-width: 100px;
    border-bottom-color: #e6738a;
    filter: drop-shadow(0 0 4px rgba(230,115,138,0.5));
  }
  .kontener-sufit {
    position: absolute;
    top: 0;
    z-index: 2;
  }
  .kolec-sufit {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 0;
    height: 0;
    border-left: 15px solid transparent;
    border-right: 15px solid transparent;
    border-top: 35px solid #d4af37;
    filter: drop-shadow(0 0 4px rgba(212,175,55,0.4));
  }
  .platforma {
    position: absolute;
    height: 14px;
    background: linear-gradient(180deg, #e8d9b5, #a9834f);
    border: 2px solid #d4af37;
    border-radius: 4px;
    z-index: 2;
  }
  #nakladka {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
  }
  #nakladka h2 { font-size: 22px; margin: 0 0 8px; }
  #nakladka p { margin: 0 0 6px; font-size: 14px; opacity: 0.85; }
  button.gra-btn {
    background: linear-gradient(135deg,#e6c15c,#d4af37);
    border: none;
    padding: 10px 26px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 10px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span>🐸 Żaba</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="podloze"></div>
    <div id="wynikNaEkranie">0</div>
    <div id="zaba">🐸</div>
    <div id="nakladka">
      <h2 id="nakladkaTytul">Żaba</h2>
      <p id="nakladkaOpis"></p>
      <button class="gra-btn" id="nakladkaBtn">Graj ▶</button>
    </div>
  </div>

<script>
  var gra = document.getElementById('gra');
  var zaba = document.getElementById('zaba');
  var wynikNaEkranie = document.getElementById('wynikNaEkranie');
  var nakladka = document.getElementById('nakladka');
  var nakladkaTytul = document.getElementById('nakladkaTytul');
  var nakladkaOpis = document.getElementById('nakladkaOpis');
  var nakladkaBtn = document.getElementById('nakladkaBtn');
  var wyciszBtn = document.getElementById('wyciszBtn');

  var ZABA_X = 0.22;
  var ZABA_R = 14;
  var ZABA_WYSOKOSC = 30;
  var GRAWITACJA = 2200;
  var SILA_SKOKU = -620;
  var PODLOZE_WYSOKOSC = 8;
  var KOLEC_SZEROKOSC = 30;
  var KOLEC_WYSOKOSC = 35;
  var KOLEC_WYSOKOSC_WYSOKI = 100;
  var TOLERANCJA_KOLIZJI = 3;
  var TOLERANCJA_LADOWANIA = 4;
  var PREDKOSC_START = 220;
  var ODSTEP_SPAWN_START = 1.8;
  var CEL_WYNIK = 20;
  var PLATFORMA_WYSOKOSC_NAD_ZIEMIA = 70;
  var PLATFORMA_SZEROKOSC = 110;
  var PODEST_KOLCE_NACHODZENIE = 25;
  var SUFIT_PRZERWA_OD_ZIEMI = 62;

  var zabaDol = 0;
  var zabaDolPoprzedni = 0;
  var zabaVY = 0;
  var naZiemi = true;
  var przeszkody = [];
  var wynik = 0;
  var trwa = false;
  var czasOstatni = null;
  var czasOdSpawnu = 0;
  var wyciszone = false;

  var audioCtx = null;

  function losowo(min, max) { return Math.random() * (max - min) + min; }

  function inicjujDzwiek() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
    } catch (e) {
      audioCtx = null;
    }
  }

  function zagrajTon(czestotliwosc, czasTrwania, typ) {
    if (!audioCtx || wyciszone) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = typ;
      osc.frequency.value = czestotliwosc;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.18, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + czasTrwania);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + czasTrwania);
    } catch (e) {
      // dzwiek to dodatek - jego brak nie moze zepsuc gry
    }
  }

  function zagrajDzwiek(typ) {
    if (typ === 'skok') zagrajTon(450, 0.07, 'square');
    else if (typ === 'punkt') zagrajTon(750, 0.1, 'sine');
    else if (typ === 'crash') zagrajTon(110, 0.35, 'sawtooth');
  }

  var interwalMuzyki = null;
  var NUTY_MUZYKI = [392.00, 0, 523.25, 392.00, 0, 659.25, 523.25, 0];
  function startMuzyke() {
    zatrzymajMuzyke();
    var i = 0;
    interwalMuzyki = setInterval(function () {
      var nuta = NUTY_MUZYKI[i % NUTY_MUZYKI.length];
      if (nuta > 0) zagrajTon(nuta, 0.09, 'square');
      i++;
    }, 190);
  }
  function zatrzymajMuzyke() {
    if (interwalMuzyki) {
      clearInterval(interwalMuzyki);
      interwalMuzyki = null;
    }
  }

  function skok() {
    if (!trwa || !naZiemi) return;
    zabaVY = SILA_SKOKU;
    naZiemi = false;
    zagrajDzwiek('skok');
  }

  function usunPrzeszkode(p) {
    if (p.typ === 'podest-kolce') {
      if (p.elPodest.parentNode) p.elPodest.remove();
      if (p.elKolec.parentNode) p.elKolec.remove();
    } else if (p.el && p.el.parentNode) {
      p.el.remove();
    }
  }

  // Ile kolcow w grupie na start TYLKO pojedyncze; podwojne i potrojne
  // dochodza stopniowo wraz z wynikiem.
  function losujLiczbeKolcow() {
    if (wynik < 5) return 1;
    if (wynik < 12) return Math.random() < 0.6 ? 1 : 2;
    return Math.random() < 0.45 ? 1 : (Math.random() < 0.75 ? 2 : 3);
  }

  // Typ nastepnej przeszkody - na start same kolce, potem dochodza
  // platformy, potem kombinacja podest+wysoki kolec (trzeba wskoczyc na
  // podest, zeby miec dosc wysokosci na przeskoczenie), a najpozniej
  // kolce sufitowe (czasem NIE wolno skakac, trzeba przebiec pod spodem).
  function losujTypPrzeszkody() {
    if (wynik < 6) return 'kolce';
    var r = Math.random();
    if (wynik < 10) {
      return r < 0.7 ? 'kolce' : 'platforma';
    }
    if (wynik < 16) {
      if (r < 0.5) return 'kolce';
      if (r < 0.75) return 'platforma';
      return 'podest-kolce';
    }
    if (r < 0.4) return 'kolce';
    if (r < 0.6) return 'platforma';
    if (r < 0.8) return 'sufit';
    return 'podest-kolce';
  }

  function stworzPrzeszkode(szer, groundY) {
    var typ = losujTypPrzeszkody();
    var xStart = szer + 20;

    if (typ === 'platforma') {
      var el = document.createElement('div');
      el.className = 'platforma';
      el.style.width = PLATFORMA_SZEROKOSC + 'px';
      el.style.left = xStart + 'px';
      var wysokoscY = groundY - PLATFORMA_WYSOKOSC_NAD_ZIEMIA;
      el.style.top = wysokoscY + 'px';
      gra.appendChild(el);
      return { typ: 'platforma', x: xStart, szerokosc: PLATFORMA_SZEROKOSC, wysokoscY: wysokoscY, minieta: false, el: el };
    }

    if (typ === 'podest-kolce') {
      var elPodest = document.createElement('div');
      elPodest.className = 'platforma';
      elPodest.style.width = PLATFORMA_SZEROKOSC + 'px';
      elPodest.style.left = xStart + 'px';
      var wysokoscY2 = groundY - PLATFORMA_WYSOKOSC_NAD_ZIEMIA;
      elPodest.style.top = wysokoscY2 + 'px';
      gra.appendChild(elPodest);

      var offsetKolca = PLATFORMA_SZEROKOSC - PODEST_KOLCE_NACHODZENIE;
      var elKolec = document.createElement('div');
      elKolec.className = 'przeszkoda-kontener';
      elKolec.style.width = KOLEC_SZEROKOSC + 'px';
      elKolec.style.left = (xStart + offsetKolca) + 'px';
      var kolecWysoki = document.createElement('div');
      kolecWysoki.className = 'kolec kolec-wysoki';
      elKolec.appendChild(kolecWysoki);
      gra.appendChild(elKolec);

      return {
        typ: 'podest-kolce', x: xStart, offsetKolca: offsetKolca,
        szerokosc: offsetKolca + KOLEC_SZEROKOSC, wysokoscY: wysokoscY2,
        elPodest: elPodest, elKolec: elKolec, minieta: false
      };
    }

    if (typ === 'sufit') {
      var kontener = document.createElement('div');
      kontener.className = 'kontener-sufit';
      kontener.style.width = KOLEC_SZEROKOSC + 'px';
      kontener.style.left = xStart + 'px';
      var dolnaKrawedzY = groundY - SUFIT_PRZERWA_OD_ZIEMI;
      kontener.style.height = dolnaKrawedzY + 'px';
      var kolec = document.createElement('div');
      kolec.className = 'kolec-sufit';
      kontener.appendChild(kolec);
      gra.appendChild(kontener);
      return { typ: 'sufit', x: xStart, szerokosc: KOLEC_SZEROKOSC, dolnaKrawedzY: dolnaKrawedzY, minieta: false, el: kontener };
    }

    var liczbaKolcow = losujLiczbeKolcow();
    var szerokoscCalkowita = liczbaKolcow * KOLEC_SZEROKOSC;
    var kontenerK = document.createElement('div');
    kontenerK.className = 'przeszkoda-kontener';
    kontenerK.style.width = szerokoscCalkowita + 'px';
    kontenerK.style.left = xStart + 'px';
    for (var i = 0; i < liczbaKolcow; i++) {
      var kolecN = document.createElement('div');
      kolecN.className = 'kolec';
      kolecN.style.left = (i * KOLEC_SZEROKOSC) + 'px';
      kontenerK.appendChild(kolecN);
    }
    gra.appendChild(kontenerK);
    return { typ: 'kolce', x: xStart, szerokosc: szerokoscCalkowita, minieta: false, el: kontenerK };
  }

  function aktualizujWynik() {
    wynikNaEkranie.textContent = wynik;
  }

  function rysuj() {
    var szer = gra.clientWidth;
    zaba.style.left = (szer * ZABA_X) + 'px';
    zaba.style.top = zabaDol + 'px';
    zaba.style.transform = 'translate(-50%, -100%)';
  }

  // Zwraca Y powierzchni, na ktorej zabka moze aktualnie stac w danym X.
  // WAZNE: platforma liczy sie jako ladowanie TYLKO jesli zabka byla w
  // POPRZEDNIEJ klatce juz na jej wysokosci lub wyzej (czyli faktycznie na
  // nia doskoczyla) - inaczej zwykle przejscie pod spodem po ziemi nie
  // powinno jej tam "teleportowac".
  function pobierzPodloze(x, zabaDolPrzed, glownaPodlogaY) {
    var najlepsza = glownaPodlogaY;
    for (var i = 0; i < przeszkody.length; i++) {
      var p = przeszkody[i];
      var jestPlatforma = p.typ === 'platforma' || p.typ === 'podest-kolce';
      if (!jestPlatforma) continue;
      if (x >= p.x && x <= p.x + PLATFORMA_SZEROKOSC) {
        if (p.wysokoscY < najlepsza && zabaDolPrzed <= p.wysokoscY + TOLERANCJA_LADOWANIA) {
          najlepsza = p.wysokoscY;
        }
      }
    }
    return najlepsza;
  }

  function petla(czas) {
    if (!trwa) { czasOstatni = null; return; }
    if (czasOstatni === null) czasOstatni = czas;
    var dt = Math.min((czas - czasOstatni) / 1000, 0.05);
    czasOstatni = czas;

    var szer = gra.clientWidth;
    var wys = gra.clientHeight;
    var groundY = wys - PODLOZE_WYSOKOSC;
    var zabaXpx = szer * ZABA_X;

    zabaDolPoprzedni = zabaDol;
    zabaVY += GRAWITACJA * dt;
    zabaDol += zabaVY * dt;
    var docelowePodloze = pobierzPodloze(zabaXpx, zabaDolPoprzedni, groundY);
    if (zabaVY >= 0 && zabaDol >= docelowePodloze) {
      zabaDol = docelowePodloze;
      zabaVY = 0;
      naZiemi = true;
    } else {
      naZiemi = false;
    }

    var mnoznik = 1 + Math.min(wynik, 25) * 0.025;
    var predkoscAktualna = PREDKOSC_START * mnoznik;

    czasOdSpawnu += dt;
    var odstepAktualny = (ODSTEP_SPAWN_START / mnoznik) * losowo(0.85, 1.25);
    if (czasOdSpawnu >= odstepAktualny) {
      czasOdSpawnu = 0;
      przeszkody.push(stworzPrzeszkode(szer, groundY));
    }

    var zabaLewa = zabaXpx - ZABA_R;
    var zabaPrawa = zabaXpx + ZABA_R;

    for (var i = przeszkody.length - 1; i >= 0; i--) {
      var p = przeszkody[i];
      p.x -= predkoscAktualna * dt;

      if (p.typ === 'podest-kolce') {
        p.elPodest.style.left = p.x + 'px';
        var xKolec = p.x + p.offsetKolca;
        p.elKolec.style.left = xKolec + 'px';
        var wZasiegKolca = zabaPrawa > xKolec && zabaLewa < xKolec + KOLEC_SZEROKOSC;
        if (wZasiegKolca && zabaDol > groundY - KOLEC_WYSOKOSC_WYSOKI + TOLERANCJA_KOLIZJI) {
          zakonczGre(false);
          return;
        }
      } else {
        p.el.style.left = p.x + 'px';
        var wZasiegu = zabaPrawa > p.x && zabaLewa < p.x + p.szerokosc;
        if (wZasiegu && p.typ === 'kolce') {
          if (zabaDol > groundY - KOLEC_WYSOKOSC + TOLERANCJA_KOLIZJI) {
            zakonczGre(false);
            return;
          }
        } else if (wZasiegu && p.typ === 'sufit') {
          var zabaGora = zabaDol - ZABA_WYSOKOSC;
          if (zabaGora < p.dolnaKrawedzY - TOLERANCJA_KOLIZJI) {
            zakonczGre(false);
            return;
          }
        }
      }

      if (!p.minieta && p.x + p.szerokosc < zabaXpx - ZABA_R) {
        p.minieta = true;
        wynik += 1;
        zagrajDzwiek('punkt');
        aktualizujWynik();
        if (wynik >= CEL_WYNIK) {
          zakonczGre(true);
          return;
        }
      }

      if (p.x + p.szerokosc < -300) {
        usunPrzeszkode(p);
        przeszkody.splice(i, 1);
      }
    }

    rysuj();
    requestAnimationFrame(petla);
  }

  function rozpocznijGre() {
    przeszkody.forEach(function (p) { usunPrzeszkode(p); });
    przeszkody = [];
    wynik = 0;
    aktualizujWynik();
    zabaDol = gra.clientHeight - PODLOZE_WYSOKOSC;
    zabaDolPoprzedni = zabaDol;
    zabaVY = 0;
    naZiemi = true;
    czasOdSpawnu = 0;
    czasOstatni = null;
    nakladka.style.display = 'none';
    trwa = true;
    rysuj();
    requestAnimationFrame(petla);
    startMuzyke();
  }

  function zakonczGre(wygrana) {
    trwa = false;
    przeszkody.forEach(function (p) { usunPrzeszkode(p); });
    przeszkody = [];
    nakladka.style.display = 'flex';
    zatrzymajMuzyke();

    if (wygrana) {
      zagrajDzwiek('punkt');
      nakladkaTytul.textContent = '🎉 Udało się!';
      nakladkaOpis.textContent = '';
      nakladkaBtn.style.display = 'none';
    } else {
      zagrajDzwiek('crash');
      nakladkaTytul.textContent = '🐸💥 Żaba nie doskoczyła...';
      nakladkaOpis.textContent = 'Wynik: ' + wynik + ' / ' + CEL_WYNIK + '. Spróbuj jeszcze raz.';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
    }
  }

  var pominDrugiSkok = false;
  gra.addEventListener('click', function () {
    if (pominDrugiSkok) return;
    if (nakladka.style.display !== 'none') return;
    skok();
  });
  gra.addEventListener('touchstart', function (e) {
    if (nakladka.style.display !== 'none') return;
    e.preventDefault();
    pominDrugiSkok = true;
    skok();
    setTimeout(function () { pominDrugiSkok = false; }, 500);
  }, { passive: false });

  wyciszBtn.addEventListener('click', function () {
    wyciszone = !wyciszone;
    wyciszBtn.textContent = wyciszone ? '🔇' : '🔊';
  });

  nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
</script>
</body>
</html>
"""

SZABLON_MEMORY = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; touch-action: manipulation; }
  body {
    margin: 0;
    font-family: -apple-system, 'Poppins', sans-serif;
    background: radial-gradient(circle at 50% 0%, #241b3a 0%, #0d0d0d 70%);
    overflow: hidden;
  }
  #panel {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  .wycisz-btn {
    background: none;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 20px;
    color: #f5f5f0;
    font-size: 16px;
    padding: 2px 10px;
    cursor: pointer;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 460px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
  }
  #siatka {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: repeat(4, 1fr);
    gap: 8px;
    padding: 14px;
    width: 100%;
    height: 100%;
  }
  .karta {
    position: relative;
    min-width: 0;
    cursor: pointer;
    perspective: 600px;
  }
  .karta-wnetrze {
    position: relative;
    width: 100%;
    height: 100%;
    transition: transform 0.4s;
    transform-style: preserve-3d;
  }
  .karta.odkryta .karta-wnetrze,
  .karta.dopasowana .karta-wnetrze {
    transform: rotateY(180deg);
  }
  .karta-tyl, .karta-przod {
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.7rem;
  }
  .karta-tyl {
    background: linear-gradient(135deg, #3a3050, #1a1a2e);
    border: 2px solid #d4af37;
  }
  .karta-przod {
    background: #2a2a3d;
    border: 2px solid #e6c15c;
    transform: rotateY(180deg);
  }
  .karta.dopasowana .karta-przod {
    border-color: #4ade80;
    background: #163a24;
  }
  #nakladka {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
  }
  #nakladka h2 { font-size: 22px; margin: 0 0 8px; }
  #nakladka p { margin: 0 0 6px; font-size: 14px; opacity: 0.85; }
  button.gra-btn {
    background: linear-gradient(135deg,#e6c15c,#d4af37);
    border: none;
    padding: 10px 26px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 10px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span id="parNaEkranie">0 / 8</span>
    <span id="czasNaEkranie">60s</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="siatka"></div>
    <div id="nakladka">
      <h2 id="nakladkaTytul">Memory</h2>
      <p id="nakladkaOpis"></p>
      <button class="gra-btn" id="nakladkaBtn">Graj ▶</button>
    </div>
  </div>

<script>
  var siatka = document.getElementById('siatka');
  var parNaEkranie = document.getElementById('parNaEkranie');
  var czasNaEkranie = document.getElementById('czasNaEkranie');
  var nakladka = document.getElementById('nakladka');
  var nakladkaTytul = document.getElementById('nakladkaTytul');
  var nakladkaOpis = document.getElementById('nakladkaOpis');
  var nakladkaBtn = document.getElementById('nakladkaBtn');
  var wyciszBtn = document.getElementById('wyciszBtn');

  var SYMBOLE = ['🍎', '🎈', '🎵', '🌙', '⭐', '🔑', '💎', '🦋'];
  var CEL_PAR = SYMBOLE.length;
  var CZAS_LIMIT = 45;

  var karty = [];
  var odkryteTeraz = [];
  var zablokowane = false;
  var dopasowanychPar = 0;
  var pozostalyCzas = CZAS_LIMIT;
  var interwalCzasu = null;
  var trwa = false;
  var wyciszone = false;

  var audioCtx = null;

  function inicjujDzwiek() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
    } catch (e) {
      audioCtx = null;
    }
  }

  function zagrajTon(czestotliwosc, czasTrwania, typ) {
    if (!audioCtx || wyciszone) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = typ;
      osc.frequency.value = czestotliwosc;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.18, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + czasTrwania);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + czasTrwania);
    } catch (e) {
      // dzwiek to dodatek - jego brak nie moze zepsuc gry
    }
  }

  function zagrajDzwiek(typ) {
    if (typ === 'odkryj') zagrajTon(500, 0.08, 'sine');
    else if (typ === 'dopasowanie') zagrajTon(800, 0.15, 'sine');
    else if (typ === 'zle') zagrajTon(180, 0.2, 'sawtooth');
  }

  var interwalMuzyki = null;
  var NUTY_MUZYKI = [329.63, 392.00, 440.00, 392.00];
  function startMuzyke() {
    zatrzymajMuzyke();
    var i = 0;
    interwalMuzyki = setInterval(function () {
      zagrajTon(NUTY_MUZYKI[i % NUTY_MUZYKI.length], 0.5, 'sine');
      i++;
    }, 900);
  }
  function zatrzymajMuzyke() {
    if (interwalMuzyki) {
      clearInterval(interwalMuzyki);
      interwalMuzyki = null;
    }
  }

  function potasuj(tablica) {
    for (var i = tablica.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = tablica[i]; tablica[i] = tablica[j]; tablica[j] = tmp;
    }
    return tablica;
  }

  function aktualizujPary() {
    parNaEkranie.textContent = dopasowanychPar + ' / ' + CEL_PAR;
  }

  function aktualizujCzas() {
    czasNaEkranie.textContent = pozostalyCzas + 's';
    czasNaEkranie.style.color = pozostalyCzas <= 10 ? '#ff6b6b' : '#f5f5f0';
  }

  function tikCzasu() {
    if (!trwa) return;
    pozostalyCzas -= 1;
    aktualizujCzas();
    if (pozostalyCzas <= 0) {
      zakonczGre(false);
    }
  }

  function odkryjKarte(indeks) {
    karty[indeks].stan = 'odkryta';
    karty[indeks].el.classList.add('odkryta');
  }

  function zakryjKarte(indeks) {
    karty[indeks].stan = 'zakryta';
    karty[indeks].el.classList.remove('odkryta');
  }

  function oznaczDopasowane(indeks) {
    karty[indeks].stan = 'dopasowana';
    karty[indeks].el.classList.remove('odkryta');
    karty[indeks].el.classList.add('dopasowana');
  }

  function kliknietoKarte(indeks) {
    if (zablokowane || !trwa) return;
    var karta = karty[indeks];
    if (karta.stan !== 'zakryta') return;

    odkryjKarte(indeks);
    zagrajDzwiek('odkryj');
    odkryteTeraz.push(indeks);

    if (odkryteTeraz.length === 2) {
      zablokowane = true;
      var a = karty[odkryteTeraz[0]];
      var b = karty[odkryteTeraz[1]];
      if (a.symbol === b.symbol) {
        setTimeout(function () {
          oznaczDopasowane(odkryteTeraz[0]);
          oznaczDopasowane(odkryteTeraz[1]);
          odkryteTeraz = [];
          zablokowane = false;
          dopasowanychPar += 1;
          aktualizujPary();
          zagrajDzwiek('dopasowanie');
          if (dopasowanychPar >= CEL_PAR) {
            zakonczGre(true);
          }
        }, 500);
      } else {
        zagrajDzwiek('zle');
        setTimeout(function () {
          zakryjKarte(odkryteTeraz[0]);
          zakryjKarte(odkryteTeraz[1]);
          odkryteTeraz = [];
          zablokowane = false;
        }, 900);
      }
    }
  }

  function stworzKarte(indeks, symbol) {
    var el = document.createElement('div');
    el.className = 'karta';
    el.innerHTML = '<div class="karta-wnetrze"><div class="karta-tyl">🔒</div><div class="karta-przod">' + symbol + '</div></div>';
    el.addEventListener('click', function () {
      if (el.dataset.dotkniete) return;
      kliknietoKarte(indeks);
    });
    el.addEventListener('touchstart', function (e) {
      e.preventDefault();
      el.dataset.dotkniete = '1';
      kliknietoKarte(indeks);
      setTimeout(function () { delete el.dataset.dotkniete; }, 500);
    }, { passive: false });
    return el;
  }

  function zbudujPlansze() {
    siatka.innerHTML = '';
    karty = [];
    var talia = potasuj(SYMBOLE.concat(SYMBOLE));
    for (var i = 0; i < talia.length; i++) {
      var el = stworzKarte(i, talia[i]);
      siatka.appendChild(el);
      karty.push({ symbol: talia[i], stan: 'zakryta', el: el });
    }
  }

  function rozpocznijGre() {
    dopasowanychPar = 0;
    odkryteTeraz = [];
    zablokowane = false;
    aktualizujPary();
    zbudujPlansze();
    nakladka.style.display = 'none';
    trwa = true;

    pozostalyCzas = CZAS_LIMIT;
    aktualizujCzas();
    if (interwalCzasu) clearInterval(interwalCzasu);
    interwalCzasu = setInterval(tikCzasu, 1000);
    startMuzyke();
  }

  function zakonczGre(wygrana) {
    trwa = false;
    if (interwalCzasu) {
      clearInterval(interwalCzasu);
      interwalCzasu = null;
    }
    nakladka.style.display = 'flex';
    zatrzymajMuzyke();

    if (wygrana) {
      nakladkaTytul.textContent = '🎉 Udało się!';
      nakladkaOpis.textContent = '';
      nakladkaBtn.style.display = 'none';
    } else {
      zagrajDzwiek('zle');
      nakladkaTytul.textContent = '⏱️ Czas minął!';
      nakladkaOpis.textContent = 'Znalazłaś ' + dopasowanychPar + ' / ' + CEL_PAR + ' par. Spróbuj jeszcze raz.';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
    }
  }

  wyciszBtn.addEventListener('click', function () {
    wyciszone = !wyciszone;
    wyciszBtn.textContent = wyciszone ? '🔇' : '🔊';
  });

  nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
</script>
</body>
</html>
"""

SZABLON_SIMON = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; touch-action: manipulation; }
  body {
    margin: 0;
    font-family: -apple-system, 'Poppins', sans-serif;
    background: radial-gradient(circle at 50% 0%, #241b3a 0%, #0d0d0d 70%);
    overflow: hidden;
  }
  #panel {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  .wycisz-btn {
    background: none;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 20px;
    color: #f5f5f0;
    font-size: 16px;
    padding: 2px 10px;
    cursor: pointer;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 380px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
  }
  #siatkaKolorow {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 10px;
    width: 100%;
    height: 100%;
    padding: 16px;
  }
  .przycisk-koloru {
    border-radius: 16px;
    cursor: pointer;
    filter: brightness(0.55);
    transition: filter 0.12s, transform 0.1s;
  }
  .przycisk-koloru.aktywny {
    filter: brightness(1.35);
    transform: scale(0.97);
  }
  .pk-0 { background: #e63950; }
  .pk-1 { background: #3a6fd4; }
  .pk-2 { background: #22a35e; }
  .pk-3 { background: #c9a13b; }
  #nakladka {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
  }
  #nakladka h2 { font-size: 22px; margin: 0 0 8px; }
  #nakladka p { margin: 0 0 6px; font-size: 14px; opacity: 0.85; }
  button.gra-btn {
    background: linear-gradient(135deg,#e6c15c,#d4af37);
    border: none;
    padding: 10px 26px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 10px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span id="dlugoscNaEkranie">0 / 8</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="siatkaKolorow">
      <div class="przycisk-koloru pk-0"></div>
      <div class="przycisk-koloru pk-1"></div>
      <div class="przycisk-koloru pk-2"></div>
      <div class="przycisk-koloru pk-3"></div>
    </div>
    <div id="nakladka">
      <h2 id="nakladkaTytul">Simon</h2>
      <p id="nakladkaOpis"></p>
      <button class="gra-btn" id="nakladkaBtn">Graj ▶</button>
    </div>
  </div>

<script>
  var przyciski = document.querySelectorAll('.przycisk-koloru');
  var dlugoscNaEkranie = document.getElementById('dlugoscNaEkranie');
  var nakladka = document.getElementById('nakladka');
  var nakladkaTytul = document.getElementById('nakladkaTytul');
  var nakladkaOpis = document.getElementById('nakladkaOpis');
  var nakladkaBtn = document.getElementById('nakladkaBtn');
  var wyciszBtn = document.getElementById('wyciszBtn');

  var CZESTOTLIWOSCI = [330, 415, 494, 262];
  var CEL_DLUGOSC = 8;

  var sekwencja = [];
  var pozycjaGracza = 0;
  var trwaOdtwarzanie = false;
  var trwa = false;
  var wyciszone = false;

  var audioCtx = null;

  function inicjujDzwiek() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
    } catch (e) {
      audioCtx = null;
    }
  }

  function zagrajTon(czestotliwosc, czasTrwania) {
    if (!audioCtx || wyciszone) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.value = czestotliwosc;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.2, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + czasTrwania);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + czasTrwania);
    } catch (e) {
      // dzwiek to dodatek - jego brak nie moze zepsuc gry
    }
  }

  function rozjasnij(idx) {
    przyciski[idx].classList.add('aktywny');
  }
  function przygas(idx) {
    przyciski[idx].classList.remove('aktywny');
  }

  function aktualizujDlugosc() {
    dlugoscNaEkranie.textContent = sekwencja.length + ' / ' + CEL_DLUGOSC;
  }

  function odtworzSekwencje() {
    trwaOdtwarzanie = true;
    pozycjaGracza = 0;
    var i = 0;
    function krok() {
      if (i >= sekwencja.length) {
        trwaOdtwarzanie = false;
        return;
      }
      var idx = sekwencja[i];
      rozjasnij(idx);
      zagrajTon(CZESTOTLIWOSCI[idx], 0.35);
      setTimeout(function () {
        przygas(idx);
        i++;
        setTimeout(krok, 200);
      }, 420);
    }
    setTimeout(krok, 500);
  }

  function dodajKrokIOdtworz() {
    sekwencja.push(Math.floor(Math.random() * 4));
    aktualizujDlugosc();
    odtworzSekwencje();
  }

  function kliknietoKolor(idx) {
    if (trwaOdtwarzanie || !trwa) return;
    rozjasnij(idx);
    zagrajTon(CZESTOTLIWOSCI[idx], 0.2);
    setTimeout(function () { przygas(idx); }, 200);

    if (idx === sekwencja[pozycjaGracza]) {
      pozycjaGracza++;
      if (pozycjaGracza === sekwencja.length) {
        if (sekwencja.length >= CEL_DLUGOSC) {
          zakonczGre(true);
        } else {
          setTimeout(dodajKrokIOdtworz, 700);
        }
      }
    } else {
      zakonczGre(false);
    }
  }

  przyciski.forEach(function (el, idx) {
    el.addEventListener('click', function () {
      if (el.dataset.dotkniete) return;
      kliknietoKolor(idx);
    });
    el.addEventListener('touchstart', function (e) {
      e.preventDefault();
      el.dataset.dotkniete = '1';
      kliknietoKolor(idx);
      setTimeout(function () { delete el.dataset.dotkniete; }, 500);
    }, { passive: false });
  });

  function rozpocznijGre() {
    sekwencja = [];
    pozycjaGracza = 0;
    trwa = true;
    aktualizujDlugosc();
    nakladka.style.display = 'none';
    setTimeout(dodajKrokIOdtworz, 500);
  }

  function zakonczGre(wygrana) {
    trwa = false;
    nakladka.style.display = 'flex';
    if (wygrana) {
      nakladkaTytul.textContent = '🎉 Udało się!';
      nakladkaOpis.textContent = '';
      nakladkaBtn.style.display = 'none';
    } else {
      nakladkaTytul.textContent = '❌ Zła kolejność...';
      nakladkaOpis.textContent = 'Doszłaś do ' + sekwencja.length + ' / ' + CEL_DLUGOSC + '. Spróbuj jeszcze raz.';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
    }
  }

  wyciszBtn.addEventListener('click', function () {
    wyciszone = !wyciszone;
    wyciszBtn.textContent = wyciszone ? '🔇' : '🔊';
  });

  nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
</script>
</body>
</html>
"""

SZABLON_PIANO = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; touch-action: manipulation; }
  body {
    margin: 0;
    font-family: -apple-system, 'Poppins', sans-serif;
    background: radial-gradient(circle at 50% 0%, #241b3a 0%, #0d0d0d 70%);
    overflow: hidden;
  }
  #panel {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  .wycisz-btn {
    background: none;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 20px;
    color: #f5f5f0;
    font-size: 16px;
    padding: 2px 10px;
    cursor: pointer;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 420px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
  }
  #pasy {
    display: flex;
    width: 100%;
    height: 100%;
  }
  .pas {
    flex: 1;
    position: relative;
    border-right: 1px solid rgba(212,175,55,0.15);
    cursor: pointer;
  }
  .pas:last-child { border-right: none; }
  #linia-trafien {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 54px;
    height: 2px;
    background: rgba(212,175,55,0.35);
    z-index: 1;
    pointer-events: none;
  }
  .kafelek {
    position: absolute;
    height: 70px;
    background: linear-gradient(135deg, #2a2a3d, #0d0d0d);
    border: 2px solid #d4af37;
    border-radius: 8px;
    z-index: 3;
    pointer-events: none;
  }
  #nakladka {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
  }
  #nakladka h2 { font-size: 22px; margin: 0 0 8px; }
  #nakladka p { margin: 0 0 6px; font-size: 14px; opacity: 0.85; }
  button.gra-btn {
    background: linear-gradient(135deg,#e6c15c,#d4af37);
    border: none;
    padding: 10px 26px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 10px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span id="postepNaEkranie">0 / 18</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="pasy">
      <div class="pas" data-idx="0"></div>
      <div class="pas" data-idx="1"></div>
      <div class="pas" data-idx="2"></div>
      <div class="pas" data-idx="3"></div>
    </div>
    <div id="linia-trafien"></div>
    <div id="nakladka">
      <h2 id="nakladkaTytul">Piano Tiles</h2>
      <p id="nakladkaOpis"></p>
      <button class="gra-btn" id="nakladkaBtn">Graj ▶</button>
    </div>
  </div>

<script>
  var gra = document.getElementById('gra');
  var pasy = document.querySelectorAll('.pas');
  var postepNaEkranie = document.getElementById('postepNaEkranie');
  var nakladka = document.getElementById('nakladka');
  var nakladkaTytul = document.getElementById('nakladkaTytul');
  var nakladkaOpis = document.getElementById('nakladkaOpis');
  var nakladkaBtn = document.getElementById('nakladkaBtn');
  var wyciszBtn = document.getElementById('wyciszBtn');

  // "Wlazl kotek na plotek" - solmizacja: sol mi mi fa re re do mi sol
  // (powtorzone), czyli G E E F D D C E G G E E F D D C E C.
  var NUTY = [
    784.00, 659.25, 659.25, 698.46, 587.33, 587.33, 523.25, 659.25, 784.00,
    784.00, 659.25, 659.25, 698.46, 587.33, 587.33, 523.25, 659.25, 523.25
  ];

  var LICZBA_PASOW = 4;
  var PREDKOSC_START = 420;
  var PREDKOSC_PRZYROST = 10;
  var WYSOKOSC_KAFELKA = 70;

  var indeksNuty = 0;
  var aktywnyKafelek = null;
  var trwa = false;
  var czasOstatni = null;
  var wyciszone = false;

  var audioCtx = null;

  function inicjujDzwiek() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
    } catch (e) {
      audioCtx = null;
    }
  }

  function zagrajTon(czestotliwosc, czasTrwania, typ) {
    if (!audioCtx || wyciszone) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = typ;
      osc.frequency.value = czestotliwosc;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.22, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + czasTrwania);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + czasTrwania);
    } catch (e) {
      // dzwiek to dodatek - jego brak nie moze zepsuc gry
    }
  }

  function aktualizujPostep() {
    postepNaEkranie.textContent = indeksNuty + ' / ' + NUTY.length;
  }

  function usunAktywnyKafelek() {
    if (aktywnyKafelek && aktywnyKafelek.el.parentNode) {
      aktywnyKafelek.el.remove();
    }
    aktywnyKafelek = null;
  }

  function stworzKafelek() {
    var pas = Math.floor(Math.random() * LICZBA_PASOW);
    var szerPasa = gra.clientWidth / LICZBA_PASOW;
    var el = document.createElement('div');
    el.className = 'kafelek';
    el.style.width = (szerPasa - 8) + 'px';
    el.style.left = (pas * szerPasa + 4) + 'px';
    el.style.top = (-WYSOKOSC_KAFELKA - 10) + 'px';
    gra.appendChild(el);
    aktywnyKafelek = { pas: pas, y: -WYSOKOSC_KAFELKA - 10, el: el };
  }

  function petla(czas) {
    if (!trwa) { czasOstatni = null; return; }
    if (czasOstatni === null) czasOstatni = czas;
    var dt = Math.min((czas - czasOstatni) / 1000, 0.05);
    czasOstatni = czas;

    var wys = gra.clientHeight;
    var predkosc = PREDKOSC_START + indeksNuty * PREDKOSC_PRZYROST;

    if (aktywnyKafelek) {
      aktywnyKafelek.y += predkosc * dt;
      aktywnyKafelek.el.style.top = aktywnyKafelek.y + 'px';
      if (aktywnyKafelek.y > wys) {
        zakonczGre(false, 'ucieklo');
        return;
      }
    }

    requestAnimationFrame(petla);
  }

  function kliknietoPas(pas) {
    if (!trwa) return;
    if (aktywnyKafelek && aktywnyKafelek.pas === pas) {
      zagrajTon(NUTY[indeksNuty], 0.4, 'triangle');
      usunAktywnyKafelek();
      indeksNuty++;
      aktualizujPostep();
      if (indeksNuty >= NUTY.length) {
        zakonczGre(true);
      } else {
        stworzKafelek();
      }
    } else {
      zakonczGre(false, 'zly-pas');
    }
  }

  pasy.forEach(function (el, idx) {
    el.addEventListener('click', function () {
      if (el.dataset.dotkniete) return;
      kliknietoPas(idx);
    });
    el.addEventListener('touchstart', function (e) {
      e.preventDefault();
      el.dataset.dotkniete = '1';
      kliknietoPas(idx);
      setTimeout(function () { delete el.dataset.dotkniete; }, 500);
    }, { passive: false });
  });

  function rozpocznijGre() {
    indeksNuty = 0;
    aktualizujPostep();
    usunAktywnyKafelek();
    czasOstatni = null;
    nakladka.style.display = 'none';
    trwa = true;
    stworzKafelek();
    requestAnimationFrame(petla);
  }

  function zakonczGre(wygrana, powod) {
    trwa = false;
    usunAktywnyKafelek();
    nakladka.style.display = 'flex';

    if (wygrana) {
      zagrajTon(1046.50, 0.5, 'triangle');
      nakladkaTytul.textContent = '🎉 Udało się!';
      nakladkaOpis.textContent = '';
      nakladkaBtn.style.display = 'none';
    } else {
      zagrajTon(140, 0.35, 'sawtooth');
      nakladkaTytul.textContent = powod === 'zly-pas' ? '🎹 Nie tam...' : '🎹 Kafelek uciekł...';
      nakladkaOpis.textContent = 'Doszłaś do ' + indeksNuty + ' / ' + NUTY.length + '. Spróbuj jeszcze raz.';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
    }
  }

  wyciszBtn.addEventListener('click', function () {
    wyciszone = !wyciszone;
    wyciszBtn.textContent = wyciszone ? '🔇' : '🔊';
  });

  nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
</script>
</body>
</html>
"""

# ======================================================================
# STYL APLIKACJI
# ======================================================================

def wstaw_styl():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Poppins:wght@400;500;600;700&display=swap');

#MainMenu, footer, header {visibility: hidden;}

.stApp {
    background: radial-gradient(circle at 50% -10%, #241b3a 0%, #0d0d0d 55%, #050505 100%);
    color: #f5f5f0;
    font-family: 'Poppins', sans-serif;
}

h1, h2, h3 { font-family: 'Cinzel', serif !important; color: #f0dfa8; }

.tytul {
    font-family: 'Cinzel', serif;
    text-align: center;
    letter-spacing: 0.03em;
    background: linear-gradient(135deg, #e6c15c, #d4af37);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: pojaw 0.9s ease;
    padding-bottom: 0.7rem;
    margin-bottom: 1.1rem;
    border-bottom: 1px solid rgba(212,175,55,0.28);
}

@keyframes pojaw {
    from { opacity: 0; transform: translateY(-12px); }
    to { opacity: 1; transform: translateY(0); }
}

.zamek-ikona {
    font-size: 3.4rem;
    text-align: center;
    animation: pulsuj 2s ease-in-out infinite;
}
@keyframes pulsuj {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}

.zamek-otwarty {
    font-size: 3.4rem;
    text-align: center;
    animation: otworz 0.7s ease;
}
@keyframes otworz {
    0% { transform: rotate(0deg) scale(0.4); opacity: 0; }
    60% { transform: rotate(-14deg) scale(1.15); opacity: 1; }
    100% { transform: rotate(0deg) scale(1); }
}

.cyfra-tarcza {
    width: 2.8rem;
    height: 3.4rem;
    background: linear-gradient(180deg, #2a2a3d, #16131f);
    border: 2px solid #d4af37;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'Cinzel', serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #e6c15c;
    box-shadow: inset 0 2px 5px rgba(0,0,0,0.6), 0 0 12px rgba(212,175,55,0.35);
}

.serce-peka {
    display: inline-block;
    animation: peknij 0.5s ease;
}
@keyframes peknij {
    0% { transform: scale(1.6); opacity: 0.4; }
    40% { transform: scale(0.85) rotate(-8deg); }
    70% { transform: scale(1.1) rotate(5deg); }
    100% { transform: scale(1) rotate(0deg); }
}

div.stButton > button {
    background: linear-gradient(135deg, #e6c15c, #d4af37);
    color: #16130a;
    border: none;
    border-radius: 30px;
    padding: 0.6rem 1.4rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    width: 100%;
    box-shadow: 0 3px 10px rgba(0,0,0,0.35);
}
div.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 0 18px rgba(212,175,55,0.55);
}
div.stButton > button:active {
    transform: scale(0.98);
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4ade80, #22c55e) !important;
    color: #062e14 !important;
}
div.stButton > button:disabled {
    opacity: 0.4;
    background: #2a2a35 !important;
    color: #8a8a8a !important;
    box-shadow: none;
}

/* Kafelki nawigacji w siatce (menu etapów + kłódka na powitaniu) -
   te same przyciski co wyzej, ale w kolumnach dostaja jezyk "medalionu
   sejfowego", spojny z tarczami kodu na ekranie koncowym. */
div[data-testid="stColumn"] div.stButton > button {
    aspect-ratio: 1 / 1;
    height: auto;
    min-height: 3.2rem;
    border-radius: 22%;
    font-size: clamp(1.4rem, 7vw, 2.6rem);
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(160deg, #f0dfa8, #d4af37 55%, #b8892a);
    box-shadow:
        inset 0 2px 3px rgba(255,255,255,0.4),
        inset 0 -4px 7px rgba(0,0,0,0.3),
        0 3px 10px rgba(0,0,0,0.4);
    border: 1px solid rgba(255,255,255,0.18);
}
div[data-testid="stColumn"] div.stButton > button[kind="primary"] {
    background: linear-gradient(160deg, #a9f0b8, #22c55e 55%, #158a3d) !important;
}
div[data-testid="stColumn"] div.stButton > button:disabled {
    background: linear-gradient(160deg, #3a3a42, #26262c) !important;
    box-shadow: inset 0 2px 3px rgba(255,255,255,0.06), 0 2px 6px rgba(0,0,0,0.3);
}

.stTextInput input {
    border-radius: 12px !important;
    border: 1px solid #d4af37 !important;
    background: #1a1a2e !important;
    color: #f5f5f0 !important;
}

[data-testid="stSelectbox"] > div > div {
    border-radius: 12px !important;
    border: 1px solid #d4af37 !important;
    background: #1a1a2e !important;
    color: #f5f5f0 !important;
}

div[data-testid="stAlert"] {
    background: rgba(26,26,46,0.85) !important;
    border: 1px solid rgba(212,175,55,0.4) !important;
    border-radius: 12px !important;
}

.stProgress > div > div {
    background-image: linear-gradient(135deg, #e6c15c, #d4af37);
}

[data-testid="stExpander"] {
    border: 1px solid rgba(212,175,55,0.35);
    border-radius: 12px;
}

/* Streamlit domyślnie chowa kolumny w jedną, pionową listę na wąskich
   ekranach (telefony) - wymuszamy, żeby zawsze zostawały w rzędzie
   i zawijały się jak prawdziwa siatka zamiast rozjeżdżać się do jednej
   kolumny po lewej. */
div[data-testid="stHorizontalBlock"] {
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 0.4rem !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    flex: 1 1 18% !important;
    width: auto !important;
    min-width: 56px !important;
}
</style>
""", unsafe_allow_html=True)


# ======================================================================
# WISIELEC — wspólny licznik pomyłek (10 elementów)
# ======================================================================

WISIELEC_CZESCI = [
    '<line x1="10" y1="140" x2="70" y2="140" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="30" y1="140" x2="30" y2="10" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="30" y1="10" x2="90" y2="10" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="10" x2="90" y2="25" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<circle cx="90" cy="36" r="11" stroke="#ff6b6b" stroke-width="4" fill="none"/>',
    '<line x1="90" y1="47" x2="90" y2="85" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="57" x2="70" y2="72" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="57" x2="110" y2="72" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="85" x2="75" y2="112" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="85" x2="105" y2="112" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
]


def rysuj_wisielca(liczba_bledow, mala=False):
    liczba_bledow = max(0, min(10, liczba_bledow))
    widoczne = "".join(WISIELEC_CZESCI[:liczba_bledow])
    rozmiar = 70 if mala else 120
    wysokosc = int(rozmiar * 150 / 120)
    st.markdown(
        f"<div style='text-align:center; margin:0.3rem 0;'><svg width='{rozmiar}' height='{wysokosc}' "
        f"viewBox='0 0 120 150'>{widoczne}</svg></div>",
        unsafe_allow_html=True,
    )


def rysuj_serca(liczba_bledow, mala=False):
    liczba_bledow = max(0, min(10, liczba_bledow))
    rozmiar = "1.15rem" if mala else "1.5rem"
    czesci = []
    for i in range(10):
        if i < liczba_bledow - 1:
            czesci.append(f"<span style='font-size:{rozmiar};'>💔</span>")
        elif i == liczba_bledow - 1:
            czesci.append(f"<span class='serce-peka' style='font-size:{rozmiar};'>💔</span>")
        else:
            czesci.append(f"<span style='font-size:{rozmiar};'>❤️</span>")
    st.markdown(
        f"<div style='text-align:center; letter-spacing:1px; margin:0.3rem 0 1.1rem;'>{''.join(czesci)}</div>",
        unsafe_allow_html=True,
    )


# ======================================================================
# TRWAŁY STAN — przetrwa zamknięcie telefonu i wznowienie po jakimś czasie.
# Zapisywany w DWÓCH miejscach naraz (link + plik na serwerze).
# ======================================================================

def wczytaj_zapisany_stan():
    if os.path.exists(PLIK_STANU):
        try:
            with open(PLIK_STANU, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def zapisz_postep():
    st.query_params["r"] = ",".join(sorted(st.session_state.rozwiazane))
    st.query_params["n"] = ",".join(sorted(st.session_state.nieudane))
    st.query_params["b"] = str(st.session_state.bledy_wisielec)
    st.query_params["j"] = st.session_state.jezyk
    if st.session_state.czas_startu:
        st.query_params["t"] = str(st.session_state.czas_startu)
    dane = {
        "rozwiazane": list(st.session_state.rozwiazane),
        "nieudane": list(st.session_state.nieudane),
        "bledy_wisielec": st.session_state.bledy_wisielec,
        "jezyk": st.session_state.jezyk,
        "czas_startu": st.session_state.czas_startu,
    }
    try:
        with open(PLIK_STANU, "w", encoding="utf-8") as f:
            json.dump(dane, f)
    except Exception:
        pass


def zainicjuj_stan():
    if "rozwiazane" in st.session_state:
        return

    r = st.query_params.get("r", "")
    rozwiazane_url = set(x for x in r.split(",") if x)
    n = st.query_params.get("n", "")
    nieudane_url = set(x for x in n.split(",") if x)
    b = st.query_params.get("b")
    bledy_url = int(b) if b and b.isdigit() else 0
    j = st.query_params.get("j")
    jezyk_url = j if j in ("pl", "en") else None
    t_param = st.query_params.get("t")
    czas_url = float(t_param) if t_param else None

    zapisane = wczytaj_zapisany_stan() or {}
    rozwiazane_plik = set(zapisane.get("rozwiazane", []))
    nieudane_plik = set(zapisane.get("nieudane", []))
    bledy_plik = zapisane.get("bledy_wisielec", 0)
    jezyk_plik = zapisane.get("jezyk")
    czas_plik = zapisane.get("czas_startu")

    st.session_state.rozwiazane = rozwiazane_url | rozwiazane_plik
    st.session_state.nieudane = nieudane_url | nieudane_plik
    st.session_state.bledy_wisielec = max(bledy_url, bledy_plik)
    st.session_state.jezyk = jezyk_url or jezyk_plik or "pl"
    st.session_state.czas_startu = czas_url or czas_plik

    juz_zaczela = bool(
        jezyk_url or jezyk_plik
        or st.session_state.rozwiazane or st.session_state.nieudane
        or st.session_state.bledy_wisielec
    )
    st.session_state.ekran = "menu" if juz_zaczela else "powitanie"

    if juz_zaczela:
        zapisz_postep()


def wznow_z_kodu(kod):
    kod = kod.strip().lower()
    if not kod:
        return False
    for etap_dane in ETAPY:
        oczekiwana = str(etap_dane.get("odpowiedz", "")).strip().lower()
        if oczekiwana and oczekiwana == kod:
            st.session_state.rozwiazane.add(etap_dane["klucz"])
            zapisz_postep()
            return True
    return False


# ======================================================================
# RENDEROWANIE POJEDYNCZYCH TYPÓW ZAGADEK
# Każdy zwraca: True (poprawnie), False (źle — dopiero co wysłane), albo
# None (nic jeszcze nie wysłano w tym przebiegu).
# ======================================================================

def renderuj_haslo(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))
    wpisane = st.text_input(t("twoja_odpowiedz"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        if znormalizuj(wpisane) == znormalizuj(etap_dane["odpowiedz"]):
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


def renderuj_krzyzowka(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane.get("info", "")))

    placeholder = t("wybierz")
    pula_wspolna = etap_dane.get("slowa_pula", [])
    odpowiedzi_uzytkownika = []
    for idx, pytanie in enumerate(etap_dane["pytania"]):
        st.markdown(f"**{idx + 1}.** {tt(pytanie['wskazowka'])}")
        if pytanie.get("podpowiedz"):
            st.caption(tt(pytanie["podpowiedz"]))
        typ_pytania = pytanie.get("typ", "tekst")

        if typ_pytania == "ulozanka":
            pula = pytanie.get("slowa_pula", pula_wspolna)
            liczba_slow = len(pytanie["odpowiedz"])
            wybrane_slowa = []
            for i in range(liczba_slow):
                wybor = st.selectbox(
                    f"{t('slowo')} {i + 1}:",
                    [placeholder] + pula,
                    key=f"{klucz}_pyt_{idx}_slowo_{i}",
                )
                wybrane_slowa.append(wybor)
            odpowiedzi_uzytkownika.append(wybrane_slowa)
        else:
            wpisane = st.text_input(
                t("twoja_odpowiedz"), key=f"{klucz}_pyt_{idx}", label_visibility="collapsed"
            )
            odpowiedzi_uzytkownika.append(wpisane)

    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        wszystkie_poprawne = True
        for idx, pytanie in enumerate(etap_dane["pytania"]):
            typ_pytania = pytanie.get("typ", "tekst")
            if typ_pytania == "ulozanka":
                wybrane = [znormalizuj(w) for w in odpowiedzi_uzytkownika[idx]]
                oczekiwane = [znormalizuj(w) for w in pytanie["odpowiedz"]]
                if wybrane != oczekiwane:
                    wszystkie_poprawne = False
            else:
                wpisana = znormalizuj(odpowiedzi_uzytkownika[idx])
                akceptowane = [znormalizuj(a) for a in pytanie["odpowiedzi"]]
                if wpisana not in akceptowane:
                    wszystkie_poprawne = False
        if wszystkie_poprawne:
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


def renderuj_rebus(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane.get("info", "")))

    czesci_html = []
    for e in etap_dane["elementy"]:
        if isinstance(e, dict) and e.get("typ") == "obraz":
            czesci_html.append(
                f"<img src='data:image/jpeg;base64,{e['dane']}' "
                f"style='height:5.5rem; margin:0 0.4rem; border-radius:8px; "
                f"vertical-align:middle;' />"
            )
        else:
            czesci_html.append(f"<span style='font-size:3rem; margin:0 0.3rem;'>{e}</span>")
    st.markdown(
        f"<div style='text-align:center; margin:1rem 0;'>{''.join(czesci_html)}</div>",
        unsafe_allow_html=True,
    )

    wpisane = st.text_input(t("twoja_odpowiedz"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        if znormalizuj(wpisane) == znormalizuj(etap_dane["odpowiedz"]):
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


def renderuj_quiz(etap_dane):
    klucz = etap_dane["klucz"]
    placeholder = t("wybierz")
    odpowiedzi = []
    for idx, pytanie in enumerate(etap_dane["pytania"]):
        wybor = st.radio(
            tt(pytanie["pytanie"]),
            [placeholder] + [tt(o) for o in pytanie["opcje"]],
            key=f"{klucz}_pyt_{idx}",
        )
        odpowiedzi.append(wybor)

    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        poprawne = 0
        for idx, pytanie in enumerate(etap_dane["pytania"]):
            oczekiwana = tt(pytanie["opcje"][pytanie["poprawna"]])
            if odpowiedzi[idx] == oczekiwana:
                poprawne += 1
        procent = poprawne / len(etap_dane["pytania"])
        if procent >= etap_dane.get("prog", 1.0):
            return True
        st.warning(f"{t('poprawnych')}: {poprawne}/{len(etap_dane['pytania'])}.")
        return False
    return None


def renderuj_gra(etap_dane):
    klucz = etap_dane["klucz"]

    html = SZABLON_GRY.replace("__POZIOMY_JSON__", json.dumps(POZIOMY_GRY))
    components.html(html, height=520, scrolling=False)

    if st.button(t("ukonczone_btn"), key=f"btn_{klucz}"):
        return True
    return None


def renderuj_dron(etap_dane):
    klucz = etap_dane["klucz"]

    components.html(SZABLON_DRONA, height=520, scrolling=False)

    if st.button(t("ukonczone_btn"), key=f"btn_{klucz}"):
        return True
    return None


def renderuj_zaba(etap_dane):
    klucz = etap_dane["klucz"]

    components.html(SZABLON_ZABY, height=520, scrolling=False)

    if st.button(t("ukonczone_btn"), key=f"btn_{klucz}"):
        return True
    return None


def renderuj_memory(etap_dane):
    klucz = etap_dane["klucz"]

    components.html(SZABLON_MEMORY, height=560, scrolling=False)

    if st.button(t("ukonczone_btn"), key=f"btn_{klucz}"):
        return True
    return None


def renderuj_simon(etap_dane):
    klucz = etap_dane["klucz"]

    components.html(SZABLON_SIMON, height=480, scrolling=False)

    if st.button(t("ukonczone_btn"), key=f"btn_{klucz}"):
        return True
    return None


def renderuj_piano(etap_dane):
    klucz = etap_dane["klucz"]

    components.html(SZABLON_PIANO, height=520, scrolling=False)

    if st.button(t("ukonczone_btn"), key=f"btn_{klucz}"):
        return True
    return None


@st.cache_data(ttl=300)  # 5 minut - dość świeżo, a nie odpytuje API bez przerwy
def pobierz_dzisiejszy_wordle():
    """Próbuje pobrać dzisiejsze słowo z (angielskiego) NYT Wordle.
    Najpierw oficjalne, szeroko używane API NYT; jeśli zawiedzie, zapasowe
    API wordlehints.co.uk. Zwraca None, jeśli oba się nie powiodą —
    wtedy renderuj_wordle() spada na ręczny kod z configu."""
    dzis_str = date.today().strftime("%Y-%m-%d")

    try:
        url = f"https://www.nytimes.com/svc/wordle/v2/{dzis_str}.json"
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if r.ok:
            slowo = str(r.json().get("solution", "")).strip().lower()
            if slowo:
                return slowo
    except Exception:
        pass

    try:
        r = requests.get(
            "https://wordlehints.co.uk/wp-json/wordlehint/v1/answers",
            params={"from": dzis_str, "to": dzis_str},
            timeout=5,
        )
        if r.ok:
            wyniki = r.json().get("results", [])
            if wyniki:
                slowo = str(wyniki[0].get("answer", "")).strip().lower()
                if slowo:
                    return slowo
    except Exception:
        pass

    return None


def renderuj_wordle(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))

    dzisiejsze_slowo = pobierz_dzisiejszy_wordle()
    if dzisiejsze_slowo is None:
        st.warning(t("wordle_brak_polaczenia"))
        if st.button(t("wordle_sprobuj_pobrac"), key=f"odswiez_{klucz}"):
            pobierz_dzisiejszy_wordle.clear()
            st.rerun()

    wpisane = st.text_input(t("twoja_odpowiedz"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        cel = dzisiejsze_slowo
        if not cel:
            zapasowa = str(etap_dane.get("odpowiedz", "")).strip().lower()
            if zapasowa and zapasowa not in ("uzupełnij", "uzupelnij"):
                cel = zapasowa
        if not cel:
            return None
        if wpisane.strip().lower() == cel:
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


def renderuj_data(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))
    st.caption(t("jedna_proba_info"))

    placeholder = t("wybierz")
    kol1, kol2, kol3 = st.columns(3)
    with kol1:
        dzien = st.selectbox(t("dzien"), [placeholder] + list(range(1, 32)), key=f"dzien_{klucz}")
    with kol2:
        miesiac = st.selectbox(t("miesiac"), [placeholder] + list(range(1, 13)), key=f"miesiac_{klucz}")
    with kol3:
        rok = st.selectbox(t("rok"), [placeholder] + list(range(2020, 2028)), key=f"rok_{klucz}")

    if st.button(t("zatwierdz"), key=f"btn_{klucz}"):
        if dzien == placeholder or miesiac == placeholder or rok == placeholder:
            st.warning(t("wybierz_najpierw"))
            return None
        try:
            wybrana = date(int(rok), int(miesiac), int(dzien))
        except ValueError:
            st.error(t("zle_jedna_proba"))
            return False
        if wybrana == etap_dane["data"]:
            return True
        st.error(t("zle_jedna_proba"))
        return False
    return None


def renderuj_szachy(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))
    st.caption(tt(etap_dane["format_info"]))
    wpisane = st.text_input(t("twoj_ruch"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        oczyszczony = wpisane.replace(",", " ").replace("+", "").replace("#", "")
        ruchy = [znormalizuj(tok) for tok in oczyszczony.split()]
        if ruchy == etap_dane["odpowiedz"]:
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


# ======================================================================
# EKRANY
# ======================================================================

def pokaz_powitanie():
    st.markdown("<div style='height:25vh;'></div>", unsafe_allow_html=True)

    kolumny = st.columns([1, 1, 1])
    with kolumny[1]:
        kliknieto = st.button("🔒", key="zamek_btn")

    if kliknieto:
        st.markdown(
            "<div class='zamek-otwarty' style='font-size:4rem; margin-top:1rem;'>🔓</div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.7)
        st.session_state.ekran = "menu"
        st.session_state.czas_startu = time.time()
        zapisz_postep()
        st.rerun()


def pokaz_menu():
    st.markdown(f"<h1 class='tytul'>{t('menu_tytul')}</h1>", unsafe_allow_html=True)
    rysuj_wisielca(st.session_state.bledy_wisielec)
    rysuj_serca(st.session_state.bledy_wisielec)

    kolumny = st.columns(5)
    for i, etap_dane in enumerate(ETAPY):
        klucz = etap_dane["klucz"]
        rozwiazany = klucz in st.session_state.rozwiazane
        nieudany = klucz in st.session_state.nieudane
        if rozwiazany:
            etykieta = etap_dane["emoji"] + " ✅"
        elif nieudany:
            etykieta = "🔒"
        else:
            etykieta = etap_dane["emoji"]
        with kolumny[i % 5]:
            if st.button(
                etykieta,
                key=f"menu_{klucz}",
                type="primary" if rozwiazany else "secondary",
                disabled=nieudany,
            ):
                st.session_state.ekran = f"etap:{klucz}"
                st.rerun()

    wszystkie = all(e["klucz"] in st.session_state.rozwiazane for e in ETAPY)
    if wszystkie:
        st.success(t("wszystko_rozwiazane"))
        if st.button(t("zobacz_kod"), key="zobacz_kod_btn"):
            st.session_state.ekran = "final"
            st.rerun()

    with st.expander(t("wznow_naglowek")):
        kod_wznow = st.text_input(t("kod_label"), key="wznow_input_menu")
        if st.button(t("wznow_btn"), key="wznow_btn_menu"):
            if wznow_z_kodu(kod_wznow):
                st.success(t("wznow_ok"))
                st.rerun()
            else:
                st.error(t("nie_rozpoznaje"))


def pokaz_ekran_etapu(etap_dane):
    klucz = etap_dane["klucz"]

    if st.button(t("wroc_do_menu"), key=f"powrot_{klucz}"):
        st.session_state.ekran = "menu"
        st.rerun()

    rysuj_wisielca(st.session_state.bledy_wisielec, mala=True)
    rysuj_serca(st.session_state.bledy_wisielec, mala=True)
    st.markdown(f"<h2 class='tytul' style='font-size:1.5rem;'>{tt(etap_dane['tytul'])}</h2>", unsafe_allow_html=True)

    if klucz in st.session_state.rozwiazane:
        st.success(t("rozwiazane_status"))
        return
    if klucz in st.session_state.nieudane:
        st.error(t("zamkniete_status"))
        return

    typ = etap_dane["typ"]
    if typ == "haslo":
        wynik = renderuj_haslo(etap_dane)
    elif typ == "krzyzowka":
        wynik = renderuj_krzyzowka(etap_dane)
    elif typ == "rebus":
        wynik = renderuj_rebus(etap_dane)
    elif typ == "quiz":
        wynik = renderuj_quiz(etap_dane)
    elif typ == "gra":
        wynik = renderuj_gra(etap_dane)
    elif typ == "dron":
        wynik = renderuj_dron(etap_dane)
    elif typ == "zaba":
        wynik = renderuj_zaba(etap_dane)
    elif typ == "memory":
        wynik = renderuj_memory(etap_dane)
    elif typ == "simon":
        wynik = renderuj_simon(etap_dane)
    elif typ == "piano":
        wynik = renderuj_piano(etap_dane)
    elif typ == "wordle":
        wynik = renderuj_wordle(etap_dane)
    elif typ == "data":
        wynik = renderuj_data(etap_dane)
    elif typ == "szachy":
        wynik = renderuj_szachy(etap_dane)
    else:
        wynik = None

    if wynik is True:
        st.session_state.rozwiazane.add(klucz)
        zapisz_postep()
        st.balloons()
        st.rerun()
    elif wynik is False:
        st.session_state.bledy_wisielec += 1
        if etap_dane.get("jedna_proba"):
            st.session_state.nieudane.add(klucz)
        zapisz_postep()
        if st.session_state.bledy_wisielec >= 10:
            st.session_state.ekran = "przegrana"
            st.rerun()


def pokaz_final():
    st.balloons()
    st.markdown("<div class='zamek-otwarty'>🔓</div>", unsafe_allow_html=True)
    st.markdown(f"<h1 class='tytul'>{t('wszystko_rozwiazane')}</h1>", unsafe_allow_html=True)
    st.markdown(tt(WIADOMOSC_KONCOWA))

    kod_koncowy = KOD_SEJFU
    tarcze = "".join(f"<div class='cyfra-tarcza'>{c}</div>" for c in kod_koncowy)
    st.markdown(
        f"""
        <div style='text-align:center; margin-top:1.5rem;'>
          <div style='font-size:0.95rem; opacity:0.75; margin-bottom:0.6rem;'>{t('kod_do_sejfu')}</div>
          <div style='display:flex; justify-content:center; gap:0.5rem;'>{tarcze}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.czas_startu:
        minuty = (time.time() - st.session_state.czas_startu) / 60
        st.caption(f"⏱️ {t('ukonczone_w')} {minuty:.1f} {t('min')}")

    if st.button(t("wroc_do_menu"), key="powrot_final"):
        st.session_state.ekran = "menu"
        st.rerun()


def pokaz_przegrana():
    rysuj_wisielca(10)
    rysuj_serca(10)
    st.markdown(f"<h1 class='tytul'>{t('przegrana_tytul')}</h1>", unsafe_allow_html=True)
    st.markdown(t("przegrana_wiadomosc"))
    if st.button(t("zacznij_od_nowa"), key="restart_btn"):
        jezyk = st.session_state.jezyk
        st.session_state.rozwiazane = set()
        st.session_state.nieudane = set()
        st.session_state.bledy_wisielec = 0
        st.session_state.czas_startu = None
        st.session_state.jezyk = jezyk
        st.session_state.ekran = "menu"
        zapisz_postep()
        st.rerun()


# ======================================================================
# GŁÓWNA LOGIKA
# ======================================================================

def main():
    st.set_page_config(page_title=f"Dla {IMIE}", page_icon="🔒", layout="centered")
    wstaw_styl()

    if st.query_params.get("resetuj") == "tak":
        if os.path.exists(PLIK_STANU):
            os.remove(PLIK_STANU)
        st.session_state.clear()
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()

    zainicjuj_stan()

    ekran = st.session_state.ekran

    if ekran == "powitanie":
        pokaz_powitanie()
    elif ekran == "przegrana":
        pokaz_przegrana()
    elif ekran == "final":
        pokaz_final()
    elif ekran.startswith("etap:"):
        klucz = ekran.split(":", 1)[1]
        etap_dane = next((e for e in ETAPY if e["klucz"] == klucz), None)
        if etap_dane is None:
            st.session_state.ekran = "menu"
            st.rerun()
        else:
            pokaz_ekran_etapu(etap_dane)
    else:
        pokaz_menu()


if __name__ == "__main__":
    main()
