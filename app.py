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

POWITANIE_TYTUL = {"pl": f"Cześć, {IMIE}", "en": f"Hi, {IMIE}"}

WIADOMOSC_POWITALNA = {
    "pl": """
Witaj w grze, którą przygotowałem specjalnie dla Ciebie.

Etapy możesz robić w DOWOLNEJ kolejności — wybierasz je z menu. Za każdy
rozwiązany zapala się zielone światełko. Cały kod do sejfu zobaczysz
dopiero, gdy rozwiążesz wszystko.

Uważaj na pomyłki — jest wspólny licznik błędów w postaci wisielca.
Jeśli dobije do końca, wszystko zaczynasz od nowa. Możesz korzystać
z dowolnej pomocy, jakiej chcesz — Google, znajomych, czego chcesz.
Powodzenia. 🖤
""",
    "en": """
Welcome to the game I made just for you.

You can do the stages in ANY order — pick them from the menu. Each
solved one turns green. You'll only see the full safe code once
everything is solved.

Watch out for mistakes — there's a shared mistake counter shown as a
hangman. If it's completed, everything starts over. You can use any
help you want — Google, friends, whatever you need.
Good luck. 🖤
""",
}

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

KOD_GRY = "4821"    # kod, który mini-gra pokaże po ukończeniu wszystkich poziomów
KOD_DRONA = "3907"  # kod, który mini-gra z dronem pokaże po ukończeniu (dowolny)
KOD_ZABY = "6152"   # kod, który mini-gra z żabą pokaże po ukończeniu (dowolny)

# Trudność mini-gry zręcznościowej — 3 poziomy, coraz trudniejsze.
POZIOMY_GRY = [
    {"serca": 6, "czarne": 2, "kierunek": "dol", "predkosc": 130, "tempo": 650},
    {"serca": 8, "czarne": 4, "kierunek": "skos", "predkosc": 190, "tempo": 480},
    {"serca": 10, "czarne": 6, "kierunek": "gora", "predkosc": 230, "tempo": 340},
]

# Pozycja szachowa (białe zaczynają) — ręcznie zweryfikowana (patrz komentarz
# niżej), ale WARTO sprawdzić samemu: wklej FEN na lichess.org/analysis
# FEN: 7k/6pp/5N2/8/3Q4/8/8/1K6 w - - 0 1
# Rozwiązanie: Qd4-d8# (król na h8 jest zablokowany własnymi pionkami g7/h7,
# a pole g8 kryje skoczek f6 — to jedyna dostępna ucieczka).
POZYCJA_SZACHOWA = {
    "h8": "♚", "g7": "♟", "h7": "♟",
    "b1": "♔", "d4": "♕", "f6": "♘",
}

# ETAPY — każdy daje JEDNĄ cyfrę kodu do sejfu, ale cyfry pokazują się
# dopiero na ekranie końcowym, po rozwiązaniu WSZYSTKIEGO.
ETAPY = [
    {
        "klucz": "gra",
        "tytul": {"pl": "🖤 Refleks", "en": "🖤 Reflexes"},
        "typ": "gra",
        "opis": {
            "pl": "Złap WSZYSTKIE kolorowe serca w każdym z 3 poziomów. Uważaj na czarne — jedna pomyłka i wracasz na początek poziomu.",
            "en": "Catch ALL the colored hearts in each of the 3 levels. Watch out for black ones — one mistake and you restart the level.",
        },
        "odpowiedz": KOD_GRY,
        "cyfra": "7",
    },
    {
        "klucz": "quiz",
        "tytul": {"pl": "💭 Ile mnie znasz?", "en": "💭 How well do you know me?"},
        "typ": "quiz",
        "prog": 1.0,  # 1.0 = wymagane 100% poprawnych odpowiedzi
        "pytania": [
            {
                "pytanie": "UZUPEŁNIJ np.: W jakim mieście był nasz pierwszy wspólny wyjazd?",
                "opcje": ["UZUPEŁNIJ opcję A", "UZUPEŁNIJ opcję B", "UZUPEŁNIJ opcję C"],
                "poprawna": 0,
            },
            {
                # Uwaga: wiek Zoe wg lore LoL jest niejednoznaczny między źródłami
                # (różne wiki podają 1398-1548 lat / "ponad tysiąc lat" / inne ramy) —
                # dopisz dokładną liczbę/opcje, które Ty uznajesz za poprawne.
                "pytanie": "Ile lat (wg lore) ma Zoe z League of Legends?",
                "opcje": ["UZUPEŁNIJ — Twoja poprawna wersja", "UZUPEŁNIJ opcję B", "UZUPEŁNIJ opcję C"],
                "poprawna": 0,
            },
            {
                "pytanie": "UZUPEŁNIJ kolejne pytanie o Was...",
                "opcje": ["Opcja A", "Opcja B", "Opcja C"],
                "poprawna": 1,
            },
            # dodaj tyle pytań ile chcesz — po prostu kopiuj wzór powyżej
        ],
        "cyfra": "3",
    },
    {
        "klucz": "jezyk",
        "tytul": {"pl": "🐦 Po ptakach", "en": "🐦 Po ptakach"},
        "typ": "haslo",
        # Ta zagadka jest o polskim idiomie, więc treść zostaje po polsku
        # niezależnie od wybranego języka aplikacji.
        "tresc": (
            "### AFTER BIRDS\n\n"
            "To nie jest prawdziwy angielski zwrot... a jednak coś powinno Ci "
            "zaświtać, jeśli przetłumaczysz to na nasze, słowo w słowo.\n\n"
            "Wpisz to polskie wyrażenie (dwa słowa):"
        ),
        "odpowiedz": "po ptakach",
        "cyfra": "9",
    },
    {
        "klucz": "wordle",
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
        "cyfra": "1",
    },
    {
        "klucz": "irl",
        "tytul": {"pl": "📍 Wyprawa", "en": "📍 The trip"},
        "typ": "haslo",
        "tresc": {
            "pl": "UZUPEŁNIJ: opisz konkretne miejsce i co ma tam znaleźć / sprawdzić.",
            "en": "FILL IN: describe a specific place and what she needs to find / check there.",
        },
        "odpowiedz": "UZUPEŁNIJ",
        "cyfra": "5",
    },
    {
        "klucz": "data",
        "tytul": {"pl": "📅 Dokładna data", "en": "📅 The exact date"},
        "typ": "data",
        "tresc": {
            "pl": "Jaka jest dokładna data, kiedy pierwszy raz jechałaś ze mną samochodem?",
            "en": "What's the exact date of the first time you rode in a car with me?",
        },
        "data": date(2026, 2, 24),
        "jedna_proba": True,
        "cyfra": "6",
    },
    {
        "klucz": "szachy",
        "tytul": {"pl": "♟️ Szachy", "en": "♟️ Chess"},
        "typ": "szachy",
        "tresc": {
            "pl": "Białe zaczynają. Znajdź ruch, który wymusza mata.",
            "en": "White to move. Find the move that forces checkmate.",
        },
        "pozycja": POZYCJA_SZACHOWA,
        "odpowiedz": "d4d8",
        "cyfra": "8",
    },
    {
        "klucz": "dron",
        "tytul": {"pl": "🚁 Dron", "en": "🚁 Drone"},
        "typ": "dron",
        "opis": {
            "pl": "Steruj dronem — stukaj / klikaj, żeby wznieść się w górę. Przeleć przez wszystkie bramki bez rozbicia. Kod pojawi się po osiągnięciu celu.",
            "en": "Fly the drone — tap / click to rise. Get through all the gates without crashing. The code appears once you hit the target.",
        },
        "odpowiedz": KOD_DRONA,
        "cyfra": "4",
    },
    {
        "klucz": "zaba",
        "tytul": {"pl": "🐸 Żaba", "en": "🐸 Frog"},
        "typ": "zaba",
        "opis": {
            "pl": "Steruj żabą — stukaj / klikaj, żeby skoczyła. Przeskocz przez wszystkie kolce, nie wpadnij na żaden. Kod pojawi się po osiągnięciu celu.",
            "en": "Control the frog — tap / click to jump. Hop over all the spikes without hitting one. The code appears once you hit the target.",
        },
        "odpowiedz": KOD_ZABY,
        "cyfra": "2",
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
        "zle_sprobuj": "To nie to. Spróbuj jeszcze raz.",
        "zle_jedna_proba": "To nie ta data. Ta zagadka jest już zamknięta — była tylko jedna próba.",
        "wybierz_date": "Wybierz datę:",
        "jedna_proba_info": "⚠️ Masz tylko JEDNĄ próbę — wybierz uważnie.",
        "wybierz_najpierw": "Najpierw wybierz datę.",
        "poprawnych": "Poprawnych",
        "twoj_ruch": "Twój ruch:",
        "format_ruchu": "Wpisz ruch jako pole-startowe + pole-docelowe, np. `e2e4`.",
        "kod_z_gry_info": "Kiedy wygrasz wszystkie 3 poziomy, przepisz kod z gry poniżej:",
        "kod_z_gry_label": "Kod z gry:",
        "zle_kod_gry": "To nie ten kod. Zagraj jeszcze raz i sprawdź uważnie!",
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
        "zle_sprobuj": "Not quite. Try again.",
        "zle_jedna_proba": "Wrong date. This puzzle is now locked — you only got one attempt.",
        "wybierz_date": "Pick a date:",
        "jedna_proba_info": "⚠️ You only get ONE attempt — choose carefully.",
        "wybierz_najpierw": "Pick a date first.",
        "poprawnych": "Correct",
        "twoj_ruch": "Your move:",
        "format_ruchu": "Type your move as start-square + end-square, e.g. `e2e4`.",
        "kod_z_gry_info": "When you beat all 3 levels, type the code from the game below:",
        "kod_z_gry_label": "Code from the game:",
        "zle_kod_gry": "That's not the code. Play again and check carefully!",
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
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; }
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
      <p id="nakladkaOpis">Łap kolorowe serca. Omijaj czarne — jedna pomyłka i zaczynasz poziom od nowa.</p>
      <div id="kodBox" style="display:none;">
        <div id="kodWygrany">__KOD_GRY__</div>
        <p style="opacity:0.7; font-size:13px;">Przepisz ten kod poniżej 👇</p>
      </div>
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
  var kodBox = document.getElementById('kodBox');
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
      gain.gain.exponentialRampToValueAtTime(0.16, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.16);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.16);
    } catch (e) {
      // dźwięk to dodatek — jego brak nie może zepsuć gry
    }
  }

  function startMuzyka(tempoMs) {
    zatrzymajMuzyke();
    var nuty = [220, 220, 277, 220];
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

    el.addEventListener('click', function () { kliknieto(el); });
    el.addEventListener('touchstart', function (e) { e.preventDefault(); kliknieto(el); }, { passive: false });

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
        nakladkaOpis.textContent = 'Twój kod czeka poniżej:';
        kodBox.style.display = 'block';
        nakladkaBtn.style.display = 'none';
      } else {
        var nastepny = aktualnyPoziom + 1;
        nakladkaTytul.textContent = '🎉 Poziom ' + (aktualnyPoziom + 1) + ' ukończony!';
        nakladkaOpis.textContent = opisPoziomu(nastepny);
        kodBox.style.display = 'none';
        nakladkaBtn.style.display = 'inline-block';
        nakladkaBtn.textContent = 'Graj ▶';
        nakladkaBtn.onclick = function () { inicjujDzwiek(); startPoziom(nastepny); };
      }
    } else {
      nakladkaTytul.textContent = powod === 'czarne' ? '🖤 To było czarne serce...' : '💔 Serduszko uciekło...';
      nakladkaOpis.textContent = 'Trzeba złapać wszystkie, bez pomyłek. Spróbuj ponownie.';
      kodBox.style.display = 'none';
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
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; }
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
    <span>🚁 Dron</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="wynikNaEkranie">0</div>
    <div id="dron">🚁</div>
    <div id="nakladka">
      <h2 id="nakladkaTytul">Dron</h2>
      <p id="nakladkaOpis">Stukaj / klikaj, żeby wznieść drona. Przeleć przez WSZYSTKIE bramki, nie rozbij się.</p>
      <div id="kodBox" style="display:none;">
        <div id="kodWygrany">__KOD_DRONA__</div>
        <p style="opacity:0.7; font-size:13px;">Przepisz ten kod poniżej 👇</p>
      </div>
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
  var kodBox = document.getElementById('kodBox');
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
  }

  function zakonczGre(wygrana) {
    trwa = false;
    przeszkody.forEach(function (p) { usunPrzeszkode(p); });
    przeszkody = [];
    nakladka.style.display = 'flex';

    if (wygrana) {
      zagrajDzwiek('punkt');
      nakladkaTytul.textContent = '🎉 Udało się!';
      nakladkaOpis.textContent = 'Twój kod czeka poniżej:';
      kodBox.style.display = 'block';
      nakladkaBtn.style.display = 'none';
    } else {
      zagrajDzwiek('crash');
      nakladkaTytul.textContent = '💥 Rozbity dron...';
      nakladkaOpis.textContent = 'Wynik: ' + wynik + ' / ' + CEL_WYNIK + '. Spróbuj jeszcze raz.';
      kodBox.style.display = 'none';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
    }
  }

  gra.addEventListener('click', function () { skok(); });
  gra.addEventListener('touchstart', function (e) { e.preventDefault(); skok(); }, { passive: false });

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
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; }
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
    <span>🐸 Żaba</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="podloze"></div>
    <div id="wynikNaEkranie">0</div>
    <div id="zaba">🐸</div>
    <div id="nakladka">
      <h2 id="nakladkaTytul">Żaba</h2>
      <p id="nakladkaOpis">Stukaj / klikaj, żeby żaba skoczyła. Przeskocz WSZYSTKIE kolce, nie wpadnij na żaden.</p>
      <div id="kodBox" style="display:none;">
        <div id="kodWygrany">__KOD_ZABY__</div>
        <p style="opacity:0.7; font-size:13px;">Przepisz ten kod poniżej 👇</p>
      </div>
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
  var kodBox = document.getElementById('kodBox');
  var wyciszBtn = document.getElementById('wyciszBtn');

  var ZABA_X = 0.22;
  var ZABA_R = 14;
  var GRAWITACJA = 2200;
  var SILA_SKOKU = -620;
  var PODLOZE_WYSOKOSC = 8;
  var KOLEC_SZEROKOSC = 30;
  var KOLEC_WYSOKOSC = 35;
  var TOLERANCJA_KOLIZJI = 3;
  var PREDKOSC_START = 220;
  var ODSTEP_SPAWN_START = 1.8;
  var CEL_WYNIK = 20;

  var zabaDol = 0;
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

  function skok() {
    if (!trwa || !naZiemi) return;
    zabaVY = SILA_SKOKU;
    naZiemi = false;
    zagrajDzwiek('skok');
  }

  function usunPrzeszkode(p) {
    if (p.el.parentNode) p.el.remove();
  }

  function stworzPrzeszkode(szer) {
    var liczbaKolcow = Math.random() < 0.55 ? 1 : (Math.random() < 0.8 ? 2 : 3);
    var szerokoscCalkowita = liczbaKolcow * KOLEC_SZEROKOSC;

    var kontener = document.createElement('div');
    kontener.className = 'przeszkoda-kontener';
    kontener.style.width = szerokoscCalkowita + 'px';
    kontener.style.left = (szer + 20) + 'px';

    for (var i = 0; i < liczbaKolcow; i++) {
      var kolec = document.createElement('div');
      kolec.className = 'kolec';
      kolec.style.left = (i * KOLEC_SZEROKOSC) + 'px';
      kontener.appendChild(kolec);
    }

    gra.appendChild(kontener);
    return { x: szer + 20, szerokosc: szerokoscCalkowita, el: kontener, minieta: false };
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

  function petla(czas) {
    if (!trwa) { czasOstatni = null; return; }
    if (czasOstatni === null) czasOstatni = czas;
    var dt = Math.min((czas - czasOstatni) / 1000, 0.05);
    czasOstatni = czas;

    var szer = gra.clientWidth;
    var wys = gra.clientHeight;
    var groundY = wys - PODLOZE_WYSOKOSC;

    zabaVY += GRAWITACJA * dt;
    zabaDol += zabaVY * dt;
    if (zabaDol >= groundY) {
      zabaDol = groundY;
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
      przeszkody.push(stworzPrzeszkode(szer));
    }

    var zabaXpx = szer * ZABA_X;

    for (var i = przeszkody.length - 1; i >= 0; i--) {
      var p = przeszkody[i];
      p.x -= predkoscAktualna * dt;
      p.el.style.left = p.x + 'px';

      var zabaLewa = zabaXpx - ZABA_R;
      var zabaPrawa = zabaXpx + ZABA_R;
      if (zabaPrawa > p.x && zabaLewa < p.x + p.szerokosc) {
        if (zabaDol > groundY - KOLEC_WYSOKOSC + TOLERANCJA_KOLIZJI) {
          zakonczGre(false);
          return;
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

      if (p.x < -200) {
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
    zabaVY = 0;
    naZiemi = true;
    czasOdSpawnu = 0;
    czasOstatni = null;
    nakladka.style.display = 'none';
    trwa = true;
    rysuj();
    requestAnimationFrame(petla);
  }

  function zakonczGre(wygrana) {
    trwa = false;
    przeszkody.forEach(function (p) { usunPrzeszkode(p); });
    przeszkody = [];
    nakladka.style.display = 'flex';

    if (wygrana) {
      zagrajDzwiek('punkt');
      nakladkaTytul.textContent = '🎉 Udało się!';
      nakladkaOpis.textContent = 'Twój kod czeka poniżej:';
      kodBox.style.display = 'block';
      nakladkaBtn.style.display = 'none';
    } else {
      zagrajDzwiek('crash');
      nakladkaTytul.textContent = '🐸💥 Żaba nie doskoczyła...';
      nakladkaOpis.textContent = 'Wynik: ' + wynik + ' / ' + CEL_WYNIK + '. Spróbuj jeszcze raz.';
      kodBox.style.display = 'none';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); rozpocznijGre(); };
    }
  }

  gra.addEventListener('click', function () { skok(); });
  gra.addEventListener('touchstart', function (e) { e.preventDefault(); skok(); }, { passive: false });

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
    background: linear-gradient(135deg, #e6c15c, #d4af37);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: pojaw 0.9s ease;
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

div.stButton > button {
    background: linear-gradient(135deg, #e6c15c, #d4af37);
    color: #16130a;
    border: none;
    border-radius: 30px;
    padding: 0.55rem 1.4rem;
    font-weight: 700;
    transition: all 0.25s ease;
    width: 100%;
}
div.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 0 18px rgba(212,175,55,0.55);
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4ade80, #22c55e) !important;
    color: #062e14 !important;
}
div.stButton > button:disabled {
    opacity: 0.45;
    background: #333 !important;
    color: #999 !important;
}

.stTextInput input {
    border-radius: 12px !important;
    border: 1px solid #d4af37 !important;
    background: #1a1a2e !important;
    color: #f5f5f0 !important;
}

.stProgress > div > div {
    background-image: linear-gradient(135deg, #e6c15c, #d4af37);
}

[data-testid="stExpander"] {
    border: 1px solid rgba(212,175,55,0.35);
    border-radius: 12px;
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
        f"<div style='text-align:center;'><svg width='{rozmiar}' height='{wysokosc}' "
        f"viewBox='0 0 120 150'>{widoczne}</svg></div>",
        unsafe_allow_html=True,
    )


def pokaz_szachownice(pozycja):
    kolumny = "abcdefgh"
    wiersze = "87654321"
    komorki = []
    for wiersz_znak in wiersze:
        rank_idx = int(wiersz_znak) - 1
        for kolumna in kolumny:
            file_idx = ord(kolumna) - ord("a")
            pole = kolumna + wiersz_znak
            ciemne = (file_idx + rank_idx) % 2 == 0
            tlo = "#7a5c3e" if ciemne else "#e8d9b5"
            figura = pozycja.get(pole, "")
            komorki.append(
                f"<div style='background:{tlo}; display:flex; align-items:center; "
                f"justify-content:center; font-size:1.6rem;'>{figura}</div>"
            )
    siatka = "".join(komorki)
    st.markdown(
        "<div style='display:grid; grid-template-columns:repeat(8,1fr); "
        "grid-template-rows:repeat(8,2.4rem); max-width:340px; margin:0.5rem auto; "
        f"border:2px solid #d4af37; border-radius:8px; overflow:hidden;'>{siatka}</div>",
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
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
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
    st.markdown(tt(etap_dane.get("opis", "")))

    html = (
        SZABLON_GRY
        .replace("__POZIOMY_JSON__", json.dumps(POZIOMY_GRY))
        .replace("__KOD_GRY__", str(KOD_GRY))
    )
    components.html(html, height=520, scrolling=False)

    st.caption(t("kod_z_gry_info"))
    wpisane = st.text_input(t("kod_z_gry_label"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error(t("zle_kod_gry"))
        return False
    return None


def renderuj_dron(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane.get("opis", "")))

    html = SZABLON_DRONA.replace("__KOD_DRONA__", str(KOD_DRONA))
    components.html(html, height=520, scrolling=False)

    st.caption(t("kod_z_gry_info"))
    wpisane = st.text_input(t("kod_z_gry_label"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error(t("zle_kod_gry"))
        return False
    return None


def renderuj_zaba(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane.get("opis", "")))

    html = SZABLON_ZABY.replace("__KOD_ZABY__", str(KOD_ZABY))
    components.html(html, height=520, scrolling=False)

    st.caption(t("kod_z_gry_info"))
    wpisane = st.text_input(t("kod_z_gry_label"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error(t("zle_kod_gry"))
        return False
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
    wybrana = st.date_input(t("wybierz_date"), key=f"data_{klucz}", value=None, format="DD.MM.YYYY")
    if st.button(t("zatwierdz"), key=f"btn_{klucz}"):
        if wybrana is None:
            st.warning(t("wybierz_najpierw"))
            return None
        if wybrana == etap_dane["data"]:
            return True
        st.error(t("zle_jedna_proba"))
        return False
    return None


def renderuj_szachy(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))
    pokaz_szachownice(etap_dane["pozycja"])
    st.caption(t("format_ruchu"))
    wpisane = st.text_input(t("twoj_ruch"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        czyste = wpisane.strip().lower().replace(" ", "")
        if czyste == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


# ======================================================================
# EKRANY
# ======================================================================

def pokaz_powitanie():
    st.markdown("<div class='zamek-ikona'>🔒</div>", unsafe_allow_html=True)

    kolumny = st.columns(2)
    with kolumny[0]:
        if st.button("🇵🇱 Polski", key="jezyk_pl"):
            st.session_state.jezyk = "pl"
            st.rerun()
    with kolumny[1]:
        if st.button("🇬🇧 English", key="jezyk_en"):
            st.session_state.jezyk = "en"
            st.rerun()

    st.markdown(f"<h1 class='tytul'>{tt(POWITANIE_TYTUL)}</h1>", unsafe_allow_html=True)
    st.markdown(tt(WIADOMOSC_POWITALNA))

    if st.button(t("rozpocznij"), key="start_btn"):
        st.session_state.ekran = "menu"
        st.session_state.czas_startu = time.time()
        zapisz_postep()
        st.rerun()

    with st.expander(t("wznow_naglowek")):
        kod_wznow = st.text_input(t("kod_label"), key="wznow_input")
        if st.button(t("wznow_btn"), key="wznow_btn2"):
            if wznow_z_kodu(kod_wznow):
                st.success(t("wznow_ok"))
            else:
                st.error(t("nie_rozpoznaje"))


def pokaz_menu():
    st.markdown(f"<h1 class='tytul'>{t('menu_tytul')}</h1>", unsafe_allow_html=True)
    rysuj_wisielca(st.session_state.bledy_wisielec)

    kolumny = st.columns(2)
    for i, etap_dane in enumerate(ETAPY):
        klucz = etap_dane["klucz"]
        rozwiazany = klucz in st.session_state.rozwiazane
        nieudany = klucz in st.session_state.nieudane
        prefiks = "✅ " if rozwiazany else ("🔒 " if nieudany else "")
        etykieta = prefiks + tt(etap_dane["tytul"])
        with kolumny[i % 2]:
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
    elif typ == "quiz":
        wynik = renderuj_quiz(etap_dane)
    elif typ == "gra":
        wynik = renderuj_gra(etap_dane)
    elif typ == "dron":
        wynik = renderuj_dron(etap_dane)
    elif typ == "zaba":
        wynik = renderuj_zaba(etap_dane)
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

    kod_koncowy = "".join(str(e["cyfra"]) for e in ETAPY)
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
